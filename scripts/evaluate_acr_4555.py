#!/usr/bin/env python3
"""ACR 4555 full evaluation script (canonical eval command from AGENTS.md).

Mirrors the admin "match test center" pipeline:
  source_modality = MODALITY_NORMALIZATION(raw)
  effective_modality = resolve_effective_modality(text, source)
  engine.match(text, effective)
  review policy applied (routed/compound downgrade)
  matched = num_standard > 0 and tier in (exact, partial, degraded)

Usage:
    .venv/bin/python scripts/evaluate_acr_4555.py
    .venv/bin/python scripts/evaluate_acr_4555.py --snapshot /tmp/base.json
    .venv/bin/python scripts/evaluate_acr_4555.py --compare /tmp/base.json
"""
import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text

from match_service.core.dispatcher import MatchDispatcher
from match_service.core.engine_holder import EngineHolder
from match_service.db import get_engine, get_session_factory
from match_service.engine.modality_resolver import resolve_effective_modality

MATCHED_TIERS = ("exact", "partial", "degraded")
MODALITY_NORMALIZATION = MatchDispatcher.MODALITY_NORMALIZATION


def norm_modality(modality):
    u = (modality or "").upper().strip()
    return MODALITY_NORMALIZATION.get(u, u)


def classify_unmatched(result):
    tier = result.get("tier", "none")
    has_entity = result.get("has_entity")
    if tier == "error":
        return "engine_error", result.get("reason") or "engine exception"
    if tier == "ambiguous":
        reason = result.get("reason") or ""
        if reason == "exact_name_collision":
            return "standard_data_conflict", "standard name collision"
        if reason == "routed_result_requires_review":
            return "modality_route_review", "cross-modality route needs review"
        if reason == "compound_item_incomplete":
            return "parser_ambiguity", "compound item partially matched"
        return "parser_ambiguity", "multi-candidate or residual"
    reason = result.get("reason") or ""
    if reason == "unsupported_modality":
        return "unsupported_modality", "modality unsupported"
    if reason == "excluded_intervention":
        return "excluded_intervention", "interventional procedure"
    if reason == "excluded_non_imaging":
        return "excluded_non_imaging", "non-imaging exam"
    if reason == "standard_lib_gap":
        return "standard_lib_gap", "entities parsed but no standard"
    if reason == "lexicon_gap":
        return "lexicon_gap", "no medical entity parsed"
    if reason == "engine_not_ready":
        return "engine_error", "keyword engine not ready"
    if has_entity is None:
        return "unmatchable_by_design", "unmatchable by design"
    if has_entity:
        return "standard_lib_gap", "entities parsed but no standard"
    return "lexicon_gap", "no medical entity parsed"


def extract_standards(result):
    out = []
    for d in result.get("data", []) or []:
        for s in d.get("standard") or []:
            out.append({"code": s.get("code"), "name": s.get("name")})
    return out


async def run_eval(engine, session_factory):
    async with session_factory() as session:
        rows = (await session.execute(text(
            "SELECT id, name_zh, modality FROM procedure_dictionary "
            "WHERE is_active = true ORDER BY id"
        ))).fetchall()
    results = []
    for pid, name, mod in rows:
        name = name or ""
        source = norm_modality(mod)
        effective = resolve_effective_modality(name, source)
        text_routed = effective != source
        try:
            r = engine.match(name, effective)
        except Exception as e:
            r = {"tier": "error", "num_standard": 0, "data": [],
                 "reason": "exc:" + type(e).__name__}
        r.setdefault("effective_modality", effective)
        MatchDispatcher._apply_result_review_policy(
            r, name, effective, text_routed, source)
        tier = r.get("tier", "none")
        matched = r.get("num_standard", 0) > 0 and tier in MATCHED_TIERS
        reason_code = None
        detail = None
        if not matched:
            reason_code, detail = classify_unmatched(r)
        results.append({
            "pid": pid,
            "name": name,
            "modality": (mod or "").upper(),
            "effective_modality": effective,
            "matched": matched,
            "tier": tier,
            "reason": reason_code,
            "detail": detail,
            "standards": extract_standards(r),
        })
    return results


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=str, help="save snapshot json path")
    parser.add_argument("--compare", type=str, help="compare with snapshot json")
    parser.add_argument("--limit", type=int, default=0, help="only first N items (debug)")
    args = parser.parse_args()

    holder = EngineHolder()
    await holder.initialize()
    engine = holder.match_engine
    db = get_engine()
    factory = get_session_factory()

    results = await run_eval(engine, factory)
    await holder.dispose()
    await db.dispose()

    if args.limit and args.limit < len(results):
        results = results[:args.limit]

    total = len(results)
    matched = [r for r in results if r["matched"]]
    unmatched = [r for r in results if not r["matched"]]

    print("=" * 72)
    print("ACR 4555 eval | rule_version: " + str(holder.rule_version))
    print("=" * 72)
    rate = len(matched) / total * 100 if total else 0
    print("total: %d | matched: %d (%.2f%%) | unmatched: %d (%.2f%%)"
          % (total, len(matched), rate, len(unmatched), 100 - rate))
    print("")
    print("unmatched by reason:")
    c = Counter(r["reason"] for r in unmatched)
    for k, v in c.most_common():
        print("  %s: %d" % (k, v))
    print("")
    print("unmatched by modality:")
    c2 = Counter(r["modality"] for r in unmatched)
    for k, v in c2.most_common():
        print("  %s: %d" % (k, v))

    if args.snapshot:
        p = Path(args.snapshot)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"rule_version": holder.rule_version, "results": results},
                      f, ensure_ascii=False)
        print("")
        print("snapshot saved: " + args.snapshot)

    if args.compare:
        with open(args.compare, encoding="utf-8") as f:
            base = json.load(f)["results"]
        base_by_pid = {r["pid"]: r for r in base}
        regressions = []
        improvements = []
        for r in results:
            br = base_by_pid.get(r["pid"])
            if br is None:
                continue
            if br["matched"] and not r["matched"]:
                regressions.append((r["pid"], r["name"], br["tier"], r["tier"],
                                    br["reason"], r["reason"]))
            elif not br["matched"] and r["matched"]:
                improvements.append((r["pid"], r["name"], br["reason"], r["tier"]))
        print("")
        print("=" * 72)
        print("compare vs " + args.compare)
        print("  regressions (matched->unmatched): %d" % len(regressions))
        for pid, name, bt, ct, br, cr in regressions[:30]:
            print("    %s %s | %s->%s | %s->%s" % (pid, name, bt, ct, br, cr))
        print("  improvements (unmatched->matched): %d" % len(improvements))
        for pid, name, br, ct in improvements[:40]:
            print("    %s %s | %s->%s" % (pid, name, br, ct))
        print("  net change: %d" % (len(improvements) - len(regressions)))


if __name__ == "__main__":
    asyncio.run(main())

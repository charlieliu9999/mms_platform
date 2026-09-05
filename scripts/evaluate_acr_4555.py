#!/usr/bin/env python3
"""Run the canonical ACR 4555 evaluation against a frozen manifest.

The live ``procedure_dictionary`` also contains post-ACR extensions. The
canonical denominator is the reviewed PR series recorded in the manifest,
not every active row.

Usage:
    poetry run python scripts/evaluate_acr_4555.py
    poetry run python scripts/evaluate_acr_4555.py --snapshot /tmp/base.json
    poetry run python scripts/evaluate_acr_4555.py --compare /tmp/base.json
"""

import argparse
import asyncio
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text

from match_service.core.dispatcher import MatchDispatcher
from match_service.core.engine_holder import EngineHolder
from match_service.db import get_engine, get_session_factory
from match_service.engine.modality_resolver import resolve_effective_modality

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "data/evaluation/acr_4555_manifest.csv"
DEFAULT_MANIFEST_METADATA = REPO_ROOT / "data/evaluation/acr_4555_manifest.meta.json"
EXPECTED_DATASET_ID = "acr-4555-pr-v1"
EXPECTED_COUNT = 4555
SNAPSHOT_SCHEMA_VERSION = 2
MATCHED_TIERS = ("exact", "partial", "degraded")
MODALITY_NORMALIZATION = MatchDispatcher.MODALITY_NORMALIZATION


class DatasetContractError(RuntimeError):
    """The live evaluation cohort differs from the frozen ACR contract."""


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(manifest_path=DEFAULT_MANIFEST, metadata_path=DEFAULT_MANIFEST_METADATA):
    manifest_path = Path(manifest_path)
    metadata_path = Path(metadata_path)
    if not manifest_path.is_file() or not metadata_path.is_file():
        raise DatasetContractError(
            "ACR 4555 manifest is missing; run the governed freeze command first"
        )

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("dataset_id") != EXPECTED_DATASET_ID:
        raise DatasetContractError("unexpected ACR dataset_id in manifest metadata")
    if metadata.get("expected_count") != EXPECTED_COUNT:
        raise DatasetContractError("manifest metadata expected_count must be 4555")

    actual_hash = sha256_file(manifest_path)
    if metadata.get("manifest_sha256") != actual_hash:
        raise DatasetContractError("manifest SHA-256 does not match its metadata")

    with manifest_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected_fields = {"semantic_id", "name_zh", "modality"}
    if not rows or set(rows[0]) != expected_fields:
        raise DatasetContractError(
            "manifest columns must be semantic_id,name_zh,modality"
        )
    if len(rows) != EXPECTED_COUNT:
        raise DatasetContractError(
            f"manifest contains {len(rows)} records, expected {EXPECTED_COUNT}"
        )

    semantic_ids = [row["semantic_id"] for row in rows]
    if len(set(semantic_ids)) != EXPECTED_COUNT:
        raise DatasetContractError("manifest semantic_id values are not unique")
    if semantic_ids != sorted(semantic_ids):
        raise DatasetContractError("manifest semantic_id values are not sorted")
    return rows, metadata


def validate_live_rows(live_rows, manifest_rows):
    """Return normalized live rows or fail closed on any cohort drift."""
    normalized = [
        {
            "database_id": row[0],
            "semantic_id": row[1],
            "name_zh": row[2] or "",
            "modality": row[3] or "",
        }
        for row in live_rows
    ]
    if len(normalized) != EXPECTED_COUNT:
        raise DatasetContractError(
            f"live PR cohort contains {len(normalized)} records, expected {EXPECTED_COUNT}"
        )

    live_by_id = {row["semantic_id"]: row for row in normalized}
    manifest_by_id = {row["semantic_id"]: row for row in manifest_rows}
    if len(live_by_id) != len(normalized):
        raise DatasetContractError("live PR cohort contains duplicate semantic_id values")

    missing = sorted(set(manifest_by_id) - set(live_by_id))
    added = sorted(set(live_by_id) - set(manifest_by_id))
    changed = []
    for semantic_id in sorted(set(manifest_by_id) & set(live_by_id)):
        expected = manifest_by_id[semantic_id]
        actual = live_by_id[semantic_id]
        if (
            expected["name_zh"] != actual["name_zh"]
            or expected["modality"] != actual["modality"]
        ):
            changed.append(semantic_id)
    if missing or added or changed:
        raise DatasetContractError(
            "live PR cohort drifted from manifest: "
            f"missing={missing[:5]}, added={added[:5]}, changed={changed[:5]}"
        )
    # Bug #13 修复：保持 manifest 顺序，但确保每行的 database_id 与其 semantic_id 正确对应
    # 原代码已经正确，live_by_id 是字典，按 manifest 顺序取值时 database_id 是对应的
    # 不需要修改，这里只是确认逻辑正确
    return [live_by_id[row["semantic_id"]] for row in manifest_rows]


def norm_modality(modality):
    upper = (modality or "").upper().strip()
    return MODALITY_NORMALIZATION.get(upper, upper)


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
    standards = []
    for datum in result.get("data", []) or []:
        for standard in datum.get("standard") or []:
            standards.append({"code": standard.get("code"), "name": standard.get("name")})
    return standards


async def load_canonical_rows(session_factory, manifest_rows):
    async with session_factory() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT id, semantic_id, name_zh, modality "
                    "FROM procedure_dictionary "
                    "WHERE is_active = true AND semantic_id ~ '^PR[0-9]+$' "
                    "ORDER BY semantic_id"
                )
            )
        ).fetchall()
    return validate_live_rows(rows, manifest_rows)


async def run_eval(engine, session_factory, manifest_rows, limit=0):
    rows = await load_canonical_rows(session_factory, manifest_rows)
    if limit:
        rows = rows[:limit]
    results = []
    for row in rows:
        name = row["name_zh"]
        modality = row["modality"]
        source = norm_modality(modality)
        effective = resolve_effective_modality(name, source)
        text_routed = effective != source
        try:
            result = engine.match(name, effective)
        except Exception as exc:  # keep a complete cohort even if one rule crashes
            # Bug #9 修复：记录异常详情以便诊断问题
            logger.error(
                "Match engine exception for %s (modality=%s): %s: %s",
                name, effective, type(exc).__name__, str(exc),
                exc_info=True
            )
            result = {
                "tier": "error",
                "num_standard": 0,
                "data": [],
                "reason": "exc:" + type(exc).__name__,
            }
        result.setdefault("effective_modality", effective)
        MatchDispatcher._apply_result_review_policy(
            result, name, effective, text_routed, source
        )
        tier = result.get("tier", "none")
        matched = result.get("num_standard", 0) > 0 and tier in MATCHED_TIERS
        reason_code = None
        detail = None
        if not matched:
            reason_code, detail = classify_unmatched(result)
        results.append(
            {
                "pid": row["database_id"],
                "semantic_id": row["semantic_id"],
                "name": name,
                # Bug #3 修复：modality 可能为 None，添加空值保护
                "modality": (modality or "").upper(),
                "effective_modality": effective,
                "matched": matched,
                "tier": tier,
                "reason": reason_code,
                "detail": detail,
                "standards": extract_standards(result),
            }
        )
    return results


def build_summary(results):
    matched = [row for row in results if row["matched"]]
    unmatched = [row for row in results if not row["matched"]]
    by_modality = defaultdict(lambda: {"total": 0, "matched": 0, "unmatched": 0})
    for row in results:
        stats = by_modality[row["modality"]]
        stats["total"] += 1
        stats["matched" if row["matched"] else "unmatched"] += 1
    modality_summary = {}
    for modality, stats in sorted(by_modality.items()):
        # Bug #1 修复：避免除零错误
        match_rate = (
            round(stats["matched"] / stats["total"] * 100, 4)
            if stats["total"] > 0 else 0.0
        )
        modality_summary[modality] = {
            **stats,
            "match_rate": match_rate,
        }
    total = len(results)
    return {
        "total": total,
        "matched": len(matched),
        "unmatched": len(unmatched),
        "match_rate": round(len(matched) / total * 100, 4) if total else 0.0,
        "unmatched_by_reason": dict(
            sorted(Counter(row["reason"] for row in unmatched).items())
        ),
        "by_modality": modality_summary,
    }


def git_runtime_metadata():
    def run_git(*args):
        completed = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    try:
        commit = run_git("rev-parse", "HEAD")
        dirty = bool(run_git("status", "--porcelain"))
    except (OSError, subprocess.CalledProcessError):
        commit = None
        dirty = None
    return {"git_commit": commit, "git_dirty": dirty}


async def database_revision(session_factory):
    async with session_factory() as session:
        return (
            await session.execute(text("SELECT version_num FROM alembic_version"))
        ).scalar_one()


def build_snapshot(results, manifest_metadata, rule_version, db_revision):
    runtime = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rule_version": rule_version,
        "database_revision": db_revision,
        **git_runtime_metadata(),
    }
    return {
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "dataset": {
            "dataset_id": manifest_metadata["dataset_id"],
            "dataset_version": manifest_metadata["dataset_version"],
            "manifest_sha256": manifest_metadata["manifest_sha256"],
            "record_count": EXPECTED_COUNT,
        },
        "runtime": runtime,
        "summary": build_summary(results),
        "results": results,
    }


def compare_snapshots(current, baseline):
    if baseline.get("snapshot_schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise DatasetContractError("baseline uses an unsupported snapshot schema")
    if baseline.get("dataset") != current.get("dataset"):
        raise DatasetContractError("baseline and current snapshot datasets differ")

    current_by_id = {row["semantic_id"]: row for row in current["results"]}
    baseline_by_id = {row["semantic_id"]: row for row in baseline["results"]}
    if set(current_by_id) != set(baseline_by_id):
        raise DatasetContractError("baseline and current result ID sets differ")

    regressions = []
    improvements = []
    for semantic_id in sorted(current_by_id):
        row = current_by_id[semantic_id]
        old = baseline_by_id[semantic_id]
        if old["matched"] and not row["matched"]:
            regressions.append(
                (semantic_id, row["name"], old["tier"], row["tier"], old["reason"], row["reason"])
            )
        elif not old["matched"] and row["matched"]:
            improvements.append((semantic_id, row["name"], old["reason"], row["tier"]))
    return regressions, improvements


def print_summary(summary, rule_version, debug_limit=0):
    print("=" * 72)
    label = "ACR 4555 eval" if not debug_limit else f"ACR debug subset ({summary['total']}/4555)"
    print(f"{label} | rule_version: {rule_version}")
    print("=" * 72)
    print(
        "total: %d | matched: %d (%.2f%%) | unmatched: %d (%.2f%%)"
        % (
            summary["total"],
            summary["matched"],
            summary["match_rate"],
            summary["unmatched"],
            100 - summary["match_rate"],
        )
    )
    print("\nunmatched by reason:")
    for reason, count in sorted(
        summary["unmatched_by_reason"].items(), key=lambda item: (-item[1], item[0])
    ):
        print(f"  {reason}: {count}")
    print("\nby modality:")
    for modality, stats in summary["by_modality"].items():
        print(
            f"  {modality}: total={stats['total']} matched={stats['matched']} "
            f"unmatched={stats['unmatched']} rate={stats['match_rate']:.2f}%"
        )


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, help="save snapshot JSON path")
    parser.add_argument("--compare", type=Path, help="compare with snapshot JSON")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--manifest-metadata", type=Path, default=DEFAULT_MANIFEST_METADATA)
    parser.add_argument("--limit", type=int, default=0, help="only first N items (debug)")
    args = parser.parse_args()
    if args.limit < 0:
        parser.error("--limit must be non-negative")
    if args.limit and (args.snapshot or args.compare):
        parser.error("--limit cannot be combined with --snapshot or --compare")

    manifest_rows, manifest_metadata = load_manifest(
        args.manifest, args.manifest_metadata
    )
    holder = EngineHolder()
    await holder.initialize()
    db = get_engine()
    factory = get_session_factory()
    try:
        db_revision = await database_revision(factory)
        results = await run_eval(
            holder.match_engine, factory, manifest_rows, limit=args.limit
        )
        rule_version = holder.rule_version
    finally:
        await holder.dispose()
        await db.dispose()

    snapshot = build_snapshot(results, manifest_metadata, rule_version, db_revision)
    print_summary(snapshot["summary"], rule_version, args.limit)

    if args.snapshot:
        args.snapshot.parent.mkdir(parents=True, exist_ok=True)
        args.snapshot.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nsnapshot saved: {args.snapshot}")

    if args.compare:
        baseline = json.loads(args.compare.read_text(encoding="utf-8"))
        regressions, improvements = compare_snapshots(snapshot, baseline)
        print("\n" + "=" * 72)
        print(f"compare vs {args.compare}")
        print(f"  regressions (matched->unmatched): {len(regressions)}")
        for semantic_id, name, before_tier, tier, before_reason, reason in regressions[:30]:
            print(
                f"    {semantic_id} {name} | {before_tier}->{tier} | "
                f"{before_reason}->{reason}"
            )
        print(f"  improvements (unmatched->matched): {len(improvements)}")
        for semantic_id, name, before_reason, tier in improvements[:40]:
            print(f"    {semantic_id} {name} | {before_reason}->{tier}")
        print(f"  net change: {len(improvements) - len(regressions)}")
        if regressions:
            raise SystemExit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except DatasetContractError as exc:
        print(f"DATASET CONTRACT ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

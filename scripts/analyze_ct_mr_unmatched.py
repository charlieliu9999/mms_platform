#!/usr/bin/env python3
"""CT/MR 未匹配项专项归因分析

对 unmatched_registry 中 status='open' 且模态为 CT/CT-DE/CT-4D/MR 的项目，
逐项重跑 match_engine_v2，按 tier 归因并细分 ambiguous 失败模式。

用法: .venv/bin/python scripts/analyze_ct_mr_unmatched.py
"""
import asyncio
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import asyncpg

DB_DSN = "postgresql://postgres:password@127.0.0.1:15432/acrac_db"
MODALITIES = ("CT", "CT-DE", "CT-4D", "MR")


async def fetch_open_items(conn):
    return await conn.fetch(
        """
        SELECT u.id, u.modality, u.reason_code, p.name_zh, p.name_en
        FROM unmatched_registry u
        JOIN procedure_dictionary p ON p.id = u.procedure_id
        WHERE u.status = 'open' AND u.modality = ANY($1::varchar[])
        ORDER BY u.modality, p.name_zh
        """,
        list(MODALITIES),
    )


async def fetch_standard_items(conn):
    rows = await conn.fetch(
        """
        SELECT item_code, item_name, modality, body_part_l2, scan_method
        FROM standard_check_items WHERE is_active = true
        """
    )
    by_mod = defaultdict(list)
    for r in rows:
        by_mod[r["modality"]].append(r["item_name"])
    return by_mod


def classify_ambiguous(name: str) -> str:
    """对 ambiguous 项按文本特征细分失败模式"""
    if re.search(r"CE-MR[AV]|MRA|MRV|CTA|CTV", name):
        return "血管成像(MRA/CTA)标准项缺口"
    if "[" in name and "]" in name:
        return "方括号修饰语"
    if re.search(r"Haste|Trufi|FLAIR|DIR|MPR|VR|三维|心电门控|UHR|Quantum|薄层|功能|波谱|弥散|灌注|SWI|DTI|fMRI", name):
        return "特殊序列/后处理修饰"
    if re.search(r"子宫输卵管|肝胆胰脾|肝胆脾胰|双肾|双髋|双肩", name):
        return "复合部位拆分"
    if "," in name or "、" in name or "+" in name:
        return "多项记录部分失配"
    if re.search(r"平扫\+增强|平扫并增强|增强", name):
        return "增强组合项"
    return "其他"


async def main():
    from match_service.core.engine_holder import EngineHolder

    holder = EngineHolder()
    await holder.initialize()
    engine = holder.match_engine
    print(f"引擎就绪: {engine.is_ready}")

    conn = await asyncpg.connect(DB_DSN)
    items_raw = await fetch_open_items(conn)
    std_by_mod = await fetch_standard_items(conn)
    # registry 存在重复行，按 (modality, name) 去重
    seen, items = set(), []
    for it in items_raw:
        key = (it["modality"], it["name_zh"] or it["name_en"])
        if key in seen:
            continue
        seen.add(key)
        items.append(it)
    print(f"open CT/MR 项: {len(items_raw)} 行 → 去重后 {len(items)} 项\n")

    buckets = defaultdict(list)  # tier -> [(modality, name, reason_code, extra)]
    amb_patterns = defaultdict(list)
    none_detail = defaultdict(list)  # 细分 -> [(mod, name)]

    for it in items:
        name = it["name_zh"] or it["name_en"] or ""
        mod = it["modality"]
        trace = {}
        try:
            res = engine.match(name, mod, trace=trace)
        except Exception as e:  # noqa: BLE001
            buckets["error"].append((mod, name, f"{type(e).__name__}: {e}", ""))
            continue
        tier = res.get("tier", "none")
        reason = res.get("reason", "")
        buckets[tier].append((mod, name, it["reason_code"], reason))
        if tier == "ambiguous":
            amb_patterns[classify_ambiguous(name)].append((mod, name))
        if tier == "none":
            if reason:
                none_detail[f"拦截:{reason}"].append((mod, name))
            elif res.get("has_entity"):
                none_detail["有实体但未命中标准项"].append((mod, name))
            else:
                none_detail["未解析出实体(词库/解析缺口)"].append((mod, name))

    print("=" * 78)
    print("一、引擎重跑 tier 分布（open 项现状）")
    print("=" * 78)
    for tier in ("exact", "partial", "degraded", "ambiguous", "none", "error"):
        rows = buckets.get(tier, [])
        if not rows:
            continue
        mc = Counter(m for m, _, _, _ in rows)
        print(f"\n[{tier}] {len(rows)} 条  模态分布: {dict(mc)}")
        for m, n, rc, extra in rows[:80]:
            suffix = f"  [{extra}]" if extra else ""
            print(f"  {m:<7} {n}  (registry归因: {rc}){suffix}")

    print("\n" + "=" * 78)
    print("一(b)、none 项细分")
    print("=" * 78)
    for cat, rows in sorted(none_detail.items(), key=lambda x: -len(x[1])):
        print(f"\n【{cat}】 {len(rows)} 条")
        for m, n in rows[:40]:
            print(f"  {m:<7} {n}")

    print("\n" + "=" * 78)
    print("二、ambiguous 失败模式细分")
    print("=" * 78)
    for pat, rows in sorted(amb_patterns.items(), key=lambda x: -len(x[1])):
        print(f"\n【{pat}】 {len(rows)} 条")
        for m, n in rows[:15]:
            print(f"  {m:<7} {n}")

    # 三、血管类缺口对照标准库
    print("\n" + "=" * 78)
    print("三、血管成像项 vs 标准库覆盖对照")
    print("=" * 78)
    mr_std = std_by_mod.get("MR", [])
    ct_std = std_by_mod.get("CT", [])
    vessel_pat = re.compile(r"(?:MR|CT)([^,，、\(\)（）]+?)(?:CE-MR[AV]|MRA|MRV|CTA|CTV)")
    missing_vessels = Counter()
    vessel_candidates = list(amb_patterns.get("血管成像(MRA/CTA)标准项缺口", []))
    vessel_candidates += [(m, n) for m, n, _, _ in buckets.get("none", [])]
    for pat_rows in (vessel_candidates,):
        for m, n in pat_rows:
            mt = vessel_pat.match(n)
            if not mt:
                continue
            vessel = mt.group(1)
            pool = mr_std if m.startswith("MR") else ct_std
            hit = [s for s in pool if vessel in s]
            if not hit:
                missing_vessels[(m, vessel)] += 1
    print("标准库中完全无对应条目的血管:")
    for (m, v), c in missing_vessels.most_common(40):
        print(f"  {m:<7} {v}  x{c}")

    await conn.close()
    await holder.dispose()


if __name__ == "__main__":
    asyncio.run(main())

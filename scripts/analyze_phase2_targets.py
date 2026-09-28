"""
分析 Phase 2 优化目标项目
导出 lexicon_gap 和 standard_lib_gap 的详细清单
"""
import sys
import asyncio
import json
from pathlib import Path
from collections import Counter, defaultdict

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from match_service.core.engine_holder import get_engine_holder


async def main():
    # 加载 ACR 4555 评估集（从 CSV manifest）
    manifest_file = Path(__file__).parent.parent / "data/evaluation/acr_4555_manifest.csv"

    cohort = []
    import csv as csv_module
    with open(manifest_file, "r", encoding="utf-8") as f:
        reader = csv_module.DictReader(f)
        for row in reader:
            cohort.append({
                "text": row["name_zh"],  # 修正字段名
                "modality": row["modality"]
            })

    print(f"加载评估集: {len(cohort)} 项")

    # 初始化引擎
    holder = get_engine_holder()
    await holder.initialize()
    engine = holder.match_engine

    # 分类统计
    lexicon_gaps = []
    standard_gaps = []

    for idx, item in enumerate(cohort, 1):
        if idx % 100 == 0:
            print(f"进度: {idx}/{len(cohort)}")

        text = item["text"]
        modality = item.get("modality", "")

        result = engine.match(text, modality)
        reason = result.get("reason", "")

        if reason == "lexicon_gap":
            lexicon_gaps.append({
                "text": text,
                "modality": modality,
                "has_entity": result.get("has_entity", False)
            })
        elif reason == "standard_lib_gap":
            standard_gaps.append({
                "text": text,
                "modality": modality,
                "has_entity": result.get("has_entity", True)
            })

    print(f"\n分析完成")
    print(f"lexicon_gap: {len(lexicon_gaps)} 项")
    print(f"standard_lib_gap: {len(standard_gaps)} 项")

    # 按模态统计 lexicon_gap
    print("\n=== lexicon_gap 按模态分布 ===")
    lex_modality = Counter(item["modality"] for item in lexicon_gaps)
    for modality, count in lex_modality.most_common():
        print(f"  {modality}: {count}")

    # 按模态统计 standard_lib_gap
    print("\n=== standard_lib_gap 按模态分布 ===")
    std_modality = Counter(item["modality"] for item in standard_gaps)
    for modality, count in std_modality.most_common():
        print(f"  {modality}: {count}")

    # US lexicon_gap 高频词汇提取
    print("\n=== US lexicon_gap 样本 (前 20 条) ===")
    us_lexicon = [item for item in lexicon_gaps if item["modality"] == "US"]
    for i, item in enumerate(us_lexicon[:20], 1):
        print(f"  {i}. {item['text']}")

    # DSA lexicon_gap 样本
    print("\n=== DSA lexicon_gap 样本 (前 10 条) ===")
    dsa_lexicon = [item for item in lexicon_gaps if item["modality"] == "DSA"]
    for i, item in enumerate(dsa_lexicon[:10], 1):
        print(f"  {i}. {item['text']}")

    # DR/XR standard_lib_gap 样本
    print("\n=== DR/XR standard_lib_gap 样本 (前 15 条) ===")
    dr_xr_std = [item for item in standard_gaps if item["modality"] in ("DR", "XR")]
    for i, item in enumerate(dr_xr_std[:15], 1):
        print(f"  {i}. [{item['modality']}] {item['text']}")

    # 导出到文件
    output = {
        "lexicon_gap": lexicon_gaps,
        "standard_lib_gap": standard_gaps,
        "summary": {
            "lexicon_gap_total": len(lexicon_gaps),
            "standard_lib_gap_total": len(standard_gaps),
            "lexicon_by_modality": dict(lex_modality),
            "standard_by_modality": dict(std_modality)
        }
    }

    output_file = Path("/tmp/phase2_analysis.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n详细数据已导出到: {output_file}")

    await holder.dispose()


if __name__ == "__main__":
    asyncio.run(main())

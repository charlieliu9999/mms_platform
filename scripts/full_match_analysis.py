#!/usr/bin/env python3
"""
全量数据匹配效果对比分析

对比两次匹配结果，统计改善情况
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from match_service.db import get_session_factory
from match_service.core.engine_holder import get_engine_holder


async def run_full_match_analysis(output_file: str):
    """运行全量数据匹配并保存结果"""
    factory = get_session_factory()
    holder = get_engine_holder()
    await holder.initialize()

    if not holder.is_ready:
        print("❌ 引擎未就绪")
        return

    engine = holder.match_engine

    async with factory() as session:
        # 查询所有检查项目（限制CT/MR/DR模态）
        query = text("""
            SELECT name_zh as item_name, modality
            FROM procedure_dictionary
            WHERE modality IN ('CT', 'MR', 'DR')
            ORDER BY modality, name_zh
        """)

        result = await session.execute(query)
        rows = result.fetchall()

        print(f"开始处理 {len(rows)} 个检查项目...")

        results = []
        tier_stats = {'exact': 0, 'partial': 0, 'degraded': 0, 'ambiguous': 0, 'none': 0}
        modality_stats = {}

        for idx, (item_name, modality) in enumerate(rows, 1):
            if idx % 100 == 0:
                print(f"  进度: {idx}/{len(rows)} ({idx/len(rows)*100:.1f}%)")

            # 执行匹配
            match_result = engine.match(item_name, modality, "V3.8.2")
            tier = match_result.get('tier', 'none')
            num_standard = match_result.get('num_standard', 0)

            # 统计
            tier_stats[tier] = tier_stats.get(tier, 0) + 1
            if modality not in modality_stats:
                modality_stats[modality] = {'exact': 0, 'partial': 0, 'degraded': 0, 'ambiguous': 0, 'none': 0}
            modality_stats[modality][tier] = modality_stats[modality].get(tier, 0) + 1

            results.append({
                'item_name': item_name,
                'modality': modality,
                'tier': tier,
                'num_standard': num_standard,
            })

        # 保存结果
        output_data = {
            'timestamp': datetime.now().isoformat(),
            'engine_version': holder.rule_version,
            'total_items': len(rows),
            'tier_stats': tier_stats,
            'modality_stats': modality_stats,
            'results': results,
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"\n✓ 结果已保存到: {output_file}")
        print(f"\n总体统计:")
        print(f"  总计: {len(rows)} 项")
        for tier, count in tier_stats.items():
            print(f"  {tier}: {count} ({count/len(rows)*100:.1f}%)")

        return output_data


async def compare_results(baseline_file: str, current_file: str):
    """对比两次匹配结果"""
    with open(baseline_file, 'r', encoding='utf-8') as f:
        baseline = json.load(f)

    with open(current_file, 'r', encoding='utf-8') as f:
        current = json.load(f)

    print("=" * 100)
    print("全量数据匹配效果对比分析")
    print("=" * 100)

    print(f"\nBaseline: {baseline.get('timestamp', 'N/A')}")
    print(f"  引擎版本: {baseline.get('engine_version', 'N/A')}")

    print(f"\nCurrent: {current.get('timestamp', 'N/A')}")
    print(f"  引擎版本: {current.get('engine_version', 'N/A')}")

    # 总体对比
    print("\n" + "=" * 100)
    print("总体匹配率对比")
    print("=" * 100)

    baseline_stats = baseline['tier_stats']
    current_stats = current['tier_stats']
    total = baseline['total_items']

    print(f"\n{'Tier':<12} {'Baseline':<15} {'Current':<15} {'变化':<15}")
    print("-" * 60)

    for tier in ['exact', 'partial', 'degraded', 'ambiguous', 'none']:
        b_count = baseline_stats.get(tier, 0)
        c_count = current_stats.get(tier, 0)
        diff = c_count - b_count
        diff_pct = (diff / total * 100) if total > 0 else 0

        b_pct = f"{b_count} ({b_count/total*100:.1f}%)"
        c_pct = f"{c_count} ({c_count/total*100:.1f}%)"
        d_str = f"{diff:+d} ({diff_pct:+.1f}%)" if diff != 0 else "无变化"

        print(f"{tier:<12} {b_pct:<15} {c_pct:<15} {d_str:<15}")

    # 匹配率（exact+partial+degraded）
    baseline_matched = baseline_stats.get('exact', 0) + baseline_stats.get('partial', 0) + baseline_stats.get('degraded', 0)
    current_matched = current_stats.get('exact', 0) + current_stats.get('partial', 0) + current_stats.get('degraded', 0)

    print("-" * 60)
    print(f"{'总匹配率':<12} {baseline_matched/total*100:.1f}% {' '*7} {current_matched/total*100:.1f}% {' '*7} {(current_matched-baseline_matched)/total*100:+.1f}%")

    # 按模态对比
    print("\n" + "=" * 100)
    print("按模态对比")
    print("=" * 100)

    for modality in ['CT', 'MR', 'DR']:
        print(f"\n{modality}:")
        b_mod = baseline['modality_stats'].get(modality, {})
        c_mod = current['modality_stats'].get(modality, {})

        mod_total = sum(b_mod.values())
        if mod_total == 0:
            continue

        for tier in ['exact', 'partial', 'degraded', 'ambiguous', 'none']:
            b_count = b_mod.get(tier, 0)
            c_count = c_mod.get(tier, 0)
            diff = c_count - b_count

            if diff != 0:
                print(f"  {tier}: {b_count} → {c_count} ({diff:+d})")

    # 详细变化分析
    print("\n" + "=" * 100)
    print("详细变化分析（tier变化的项目）")
    print("=" * 100)

    # 构建快速查找字典
    baseline_dict = {(r['item_name'], r['modality']): r for r in baseline['results']}
    current_dict = {(r['item_name'], r['modality']): r for r in current['results']}

    changes = []
    for key, curr in current_dict.items():
        base = baseline_dict.get(key)
        if base and base['tier'] != curr['tier']:
            changes.append({
                'item_name': key[0],
                'modality': key[1],
                'baseline_tier': base['tier'],
                'current_tier': curr['tier'],
                'baseline_num': base['num_standard'],
                'current_num': curr['num_standard'],
            })

    if changes:
        print(f"\n发现 {len(changes)} 个项目的tier发生变化:")

        # 按变化类型分类
        improvements = [c for c in changes if _tier_rank(c['current_tier']) > _tier_rank(c['baseline_tier'])]
        degradations = [c for c in changes if _tier_rank(c['current_tier']) < _tier_rank(c['baseline_tier'])]

        if improvements:
            print(f"\n✅ 改善项 ({len(improvements)}个):")
            for change in improvements[:20]:  # 只显示前20个
                print(f"  {change['modality']}: {change['item_name']}")
                print(f"    {change['baseline_tier']} → {change['current_tier']} (标准项: {change['baseline_num']} → {change['current_num']})")

        if degradations:
            print(f"\n❌ 退化项 ({len(degradations)}个):")
            for change in degradations[:10]:  # 只显示前10个
                print(f"  {change['modality']}: {change['item_name']}")
                print(f"    {change['baseline_tier']} → {change['current_tier']} (标准项: {change['baseline_num']} → {change['current_num']})")
    else:
        print("\n无tier变化的项目")

    print("\n" + "=" * 100)


def _tier_rank(tier: str) -> int:
    """Tier排名（数字越大越好）"""
    ranks = {'exact': 5, 'partial': 4, 'degraded': 3, 'ambiguous': 2, 'none': 1}
    return ranks.get(tier, 0)


async def main():
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  生成基线: python scripts/full_match_analysis.py baseline")
        print("  运行对比: python scripts/full_match_analysis.py compare baseline.json current.json")
        return

    action = sys.argv[1]

    if action == 'baseline':
        output_file = 'match_results_baseline.json'
        await run_full_match_analysis(output_file)

    elif action == 'run':
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'match_results_current.json'
        await run_full_match_analysis(output_file)

    elif action == 'compare':
        if len(sys.argv) < 4:
            print("需要提供baseline和current文件路径")
            return
        baseline_file = sys.argv[2]
        current_file = sys.argv[3]
        await compare_results(baseline_file, current_file)

    else:
        print(f"未知操作: {action}")


if __name__ == "__main__":
    asyncio.run(main())

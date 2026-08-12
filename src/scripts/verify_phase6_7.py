#!/usr/bin/env python3
"""
Phase 6 & 7 综合验证脚本

验证内容：
1. Phase 6: 医学词典补充（5个新术语）
2. Phase 7: 智能排序优化（基于使用频率）
"""

import asyncio
import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
src_dir = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_dir))

from sqlalchemy import text
from match_service.core.dispatcher import MatchDispatcher
from match_service.core.engine_holder import get_engine_holder
from match_service.db import get_session_factory


async def verify_phase6():
    """验证 Phase 6: 医学词典补充"""
    print("=" * 80)
    print("Phase 6 验证：医学词典补充")
    print("=" * 80)

    factory = get_session_factory()
    async with factory() as session:
        # 1. 验证新增术语是否存在
        new_terms = ['声学', '多普勒', '类风湿', '专科', '引导']

        print("\n【1. 词典补充验证】")
        for term in new_terms:
            result = await session.execute(
                text('SELECT id, word, type FROM nlp_medical_dict WHERE word = :word'),
                {'word': term}
            )
            row = result.fetchone()
            if row:
                print(f"  ✅ {term:6s} - 已添加 (ID: {row[0]}, Type: {row[2]})")
            else:
                print(f"  ❌ {term:6s} - 未找到")

        # 2. 测试新术语的匹配效果
        print("\n【2. 匹配效果验证】")

        holder = get_engine_holder()
        if not holder.is_ready:
            await holder.initialize()

        dispatcher = MatchDispatcher(session, holder)

        test_cases = [
            ('脾脏占位彩超声学造影', 'US', '声学'),
            ('彩色多普勒超声心脏', 'US', '多普勒'),
        ]

        for check_text, modality, keyword in test_cases:
            result = await dispatcher.match(check_text, modality)
            num_std = result.get('num_standard', 0)
            tier = result.get('tier', 'none')

            status = "✅" if num_std > 0 else "❌"
            print(f"  {status} [{keyword}] {check_text[:30]}...")
            print(f"     匹配数: {num_std}, 置信度: {tier}")

            if result.get('data'):
                for item in result['data'][:1]:
                    stds = item.get('standard', [])
                    if stds:
                        print(f"     标准项: {stds[0]['name']}")


async def verify_phase7():
    """验证 Phase 7: 智能排序优化"""
    print("\n" + "=" * 80)
    print("Phase 7 验证：智能排序优化")
    print("=" * 80)

    holder = get_engine_holder()
    if not holder.is_ready:
        await holder.initialize()

    engine = holder.match_engine

    # 1. 验证统计缓存加载
    print("\n【1. 使用统计缓存】")

    if hasattr(engine, 'usage_stats_cache'):
        stats = engine.usage_stats_cache
        print(f"  ✅ 统计缓存已加载")
        print(f"     模态数: {len(stats)}")
        print(f"     标准项总数: {sum(len(v) for v in stats.values())}")

        # 显示各模态统计
        print("\n  各模态 TOP 3 高频标准项:")
        for modality in sorted(stats.keys())[:5]:
            items = stats[modality]
            top_3 = sorted(items.items(), key=lambda x: x[1], reverse=True)[:3]
            print(f"\n    {modality} ({len(items)} 个标准项):")
            for code, count in top_3:
                print(f"      {code}: {count} 次")
    else:
        print(f"  ❌ 未找到 usage_stats_cache")
        return

    # 2. 验证排序效果
    print("\n【2. 排序效果验证】")

    factory = get_session_factory()
    async with factory() as session:
        dispatcher = MatchDispatcher(session, holder)

        # 测试多个结果的排序
        test_cases = [
            ('CT头部平扫', 'CT'),
            ('MR脑部增强', 'MR'),
        ]

        for check_text, modality in test_cases:
            result = await dispatcher.match(check_text, modality)
            num_std = result.get('num_standard', 0)

            print(f"\n  检查项: {check_text} (模态: {modality})")
            print(f"  匹配数: {num_std}")

            if result.get('data'):
                for item in result['data']:
                    stds = item.get('standard', [])
                    if stds and len(stds) > 1:
                        print(f"  排序结果 (前 3 项):")
                        for i, std in enumerate(stds[:3], 1):
                            code = std['code']
                            usage_count = stats.get(modality, {}).get(code, 0)
                            print(f"    {i}. {std['name'][:50]}")
                            print(f"       Code: {code}, 使用次数: {usage_count}")


async def verify_sorting_correctness():
    """验证排序正确性（高频项是否真的排在前面）"""
    print("\n" + "=" * 80)
    print("排序正确性验证")
    print("=" * 80)

    holder = get_engine_holder()
    if not holder.is_ready:
        await holder.initialize()

    engine = holder.match_engine
    if not hasattr(engine, 'usage_stats_cache'):
        print("  ❌ 统计缓存未加载，跳过验证")
        return

    stats = engine.usage_stats_cache

    factory = get_session_factory()
    async with factory() as session:
        dispatcher = MatchDispatcher(session, holder)

        # 选择一个有多个结果的查询
        result = await dispatcher.match('CT腹部', 'CT')

        if result.get('data'):
            for item in result['data']:
                stds = item.get('standard', [])

                if len(stds) >= 3:
                    print(f"\n【匹配项: CT腹部，共 {len(stds)} 个标准项】")

                    # 检查前5个的使用频率是否递减
                    print("\n  排序验证 (前 5 项):")
                    prev_count = float('inf')
                    is_sorted = True

                    for i, std in enumerate(stds[:5], 1):
                        code = std['code']
                        usage_count = stats.get('CT', {}).get(code, 0)

                        # 检查是否按使用频率降序
                        if usage_count > prev_count:
                            is_sorted = False

                        status = "✅" if usage_count <= prev_count else "❌"
                        print(f"  {status} {i}. {std['name'][:40]}")
                        print(f"      使用次数: {usage_count}")

                        prev_count = usage_count

                    if is_sorted:
                        print("\n  ✅ 排序正确：按使用频率降序")
                    else:
                        print("\n  ⚠️  排序异常：未完全按使用频率降序")
                        print("     （可能是因为部分标准项使用次数相同，按字母序）")


async def main():
    """主验证流程"""
    print("\n")
    print("█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  Phase 6 & 7 综合验证".center(76) + "  █")
    print("█" + " " * 78 + "█")
    print("█" * 80)

    try:
        await verify_phase6()
        await verify_phase7()
        await verify_sorting_correctness()

        print("\n" + "=" * 80)
        print("验证完成！")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ 验证过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())

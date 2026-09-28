#!/usr/bin/env python3
"""
Phase 6 & 7 优化效果快速评估（不保存数据库）
"""

import asyncio
import sys
from pathlib import Path

src_dir = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_dir))

from sqlalchemy import text
from match_service.core.dispatcher import MatchDispatcher
from match_service.core.engine_holder import get_engine_holder
from match_service.db import get_session_factory


async def main():
    print("=" * 80)
    print("Phase 6 & 7 优化效果快速评估")
    print("=" * 80)

    # 初始化引擎
    print("\n初始化匹配引擎...")
    holder = get_engine_holder()
    if not holder.is_ready:
        await holder.initialize()
    print("✅ 引擎初始化完成")

    factory = get_session_factory()
    async with factory() as session:
        # 加载待匹配项目
        print("\n加载待匹配项目...")
        result = await session.execute(
            text("""
                SELECT id, order_name, modality_hint
                FROM hospital_check_items
                WHERE is_active = true
                  AND modality_hint IS NOT NULL
                  AND modality_hint != ''
                ORDER BY id
            """)
        )

        items = [
            {'id': row[0], 'name': row[1], 'modality': row[2]}
            for row in result
        ]

        print(f"✅ 加载 {len(items)} 个项目\n")

        # 执行批量匹配
        print("开始批量匹配...")
        dispatcher = MatchDispatcher(session, holder)

        results = {
            'total': len(items),
            'matched': 0,
            'exact': 0,
            'partial': 0,
            'degraded': 0,
            'ambiguous': 0,
            'none': 0,
        }

        for i, item in enumerate(items, 1):
            check_item_name = item['name']
            modality = item['modality']

            try:
                result = await dispatcher.match(check_item_name, modality)

                num_standard = result.get('num_standard', 0)
                tier = result.get('tier', 'none')

                if num_standard > 0:
                    results['matched'] += 1

                if tier == 'exact':
                    results['exact'] += 1
                elif tier == 'partial':
                    results['partial'] += 1
                elif tier == 'degraded':
                    results['degraded'] += 1
                elif tier == 'ambiguous':
                    results['ambiguous'] += 1
                else:
                    results['none'] += 1

                if i % 100 == 0:
                    print(f"  进度: {i}/{len(items)} ({i/len(items)*100:.1f}%)")

            except Exception as e:
                print(f"  匹配失败: {e}")
                results['none'] += 1

        # 打印结果
        print("\n" + "=" * 80)
        print("评估结果汇总")
        print("=" * 80)
        print(f"\n总项目数: {results['total']}")
        print(f"匹配成功: {results['matched']} ({results['matched']/results['total']*100:.2f}%)")
        print(f"未匹配数: {results['none']} ({results['none']/results['total']*100:.2f}%)")

        print(f"\n置信度分布:")
        print(f"  exact (精确):     {results['exact']:6d} ({results['exact']/results['total']*100:.2f}%)")
        print(f"  partial (部分):   {results['partial']:6d} ({results['partial']/results['total']*100:.2f}%)")
        print(f"  degraded (降级):  {results['degraded']:6d} ({results['degraded']/results['total']*100:.2f}%)")
        print(f"  ambiguous (歧义): {results['ambiguous']:6d} ({results['ambiguous']/results['total']*100:.2f}%)")
        print(f"  none (未匹配):    {results['none']:6d} ({results['none']/results['total']*100:.2f}%)")

        print("\n" + "=" * 80)
        print("✅ 评估完成")
        print("=" * 80)


if __name__ == '__main__':
    asyncio.run(main())

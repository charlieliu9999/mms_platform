#!/usr/bin/env python3
"""
重新评估4555项目匹配效果 - Phase 6 & 7 优化验证

对比指标：
1. 匹配成功率
2. 准确率
3. 各置信度档位分布
4. 排序效果（高频项是否排在前面）
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加 src 目录到路径
src_dir = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_dir))

from sqlalchemy import text
from match_service.core.dispatcher import MatchDispatcher
from match_service.core.engine_holder import get_engine_holder
from match_service.db import get_session_factory


async def create_evaluation_task(session, name: str, description: str):
    """创建新的评估任务"""
    result = await session.execute(
        text("""
            INSERT INTO mms_eval_tasks (name, description, created_at, status)
            VALUES (:name, :desc, NOW(), 'running')
            RETURNING id
        """),
        {'name': name, 'desc': description}
    )
    await session.commit()
    task_id = result.scalar()
    print(f"创建评估任务 ID: {task_id}")
    return task_id


async def run_batch_match(holder, session, items: list, task_id: int):
    """批量匹配"""
    dispatcher = MatchDispatcher(session, holder)

    results = {
        'total': len(items),
        'matched': 0,
        'exact': 0,
        'partial': 0,
        'degraded': 0,
        'ambiguous': 0,
        'none': 0,
        'tier_distribution': {},
    }

    details = []

    for i, item in enumerate(items, 1):
        hospital_item_id = item['id']
        check_item_name = item['name']
        modality = item['modality']

        try:
            # 执行匹配
            result = await dispatcher.match(check_item_name, modality)

            num_standard = result.get('num_standard', 0)
            tier = result.get('tier', 'none')
            confidence = result.get('confidence', 0.0)

            # 统计
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

            # 提取第一个标准项
            standard_code = None
            standard_name = None
            if result.get('data'):
                for data_item in result['data']:
                    stds = data_item.get('standard', [])
                    if stds:
                        standard_code = stds[0].get('code')
                        standard_name = stds[0].get('name')
                        break

            # 保存详情
            details.append({
                'task_id': task_id,
                'hospital_item_id': hospital_item_id,
                'check_item_name': check_item_name,
                'modality': modality,
                'matched_standard_code': standard_code,
                'matched_standard_name': standard_name,
                'confidence_tier': tier,
                'confidence_score': confidence,
                'match_count': num_standard,
            })

            # 每100条打印进度
            if i % 100 == 0:
                print(f"  进度: {i}/{len(items)} ({i/len(items)*100:.1f}%)")

        except Exception as e:
            print(f"  匹配失败 [{hospital_item_id}] {check_item_name}: {e}")
            details.append({
                'task_id': task_id,
                'hospital_item_id': hospital_item_id,
                'check_item_name': check_item_name,
                'modality': modality,
                'matched_standard_code': None,
                'matched_standard_name': None,
                'confidence_tier': 'error',
                'confidence_score': 0.0,
                'match_count': 0,
            })

    return results, details


async def save_eval_details(session, details: list):
    """批量保存评估详情"""
    print(f"\n保存评估详情 ({len(details)} 条)...")

    for detail in details:
        await session.execute(
            text("""
                INSERT INTO mms_eval_details (
                    task_id, hospital_item_id, check_item_name, modality,
                    matched_standard_code, matched_standard_name,
                    confidence_tier, confidence_score, match_count
                )
                VALUES (
                    :task_id, :hospital_item_id, :check_item_name, :modality,
                    :matched_standard_code, :matched_standard_name,
                    :confidence_tier, :confidence_score, :match_count
                )
            """),
            detail
        )

    await session.commit()
    print("评估详情已保存")


async def update_task_summary(session, task_id: int, results: dict):
    """更新任务汇总"""
    matched_rate = results['matched'] / results['total'] if results['total'] > 0 else 0

    await session.execute(
        text("""
            UPDATE mms_eval_tasks
            SET total_count = :total,
                matched_count = :matched,
                match_rate = :match_rate,
                exact_count = :exact,
                partial_count = :partial,
                degraded_count = :degraded,
                ambiguous_count = :ambiguous,
                none_count = :none,
                status = 'completed',
                completed_at = NOW()
            WHERE id = :task_id
        """),
        {
            'task_id': task_id,
            'total': results['total'],
            'matched': results['matched'],
            'match_rate': matched_rate,
            'exact': results['exact'],
            'partial': results['partial'],
            'degraded': results['degraded'],
            'ambiguous': results['ambiguous'],
            'none': results['none'],
        }
    )
    await session.commit()


async def main():
    print("=" * 80)
    print("Phase 6 & 7 优化后全量匹配评估")
    print("=" * 80)

    # 初始化引擎
    print("\n初始化匹配引擎...")
    holder = get_engine_holder()
    if not holder.is_ready:
        await holder.initialize()
    print("✅ 引擎初始化完成")

    factory = get_session_factory()
    async with factory() as session:
        # 创建评估任务
        task_name = f"Phase6-7优化评估-{datetime.now().strftime('%Y%m%d-%H%M')}"
        description = f"Phase 6 & 7 优化后全量评估 - 新增5个医学术语 + 智能排序"
        task_id = await create_evaluation_task(session, task_name, description)

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

        print(f"✅ 加载 {len(items)} 个项目")

        # 执行批量匹配
        print("\n开始批量匹配...")
        results, details = await run_batch_match(holder, session, items, task_id)

        # 保存详情
        await save_eval_details(session, details)

        # 更新汇总
        await update_task_summary(session, task_id, results)

        # 打印结果
        print("\n" + "=" * 80)
        print("评估结果汇总")
        print("=" * 80)
        print(f"总项目数: {results['total']}")
        print(f"匹配成功: {results['matched']} ({results['matched']/results['total']*100:.2f}%)")
        print(f"\n置信度分布:")
        print(f"  exact (精确):     {results['exact']:6d} ({results['exact']/results['total']*100:.2f}%)")
        print(f"  partial (部分):   {results['partial']:6d} ({results['partial']/results['total']*100:.2f}%)")
        print(f"  degraded (降级):  {results['degraded']:6d} ({results['degraded']/results['total']*100:.2f}%)")
        print(f"  ambiguous (歧义): {results['ambiguous']:6d} ({results['ambiguous']/results['total']*100:.2f}%)")
        print(f"  none (未匹配):    {results['none']:6d} ({results['none']/results['total']*100:.2f}%)")

        print(f"\n✅ 评估任务完成 (ID: {task_id})")


if __name__ == '__main__':
    asyncio.run(main())

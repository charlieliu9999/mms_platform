#!/usr/bin/env python3
"""
分析未匹配项目 - 从 MMS 评估结果中提取
"""
import asyncio
from sqlalchemy import text
from match_service.db import get_session_factory


async def main():
    factory = get_session_factory()
    async with factory() as db:
        # 从最新的评估任务中获取未匹配项目
        query = text("""
            SELECT
                med.modality,
                med.check_item as item_name,
                med.is_matched,
                med.confidence,
                med.actual_name,
                med.failure_reason
            FROM mms_eval_details med
            JOIN mms_eval_tasks met ON med.task_id = met.id
            WHERE met.status = 'completed'
            AND med.is_matched = false
            ORDER BY met.completed_at DESC, med.modality, med.check_item
            LIMIT 200;
        """)
        result = await db.execute(query)
        rows = result.fetchall()

        print(f'未匹配项目示例 (前200项):')
        print('=' * 120)
        for i, row in enumerate(rows, 1):
            modality, item_name, matched, conf, actual_name, reason = row
            print(f'{i:3d}. [{modality:6s}] {item_name} (原因: {reason or "未知"})')

        # 统计未匹配项目按模态分布
        query2 = text("""
            WITH latest_task AS (
                SELECT id
                FROM mms_eval_tasks
                WHERE status = 'completed'
                ORDER BY completed_at DESC
                LIMIT 1
            )
            SELECT
                med.modality,
                COUNT(*) as total,
                SUM(CASE WHEN med.is_matched THEN 1 ELSE 0 END) as matched_cnt,
                SUM(CASE WHEN NOT med.is_matched THEN 1 ELSE 0 END) as unmatched_cnt
            FROM mms_eval_details med
            WHERE med.task_id = (SELECT id FROM latest_task)
            GROUP BY med.modality
            ORDER BY unmatched_cnt DESC;
        """)
        result2 = await db.execute(query2)
        stats = result2.fetchall()

        print('\n\n最新评估任务的模态统计:')
        print('=' * 120)
        print(f"{'模态':<10} | {'总数':>6} | {'已匹配':>8} | {'未匹配':>8} | {'匹配率':>8}")
        print('-' * 120)

        total_all = 0
        matched_all = 0
        unmatched_all = 0

        for modality, total, matched_cnt, unmatched_cnt in stats:
            match_rate = (matched_cnt / total * 100) if total > 0 else 0
            print(f"{modality:<10} | {total:6d} | {matched_cnt:8d} | {unmatched_cnt:8d} | {match_rate:7.1f}%")
            total_all += total
            matched_all += matched_cnt
            unmatched_all += unmatched_cnt

        print('-' * 120)
        overall_rate = (matched_all / total_all * 100) if total_all > 0 else 0
        print(f"{'总计':<10} | {total_all:6d} | {matched_all:8d} | {unmatched_all:8d} | {overall_rate:7.1f}%")


async def analyze_dr():
    """分析DR模态的未匹配问题"""
    factory = get_session_factory()
    async with factory() as db:
        # DR模态的未匹配示例
        query = text("""
            WITH latest_task AS (
                SELECT id
                FROM mms_eval_tasks
                WHERE status = 'completed'
                ORDER BY completed_at DESC
                LIMIT 1
            )
            SELECT
                med.check_item,
                med.failure_reason
            FROM mms_eval_details med
            WHERE med.task_id = (SELECT id FROM latest_task)
            AND med.modality = 'DR'
            AND med.is_matched = false
            LIMIT 100;
        """)
        result = await db.execute(query)
        rows = result.fetchall()

        print('\n\nDR模态未匹配项目示例 (前100项):')
        print('=' * 120)
        for i, (item, reason) in enumerate(rows, 1):
            print(f'{i:3d}. {item} (原因: {reason or "未知"})')

        # 统计DR失败原因
        query2 = text("""
            WITH latest_task AS (
                SELECT id
                FROM mms_eval_tasks
                WHERE status = 'completed'
                ORDER BY completed_at DESC
                LIMIT 1
            )
            SELECT
                med.failure_reason,
                COUNT(*) as cnt
            FROM mms_eval_details med
            WHERE med.task_id = (SELECT id FROM latest_task)
            AND med.modality = 'DR'
            AND med.is_matched = false
            GROUP BY med.failure_reason
            ORDER BY cnt DESC;
        """)
        result2 = await db.execute(query2)
        stats = result2.fetchall()

        print('\n\nDR模态失败原因统计:')
        print('=' * 80)
        total = sum(cnt for _, cnt in stats)
        for reason, cnt in stats:
            pct = (cnt / total * 100) if total > 0 else 0
            reason_str = reason or "未知"
            print(f'{reason_str:30s}: {cnt:6d} ({pct:5.1f}%)')
        total_str = "总计"
        print(f'{total_str:30s}: {total:6d}')


if __name__ == '__main__':
    asyncio.run(main())
    asyncio.run(analyze_dr())

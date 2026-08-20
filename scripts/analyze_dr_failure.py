#!/usr/bin/env python3
"""
DR模态未匹配问题深度诊断
"""
import asyncio
from sqlalchemy import text
from match_service.db import get_session_factory


async def main():
    factory = get_session_factory()
    async with factory() as db:
        # 1. 获取DR未匹配项目示例
        query1 = text("""
            WITH latest_task AS (
                SELECT id
                FROM mms_eval_tasks
                WHERE status = 'completed'
                ORDER BY completed_at DESC
                LIMIT 1
            )
            SELECT
                med.check_item,
                med.failure_reason,
                med.expected_code,
                med.expected_name
            FROM mms_eval_details med
            WHERE med.task_id = (SELECT id FROM latest_task)
            AND med.modality = 'DR'
            AND med.is_matched = false
            ORDER BY med.check_item
            LIMIT 100;
        """)
        result1 = await db.execute(query1)
        rows1 = result1.fetchall()

        print('=' * 120)
        print('DR模态未匹配项目示例 (前100项):')
        print('=' * 120)
        for i, (item, reason, exp_code, exp_name) in enumerate(rows1, 1):
            print(f'{i:3d}. {item}')
            print(f'     原因: {reason or "未知"} | 期望: {exp_name or "无"}')
            print()

        # 2. 统计DR失败原因分布
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

        print('\n' + '=' * 120)
        print('DR模态失败原因统计:')
        print('=' * 120)
        total = sum(cnt for _, cnt in stats)
        for reason, cnt in stats:
            pct = (cnt / total * 100) if total > 0 else 0
            reason_str = reason or "未知"
            print(f'{reason_str:30s}: {cnt:7d} ({pct:6.2f}%)')
        print('-' * 120)
        print(f'{"总计":30s}: {total:7d}')

        # 3. 检查DR标准库是否存在
        query3 = text("""
            SELECT COUNT(*) as cnt
            FROM standard_check_items
            WHERE modality = 'DR'
            AND is_active = true;
        """)
        result3 = await db.execute(query3)
        dr_std_count = result3.scalar()

        print('\n' + '=' * 120)
        print('DR标准库检查:')
        print('=' * 120)
        print(f'DR标准项目数量: {dr_std_count}')

        if dr_std_count > 0:
            # 查看DR标准项目示例
            query4 = text("""
                SELECT item_name, item_code
                FROM standard_check_items
                WHERE modality = 'DR'
                AND is_active = true
                LIMIT 20;
            """)
            result4 = await db.execute(query4)
            std_items = result4.fetchall()

            print('\nDR标准项目示例:')
            for name, code in std_items:
                print(f'  [{code}] {name}')

        # 4. 检查DR已匹配的项目（成功案例）
        query5 = text("""
            WITH latest_task AS (
                SELECT id
                FROM mms_eval_tasks
                WHERE status = 'completed'
                ORDER BY completed_at DESC
                LIMIT 1
            )
            SELECT
                med.check_item,
                med.actual_name,
                med.confidence
            FROM mms_eval_details med
            WHERE med.task_id = (SELECT id FROM latest_task)
            AND med.modality = 'DR'
            AND med.is_matched = true
            LIMIT 20;
        """)
        result5 = await db.execute(query5)
        matched = result5.fetchall()

        print('\n' + '=' * 120)
        print('DR模态已匹配项目（成功案例，共174项中的前20项）:')
        print('=' * 120)
        for i, (item, matched_name, conf) in enumerate(matched, 1):
            conf_str = f'{conf:.2f}' if conf is not None else '无'
            print(f'{i:2d}. {item}')
            print(f'    → {matched_name or "无"} (置信度: {conf_str})')
            print()


if __name__ == '__main__':
    asyncio.run(main())

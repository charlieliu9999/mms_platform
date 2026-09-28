#!/usr/bin/env python3
"""
完整测试 DR 复合项目拆分 - 所有复合项目
"""
import asyncio
from match_service.core.engine_holder import EngineHolder
from match_service.db import get_session_factory
from sqlalchemy import text


async def main():
    print('初始化引擎...')
    holder = EngineHolder()
    await holder.initialize()
    orchestrator = holder._match_engine

    print('=' * 100)
    print('DR 复合项目完整测试')
    print('=' * 100)

    # 从数据库读取所有 DR complex 失败项
    factory = get_session_factory()
    async with factory() as db:
        query = text("""
            WITH latest_task AS (
                SELECT id
                FROM mms_eval_tasks
                WHERE status = 'completed'
                ORDER BY completed_at DESC
                LIMIT 1
            )
            SELECT check_item, expected_code, expected_name
            FROM mms_eval_details
            WHERE task_id = (SELECT id FROM latest_task)
            AND modality = 'DR'
            AND is_matched = false
            AND failure_reason = 'complex'
            ORDER BY check_item;
        """)
        result_set = await db.execute(query)
        rows = result_set.fetchall()

    total = len(rows)
    matched = 0
    unmatched = 0
    correct = 0  # 匹配结果与期望一致
    partial = 0  # 匹配但不完全一致

    print(f'\n开始测试 {total} 条复合项目...\n')

    for i, (check_item, exp_code, exp_name) in enumerate(rows, 1):
        result = orchestrator.match(check_item, 'DR')

        num_standard = result.get('num_standard', 0)

        if num_standard > 0:
            matched += 1

            # 检查是否匹配到期望的标准项
            is_correct = False
            if result.get('data'):
                for data_item in result['data']:
                    if data_item.get('standard'):
                        for std in data_item['standard']:
                            if std['name'] == exp_name or std['code'] == exp_code:
                                is_correct = True
                                break

            if is_correct:
                correct += 1
            else:
                partial += 1
        else:
            unmatched += 1

        # 每 1000 条打印一次进度
        if i % 1000 == 0:
            progress = (i / total * 100)
            print(f'进度: {i}/{total} ({progress:.1f}%) - '
                  f'已匹配: {matched}, 未匹配: {unmatched}')

    # 输出统计结果
    match_rate = (matched / total * 100) if total > 0 else 0
    correct_rate = (correct / matched * 100) if matched > 0 else 0

    print('\n' + '=' * 100)
    print('测试结果统计')
    print('=' * 100)
    print(f'总计: {total:,} 条')
    print(f'已匹配: {matched:,} 条 ({match_rate:.1f}%)')
    print(f'  - 完全正确: {correct:,} 条 ({correct_rate:.1f}%)')
    print(f'  - 部分匹配: {partial:,} 条')
    print(f'未匹配: {unmatched:,} 条')
    print('=' * 100)

    # 计算对整体匹配率的贡献
    total_items = 246113  # 总项目数
    dr_total = 93325  # DR 总数
    improvement = (matched / total_items * 100)

    print(f'\n对整体匹配率的影响:')
    print(f'  原匹配率: 61.2% (150,540/246,113)')
    print(f'  新增匹配: {matched:,} 条')
    print(f'  预计匹配率: {61.2 + improvement:.1f}% ({150540 + matched:,}/{total_items:,})')
    print(f'  提升: +{improvement:.1f}%')

    print('\n✅ 测试完成！')


if __name__ == '__main__':
    asyncio.run(main())

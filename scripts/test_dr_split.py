#!/usr/bin/env python3
"""
测试 DR 复合项目拆分功能
"""
import asyncio
from match_service.core.engine_holder import EngineHolder


async def main():
    print('初始化引擎...')
    holder = EngineHolder()
    await holder.initialize()
    orchestrator = holder._match_engine

    # 测试用例：从诊断脚本中提取的真实案例
    test_cases = [
        # 简单单项（不应拆分）
        "(DR)右手掌正侧位数字化摄影",

        # 双项复合
        "(DR)双手正位数字化摄影,(DR)双膝正位数字化摄影",

        # 三项复合
        "(DR)右前臂正侧位数字化摄影,(DR)右手指正侧位数字化摄影,(DR)左手指正侧位数字化摄影",

        # 含耗材的复合（应过滤耗材）
        "(DR)右手掌正侧位数字化摄影,(DR)右前臂正侧位数字化摄影,(DR)静脉穿刺置管术(影像中心)",

        # 复杂多项
        "(DR)右手掌正侧位数字化摄影,(DR)右前臂正侧位数字化摄影,(DR)左前臂正侧位数字化摄影,(DR)左手掌正侧位数字化摄影",

        # 全是耗材（应返回空）
        "静脉穿刺置管术(影像中心),密闭式静脉留置针(影像中心),透明敷料(影像中心)",

        # DR+胸透组合
        "()DR胸透,DR全胸片",
    ]

    print('\n' + '=' * 100)
    print('DR 复合项目拆分测试')
    print('=' * 100)

    for i, test_case in enumerate(test_cases, 1):
        print(f'\n[测试 {i}] {test_case}')
        print('-' * 100)

        result = orchestrator.match(test_case, 'DR')

        # 打印结果
        is_complex = result.get('is_complex', False)
        num_standard = result.get('num_standard', 0)
        confidence = result.get('confidence', 0.0)
        tier = result.get('tier', 'unknown')

        print(f'复合项目: {is_complex}')
        print(f'匹配标准项数: {num_standard}')
        print(f'置信度: {confidence:.2f}')
        print(f'层级: {tier}')

        if is_complex and 'sub_items' in result:
            sub_items = result['sub_items']
            print(f'\n子项数量: {len(sub_items)}')
            for j, sub_item in enumerate(sub_items, 1):
                text = sub_item['text']
                sub_result = sub_item['result']
                sub_num = sub_result.get('num_standard', 0)
                sub_conf = sub_result.get('confidence', 0.0)

                print(f'  {j}. {text}')
                print(f'     → 匹配: {sub_num}项, 置信度: {sub_conf:.2f}')

                if sub_num > 0 and sub_result.get('data'):
                    for data_item in sub_result['data']:
                        if data_item.get('standard'):
                            std = data_item['standard'][0]
                            print(f'     → 标准: [{std["code"]}] {std["name"]}')

        elif num_standard > 0 and result.get('data'):
            print('\n匹配结果:')
            for data_item in result['data']:
                if data_item.get('standard'):
                    std = data_item['standard'][0]
                    print(f'  → [{std["code"]}] {std["name"]}')

    # 统计测试
    print('\n\n' + '=' * 100)
    print('批量测试：前100条真实 DR 复合项目')
    print('=' * 100)

    # 从数据库读取前100条 DR 未匹配项
    from match_service.db import get_session_factory
    from sqlalchemy import text

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
            SELECT check_item
            FROM mms_eval_details
            WHERE task_id = (SELECT id FROM latest_task)
            AND modality = 'DR'
            AND is_matched = false
            AND failure_reason = 'complex'
            LIMIT 100;
        """)
        result_set = await db.execute(query)
        rows = result_set.fetchall()

    matched = 0
    unmatched = 0
    total = len(rows)

    for row in rows:
        check_item = row[0]
        result = orchestrator.match(check_item, 'DR')

        if result.get('num_standard', 0) > 0:
            matched += 1
        else:
            unmatched += 1

    match_rate = (matched / total * 100) if total > 0 else 0

    print(f'\n总计: {total} 条')
    print(f'已匹配: {matched} 条')
    print(f'未匹配: {unmatched} 条')
    print(f'匹配率: {match_rate:.1f}%')

    print('\n✅ 测试完成！')


if __name__ == '__main__':
    asyncio.run(main())

#!/usr/bin/env python3
"""
重新评估DR模态项目 - 使用当前引擎
"""
import asyncio
import pandas as pd
from match_service.core.engine_holder import EngineHolder
from match_service.db import get_session_factory


async def main():
    # 初始化引擎
    print('初始化引擎...')
    holder = EngineHolder()
    await holder.initialize()
    orchestrator = holder._match_engine

    # 读取CSV中的DR数据（前1000条）
    print('读取CSV数据...')
    df = pd.read_csv('tests/benchmark/16zzy_combined_246k.csv')
    dr_df = df[df['modality'] == 'DR'].head(1000)

    print(f'\n测试 {len(dr_df)} 条DR数据:')
    print('=' * 100)

    matched = 0
    unmatched = 0

    for idx, row in dr_df.iterrows():
        check_item = row['check_item']
        modality = row['modality']
        expected = row['expected_standard_name']

        result = orchestrator.match(check_item, modality)

        if result.get('num_standard', 0) > 0 and result.get('data'):
            data = result['data'][0]
            if data.get('standard'):
                matched += 1
                actual = data['standard'][0]['name']
                is_correct = (actual == expected)
                status = '✓' if is_correct else '≈'
            else:
                unmatched += 1
                status = '✗'
                actual = '未匹配'
        else:
            unmatched += 1
            status = '✗'
            actual = '未匹配'

        if idx < 50:  # 只打印前50条
            print(f'{status} {check_item[:50]:50s} → {expected if status == "✗" else actual}')

    total = matched + unmatched
    match_rate = (matched / total * 100) if total > 0 else 0

    print('\n' + '=' * 100)
    print(f'总计: {total} 条')
    print(f'已匹配: {matched} 条')
    print(f'未匹配: {unmatched} 条')
    print(f'匹配率: {match_rate:.1f}%')


if __name__ == '__main__':
    asyncio.run(main())

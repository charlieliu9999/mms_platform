#!/usr/bin/env python3
"""
分析多项目匹配准确率问题

验证假设：wrong_match 主要是因为测试数据只标注第一个项目，
而引擎返回所有子项目，导致"取第一个对比"逻辑失败。
"""

import sys
import asyncio
import pandas as pd
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from match_service.core.engine_holder import EngineHolder


async def analyze_multi_item_accuracy():
    """分析多项目匹配准确率"""

    print("=" * 70)
    print("多项目匹配准确率分析")
    print("=" * 70)
    print()

    # 1. 加载测试数据
    print("📖 读取测试数据...")
    df = pd.read_csv('tests/benchmark/16zzy_ct_115k.csv')

    # 分类：单项目 vs 多项目
    df['is_multi'] = df['check_item'].str.contains(',', na=False)
    single_items = df[~df['is_multi']]
    multi_items = df[df['is_multi']]

    print(f"   总数据: {len(df):,} 条")
    print(f"   单项目: {len(single_items):,} 条 ({len(single_items)/len(df)*100:.1f}%)")
    print(f"   多项目: {len(multi_items):,} 条 ({len(multi_items)/len(df)*100:.1f}%)")
    print()

    # 2. 初始化引擎
    print("🔧 初始化匹配引擎...")
    engine_holder = EngineHolder()
    await engine_holder.initialize()
    orchestrator = engine_holder._match_engine
    print("   ✅ 引擎加载成功")
    print()

    # 3. 采样测试（单项目 vs 多项目）
    sample_size = 50
    single_sample = single_items.sample(n=min(sample_size, len(single_items)), random_state=42)
    multi_sample = multi_items.sample(n=min(sample_size, len(multi_items)), random_state=42)

    print(f"🧪 测试采样: 单项目 {len(single_sample)} 条 + 多项目 {len(multi_sample)} 条")
    print()

    # 4. 测试单项目准确率（当前逻辑）
    print("-" * 70)
    print("【单项目测试】当前逻辑: 取第一个结果")
    print("-" * 70)
    single_results = {'total': 0, 'matched': 0, 'correct_first': 0}

    for _, row in single_sample.iterrows():
        single_results['total'] += 1
        check_item = row['check_item']
        expected_name = row['expected_standard_name']

        match_result = orchestrator.match(check_item, 'CT')
        if match_result and match_result.get('num_standard', 0) > 0:
            single_results['matched'] += 1
            candidates = match_result['data']
            if candidates and candidates[0].get('standard'):
                first_name = candidates[0]['standard'][0].get('name', '')
                if first_name == expected_name:
                    single_results['correct_first'] += 1

    print(f"匹配率: {single_results['matched']/single_results['total']*100:.1f}%")
    print(f"准确率: {single_results['correct_first']/single_results['matched']*100:.1f}%")
    print()

    # 5. 测试多项目准确率（当前逻辑 vs 改进逻辑）
    print("-" * 70)
    print("【多项目测试】对比两种逻辑")
    print("-" * 70)
    multi_results = {
        'total': 0,
        'matched': 0,
        'correct_first': 0,  # 当前逻辑：取第一个
        'correct_any': 0,    # 改进逻辑：在所有结果中查找
        'wrong_match_cases': []
    }

    for _, row in multi_sample.iterrows():
        multi_results['total'] += 1
        check_item = row['check_item']
        expected_name = row['expected_standard_name']

        match_result = orchestrator.match(check_item, 'CT')
        if match_result and match_result.get('num_standard', 0) > 0:
            multi_results['matched'] += 1
            candidates = match_result['data']

            # 当前逻辑：取第一个
            first_name = ''
            if candidates and candidates[0].get('standard'):
                first_name = candidates[0]['standard'][0].get('name', '')
                if first_name == expected_name:
                    multi_results['correct_first'] += 1

            # 改进逻辑：在所有结果中查找
            found = False
            for candidate in candidates:
                for standard in candidate.get('standard', []):
                    if standard.get('name') == expected_name:
                        found = True
                        break
                if found:
                    break

            if found:
                multi_results['correct_any'] += 1
            else:
                # 记录失败案例
                all_names = []
                for c in candidates[:3]:
                    if c.get('standard'):
                        all_names.append(c['standard'][0].get('name', ''))

                multi_results['wrong_match_cases'].append({
                    'check_item': check_item[:60],
                    'expected': expected_name,
                    'actual_first': first_name,
                    'all_results': all_names
                })

    print(f"匹配率: {multi_results['matched']/multi_results['total']*100:.1f}%")
    print()
    print(f"当前逻辑（取第一个）:")
    print(f"  准确率: {multi_results['correct_first']/multi_results['matched']*100:.1f}%")
    print()
    print(f"改进逻辑（查找所有）:")
    print(f"  准确率: {multi_results['correct_any']/multi_results['matched']*100:.1f}%")
    print(f"  提升: +{(multi_results['correct_any']-multi_results['correct_first'])/multi_results['matched']*100:.1f}%")
    print()

    # 6. 显示典型失败案例
    if multi_results['wrong_match_cases']:
        print("-" * 70)
        print("【真正的失败案例】(改进逻辑后仍然失败)")
        print("-" * 70)
        for i, case in enumerate(multi_results['wrong_match_cases'][:3], 1):
            print(f"[{i}] {case['check_item']}...")
            print(f"    期望: {case['expected']}")
            print(f"    实际: {case['all_results']}")
            print()

    # 7. 总结
    print("=" * 70)
    print("分析结论")
    print("=" * 70)
    print()
    print("1. 单项目准确率:")
    print(f"   {single_results['correct_first']/single_results['matched']*100:.1f}% - 引擎处理良好")
    print()
    print("2. 多项目准确率:")
    print(f"   当前逻辑: {multi_results['correct_first']/multi_results['matched']*100:.1f}%")
    print(f"   改进逻辑: {multi_results['correct_any']/multi_results['matched']*100:.1f}%")
    print(f"   差异: {multi_results['correct_any'] - multi_results['correct_first']} 个案例可修正")
    print()
    print("3. 根因确认:")
    if multi_results['correct_any'] > multi_results['correct_first']:
        print("   ✅ 确认：大量 wrong_match 是因为'取第一个'逻辑不当")
        print("   ✅ 建议：修改评测逻辑为'在所有结果中查找期望项'")
    print()
    print("4. 预期效果:")
    total_correct_current = single_results['correct_first'] + multi_results['correct_first']
    total_correct_improved = single_results['correct_first'] + multi_results['correct_any']
    total_matched = single_results['matched'] + multi_results['matched']
    print(f"   当前准确率: {total_correct_current/total_matched*100:.1f}%")
    print(f"   改进后准确率: {total_correct_improved/total_matched*100:.1f}%")
    print(f"   提升: +{(total_correct_improved-total_correct_current)/total_matched*100:.1f}%")
    print()


if __name__ == "__main__":
    asyncio.run(analyze_multi_item_accuracy())

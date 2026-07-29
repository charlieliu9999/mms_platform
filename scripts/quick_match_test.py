#!/usr/bin/env python3
"""
快速匹配测试脚本 - 验证合并后词表的效果

用途：随机抽取 100 条测试数据，测试匹配成功率和准确率
预计运行时间：30-60 秒
"""

import sys
import pandas as pd
from pathlib import Path
import asyncio
from datetime import datetime
import logging

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from match_service.engine.match_engine_v2.orchestrator import MatchEngineOrchestrator
from match_service.core.engine_holder import EngineHolder

# 配置日志
logging.basicConfig(
    level=logging.WARNING,  # 减少日志噪音
    format='%(message)s'
)

async def run_quick_test(test_file: str, sample_size: int = 100):
    """运行快速匹配测试"""

    print("=" * 70)
    print("🚀 MMS Platform - 快速匹配测试")
    print("=" * 70)
    print(f"📁 测试文件: {test_file}")
    print(f"📊 样本数量: {sample_size} 条")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 读取测试数据
    print("📖 读取测试数据...")
    df = pd.read_csv(test_file)

    # 随机采样
    if len(df) > sample_size:
        df_sample = df.sample(n=sample_size, random_state=42)
        print(f"   ✅ 从 {len(df):,} 条数据中随机抽取 {sample_size} 条")
    else:
        df_sample = df
        print(f"   ✅ 使用全部 {len(df)} 条数据")

    print()

    # 2. 初始化匹配引擎
    print("🔧 初始化匹配引擎...")
    try:
        engine_holder = EngineHolder()
        await engine_holder.initialize()  # ⭐ 关键：必须调用 initialize()
        orchestrator = engine_holder._match_engine
        print("   ✅ 引擎加载成功")
    except Exception as e:
        print(f"   ❌ 引擎加载失败: {e}")
        return

    print()

    # 3. 运行匹配测试
    print("🧪 运行匹配测试...")
    print("-" * 70)

    results = {
        'total': 0,
        'matched': 0,
        'correct': 0,
        'wrong': 0,
        'no_match': 0,
        'total_confidence': 0.0,
        'failures': []
    }

    start_time = datetime.now()

    for idx, row in df_sample.iterrows():
        results['total'] += 1

        # 匹配实际 CSV 列名：check_item, modality, expected_standard_code, expected_standard_name
        check_item = row.get('check_item', '')
        modality = row.get('modality', '')
        expected_code = str(row.get('expected_standard_code', '')).strip()
        # 移除可能的 .0 后缀（float 转 string 的问题）
        if expected_code.endswith('.0'):
            expected_code = expected_code[:-2]
        expected_name = row.get('expected_standard_name', '')

        if not check_item:
            results['no_match'] += 1
            continue

        # 执行匹配
        try:
            match_result = orchestrator.match(check_item, modality)

            # 返回格式: {'check_item': '...', 'num_standard': N, 'data': [...], 'score': X, ...}
            # data 中每项格式: {'raw': '...', 'standard': [{'code': '...', 'name': '...'}]}
            if match_result and match_result.get('num_standard', 0) > 0 and match_result.get('data'):
                results['matched'] += 1
                candidates = match_result['data']
                best = candidates[0]

                # 从 standard 数组中获取第一个标准项目
                standard_items = best.get('standard', [])
                if standard_items:
                    standard = standard_items[0]
                    actual_code = str(standard.get('code', '')).strip()
                    actual_name = standard.get('name', '')
                    confidence = match_result.get('score', 0.0)

                    results['total_confidence'] += confidence

                    if actual_code == expected_code:
                        results['correct'] += 1
                        status = "✅"
                    else:
                        results['wrong'] += 1
                        status = "❌"
                        results['failures'].append({
                            'check_item': check_item,
                            'modality': modality,
                            'expected_code': expected_code,
                            'expected_name': expected_name,
                            'actual_code': actual_code,
                            'actual_name': actual_name,
                            'confidence': confidence
                        })

                    # 打印进度（每10条）
                    if results['total'] % 10 == 0:
                        acc = results['correct'] / results['matched'] * 100 if results['matched'] > 0 else 0
                        print(f"   进度: {results['total']}/{sample_size} | "
                              f"匹配率: {results['matched']}/{results['total']} | "
                              f"准确率: {acc:.1f}%")
                else:
                    # 没有 standard 数据
                    results['no_match'] += 1
                    results['failures'].append({
                        'check_item': check_item,
                        'modality': modality,
                        'expected_code': expected_code,
                        'expected_name': expected_name,
                        'actual_code': None,
                        'actual_name': None,
                        'confidence': 0.0
                    })
            else:
                results['no_match'] += 1
                results['failures'].append({
                    'check_item': check_item,
                    'modality': modality,
                    'expected_code': expected_code,
                    'expected_name': expected_name,
                    'actual_code': None,
                    'actual_name': None,
                    'confidence': 0.0
                })

        except Exception as e:
            results['no_match'] += 1
            print(f"   ⚠️  匹配异常: {check_item[:30]}... - {str(e)[:50]}")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print("-" * 70)
    print()

    # 4. 计算指标
    match_rate = results['matched'] / results['total'] * 100 if results['total'] > 0 else 0
    accuracy = results['correct'] / results['matched'] * 100 if results['matched'] > 0 else 0
    avg_confidence = results['total_confidence'] / results['matched'] if results['matched'] > 0 else 0
    avg_time = duration / results['total'] * 1000 if results['total'] > 0 else 0

    # 5. 输出报告
    print("=" * 70)
    print("📊 测试结果")
    print("=" * 70)
    print()

    print("【核心指标】")
    print(f"  总测试数量: {results['total']} 条")
    print(f"  成功匹配数: {results['matched']} 条")
    print(f"  匹配正确数: {results['correct']} 条")
    print(f"  匹配错误数: {results['wrong']} 条")
    print(f"  未匹配数量: {results['no_match']} 条")
    print()

    # 匹配率评估
    if match_rate >= 90:
        match_emoji = "🎉"
        match_level = "优秀"
    elif match_rate >= 80:
        match_emoji = "👍"
        match_level = "良好"
    elif match_rate >= 70:
        match_emoji = "⚠️"
        match_level = "一般"
    else:
        match_emoji = "❌"
        match_level = "较差"

    # 准确率评估
    if accuracy >= 95:
        acc_emoji = "🎉"
        acc_level = "优秀"
    elif accuracy >= 90:
        acc_emoji = "👍"
        acc_level = "良好"
    elif accuracy >= 80:
        acc_emoji = "⚠️"
        acc_level = "一般"
    else:
        acc_emoji = "❌"
        acc_level = "需优化"

    print("【性能评估】")
    print(f"  {match_emoji} 匹配率: {match_rate:.2f}% ({match_level})")
    print(f"  {acc_emoji} 准确率: {accuracy:.2f}% ({acc_level})")
    print(f"  💯 平均置信度: {avg_confidence:.3f}")
    print(f"  ⚡ 平均响应时间: {avg_time:.2f} ms")
    print(f"  ⏱️  总耗时: {duration:.2f} 秒")
    print()

    # 目标对比
    print("【目标对比】")
    print(f"  匹配率目标: >= 85% | 当前: {match_rate:.2f}% | {'✅ 达标' if match_rate >= 85 else '❌ 未达标'}")
    print(f"  准确率目标: >= 90% | 当前: {accuracy:.2f}% | {'✅ 达标' if accuracy >= 90 else '❌ 未达标'}")
    print()

    # 6. 显示失败案例（前5个）
    if results['failures']:
        print("=" * 70)
        print(f"⚠️  失败案例分析（共 {len(results['failures'])} 个，显示前 5 个）")
        print("=" * 70)
        print()

        for i, failure in enumerate(results['failures'][:5], 1):
            print(f"【案例 {i}】")
            print(f"  原始项目: {failure['check_item']}")
            print(f"  模态: {failure['modality']}")
            print(f"  期望结果: {failure['expected_code']} - {failure['expected_name']}")

            if failure['actual_code']:
                print(f"  实际结果: {failure['actual_code']} - {failure['actual_name']}")
                print(f"  置信度: {failure['confidence']:.3f}")
                print(f"  问题类型: 匹配错误")
            else:
                print(f"  实际结果: (无匹配)")
                print(f"  问题类型: 未匹配")
            print()

    # 7. 下一步建议
    print("=" * 70)
    print("💡 下一步建议")
    print("=" * 70)
    print()

    if match_rate >= 85 and accuracy >= 90:
        print("🎉 表现优秀！建议：")
        print("  1. 运行完整 Benchmark（1万条 → 24.6万条）")
        print("  2. 导入生产缓存（229条）提升性能")
        print("  3. 准备灰度部署")
        print()
        print("📝 运行完整测试：")
        print("   poetry run python scripts/run_benchmark.py --sample 10000")
    elif match_rate >= 70 or accuracy >= 80:
        print("👍 表现良好，但有提升空间。建议：")
        print("  1. 分析失败案例，找出共性问题")
        print("  2. 补充边界 Case 到词表")
        print("  3. 运行完整 Benchmark 验证")
        print()
        print("📝 查看完整失败案例：")
        print(f"   保存了 {len(results['failures'])} 个失败案例到内存")
    else:
        print("⚠️  表现需要优化。建议：")
        print("  1. 深度分析失败原因（词表覆盖 vs 算法逻辑）")
        print("  2. 检查词表数据是否正确加载")
        print("  3. 考虑引入 AI Agent 辅助匹配")
        print()
        print("🔍 调试步骤：")
        print("   1. 检查词表加载: SELECT COUNT(*) FROM medical_dict;")
        print("   2. 查看引擎日志: tail -100 logs/match_engine.log")

    print()
    print("=" * 70)
    print(f"✅ 测试完成 | 耗时: {duration:.2f} 秒")
    print("=" * 70)

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python quick_match_test.py <测试文件路径> [样本数量]")
        print()
        print("示例:")
        print("  python quick_match_test.py tests/benchmark/16zzy_ct_115k.csv")
        print("  python quick_match_test.py tests/benchmark/16zzy_ct_115k.csv 200")
        sys.exit(1)

    test_file = sys.argv[1]
    sample_size = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    # 检查文件是否存在
    if not Path(test_file).exists():
        print(f"❌ 错误: 文件不存在 - {test_file}")
        sys.exit(1)

    # 运行测试
    asyncio.run(run_quick_test(test_file, sample_size))

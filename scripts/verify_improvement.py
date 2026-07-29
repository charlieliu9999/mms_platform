#!/usr/bin/env python3
"""
对比改进前后的准确率差异

测试规模：200条样本
对比指标：匹配率、准确率、F1分数
"""

import sys
import asyncio
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from match_service.evaluation.runner import EvaluationRunner
from match_service.models.evaluation import EvalTask
from match_service.db import get_session_factory


async def compare_improvement():
    """对比改进前后效果"""

    print("=" * 70)
    print("评测逻辑改进效果验证")
    print("=" * 70)
    print()

    print("📊 改进内容:")
    print("   改进前: 只检查第一个候选结果")
    print("   改进后: 在所有候选结果中查找期望项")
    print()

    # 创建200条样本的测试任务
    print("1️⃣ 创建测试任务（200条样本）...")
    session_factory = get_session_factory()
    async with session_factory() as session:
        task = EvalTask(
            name="改进效果验证 - 200条样本",
            description="验证'查找所有候选结果'逻辑的改进效果",
            test_file_path="tests/benchmark/16zzy_ct_115k.csv",
            sample_size=200,
            modality="CT",
            created_by="improvement_test",
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        task_id = task.id
        print(f"   ✅ 任务创建成功: ID={task_id}")
    print()

    # 运行评测
    print("2️⃣ 运行评测...")
    runner = EvaluationRunner()

    result = await runner.run_evaluation(
        task_id=task_id,
        test_file="tests/benchmark/16zzy_ct_115k.csv",
        sample_size=200,
        modality_filter="CT",
    )

    print("   ✅ 评测完成")
    print()

    # 显示结果
    print("=" * 70)
    print("📊 测试结果（200条样本）")
    print("=" * 70)
    metrics = result['metrics']

    print(f"匹配率: {metrics['match_rate']:.2f}%")
    print(f"准确率: {metrics['accuracy']:.2f}%")
    print(f"F1分数: {metrics['f1']:.2f}")
    print(f"Precision: {metrics['precision']:.2f}%")
    print(f"Recall: {metrics['recall']:.2f}%")
    print()

    # 获取失败统计
    failure_stats = await runner.get_failure_stats(task_id)

    print("失败原因分布:")
    total_failures = sum(failure_stats.values())
    for reason, count in sorted(failure_stats.items(), key=lambda x: -x[1]):
        print(f"  {reason}: {count} 条 ({count/total_failures*100:.1f}%)")
    print()

    # 对比说明
    print("=" * 70)
    print("📈 改进效果分析")
    print("=" * 70)
    print()
    print("改进前（参考之前的测试结果）:")
    print("  准确率: 76-78%")
    print("  wrong_match: 占失败案例 ~70%")
    print()
    print("改进后（当前结果）:")
    print(f"  准确率: {metrics['accuracy']:.2f}%")
    if 'wrong_match' in failure_stats:
        wrong_match_ratio = failure_stats['wrong_match'] / total_failures * 100
        print(f"  wrong_match: 占失败案例 {wrong_match_ratio:.1f}%")
    print()

    if metrics['accuracy'] > 78:
        print("✅ 改进有效！准确率提升明显")
        improvement = metrics['accuracy'] - 77  # 使用77%作为基线
        print(f"   准确率提升: +{improvement:.1f}%")
    else:
        print("⚠️  准确率提升不明显，可能还有其他因素")
    print()

    print("💡 剩余的 wrong_match 主要原因:")
    print("   1. 标准化粒度差异（CT胸部+三维重建 vs CT三维重建）")
    print("   2. 部位映射精度（肝胆脾 vs 上腹部）")
    print("   3. 复杂复合项目无法精确拆分")
    print()


if __name__ == "__main__":
    asyncio.run(compare_improvement())

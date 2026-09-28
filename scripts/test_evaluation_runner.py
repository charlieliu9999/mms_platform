#!/usr/bin/env python3
"""
测试评测执行器 - 验证核心功能
"""

import sys
import asyncio
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from match_service.evaluation.runner import EvaluationRunner
from match_service.models.evaluation import EvalTask
from match_service.db import get_session_factory


async def test_runner():
    """测试评测执行器"""
    print("=" * 70)
    print("🧪 测试评测执行器")
    print("=" * 70)
    print()

    # 1. 创建测试任务
    print("1️⃣ 创建测试任务...")
    session_factory = get_session_factory()
    async with session_factory() as session:
        task = EvalTask(
            name="测试任务 - 评测执行器验证",
            description="验证评测执行器核心功能",
            test_file_path="tests/benchmark/16zzy_ct_115k.csv",
            sample_size=50,
            modality="CT",
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        task_id = task.id
        print(f"   ✅ 任务创建成功: ID={task_id}")
    print()

    # 2. 运行评测
    print("2️⃣ 运行评测（50条样本）...")
    runner = EvaluationRunner()

    # 进度回调
    def progress_callback(current, total, metrics):
        if current % 10 == 0 or current == total:
            print(f"   进度: {current}/{total} | "
                  f"匹配率: {metrics['match_rate']:.1f}% | "
                  f"准确率: {metrics['correct']/metrics['matched']*100 if metrics['matched'] > 0 else 0:.1f}%")

    try:
        result = await runner.run_evaluation(
            task_id=task_id,
            test_file="tests/benchmark/16zzy_ct_115k.csv",
            sample_size=50,
            modality_filter="CT",
            progress_callback=progress_callback,
        )
        print()
        print("   ✅ 评测完成")
        print()

        # 3. 显示结果
        print("3️⃣ 评测结果:")
        metrics = result['metrics']
        print(f"   匹配率: {metrics['match_rate']:.2f}%")
        print(f"   准确率: {metrics['accuracy']:.2f}%")
        print(f"   F1分数: {metrics['f1']:.2f}")
        print(f"   平均置信度: {metrics['avg_confidence']:.3f}")
        print(f"   平均响应时间: {metrics['avg_response_time']:.2f} ms")
        print(f"   总耗时: {metrics['total_duration']:.2f} 秒")
        print()

        # 4. 获取失败案例
        print("4️⃣ 失败案例分析:")
        failure_stats = await runner.get_failure_stats(task_id)
        if failure_stats:
            for reason, count in failure_stats.items():
                print(f"   {reason}: {count} 条")
            print()

            # 显示前3个失败案例
            failures = await runner.get_failure_cases(task_id, limit=3)
            if failures:
                print("   前3个失败案例:")
                for i, f in enumerate(failures, 1):
                    print(f"   [{i}] {f['check_item'][:40]}...")
                    print(f"       期望: {f['expected_name']}")
                    if f['actual_name']:
                        print(f"       实际: {f['actual_name']}")
                    else:
                        print(f"       实际: (未匹配)")
                    print(f"       原因: {f['failure_reason']}")
                    print()
        else:
            print("   ✅ 无失败案例（100%正确）")
            print()

        # 5. 验证数据库持久化
        print("5️⃣ 验证数据库持久化:")
        summary = await runner.get_task_summary(task_id)
        if summary:
            print(f"   任务状态: {summary['status']}")
            print(f"   测试总数: {summary['total_count']}")
            print(f"   匹配数量: {summary['matched_count']}")
            print(f"   正确数量: {summary['correct_count']}")
            print(f"   ✅ 数据已保存到数据库")
        print()

        print("=" * 70)
        print("✅ 测试通过！评测执行器工作正常")
        print("=" * 70)

    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_runner())

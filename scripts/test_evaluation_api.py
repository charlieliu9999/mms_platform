#!/usr/bin/env python3
"""
测试评测系统 API - 验证所有端点

测试流程：
1. 启动后端服务
2. 创建评测任务
3. 启动评测
4. 轮询进度
5. 获取结果
6. 查询失败案例
7. 清理数据
"""

import sys
import time
import requests
from pathlib import Path

BASE_URL = "http://localhost:9100"


def test_api():
    """测试评测系统 API"""
    print("=" * 70)
    print("🧪 测试评测系统 API")
    print("=" * 70)
    print()

    # 0. 健康检查（使用 docs 端点）
    print("0️⃣ 健康检查...")
    try:
        resp = requests.get(f"{BASE_URL}/docs", timeout=5)
        if resp.status_code == 200:
            print("   ✅ 后端服务正常")
        else:
            print(f"   ❌ 后端服务异常: {resp.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ 无法连接后端服务: {e}")
        print("   💡 请先启动后端: poetry run uvicorn match_service.main:app --reload --port 9100")
        return False
    print()

    # 1. 创建任务
    print("1️⃣ 创建评测任务...")
    create_data = {
        "name": "API测试任务",
        "description": "通过 API 创建的测试任务",
        "test_file_path": "tests/benchmark/16zzy_ct_115k.csv",
        "sample_size": 30,
        "modality": "CT",
        "created_by": "test_script",
    }

    try:
        resp = requests.post(f"{BASE_URL}/api/evaluation/tasks", json=create_data)
        resp.raise_for_status()
        task = resp.json()
        task_id = task['id']
        print(f"   ✅ 任务创建成功: ID={task_id}")
        print(f"      状态: {task['status']}")
        print(f"      名称: {task['name']}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ 创建任务失败: {e}")
        if hasattr(e.response, 'text'):
            print(f"      错误详情: {e.response.text}")
        return False
    print()

    # 2. 启动评测
    print("2️⃣ 启动评测...")
    try:
        resp = requests.post(f"{BASE_URL}/api/evaluation/tasks/{task_id}/start")
        resp.raise_for_status()
        result = resp.json()
        print(f"   ✅ 评测已启动: {result['message']}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ 启动评测失败: {e}")
        return False
    print()

    # 3. 轮询进度
    print("3️⃣ 轮询评测进度...")
    max_wait = 60  # 最多等待 60 秒
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            resp = requests.get(f"{BASE_URL}/api/evaluation/tasks/{task_id}")
            resp.raise_for_status()
            task = resp.json()

            status = task['status']
            progress = task['progress']

            if status == 'completed':
                print(f"   ✅ 评测完成！进度: {progress}%")
                break
            elif status == 'failed':
                print(f"   ❌ 评测失败")
                return False
            elif status == 'running':
                print(f"   ⏳ 进度: {progress}% | 已匹配: {task['matched_count']}/{task['total_count']}")
                time.sleep(2)
            else:
                print(f"   ⏳ 状态: {status}")
                time.sleep(1)

        except requests.exceptions.RequestException as e:
            print(f"   ❌ 查询进度失败: {e}")
            return False
    else:
        print(f"   ⚠️ 评测超时（>{max_wait}秒）")
        return False
    print()

    # 4. 获取任务详情
    print("4️⃣ 获取任务详情...")
    try:
        resp = requests.get(f"{BASE_URL}/api/evaluation/tasks/{task_id}")
        resp.raise_for_status()
        task = resp.json()

        print(f"   任务名称: {task['name']}")
        print(f"   状态: {task['status']}")
        print(f"   总数: {task['total_count']}")
        print(f"   匹配数: {task['matched_count']}")
        print(f"   正确数: {task['correct_count']}")
        print(f"   错误数: {task['wrong_count']}")
        print(f"   未匹配: {task['no_match_count']}")
        print()
        print(f"   📊 核心指标:")
        print(f"      匹配率: {task['match_rate']:.2f}%")
        print(f"      准确率: {task['accuracy']:.2f}%")
        print(f"      F1分数: {task['f1_score']:.2f}")
        print(f"      平均置信度: {task['avg_confidence']:.3f}")
        print(f"      平均响应时间: {task['avg_response_time']:.2f} ms")
        print()

    except requests.exceptions.RequestException as e:
        print(f"   ❌ 获取详情失败: {e}")
        return False

    # 5. 获取失败统计
    print("5️⃣ 获取失败统计...")
    try:
        resp = requests.get(f"{BASE_URL}/api/evaluation/tasks/{task_id}/failures/stats")
        resp.raise_for_status()
        stats = resp.json()

        if stats['stats']:
            print(f"   失败原因分布:")
            for reason, count in stats['stats'].items():
                print(f"      {reason}: {count} 条")
        else:
            print(f"   ✅ 无失败案例")
        print()

    except requests.exceptions.RequestException as e:
        print(f"   ❌ 获取统计失败: {e}")
        return False

    # 6. 获取失败案例
    print("6️⃣ 获取失败案例（前3条）...")
    try:
        resp = requests.get(f"{BASE_URL}/api/evaluation/tasks/{task_id}/failures?limit=3")
        resp.raise_for_status()
        failures = resp.json()

        if failures['cases']:
            print(f"   共 {failures['total']} 个失败案例，显示前 3 个:")
            for i, case in enumerate(failures['cases'], 1):
                print(f"   [{i}] {case['check_item'][:40]}...")
                print(f"       期望: {case['expected_name']}")
                if case['actual_name']:
                    print(f"       实际: {case['actual_name']}")
                else:
                    print(f"       实际: (未匹配)")
                print(f"       原因: {case['failure_reason']}")
                print()
        else:
            print(f"   ✅ 无失败案例")

    except requests.exceptions.RequestException as e:
        print(f"   ❌ 获取失败案例失败: {e}")
        return False

    # 7. 获取任务列表
    print("7️⃣ 获取任务列表...")
    try:
        resp = requests.get(f"{BASE_URL}/api/evaluation/tasks?limit=5")
        resp.raise_for_status()
        task_list = resp.json()

        print(f"   共 {task_list['total']} 个任务，显示前 {len(task_list['tasks'])} 个:")
        for task in task_list['tasks']:
            print(f"   - [{task['id']}] {task['name']} | {task['status']} | "
                  f"匹配率: {task['match_rate']:.1f}% | 准确率: {task['accuracy']:.1f}%")
        print()

    except requests.exceptions.RequestException as e:
        print(f"   ❌ 获取任务列表失败: {e}")
        return False

    # 8. 清理测试数据（可选）
    print("8️⃣ 清理测试数据...")
    cleanup = input("   是否删除测试任务？(y/N): ").strip().lower()
    if cleanup == 'y':
        try:
            resp = requests.delete(f"{BASE_URL}/api/evaluation/tasks/{task_id}")
            resp.raise_for_status()
            print(f"   ✅ 测试任务已删除")
        except requests.exceptions.RequestException as e:
            print(f"   ❌ 删除失败: {e}")
    else:
        print(f"   ⏭️  跳过清理，任务 ID={task_id} 保留")
    print()

    print("=" * 70)
    print("✅ API 测试通过！所有端点工作正常")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)

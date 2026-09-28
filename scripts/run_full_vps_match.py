#!/usr/bin/env python3
"""
VPS 全量匹配测试脚本
目标：对 4374 条影像检查项目进行匹配测试，达到 95% 匹配率
"""
import sys
import os
import time
import csv
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import requests
from datetime import datetime

# MMS 服务配置
MMS_API_BASE = os.getenv("MMS_API_BASE", "http://127.0.0.1:9100")

def create_evaluation_task(csv_file_path: str) -> int:
    """创建评测任务"""
    url = f"{MMS_API_BASE}/api/evaluation/tasks"

    payload = {
        "name": "VPS全量匹配测试 - 4374条项目",
        "description": "对VPS系统中4374条影像检查项目进行全量匹配测试，目标匹配率95%",
        "test_file_path": csv_file_path,
        "modality": "ALL",
        "tags": ["vps-full", "baseline", f"date-{datetime.now().strftime('%Y%m%d')}"]
    }

    print(f"📝 创建评测任务...")
    print(f"   数据文件: {csv_file_path}")

    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()

    task_data = response.json()
    task_id = task_data.get("task_id") or task_data.get("id")

    print(f"✅ 任务创建成功 (ID: {task_id})")
    return task_id

def start_evaluation(task_id: int):
    """启动评测任务"""
    url = f"{MMS_API_BASE}/api/evaluation/tasks/{task_id}/start"

    print(f"\n🚀 启动评测任务 {task_id}...")

    response = requests.post(url, timeout=30)
    response.raise_for_status()

    print(f"✅ 评测任务已启动")

def poll_task_status(task_id: int, poll_interval: int = 5):
    """轮询任务状态直到完成"""
    url = f"{MMS_API_BASE}/api/evaluation/tasks/{task_id}"

    print(f"\n⏳ 监控评测进度...")
    print(f"   刷新间隔: {poll_interval}秒")
    print("-" * 80)

    last_progress = -1
    start_time = time.time()

    while True:
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            task = response.json()

            status = task.get("status")
            progress = task.get("progress", 0)
            total = task.get("total_count", 0)
            matched = task.get("matched_count", 0)

            if progress != last_progress:
                elapsed = time.time() - start_time
                match_rate = (matched / total * 100) if total > 0 else 0

                print(f"[{elapsed:.0f}s] 进度: {progress}/{total} ({progress/total*100:.1f}%) | "
                      f"已匹配: {matched} ({match_rate:.2f}%)")
                last_progress = progress

            if status == "completed":
                print("-" * 80)
                print(f"✅ 评测完成！")
                return task
            elif status == "failed":
                print(f"❌ 评测失败")
                return task

            time.sleep(poll_interval)

        except KeyboardInterrupt:
            print(f"\n⚠️  用户中断")
            return None
        except Exception as e:
            print(f"⚠️  轮询出错: {e}")
            time.sleep(poll_interval)

def print_summary(task: dict):
    """打印评测结果摘要"""
    print("\n" + "=" * 80)
    print("📊 匹配结果摘要")
    print("=" * 80)

    total = task.get("total_count", 0)
    matched = task.get("matched_count", 0)
    no_match = task.get("no_match_count", 0)
    match_rate = task.get("match_rate", 0)

    print(f"总项目数:     {total:,}")
    print(f"匹配成功:     {matched:,}")
    print(f"未匹配:       {no_match:,}")
    print(f"匹配率:       {match_rate:.2f}%")

    target_rate = 95.0
    gap = target_rate - match_rate
    gap_count = int(gap / 100 * total)

    print()
    if match_rate >= target_rate:
        print(f"✅ 已达到目标匹配率 {target_rate}%！")
    else:
        print(f"⚠️  距离目标 {target_rate}% 还差 {gap:.2f}%")
        print(f"   需要额外匹配 {gap_count} 个项目")

    print("=" * 80)

def analyze_failures(task_id: int):
    """分析失败案例"""
    url = f"{MMS_API_BASE}/api/evaluation/tasks/{task_id}/analysis"

    print("\n🔍 获取失败案例分析...")

    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        analysis = response.json()

        print("\n" + "-" * 80)
        print("📋 按模态分类的匹配情况")
        print("-" * 80)

        modality_stats = analysis.get("by_modality", [])
        for stat in modality_stats[:10]:  # 显示前10个
            modality = stat.get("modality", "N/A")
            total = stat.get("total", 0)
            matched = stat.get("matched", 0)
            rate = stat.get("match_rate", 0)

            bar_length = int(rate / 100 * 30)
            bar = "█" * bar_length + "░" * (30 - bar_length)

            print(f"{modality:8} | {bar} {rate:5.1f}% ({matched:4}/{total:4})")

        print("-" * 80)

        # 显示高频失败项目
        print("\n📋 高频失败项目 TOP 10")
        print("-" * 80)

        top_failures = analysis.get("top_unmatched", [])
        for i, item in enumerate(top_failures[:10], 1):
            name = item.get("item_name", "N/A")
            count = item.get("count", 0)
            modality = item.get("modality", "N/A")
            print(f"{i:2}. [{modality:6}] {name[:50]:50} (出现 {count} 次)")

        print("-" * 80)

    except Exception as e:
        print(f"⚠️  获取分析数据失败: {e}")

def main():
    csv_file = "data/evaluation/vps_full_4374_items.csv"

    if not os.path.exists(csv_file):
        print(f"❌ 数据文件不存在: {csv_file}")
        return 1

    print("=" * 80)
    print("🏥 VPS 全量匹配测试")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标匹配率: 95%")
    print(f"数据文件: {csv_file}")
    print("=" * 80)

    try:
        # 1. 创建评测任务
        task_id = create_evaluation_task(csv_file)

        # 2. 启动评测
        start_evaluation(task_id)

        # 3. 监控进度
        task = poll_task_status(task_id, poll_interval=3)

        if task:
            # 4. 显示结果
            print_summary(task)

            # 5. 分析失败案例
            analyze_failures(task_id)

            # 6. 保存任务ID供后续分析
            with open("data/evaluation/latest_task_id.txt", "w") as f:
                f.write(str(task_id))

            print(f"\n💾 任务ID已保存到: data/evaluation/latest_task_id.txt")
            print(f"   任务ID: {task_id}")

            match_rate = task.get("match_rate", 0)
            return 0 if match_rate >= 95.0 else 1

        return 1

    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

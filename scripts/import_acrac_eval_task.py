#!/usr/bin/env python3
"""
从原系统导入ACR-AC检查项目数据作为评测任务
1. 先转换为标准CSV格式
2. 通过API创建评测任务
"""
import csv
import requests
from pathlib import Path
from datetime import datetime

# API配置
API_BASE_URL = "http://localhost:9100/api"

# 模态映射（统一到标准模态名称）
MODALITY_MAP = {
    'CT': 'CT',
    'MR': 'MR',
    'MRI': 'MR',
    'DR': 'DR',
    'XR': 'DR',
    'US': 'US',
    'DSA': 'DSA',
    'ANGIO': 'DSA',
    'IR': 'DSA',
    'RF': 'RF',
    'MG': 'MG',
    'NM': 'SPECT',
    'PET': 'PET/CT',
    'SPECT': 'SPECT',
    # 忽略非影像类型
    'THERAPY': None,
    'SURG': None,
    'ENDO': None,
    'ASSESS': None,
    'CONSULT': None,
    'FUNC': None,
    'FL': None,
}


def convert_acrac_to_standard_csv():
    """转换ACR-AC数据为标准评测CSV格式"""

    # 源文件
    source_file = Path("/Users/charlieliu/git_project_vscode/09_medical/acrac_web_mgmt/outputs/acrac_ac_standard_final_20260604/final_acrac_ac_mapping_detail.csv")

    # 输出目录和文件
    output_dir = Path("data/eval_tasks")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"acrac_全模态测试_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    if not source_file.exists():
        print(f"❌ 数据文件不存在: {source_file}")
        return None

    print(f"📁 读取数据文件: {source_file}")

    # 读取CSV数据
    with open(source_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    print(f"📊 原始数据: {len(all_rows)} 条")

    # 转换数据
    converted_rows = []
    skipped_count = 0
    modality_stats = {}

    for row in all_rows:
        original_modality = row.get('当前统计模态', '').strip()
        check_item = row.get('当前项目名', '').strip()
        expected_code = row.get('最终匹配标准编码', '').strip()
        expected_name = row.get('最终匹配标准项目名', '').strip()

        # 跳过空数据
        if not check_item or not original_modality:
            skipped_count += 1
            continue

        # 映射模态
        mapped_modality = MODALITY_MAP.get(original_modality)
        if mapped_modality is None:
            skipped_count += 1
            continue

        # 统计模态分布
        modality_stats[mapped_modality] = modality_stats.get(mapped_modality, 0) + 1

        converted_rows.append({
            'check_item': check_item,
            'modality': mapped_modality,
            'expected_code': expected_code if expected_code else '',
            'expected_name': expected_name if expected_name else '',
        })

    print(f"\n✅ 有效数据: {len(converted_rows)} 条")
    print(f"⚠️  跳过数据: {skipped_count} 条（非影像类型或数据不完整）")
    print("\n📋 按模态分布:")
    for modality, count in sorted(modality_stats.items(), key=lambda x: -x[1]):
        print(f"   {modality}: {count} 条")

    # 写入CSV
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['check_item', 'modality', 'expected_code', 'expected_name']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(converted_rows)

    print(f"\n✅ 数据已转换并保存到: {output_file}")
    print(f"📦 文件大小: {output_file.stat().st_size / 1024:.2f} KB")

    return output_file


def create_eval_task(csv_file_path):
    """通过API创建评测任务"""

    task_name = f"ACR-AC全模态匹配测试_{datetime.now().strftime('%Y%m%d_%H%M')}"
    task_desc = "从原系统ACR-AC导入的检查项目数据，覆盖CT/MR/US/DSA/SPECT/DR/RF/MG共8种模态，测试全模态匹配算法准确率"

    print(f"\n📤 创建评测任务: {task_name}")

    response = requests.post(
        f"{API_BASE_URL}/evaluation/tasks",
        json={
            "name": task_name,
            "description": task_desc,
            "test_file_path": str(csv_file_path.absolute()),
        }
    )

    if response.status_code == 200:
        result = response.json()
        task_id = result['task_id']
        print(f"✅ 成功创建任务 (ID: {task_id})")
        print(f"\n🎯 任务详情:")
        print(f"   - 任务ID: {task_id}")
        print(f"   - 任务名称: {task_name}")
        print(f"   - 测试文件: {csv_file_path}")
        print(f"\n📊 查看和执行任务：")
        print(f"   1. 前端: http://localhost:3100/evaluation")
        print(f"   2. 执行: POST {API_BASE_URL}/evaluation/tasks/{task_id}/execute")
        print(f"\n💡 执行命令:")
        print(f"   curl -X POST {API_BASE_URL}/evaluation/tasks/{task_id}/execute")
        return task_id
    else:
        print(f"❌ 创建任务失败: {response.status_code}")
        print(f"   {response.text}")
        return None


if __name__ == "__main__":
    # 步骤1: 转换CSV
    csv_file = convert_acrac_to_standard_csv()

    if csv_file:
        # 步骤2: 创建评测任务
        task_id = create_eval_task(csv_file)

        if task_id:
            print(f"\n✅ 全部完成！任务ID: {task_id}")
        else:
            print(f"\n❌ 创建任务失败，但CSV文件已生成: {csv_file}")
    else:
        print(f"\n❌ 数据转换失败")

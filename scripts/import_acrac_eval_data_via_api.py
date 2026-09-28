#!/usr/bin/env python3
"""
从原系统导入ACR-AC检查项目数据作为评测任务（通过API）
测试全模态匹配算法的准确率
"""
import csv
import requests
import json
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
    'NM': 'SPECT',  # 核医学
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


def import_acrac_eval_data():
    """导入ACR-AC评测数据"""

    # 数据文件路径
    source_file = Path("/Users/charlieliu/git_project_vscode/09_medical/acrac_web_mgmt/outputs/acrac_ac_standard_final_20260604/final_acrac_ac_mapping_detail.csv")

    if not source_file.exists():
        print(f"❌ 数据文件不存在: {source_file}")
        return

    print(f"📁 读取数据文件: {source_file}")

    # 读取CSV数据
    with open(source_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    print(f"📊 原始数据: {len(all_rows)} 条")

    # 过滤和转换数据
    test_cases = []
    skipped_count = 0
    modality_stats = {}

    for row in all_rows:
        original_modality = row.get('当前统计模态', '').strip()
        check_item = row.get('当前项目名', '').strip()
        expected_code = row.get('最终匹配标准编码', '').strip()
        expected_name = row.get('最终匹配标准项目名', '').strip()
        match_status = row.get('最终状态', '').strip()

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

        test_cases.append({
            'check_item': check_item,
            'modality': mapped_modality,
            'expected_code': expected_code if expected_code else None,
            'expected_name': expected_name if expected_name else None,
            'source': f"ACR-AC",
        })

    print(f"\n✅ 有效数据: {len(test_cases)} 条")
    print(f"⚠️  跳过数据: {skipped_count} 条（非影像类型或数据不完整）")
    print("\n📋 按模态分布:")
    for modality, count in sorted(modality_stats.items(), key=lambda x: -x[1]):
        print(f"   {modality}: {count} 条")

    # 创建评测任务
    task_name = f"ACR-AC全模态匹配测试_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    task_desc = f"从原系统ACR-AC导入的{len(test_cases)}条检查项目，覆盖{len(modality_stats)}种模态，测试全模态匹配算法"

    print(f"\n📤 创建评测任务: {task_name}")

    response = requests.post(
        f"{API_BASE_URL}/evaluation/tasks",
        json={
            "name": task_name,
            "description": task_desc,
            "test_cases": test_cases
        }
    )

    if response.status_code == 200:
        result = response.json()
        task_id = result['task_id']
        print(f"✅ 成功创建任务 (ID: {task_id})")
        print(f"✅ 导入 {len(test_cases)} 条测试用例")
        print(f"\n🎯 任务详情:")
        print(f"   - 任务ID: {task_id}")
        print(f"   - 测试用例数: {len(test_cases)}")
        print(f"   - 覆盖模态: {', '.join(sorted(modality_stats.keys()))}")
        print(f"\n📊 可以通过以下方式查看和执行任务：")
        print(f"   1. 前端: http://localhost:3100/evaluation")
        print(f"   2. API执行: POST {API_BASE_URL}/evaluation/tasks/{task_id}/execute")
        return task_id
    else:
        print(f"❌ 创建任务失败: {response.status_code}")
        print(f"   {response.text}")
        return None


if __name__ == "__main__":
    task_id = import_acrac_eval_data()
    if task_id:
        print(f"\n✅ 导入完成！任务ID: {task_id}")
    else:
        print(f"\n❌ 导入失败")

#!/usr/bin/env python3
"""
从原系统导入ACR-AC检查项目数据作为评测任务
测试全模态匹配算法的准确率
"""
import asyncio
import csv
from pathlib import Path
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# 数据库连接
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/mms_db"

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


async def import_acrac_eval_data():
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
            'source': f"ACR-AC (原模态: {original_modality})",
            'match_status': match_status,
        })

    print(f"\n✅ 有效数据: {len(test_cases)} 条")
    print(f"⚠️  跳过数据: {skipped_count} 条（非影像类型或数据不完整）")
    print("\n📋 按模态分布:")
    for modality, count in sorted(modality_stats.items(), key=lambda x: -x[1]):
        print(f"   {modality}: {count} 条")

    # 连接数据库
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 创建评测任务
        task_name = f"ACR-AC全模态匹配测试_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        task_desc = f"从原系统ACR-AC导入的{len(test_cases)}条检查项目，测试全模态匹配算法"

        result = await session.execute(text("""
            INSERT INTO evaluation_tasks (name, description, status, total_count, progress)
            VALUES (:name, :description, 'pending', :total, 0)
            RETURNING id
        """), {
            'name': task_name,
            'description': task_desc,
            'total': len(test_cases)
        })

        task_id = result.scalar()
        await session.commit()

        print(f"\n✅ 创建评测任务: {task_name} (ID: {task_id})")

        # 批量插入测试用例
        print(f"📥 开始导入测试用例...")

        await session.execute(text("""
            INSERT INTO evaluation_test_cases (
                task_id, check_item, modality,
                expected_code, expected_name,
                source, status
            ) VALUES (
                :task_id, :check_item, :modality,
                :expected_code, :expected_name,
                :source, 'pending'
            )
        """), [
            {
                'task_id': task_id,
                'check_item': case['check_item'],
                'modality': case['modality'],
                'expected_code': case['expected_code'],
                'expected_name': case['expected_name'],
                'source': case['source'],
            }
            for case in test_cases
        ])

        await session.commit()

        print(f"✅ 成功导入 {len(test_cases)} 条测试用例")
        print(f"\n🎯 任务ID: {task_id}")
        print(f"📊 可以通过以下方式查看和执行任务：")
        print(f"   1. 前端: http://localhost:3100/evaluation")
        print(f"   2. API: POST http://localhost:9100/api/evaluation/tasks/{task_id}/execute")

    await engine.dispose()

    return task_id


if __name__ == "__main__":
    task_id = asyncio.run(import_acrac_eval_data())
    print(f"\n✅ 导入完成！任务ID: {task_id}")

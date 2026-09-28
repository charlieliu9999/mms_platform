#!/usr/bin/env python3
"""
从原系统 acrac_web_mgmt 导出完整的 nlp_checkitem_standard 数据
包含所有模态（CT、MR、X线、DSA、US、PET、SPECT等）
"""
import asyncio
import csv
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 原系统数据库连接（使用与原系统相同的配置）
OLD_SYSTEM_DB_URL = "postgresql://postgres:postgres@localhost:5432/acrac_db"

async def export_standard_items():
    """导出原系统中的所有标准项目数据"""

    # 创建同步引擎用于导出
    engine = create_engine(OLD_SYSTEM_DB_URL.replace("+asyncpg", ""))
    Session = sessionmaker(bind=engine)

    output_dir = Path(__file__).parent.parent / "data" / "phase2-standard-items"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "all_standard_items.csv"

    print(f"📁 输出目录: {output_dir}")
    print(f"📄 输出文件: {output_file}")

    with Session() as session:
        # 查询所有标准项目数据
        query = text("""
            SELECT
                id,
                rule_id,
                modality_code,
                modality_name,
                one_level_name,
                two_level_name,
                three_level_name,
                scan_name,
                post_processing_name,
                position_name,
                checkitem_code,
                checkitem_name,
                version,
                is_deleted,
                scope_name,
                created_at,
                updated_at
            FROM nlp_checkitem_standard
            WHERE is_deleted = 0
            ORDER BY modality_name, one_level_name, checkitem_code
        """)

        result = session.execute(query)
        rows = result.fetchall()

        print(f"📊 查询到 {len(rows)} 条标准项目记录")

        # 按模态统计
        modality_stats = {}
        for row in rows:
            modality = row.modality_name
            modality_stats[modality] = modality_stats.get(modality, 0) + 1

        print("\n📋 按模态分布:")
        for modality, count in sorted(modality_stats.items()):
            print(f"   {modality}: {count} 条")

        # 写入CSV
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)

            # 写入表头
            writer.writerow([
                'id', 'rule_id', 'modality_code', 'modality_name',
                'one_level_name', 'two_level_name', 'three_level_name',
                'scan_name', 'post_processing_name', 'position_name',
                'checkitem_code', 'checkitem_name', 'version', 'is_deleted',
                'scope_name', 'created_at', 'updated_at'
            ])

            # 写入数据
            for row in rows:
                writer.writerow([
                    row.id, row.rule_id, row.modality_code, row.modality_name,
                    row.one_level_name, row.two_level_name, row.three_level_name,
                    row.scan_name, row.post_processing_name, row.position_name,
                    row.checkitem_code, row.checkitem_name, row.version, row.is_deleted,
                    row.scope_name, row.created_at, row.updated_at
                ])

        print(f"\n✅ 数据已导出到: {output_file}")
        print(f"📦 文件大小: {output_file.stat().st_size / 1024:.2f} KB")

        return output_file

if __name__ == "__main__":
    asyncio.run(export_standard_items())

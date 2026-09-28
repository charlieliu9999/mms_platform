#!/usr/bin/env python3
"""验证导入结果"""

import asyncio
import asyncpg

DATABASE_URL = "postgresql://postgres:password@127.0.0.1:15432/acrac_db"


async def main():
    conn = await asyncpg.connect(DATABASE_URL)

    print("=" * 80)
    print("导入后的模态分布统计")
    print("=" * 80)

    rows = await conn.fetch("""
        SELECT
            modality_code,
            modality_name,
            COUNT(*) as count
        FROM nlp_checkitem_standard
        WHERE is_deleted = 0
        GROUP BY modality_code, modality_name
        ORDER BY modality_code
    """)

    total = 0
    for row in rows:
        print(f"模态 {row['modality_code']:3s} ({row['modality_name']:8s}): {row['count']:5d} 条")
        total += row['count']

    print(f"\n总计: {total} 条标准项目")

    # 检查新导入的版本
    print("\n" + "=" * 80)
    print("新导入数据统计（version='V1.0-imported'）")
    print("=" * 80)

    imported = await conn.fetch("""
        SELECT
            modality_code,
            modality_name,
            COUNT(*) as count
        FROM nlp_checkitem_standard
        WHERE version = 'V1.0-imported' AND is_deleted = 0
        GROUP BY modality_code, modality_name
        ORDER BY modality_code
    """)

    imported_total = 0
    for row in imported:
        print(f"模态 {row['modality_code']:3s} ({row['modality_name']:8s}): {row['count']:5d} 条")
        imported_total += row['count']

    print(f"\n新导入总计: {imported_total} 条")

    # 查看几条新导入的示例
    print("\n" + "=" * 80)
    print("新导入数据示例（每个模态各1条）")
    print("=" * 80)

    for row in imported:
        sample = await conn.fetchrow("""
            SELECT checkitem_code, checkitem_name, one_level_name, scan_name
            FROM nlp_checkitem_standard
            WHERE modality_code = $1 AND version = 'V1.0-imported'
            LIMIT 1
        """, row['modality_code'])

        if sample:
            print(f"\n模态 {row['modality_name']}:")
            print(f"  编码: {sample['checkitem_code']}")
            print(f"  名称: {sample['checkitem_name']}")
            print(f"  部位: {sample['one_level_name'] or '未分类'}")
            print(f"  扫描: {sample['scan_name'] or '未分类'}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

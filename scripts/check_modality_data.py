#!/usr/bin/env python3
"""检查原系统和MMS系统的模态数据分布"""

import asyncio
import asyncpg

DATABASE_URL = "postgresql://postgres:password@127.0.0.1:15432/acrac_db"


async def check_source_data():
    """检查原系统 procedure_dictionary 表的模态分布"""
    conn = await asyncpg.connect(DATABASE_URL)

    print("=" * 80)
    print("原系统 (procedure_dictionary) 模态数据分布:")
    print("=" * 80)

    rows = await conn.fetch("""
        SELECT
            modality,
            COUNT(*) as count
        FROM procedure_dictionary
        WHERE modality IS NOT NULL AND is_active = true
        GROUP BY modality
        ORDER BY modality
    """)

    total = 0
    for row in rows:
        print(f"模态 {row['modality']:8s}: {row['count']:4d} 条")
        total += row['count']

    print(f"\n总计: {total} 条标准项目")

    await conn.close()
    return rows


async def check_target_data():
    """检查MMS系统 nlp_checkitem_standard 表的模态分布"""
    conn = await asyncpg.connect(DATABASE_URL)

    print("\n" + "=" * 80)
    print("MMS系统 (nlp_checkitem_standard) 模态数据分布:")
    print("=" * 80)

    rows = await conn.fetch("""
        SELECT
            modality_code,
            modality_name,
            COUNT(*) as count
        FROM nlp_checkitem_standard
        GROUP BY modality_code, modality_name
        ORDER BY modality_code
    """)

    if not rows:
        print("当前无数据")
    else:
        total = 0
        for row in rows:
            print(f"模态 {row['modality_code']} ({row['modality_name']:8s}): {row['count']:4d} 条")
            total += row['count']
        print(f"\n总计: {total} 条标准项目")

    await conn.close()
    return rows


async def main():
    source_data = await check_source_data()
    target_data = await check_target_data()

    # 分析需要导入的模态
    source_modalities = {row['modality'] for row in source_data}
    target_codes = {row['modality_code'] for row in target_data}

    # 模态名称到代码的映射
    modality_map = {
        'CT': 1, 'MR': 2, 'DR': 3, 'CR': 3, 'DX': 3,
        'US': 4, 'NM': 5, 'PT': 5, 'RF': 6,
        'MG': 7, 'XA': 8, 'ES': 9, 'ECG': 11,
        'PET': 10, 'OCT': 12, 'DSA': 8
    }

    print("\n" + "=" * 80)
    print("需要导入的模态:")
    print("=" * 80)

    for row in source_data:
        modality = row['modality']
        modality_code = modality_map.get(modality)

        if modality_code and modality_code not in target_codes:
            print(f"模态 {modality:8s} (code={modality_code}): {row['count']:4d} 条 - 需要导入")
        elif not modality_code:
            print(f"模态 {modality:8s} (未映射): {row['count']:4d} 条 - 需要确认映射关系")


if __name__ == "__main__":
    asyncio.run(main())

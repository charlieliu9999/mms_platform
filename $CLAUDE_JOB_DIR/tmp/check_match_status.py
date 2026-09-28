#!/usr/bin/env python3
"""检查4555条项目的匹配状态"""
import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(
        host='127.0.0.1',
        port=15432,
        user='postgres',
        password='postgres',
        database='acrac_db'
    )

    # 1. 总体统计
    print("=" * 80)
    print("总体匹配状态")
    print("=" * 80)
    result = await conn.fetchrow("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN matched_standard_id IS NOT NULL THEN 1 ELSE 0 END) as matched,
               SUM(CASE WHEN matched_standard_id IS NULL THEN 1 ELSE 0 END) as unmatched
        FROM hospital_check_items
        WHERE is_deleted = false
    """)
    total = result['total']
    matched = result['matched']
    unmatched = result['unmatched']
    match_rate = 100.0 * matched / total if total > 0 else 0
    print(f"总数: {total}")
    print(f"已匹配: {matched} ({match_rate:.1f}%)")
    print(f"未匹配: {unmatched} ({100-match_rate:.1f}%)")
    print()

    # 2. 各模态统计
    print("=" * 80)
    print("各模态匹配率")
    print("=" * 80)
    rows = await conn.fetch("""
        SELECT
            modality,
            COUNT(*) as total,
            SUM(CASE WHEN matched_standard_id IS NOT NULL THEN 1 ELSE 0 END) as matched,
            SUM(CASE WHEN matched_standard_id IS NULL THEN 1 ELSE 0 END) as unmatched
        FROM hospital_check_items
        WHERE is_deleted = false
        GROUP BY modality
        ORDER BY unmatched DESC
    """)
    for row in rows:
        m_rate = 100.0 * row['matched'] / row['total'] if row['total'] > 0 else 0
        print(f"{row['modality']:8s} | 总数:{row['total']:4d} | 已匹配:{row['matched']:4d} | 未匹配:{row['unmatched']:4d} | 匹配率:{m_rate:5.1f}%")
    print()

    # 3. DR未匹配样本（第一批目标）
    print("=" * 80)
    print("DR未匹配项样本（前30条）")
    print("=" * 80)
    dr_samples = await conn.fetch("""
        SELECT id, original_name
        FROM hospital_check_items
        WHERE is_deleted = false
          AND matched_standard_id IS NULL
          AND modality = 'DR'
        ORDER BY id
        LIMIT 30
    """)
    for i, row in enumerate(dr_samples, 1):
        print(f"{i:2d}. [{row['id']:5d}] {row['original_name']}")
    print()

    # 4. MR血管未匹配样本（第二批目标）
    print("=" * 80)
    print("MR未匹配项样本（前20条，重点看血管相关）")
    print("=" * 80)
    mr_samples = await conn.fetch("""
        SELECT id, original_name
        FROM hospital_check_items
        WHERE is_deleted = false
          AND matched_standard_id IS NULL
          AND modality = 'MR'
        ORDER BY id
        LIMIT 20
    """)
    for i, row in enumerate(mr_samples, 1):
        marker = "🔴" if any(x in row['original_name'] for x in ['MRA', 'MRV', '血管', '动脉', '静脉']) else "  "
        print(f"{marker} {i:2d}. [{row['id']:5d}] {row['original_name']}")

    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())

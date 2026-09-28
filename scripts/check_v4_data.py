#!/usr/bin/env python3
"""检查 v4.0.0 数据完整性"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    db_url = os.getenv('MATCH_SVC_DATABASE_URL', 'postgresql://postgres:password@127.0.0.1:15432/acrac_db')
    db_url_sync = db_url.replace('postgresql+asyncpg://', 'postgresql://')

    print("🔗 连接数据库...")
    conn = await asyncpg.connect(db_url_sync)

    try:
        print("\n📊 v4.0.0 数据分析:\n")

        # 总数统计
        total = await conn.fetchval("SELECT COUNT(*) FROM standard_check_items WHERE version = 'v4.0.0'")
        print(f"总数据量: {total} 条")

        # 按检查方式统计
        print("\n按检查方式（modality）统计:")
        rows = await conn.fetch("""
            SELECT modality, COUNT(*) as count
            FROM standard_check_items
            WHERE version = 'v4.0.0'
            GROUP BY modality
            ORDER BY count DESC
        """)
        for row in rows:
            print(f"  {row['modality']}: {row['count']} 条")

        # 检查关键字段
        print("\n检查关键字段完整性:")
        checks = [
            ("insurance_code", "医保编码"),
            ("body_part_l1", "一级部位"),
            ("body_part_l2", "二级部位"),
            ("body_part_l3", "三级部位"),
            ("scan_method", "扫描方式"),
        ]

        for field, label in checks:
            null_count = await conn.fetchval(f"""
                SELECT COUNT(*) FROM standard_check_items
                WHERE version = 'v4.0.0' AND ({field} IS NULL OR {field} = '')
            """)
            filled_count = total - null_count
            percentage = (filled_count / total * 100) if total > 0 else 0
            print(f"  {label} ({field}): {filled_count}/{total} ({percentage:.1f}%)")

        # 查看示例数据
        print("\n示例数据（前 3 条）:")
        samples = await conn.fetch("""
            SELECT item_code, item_name, modality, insurance_code, body_part_l1, scan_method
            FROM standard_check_items
            WHERE version = 'v4.0.0'
            ORDER BY id
            LIMIT 3
        """)
        for i, row in enumerate(samples, 1):
            print(f"\n  {i}. {row['item_name']}")
            print(f"     编码: {row['item_code']}")
            print(f"     医保: {row['insurance_code']}")
            print(f"     部位: {row['body_part_l1']}")
            print(f"     方式: {row['scan_method']}")

        # 检查重复
        print("\n检查重复数据:")
        duplicates = await conn.fetch("""
            SELECT item_code, COUNT(*) as count
            FROM standard_check_items
            WHERE version = 'v4.0.0'
            GROUP BY item_code
            HAVING COUNT(*) > 1
            LIMIT 5
        """)
        if duplicates:
            print(f"  ⚠️  发现 {len(duplicates)} 个重复编码:")
            for row in duplicates:
                print(f"     {row['item_code']}: {row['count']} 条")
        else:
            print("  ✅ 无重复数据")

        print("\n" + "="*60)
        print(f"预期数据量: 1488 条（根据文档）")
        print(f"实际数据量: {total} 条")
        print(f"差异: {1488 - total} 条")
        if total < 1488:
            print(f"⚠️  缺少数据，需要检查导入过程")
        else:
            print(f"✅ 数据完整")

    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())

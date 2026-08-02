#!/usr/bin/env python3
"""检查 nlp_checkitem_standard 表结构"""

import asyncio
import asyncpg

DATABASE_URL = "postgresql://postgres:password@127.0.0.1:15432/acrac_db"


async def main():
    conn = await asyncpg.connect(DATABASE_URL)

    print("=" * 80)
    print("nlp_checkitem_standard 表结构:")
    print("=" * 80)

    rows = await conn.fetch("""
        SELECT column_name, data_type, character_maximum_length
        FROM information_schema.columns
        WHERE table_name = 'nlp_checkitem_standard'
        ORDER BY ordinal_position
    """)

    for row in rows:
        length = f"({row['character_maximum_length']})" if row['character_maximum_length'] else ""
        print(f"  {row['column_name']:30s} {row['data_type']}{length}")

    # 查看示例数据
    print("\n" + "=" * 80)
    print("示例数据 (前3条):")
    print("=" * 80)

    sample = await conn.fetch("SELECT * FROM nlp_checkitem_standard LIMIT 3")
    if sample:
        for i, row in enumerate(sample, 1):
            print(f"\n记录 {i}:")
            for key, value in row.items():
                print(f"  {key:30s}: {value}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

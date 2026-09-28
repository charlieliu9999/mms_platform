#!/usr/bin/env python3
"""检查原系统表结构"""

import asyncio
import asyncpg

DATABASE_URL = "postgresql://postgres:password@127.0.0.1:15432/acrac_db"


async def main():
    conn = await asyncpg.connect(DATABASE_URL)

    # 检查 procedure_dictionary 表结构
    print("=" * 80)
    print("procedure_dictionary 表结构:")
    print("=" * 80)

    rows = await conn.fetch("""
        SELECT column_name, data_type, character_maximum_length
        FROM information_schema.columns
        WHERE table_name = 'procedure_dictionary'
        ORDER BY ordinal_position
    """)

    for row in rows:
        length = f"({row['character_maximum_length']})" if row['character_maximum_length'] else ""
        print(f"  {row['column_name']:30s} {row['data_type']}{length}")

    # 查看几条示例数据
    print("\n" + "=" * 80)
    print("示例数据 (前5条):")
    print("=" * 80)

    sample = await conn.fetch("SELECT * FROM procedure_dictionary LIMIT 5")
    if sample:
        # 打印列名
        cols = list(sample[0].keys())
        print("  " + " | ".join(cols))
        print("  " + "-" * 100)

        # 打印数据
        for row in sample:
            values = [str(row[col])[:20] if row[col] else 'NULL' for col in cols]
            print("  " + " | ".join(values))

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

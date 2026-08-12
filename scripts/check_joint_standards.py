#!/usr/bin/env python3
"""查询标准库中包含"关节"的项目"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from match_service.db import get_session_factory


async def main():
    factory = get_session_factory()

    async with factory() as session:
        # 查询包含"关节"的标准项
        query = text("""
            SELECT item_name, modality, body_part_l3, scan_method
            FROM standard_check_items
            WHERE is_active = true
              AND body_part_l3 LIKE '%关节%'
              AND modality IN ('CT', 'MR')
            ORDER BY modality, body_part_l3
            LIMIT 20;
        """)

        result = await session.execute(query)
        rows = result.fetchall()

        print("=" * 100)
        print(f"标准库中包含'关节'的项目（前20个）:")
        print("=" * 100)

        for row in rows:
            print(f"\n项目: {row[0]}")
            print(f"  模态: {row[1]}")
            print(f"  部位: {row[2]}")
            print(f"  扫描: {row[3] or 'N/A'}")

        print(f"\n总计: {len(rows)} 个项目")

        # 查询是否有"关节"作为独立部位的项目
        query2 = text("""
            SELECT item_name, modality, body_part_l3, scan_method
            FROM standard_check_items
            WHERE is_active = true
              AND body_part_l3 = '关节'
              AND modality IN ('CT', 'MR')
            LIMIT 10;
        """)

        result2 = await session.execute(query2)
        rows2 = result2.fetchall()

        print("\n" + "=" * 100)
        print(f"标准库中body_part_l3='关节'的项目:")
        print("=" * 100)

        if rows2:
            for row in rows2:
                print(f"\n项目: {row[0]}")
                print(f"  模态: {row[1]}")
                print(f"  部位: {row[2]}")
                print(f"  扫描: {row[3] or 'N/A'}")
        else:
            print("❌ 未找到body_part_l3='关节'的项目")
            print("这解释了为什么'CT关节(平扫)'无法匹配")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""检查标准库中的重复编码项目"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from match_service.db import get_session_factory


async def main():
    factory = get_session_factory()
    async with factory() as session:
        # 查询重复编码项
        query = text("""
            SELECT item_name, modality,
                   array_agg(item_code) as codes,
                   COUNT(DISTINCT item_code) as code_count
            FROM standard_check_items
            WHERE is_active = true
            GROUP BY item_name, modality
            HAVING COUNT(DISTINCT item_code) > 1
            ORDER BY code_count DESC, modality, item_name;
        """)

        result = await session.execute(query)
        rows = result.fetchall()

        if not rows:
            print("✓ 未发现重复编码项")
            return

        print(f"发现 {len(rows)} 个重复编码项:\n")
        print("=" * 100)

        for row in rows:
            item_name = row[0]
            modality = row[1]
            codes = row[2]
            code_count = row[3]

            print(f"\n模态: {modality}")
            print(f"项目名称: {item_name}")
            print(f"编码数量: {code_count}")
            print(f"编码列表: {codes}")

            # 查询每个编码的详细信息
            detail_query = text("""
                SELECT item_code, body_part_l3, scan_method, created_at
                FROM standard_check_items
                WHERE item_name = :item_name
                  AND modality = :modality
                  AND is_active = true
                ORDER BY created_at
            """)
            detail_result = await session.execute(
                detail_query,
                {"item_name": item_name, "modality": modality}
            )
            items = detail_result.fetchall()

            print("详细信息:")
            for item in items:
                print(f"  - 编码: {item[0]}")
                print(f"    检查部位: {item[1] or 'N/A'}")
                print(f"    扫描方式: {item[2] or 'N/A'}")
                print(f"    创建时间: {item[3]}")
                print()

            print("-" * 100)


if __name__ == "__main__":
    asyncio.run(main())

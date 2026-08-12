#!/usr/bin/env python3
"""
Phase 3B: 清理标准库重复编码

问题：MR全脊柱有重复编码
- 旧编码（ACR标准）：3003xxxx（正确，应保留）
- 新编码（自定义）：3099xxxx（重复，应禁用）

解决方案：将3099开头的重复编码设置为is_active=false
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from match_service.db import get_session_factory


async def main():
    factory = get_session_factory()

    # 要禁用的重复编码（3099开头的自定义编码）
    duplicate_codes = [
        '30990002110000',  # MR全脊柱(平扫) - 重复
        '30990002210000',  # MR全脊柱(增强) - 重复
        '30990002310000',  # MR全脊柱(平扫+增强) - 重复
    ]

    async with factory() as session:
        print("Phase 3B: 清理标准库重复编码\n")
        print("=" * 80)

        # 1. 显示要禁用的项目
        print("\n1. 检查要禁用的项目：\n")
        for code in duplicate_codes:
            query = text("""
                SELECT item_code, item_name, modality, body_part_l3, scan_method, is_active
                FROM standard_check_items
                WHERE item_code = :code
            """)
            result = await session.execute(query, {"code": code})
            row = result.fetchone()

            if row:
                print(f"  编码: {row[0]}")
                print(f"  名称: {row[1]}")
                print(f"  模态: {row[2]}")
                print(f"  部位: {row[3]}")
                print(f"  扫描: {row[4]}")
                print(f"  状态: {'启用' if row[5] else '已禁用'}")
                print()

        # 2. 确认用户是否继续
        print("-" * 80)
        confirm = input("\n是否禁用这些重复编码？(yes/no): ")

        if confirm.lower() != 'yes':
            print("操作已取消")
            return

        # 3. 禁用重复编码
        print("\n2. 禁用重复编码：\n")
        for code in duplicate_codes:
            update_query = text("""
                UPDATE standard_check_items
                SET is_active = false
                WHERE item_code = :code
            """)
            await session.execute(update_query, {"code": code})
            print(f"  ✓ 已禁用: {code}")

        await session.commit()

        # 4. 验证结果
        print("\n3. 验证结果：\n")
        verify_query = text("""
            SELECT item_name, modality,
                   array_agg(item_code) as codes,
                   COUNT(DISTINCT item_code) as code_count
            FROM standard_check_items
            WHERE is_active = true
              AND item_name LIKE '%全脊柱%'
              AND modality = 'MR'
            GROUP BY item_name, modality
            ORDER BY item_name;
        """)
        result = await session.execute(verify_query)
        rows = result.fetchall()

        for row in rows:
            print(f"  {row[0]}: {row[2]} (编码数: {row[3]})")

        print("\n" + "=" * 80)
        print("✓ Phase 3B完成：已禁用3个重复编码")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

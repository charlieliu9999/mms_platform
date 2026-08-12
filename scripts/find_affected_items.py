#!/usr/bin/env python3
"""查找使用了破坏性替换规则的实际项目"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from match_service.db import get_session_factory


async def main():
    factory = get_session_factory()

    # 破坏性规则涉及的关键词
    keywords = [
        '动脉血管成像(MRA)(增强)',
        '强化磁共振血管成像(CEMRA)',
        '动脉高分辨磁共振血管成像(HRMRA)',
        '高分辨磁共振血管成像(HRMRA)',
        '高分辨磁共振血管成像(HRMRV)',
    ]

    async with factory() as session:
        print("=" * 100)
        print("查找使用了破坏性替换规则的实际项目")
        print("=" * 100)

        total_found = 0
        for keyword in keywords:
            query = text("""
                SELECT name_zh, modality
                FROM procedure_dictionary
                WHERE name_zh LIKE :pattern
                  AND modality IN ('CT', 'MR', 'DR')
                LIMIT 10
            """)

            result = await session.execute(query, {'pattern': f'%{keyword}%'})
            rows = result.fetchall()

            if rows:
                print(f"\n关键词: '{keyword}' ({len(rows)}个)")
                for name_zh, modality in rows[:5]:
                    print(f"  {modality}: {name_zh}")
                total_found += len(rows)

        if total_found == 0:
            print("\n❌ 未找到任何使用这些规则的项目")
            print("这解释了为什么修复Pre规则后没有tier变化")


if __name__ == "__main__":
    asyncio.run(main())

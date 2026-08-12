#!/usr/bin/env python3
"""查询Pre规则中的血管成像映射"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from match_service.db import get_session_factory


async def main():
    factory = get_session_factory()

    async with factory() as session:
        # 查询包含"血管成像"或"CTA"的Pre规则
        query = text("""
            SELECT id, src_word, dst_word, step, modality, version
            FROM nlp_phrase_map
            WHERE step = 'pre'
              AND (src_word LIKE '%血管成像%' OR src_word LIKE '%CTA%' OR dst_word LIKE '%CTA%')
            ORDER BY modality, src_word
        """)

        result = await session.execute(query)
        rows = result.fetchall()

        print("=" * 100)
        print(f"Pre规则中包含'血管成像'或'CTA'的映射（共{len(rows)}条）:")
        print("=" * 100)

        for row in rows:
            print(f"\nID: {row[0]}")
            print(f"  源词: '{row[1]}'")
            print(f"  目标: '{row[2]}'")
            print(f"  步骤: {row[3]}")
            print(f"  模态: {row[4] or 'ALL'}")
            print(f"  版本: {row[5] or 'ALL'}")

            # 检查是否是破坏性替换
            if '血管成像' in row[1] and '血管成像' not in row[2]:
                print(f"  ⚠️  破坏性替换：删除了'血管成像'关键词")


if __name__ == "__main__":
    asyncio.run(main())

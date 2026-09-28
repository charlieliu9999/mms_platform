#!/usr/bin/env python3
"""
Phase 4B: 修复Pre规则破坏性替换

修复删除"血管成像"关键词的Pre规则
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from match_service.db import get_session_factory


async def main():
    factory = get_session_factory()

    # 需要修复的规则（保留"血管成像"关键词）
    fixes = [
        # MR模态
        {
            'src_word': '动脉血管成像(MRA)(增强)',
            'old_dst': ' CEMRA',
            'new_dst': '血管成像CEMRA',
            'modality': 'ALL',
        },
        {
            'src_word': '强化磁共振血管成像(CEMRA)',
            'old_dst': ' CEMRA',
            'new_dst': '血管成像CEMRA',
            'modality': 'ALL',
        },
        {
            'src_word': '动脉高分辨磁共振血管成像(HRMRA)',
            'old_dst': ' HRMRA',
            'new_dst': '血管成像HRMRA',
            'modality': 'MR',
        },
        {
            'src_word': '高分辨磁共振血管成像(HRMRA)',
            'old_dst': ' HRMRA',
            'new_dst': '血管成像HRMRA',
            'modality': 'MR',
        },
        {
            'src_word': '高分辨磁共振血管成像(HRMRV)',
            'old_dst': ' HRMRV',
            'new_dst': '血管成像HRMRV',
            'modality': 'MR',
        },
    ]

    async with factory() as session:
        print("=" * 100)
        print("Phase 4B: 修复Pre规则破坏性替换")
        print("=" * 100)

        print(f"\n将修复 {len(fixes)} 条破坏性规则\n")

        for idx, fix in enumerate(fixes, 1):
            print(f"{idx}. 源词: '{fix['src_word']}'")
            print(f"   当前目标: '{fix['old_dst']}'")
            print(f"   修复后目标: '{fix['new_dst']}'")

        # 确认
        confirm = input("\n是否执行修复？(yes/no): ")
        if confirm.lower() != 'yes':
            print("操作已取消")
            return

        print("\n开始修复...")

        fixed_count = 0
        for fix in fixes:
            # 查找匹配的规则
            query = text("""
                SELECT id FROM nlp_phrase_map
                WHERE src_word = :src_word
                  AND dst_word = :old_dst
                  AND step = 'pre'
                  AND (modality = :modality OR modality IS NULL)
            """)

            result = await session.execute(query, {
                'src_word': fix['src_word'],
                'old_dst': fix['old_dst'],
                'modality': fix['modality'],
            })
            rows = result.fetchall()

            if not rows:
                print(f"  ⚠️  未找到: {fix['src_word']}")
                continue

            # 更新规则
            for row in rows:
                rule_id = row[0]
                update = text("""
                    UPDATE nlp_phrase_map
                    SET dst_word = :new_dst
                    WHERE id = :id
                """)

                await session.execute(update, {
                    'new_dst': fix['new_dst'],
                    'id': rule_id,
                })

                fixed_count += 1
                print(f"  ✓ 已修复 ID={rule_id}: '{fix['src_word']}'")

        await session.commit()

        print(f"\n总计修复 {fixed_count} 条规则")
        print("=" * 100)
        print("\n✓ Phase 4B完成：Pre规则破坏性替换已修复")
        print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())

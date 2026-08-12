#!/usr/bin/env python3
"""清除DR乳腺检查的缓存记录以测试新的路由逻辑"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from match_service.db import get_session_factory
from match_service.cache.models import MatchCache


async def main():
    factory = get_session_factory()
    async with factory() as session:
        # 查询DR乳腺相关的缓存
        from sqlalchemy import select, delete

        stmt = select(MatchCache).where(
            MatchCache.modality == 'DR'
        ).where(
            MatchCache.original_text.contains('乳腺')
        )

        result = await session.execute(stmt)
        records = result.scalars().all()

        print(f"找到 {len(records)} 条DR乳腺相关的缓存记录")
        for rec in records[:5]:
            print(f"  - {rec.original_text}")

        if records:
            # 删除这些记录
            delete_stmt = delete(MatchCache).where(
                MatchCache.modality == 'DR'
            ).where(
                MatchCache.original_text.contains('乳腺')
            )

            await session.execute(delete_stmt)
            await session.commit()
            print(f"✓ 已删除 {len(records)} 条缓存记录")
        else:
            print("未找到需要清除的缓存")


if __name__ == "__main__":
    asyncio.run(main())

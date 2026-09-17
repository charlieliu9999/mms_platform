#!/usr/bin/env python3
"""分析未匹配的检查项目，找出可优化的模式"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import select, func, and_
from match_service.db import get_session_factory
from match_service.cache.models import Base

# 使用原系统的数据库连接
sys.path.insert(0, "/Users/charlieliu/git_project_vscode/09_medical/acrac_web_mgmt/acrac_backend")
from app.db.database import get_async_session
from app.db.models import CheckItem, StandardItem


async def analyze_unmatched():
    """分析未匹配项目"""
    async for session in get_async_session():
        # 1. 统计总体情况
        total_stmt = select(func.count(CheckItem.id)).where(CheckItem.is_deleted == False)
        unmatched_stmt = select(func.count(CheckItem.id)).where(
            and_(CheckItem.is_deleted == False, CheckItem.standard_item_id.is_(None))
        )

        total_result = await session.execute(total_stmt)
        total = total_result.scalar()

        unmatched_result = await session.execute(unmatched_stmt)
        unmatched = unmatched_result.scalar()

        matched = total - unmatched
        match_rate = matched / total * 100 if total > 0 else 0

        print("=" * 80)
        print(f"总体匹配情况")
        print("=" * 80)
        print(f"总项目数: {total}")
        print(f"已匹配: {matched} ({match_rate:.1f}%)")
        print(f"未匹配: {unmatched} ({100-match_rate:.1f}%)")
        print()

        # 2. 按模态统计未匹配分布
        stmt = select(
            CheckItem.modality,
            func.count(CheckItem.id).label('count')
        ).where(
            and_(CheckItem.is_deleted == False, CheckItem.standard_item_id.is_(None))
        ).group_by(
            CheckItem.modality
        ).order_by(
            func.count(CheckItem.id).desc()
        )

        result = await session.execute(stmt)
        modality_stats = result.all()

        print("=" * 80)
        print("未匹配项目模态分布")
        print("=" * 80)
        for modality, count in modality_stats:
            pct = count / unmatched * 100
            print(f"{modality or '空':<10} {count:>4} ({pct:>5.1f}%)")
        print()

        # 3. 分析主要模态的未匹配示例
        for modality, count in modality_stats:
            if count < 20:  # 只分析数量较多的模态
                continue

            print("=" * 80)
            print(f"{modality} 模态未匹配示例 (共{count}个)")
            print("=" * 80)

            stmt = select(CheckItem).where(
                and_(
                    CheckItem.is_deleted == False,
                    CheckItem.modality == modality,
                    CheckItem.standard_item_id.is_(None)
                )
            ).limit(15)

            result = await session.execute(stmt)
            items = result.scalars().all()

            for i, item in enumerate(items, 1):
                print(f"{i:2d}. {item.name}")
            print()

        # 4. 特殊分析：查看是否有明显的模式
        print("=" * 80)
        print("文本长度分析（未匹配项目）")
        print("=" * 80)

        stmt = select(CheckItem).where(
            and_(CheckItem.is_deleted == False, CheckItem.standard_item_id.is_(None))
        )
        result = await session.execute(stmt)
        all_unmatched = result.scalars().all()

        # 按长度分组
        length_groups = {
            "短文本(≤5字)": 0,
            "中等(6-15字)": 0,
            "长文本(>15字)": 0
        }

        for item in all_unmatched:
            name_len = len(item.name)
            if name_len <= 5:
                length_groups["短文本(≤5字)"] += 1
            elif name_len <= 15:
                length_groups["中等(6-15字)"] += 1
            else:
                length_groups["长文本(>15字)"] += 1

        for group, count in length_groups.items():
            pct = count / len(all_unmatched) * 100
            print(f"{group:<15} {count:>4} ({pct:>5.1f}%)")
        print()

        # 5. 查找可能的问题模式
        print("=" * 80)
        print("可能的问题模式")
        print("=" * 80)

        # 包含特殊字符的
        special_char_items = [item for item in all_unmatched if any(c in item.name for c in ['(', ')', '（', '）', '+', '-', '/', '、'])]
        print(f"包含特殊字符: {len(special_char_items)} ({len(special_char_items)/len(all_unmatched)*100:.1f}%)")
        if special_char_items:
            print("示例:")
            for item in special_char_items[:5]:
                print(f"  - {item.name}")
        print()

        # 包含数字的
        digit_items = [item for item in all_unmatched if any(c.isdigit() for c in item.name)]
        print(f"包含数字: {len(digit_items)} ({len(digit_items)/len(all_unmatched)*100:.1f}%)")
        if digit_items:
            print("示例:")
            for item in digit_items[:5]:
                print(f"  - {item.name}")
        print()

        # 包含英文的
        english_items = [item for item in all_unmatched if any(c.isalpha() and ord(c) < 128 for c in item.name)]
        print(f"包含英文: {len(english_items)} ({len(english_items)/len(all_unmatched)*100:.1f}%)")
        if english_items:
            print("示例:")
            for item in english_items[:5]:
                print(f"  - {item.name}")
        print()


if __name__ == "__main__":
    asyncio.run(analyze_unmatched())

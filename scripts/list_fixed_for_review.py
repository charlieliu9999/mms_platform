#!/usr/bin/env python3
"""列出所有已修复项目，供审核"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from match_service.db import get_engine, AsyncSession
from sqlalchemy import text
from match_service.core.engine_holder import EngineHolder


async def list_fixed_items():
    """列出所有已修复的项目及其匹配结果"""
    
    holder = EngineHolder()
    await holder.initialize()
    engine = holder.match_engine
    
    db_engine = get_engine()
    
    # 获取所有open状态的CT/MR未匹配项
    async with AsyncSession(db_engine) as session:
        sql = text("""
            SELECT u.id, u.modality, u.reason_code, p.name_zh as name
            FROM unmatched_registry u
            JOIN procedure_dictionary p ON p.id = u.procedure_id
            WHERE u.status = 'open' 
              AND u.modality IN ('CT', 'MR')
            ORDER BY u.modality, p.name_zh
        """)
        result = await session.execute(sql)
        all_items = result.fetchall()
    
    # 找出已修复的（现在能匹配上的）
    fixed_ct = []
    fixed_mr = []
    
    for item in all_items:
        result = engine.match(item.name, item.modality)
        if result['tier'] != 'none':
            # 获取匹配到的标准项
            standards = []
            if result['data']:
                for match_item in result['data'][:3]:  # 最多3个
                    for std in match_item.get('standard', [])[:2]:  # 每个最多2个标准项
                        standards.append(std.get('name', ''))
            
            item_info = {
                'name': item.name,
                'modality': item.modality,
                'tier': result['tier'],
                'num': result['num_standard'],
                'standards': standards[:5]  # 最多显示5个标准项
            }
            
            if item.modality == 'CT':
                fixed_ct.append(item_info)
            else:
                fixed_mr.append(item_info)
    
    # 输出CT
    print("="*100)
    print(f"CT已修复项目（{len(fixed_ct)}项）- 供审核")
    print("="*100)
    print()
    
    for i, item in enumerate(fixed_ct, 1):
        print(f"{i}. {item['name']}")
        print(f"   匹配结果: tier={item['tier']}, 标准项数量={item['num']}")
        print(f"   匹配到的标准项:")
        for std in item['standards']:
            print(f"     - {std}")
        print()
    
    # 输出MR
    print("="*100)
    print(f"MR已修复项目（{len(fixed_mr)}项）- 供审核")
    print("="*100)
    print()
    
    for i, item in enumerate(fixed_mr, 1):
        print(f"{i}. {item['name']}")
        print(f"   匹配结果: tier={item['tier']}, 标准项数量={item['num']}")
        print(f"   匹配到的标准项:")
        for std in item['standards']:
            print(f"     - {std}")
        print()
    
    print("="*100)
    print(f"总计: CT {len(fixed_ct)}项 + MR {len(fixed_mr)}项 = {len(fixed_ct) + len(fixed_mr)}项")
    print("="*100)
    
    await holder.dispose()
    await db_engine.dispose()


if __name__ == "__main__":
    asyncio.run(list_fixed_items())

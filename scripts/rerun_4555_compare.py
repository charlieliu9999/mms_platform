#!/usr/bin/env python3
"""重跑4555条数据，对比修复前后的实际效果"""
import asyncio
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from match_service.db import get_engine, AsyncSession
from sqlalchemy import select, text
from match_service.core.engine_holder import EngineHolder


async def rerun_4555_and_compare():
    """重跑4555条，对比修复前后"""
    
    holder = EngineHolder()
    await holder.initialize()
    engine = holder.match_engine
    
    db_engine = get_engine()
    
    # 1. 获取所有4555条数据的原始tier状态
    async with AsyncSession(db_engine) as session:
        # 从match_results获取原始数据
        sql = text("""
            SELECT 
                original_input as name,
                modality,
                tier as old_tier
            FROM match_results
            WHERE modality IN ('CT', 'MR')
            ORDER BY modality, original_input
        """)
        result = await session.execute(sql)
        all_items = result.fetchall()
    
    print(f"总记录数: {len(all_items)}")
    
    # 2. 用当前引擎重新匹配
    stats_before = defaultdict(lambda: {'CT': 0, 'MR': 0})
    stats_after = defaultdict(lambda: {'CT': 0, 'MR': 0})
    
    improved_items = []
    degraded_items = []
    
    for item in all_items:
        name = item.name
        modality = item.modality
        old_tier = item.old_tier
        
        # 统计修复前
        stats_before[old_tier][modality] += 1
        
        # 重新匹配
        result = engine.match(name, modality)
        new_tier = result['tier']
        
        # 统计修复后
        stats_after[new_tier][modality] += 1
        
        # 记录变化
        if old_tier == 'none' and new_tier != 'none':
            improved_items.append((modality, name, old_tier, new_tier))
        elif old_tier != 'none' and new_tier == 'none':
            degraded_items.append((modality, name, old_tier, new_tier))
    
    # 3. 输出对比结果
    print("\n" + "="*80)
    print("修复前后对比 - 4555条完整数据")
    print("="*80)
    
    print("\n【CT未匹配数量对比】")
    ct_none_before = stats_before['none']['CT']
    ct_none_after = stats_after['none']['CT']
    ct_improve = ct_none_before - ct_none_after
    print(f"修复前: {ct_none_before}项")
    print(f"修复后: {ct_none_after}项")
    print(f"改善: {ct_improve}项 ({ct_improve*100/ct_none_before:.1f}%)")
    
    print("\n【MR未匹配数量对比】")
    mr_none_before = stats_before['none']['MR']
    mr_none_after = stats_after['none']['MR']
    mr_improve = mr_none_before - mr_none_after
    print(f"修复前: {mr_none_before}项")
    print(f"修复后: {mr_none_after}项")
    print(f"改善: {mr_improve}项 ({mr_improve*100/mr_none_before:.1f}%)")
    
    print("\n【总计】")
    total_none_before = ct_none_before + mr_none_before
    total_none_after = ct_none_after + mr_none_after
    total_improve = total_none_before - total_none_after
    print(f"修复前未匹配: {total_none_before}项")
    print(f"修复后未匹配: {total_none_after}项")
    print(f"总改善: {total_improve}项")
    
    # 4. 列出改善的项目
    if improved_items:
        print(f"\n【改善的项目】{len(improved_items)}项")
        ct_improved = [x for x in improved_items if x[0] == 'CT']
        mr_improved = [x for x in improved_items if x[0] == 'MR']
        
        if ct_improved:
            print(f"\nCT改善 {len(ct_improved)}项:")
            for modality, name, old, new in ct_improved[:20]:
                print(f"  {old} → {new}: {name}")
            if len(ct_improved) > 20:
                print(f"  ... 还有{len(ct_improved)-20}项")
        
        if mr_improved:
            print(f"\nMR改善 {len(mr_improved)}项:")
            for modality, name, old, new in mr_improved[:20]:
                print(f"  {old} → {new}: {name}")
            if len(mr_improved) > 20:
                print(f"  ... 还有{len(mr_improved)-20}项")
    
    # 5. 列出退步的项目
    if degraded_items:
        print(f"\n【退步的项目】{len(degraded_items)}项")
        for modality, name, old, new in degraded_items:
            print(f"  {modality} {old} → {new}: {name}")
    
    # 6. 仍未匹配的项目统计
    still_none_ct = [x for x in all_items if x.modality == 'CT' and 
                     engine.match(x.name, x.modality)['tier'] == 'none']
    still_none_mr = [x for x in all_items if x.modality == 'MR' and 
                     engine.match(x.name, x.modality)['tier'] == 'none']
    
    print(f"\n【仍未匹配】")
    print(f"CT: {len(still_none_ct)}项")
    print(f"MR: {len(still_none_mr)}项")
    
    await holder.dispose()
    await db_engine.dispose()


if __name__ == "__main__":
    asyncio.run(rerun_4555_and_compare())

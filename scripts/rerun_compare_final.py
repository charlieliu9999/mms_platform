#!/usr/bin/env python3
"""重跑unmatched_registry中的open项，对比修复前后"""
import asyncio
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from match_service.db import get_engine, AsyncSession
from sqlalchemy import text
from match_service.core.engine_holder import EngineHolder


async def rerun_and_compare():
    """重跑open项，对比修复效果"""
    
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
    
    print(f"Open未匹配项总数: {len(all_items)}")
    
    # 重新匹配并统计
    ct_before = len([x for x in all_items if x.modality == 'CT'])
    mr_before = len([x for x in all_items if x.modality == 'MR'])
    
    ct_fixed = []
    mr_fixed = []
    ct_still_none = []
    mr_still_none = []
    
    for item in all_items:
        name = item.name
        modality = item.modality
        
        result = engine.match(name, modality)
        tier = result['tier']
        
        if tier != 'none':
            if modality == 'CT':
                ct_fixed.append((name, tier, result['num_standard']))
            else:
                mr_fixed.append((name, tier, result['num_standard']))
        else:
            if modality == 'CT':
                ct_still_none.append(name)
            else:
                mr_still_none.append(name)
    
    # 输出结果
    print("\n" + "="*80)
    print("修复效果对比")
    print("="*80)
    
    print(f"\n【CT】")
    print(f"修复前未匹配: {ct_before}项")
    print(f"修复后仍未匹配: {len(ct_still_none)}项")
    print(f"已修复: {len(ct_fixed)}项 ({len(ct_fixed)*100/ct_before:.1f}%)")
    
    print(f"\n【MR】")
    print(f"修复前未匹配: {mr_before}项")
    print(f"修复后仍未匹配: {len(mr_still_none)}项")
    print(f"已修复: {len(mr_fixed)}项 ({len(mr_fixed)*100/mr_before:.1f}%)")
    
    print(f"\n【总计】")
    total_before = ct_before + mr_before
    total_fixed = len(ct_fixed) + len(mr_fixed)
    total_still = len(ct_still_none) + len(mr_still_none)
    print(f"修复前未匹配: {total_before}项")
    print(f"修复后仍未匹配: {total_still}项")
    print(f"已修复: {total_fixed}项 ({total_fixed*100/total_before:.1f}%)")
    
    # 列出已修复的项目
    if ct_fixed:
        print(f"\n【CT已修复】{len(ct_fixed)}项:")
        for name, tier, num in ct_fixed[:30]:
            print(f"  {tier:10s} (n={num}) {name}")
        if len(ct_fixed) > 30:
            print(f"  ... 还有{len(ct_fixed)-30}项")
    
    if mr_fixed:
        print(f"\n【MR已修复】{len(mr_fixed)}项:")
        for name, tier, num in mr_fixed[:30]:
            print(f"  {tier:10s} (n={num}) {name}")
        if len(mr_fixed) > 30:
            print(f"  ... 还有{len(mr_fixed)-30}项")
    
    # 仍未匹配的分析
    print(f"\n【CT仍未匹配】{len(ct_still_none)}项:")
    for name in ct_still_none[:20]:
        print(f"  {name}")
    if len(ct_still_none) > 20:
        print(f"  ... 还有{len(ct_still_none)-20}项")
    
    print(f"\n【MR仍未匹配】{len(mr_still_none)}项:")
    for name in mr_still_none[:20]:
        print(f"  {name}")
    if len(mr_still_none) > 20:
        print(f"  ... 还有{len(mr_still_none)-20}项")
    
    # 差距分析
    print("\n" + "="*80)
    print("差距分析")
    print("="*80)
    print(f"CT修复率: {len(ct_fixed)*100/ct_before:.1f}%，仍需解决{len(ct_still_none)}项")
    print(f"MR修复率: {len(mr_fixed)*100/mr_before:.1f}%，仍需解决{len(mr_still_none)}项")
    
    # 下一步建议
    print("\n" + "="*80)
    print("下一步")
    print("="*80)
    if len(ct_still_none) > 0 or len(mr_still_none) > 0:
        print("Phase 2: 查表逻辑增强（部位层级、泛化、模糊匹配）")
        print("Phase 3: 标准库补充")
    else:
        print("所有项目已修复！")
    
    await holder.dispose()
    await db_engine.dispose()


if __name__ == "__main__":
    asyncio.run(rerun_and_compare())

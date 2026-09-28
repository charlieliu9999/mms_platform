#!/usr/bin/env python3
"""对比修复前后的效果"""
import asyncio
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from match_service.db import get_engine, AsyncSession
from sqlalchemy import select, text
from match_service.core.engine_holder import EngineHolder


async def compare_before_after():
    """对比修复前后的匹配效果"""
    
    # 初始化引擎
    holder = EngineHolder()
    await holder.initialize()
    engine = holder.match_engine
    
    # 获取数据库引擎
    db_engine = get_engine()
    
    print("="*80)
    print("修复前后对比测试")
    print("="*80)
    
    # 查询所有CT/MR未匹配项
    async with AsyncSession(db_engine) as session:
        sql = text("""
            SELECT DISTINCT 
                check_item_name as name,
                modality
            FROM match_cache
            WHERE tier = 'none'
              AND modality IN ('CT', 'MR')
              AND check_item_name NOT LIKE '%放疗%'
              AND check_item_name NOT LIKE '%定位%'
              AND check_item_name NOT LIKE '%穿刺%'
              AND check_item_name NOT LIKE '%活检%'
            ORDER BY modality, check_item_name
        """)
        result = await session.execute(sql)
        unmatched_items = result.fetchall()
    
    print(f"\n数据库中tier=none的CT/MR项: {len(unmatched_items)}条\n")
    
    # 统计
    stats = {
        'total': len(unmatched_items),
        'ct_total': 0,
        'mr_total': 0,
        'ct_improved': 0,
        'mr_improved': 0,
        'ct_degraded': 0,
        'mr_degraded': 0,
        'improved_items': [],
        'degraded_items': [],
    }
    
    # 重新匹配每一项
    for item in unmatched_items:
        name = item.name
        modality = item.modality
        
        if modality == 'CT':
            stats['ct_total'] += 1
        else:
            stats['mr_total'] += 1
        
        # 使用当前引擎重新匹配
        result = engine.match(name, modality)
        new_tier = result['tier']
        
        # 如果从none变为非none，说明改善了
        if new_tier != 'none':
            if modality == 'CT':
                stats['ct_improved'] += 1
            else:
                stats['mr_improved'] += 1
            stats['improved_items'].append((modality, name, new_tier))
        
        # 理论上不应该有退步（因为数据库记录的是none）
        # 但如果有，也要记录
    
    print("="*80)
    print("统计结果")
    print("="*80)
    print(f"\n总计未匹配项: {stats['total']}条")
    print(f"  CT: {stats['ct_total']}条")
    print(f"  MR: {stats['mr_total']}条")
    
    print(f"\n修复后改善:")
    print(f"  CT改善: {stats['ct_improved']}条 ({stats['ct_improved']*100/stats['ct_total']:.1f}%)" if stats['ct_total'] > 0 else "  CT改善: 0条")
    print(f"  MR改善: {stats['mr_improved']}条 ({stats['mr_improved']*100/stats['mr_total']:.1f}%)" if stats['mr_total'] > 0 else "  MR改善: 0条")
    print(f"  总改善: {stats['ct_improved']+stats['mr_improved']}条 ({(stats['ct_improved']+stats['mr_improved'])*100/stats['total']:.1f}%)")
    
    if stats['improved_items']:
        print(f"\n改善的项目明细:")
        for modality, name, new_tier in stats['improved_items']:
            print(f"  ✅ {modality:4s} {new_tier:10s} {name}")
    
    if stats['degraded_items']:
        print(f"\n退步的项目明细:")
        for modality, name, old_tier, new_tier in stats['degraded_items']:
            print(f"  ❌ {modality:4s} {old_tier} → {new_tier} {name}")
    
    print("\n" + "="*80)
    print("结论")
    print("="*80)
    
    total_improved = stats['ct_improved'] + stats['mr_improved']
    total_degraded = stats['ct_degraded'] + stats['mr_degraded']
    
    if total_improved > 0 and total_degraded == 0:
        print("✅ 修复成功！有改善，无退步")
    elif total_improved > total_degraded:
        print("⚠️  修复有效但有副作用，改善多于退步")
    elif total_improved == 0 and total_degraded == 0:
        print("⚪ 修复对tier=none的项目无明显影响")
    else:
        print("❌ 修复导致退步，需要回滚")
    
    print(f"\n净改善: {total_improved - total_degraded}条")
    print(f"改善率: {total_improved*100/stats['total']:.1f}%")
    
    await holder.dispose()
    await db_engine.dispose()


if __name__ == "__main__":
    asyncio.run(compare_before_after())

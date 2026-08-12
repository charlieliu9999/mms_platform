#!/usr/bin/env python3
"""分析仍未匹配的项目，规划Phase 2"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from match_service.db import get_engine, AsyncSession
from sqlalchemy import text
from match_service.core.engine_holder import EngineHolder


async def analyze_still_unmatched():
    """分析仍未匹配的项目"""
    
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
    
    # 找出仍未匹配的
    still_none = []
    for item in all_items:
        result = engine.match(item.name, item.modality)
        if result['tier'] == 'none':
            # 获取trace信息
            trace = {}
            result = engine.match(item.name, item.modality, trace=trace)
            still_none.append({
                'name': item.name,
                'modality': item.modality,
                'trace': trace
            })
    
    print(f"仍未匹配: {len(still_none)}项\n")
    
    # 分类分析
    categories = {
        'design_exclude': [],  # 设计排除
        'parser_fail': [],      # 解析失败
        'lookup_fail': [],      # 查表失败（有实体但查不到）
        'standard_gap': [],     # 标准库缺口
    }
    
    for item in still_none:
        name = item['name']
        modality = item['modality']
        trace = item['trace']
        
        # 设计排除
        if '穿刺' in name or '活检' in name or '定位' in name or '放疗' in name:
            categories['design_exclude'].append(name)
            continue
        
        # 检查是否有实体识别结果
        has_entities = False
        if '9-find_default_process' in trace:
            nodes = trace['9-find_default_process']
            if nodes:
                has_entities = True
                
                # 打印前几个看看实体识别情况
                if len(categories['lookup_fail']) < 10:
                    node = nodes[0]
                    categories['lookup_fail'].append({
                        'name': name,
                        'modality': modality,
                        'node': str(node)[:200]
                    })
        
        if not has_entities:
            categories['parser_fail'].append(name)
    
    # 输出分析
    print("="*80)
    print("Phase 2 实施规划")
    print("="*80)
    
    print(f"\n【设计排除】{len(categories['design_exclude'])}项 - 无需处理")
    for name in categories['design_exclude'][:10]:
        print(f"  {name}")
    
    print(f"\n【解析失败】{len(categories['parser_fail'])}项 - 词库补充")
    for name in categories['parser_fail'][:10]:
        print(f"  {name}")
    
    print(f"\n【查表失败】{len(categories['lookup_fail'])}项 - 查表逻辑增强（Phase 2重点）")
    for item in categories['lookup_fail'][:10]:
        print(f"  {item['modality']}: {item['name']}")
        print(f"    实体: {item['node']}")
    
    print(f"\n剩余: {len(still_none) - len(categories['design_exclude']) - len(categories['parser_fail']) - len(categories['lookup_fail'])}项")
    
    print("\n" + "="*80)
    print("Phase 2 具体任务")
    print("="*80)
    print(f"目标: 解决查表失败的{len(categories['lookup_fail'])}项")
    print("方法:")
    print("  1. 部位层级映射（小肠→全腹部）")
    print("  2. 扫描方式模糊匹配（特殊序列→基础扫描）")
    print("  3. 后处理忽略（三维重建、MPR等）")
    print("  4. 部位泛化（四肢及关节→具体关节）")
    
    await holder.dispose()
    await db_engine.dispose()


if __name__ == "__main__":
    asyncio.run(analyze_still_unmatched())

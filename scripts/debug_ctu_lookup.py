#!/usr/bin/env python3
"""调试查表逻辑 - 追踪CT尿路造影的查表过程"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from match_service.core.engine_holder import EngineHolder
import pandas as pd


async def debug_ctu_lookup():
    """调试CT尿路造影查表失败问题"""
    
    # 初始化引擎
    holder = EngineHolder()
    await holder.initialize()
    engine = holder.match_engine
    
    # 测试案例
    test_name = "CT尿路造影(平扫+增强)"
    print(f"{'='*80}")
    print(f"测试案例: {test_name}")
    print(f"{'='*80}\n")
    
    # 1. 执行匹配，获取trace
    trace = {}
    result = engine.match(test_name, 'CT', trace=trace)
    
    print("1. 匹配结果:")
    print(f"   Tier: {result['tier']}")
    print(f"   匹配数: {result['num_standard']}")
    print(f"   Has entity: {result.get('has_entity', False)}")
    print()
    
    # 2. 查看预处理结果
    if '1-preprocess' in trace:
        print("2. 预处理结果:")
        print(f"   {trace['1-preprocess']}")
        print()
    
    # 3. 查看trace中所有的键
    print("3. Trace中的所有步骤:")
    for key in sorted(trace.keys()):
        print(f"   {key}: {type(trace[key])}")
    print()
    
    # 4. 直接查询标准表
    print("4. 标准表中的相关项:")
    df_std = engine.data_loader.df_standard.get('CT', {}).get('v1', None)
    if df_std is not None:
        print(f"   标准表总数: {len(df_std)} 项")
        
        # 查找包含"尿路"的项
        mask = df_std['checkitem_name'].str.contains('尿路', na=False)
        urinary_items = df_std[mask]
        print(f"\n   包含'尿路'的标准项: {len(urinary_items)} 项")
        for _, row in urinary_items.iterrows():
            print(f"   [{row['checkitem_code']}] {row['checkitem_name']}")
            print(f"     three_level_name: '{row['three_level_name']}'")
            print(f"     scan_name: '{row['scan_name']}'")
            print(f"     post_processing_name: '{row['post_processing_name']}'")
            print()
    
    # 5. 模拟查表逻辑
    print("5. 模拟查表逻辑:")
    lookup_service = engine.standard_lookup_service
    
    # 假设引擎解析出的值（需要从实际trace确认）
    bodies = ['全腹部']  # 从trace推测
    scan = ['尿路造影成像(CTU)']  # 从trace推测
    post = []
    
    print(f"   输入参数:")
    print(f"     bodies: {bodies}")
    print(f"     scan: {scan}")
    print(f"     post: {post}")
    print()
    
    # 测试不同的查询条件
    if df_std is not None:
        # 测试1: 精确匹配
        print("   测试1: 精确匹配")
        mask1 = (
            df_std['three_level_name'].isin(bodies) &
            df_std['scan_name'].isin(scan) &
            ((df_std['post_processing_name'] == '') | df_std['post_processing_name'].isna())
        )
        result1 = df_std[mask1]
        print(f"     结果: {len(result1)} 项")
        if not result1.empty:
            for _, row in result1.iterrows():
                print(f"       [{row['checkitem_code']}] {row['checkitem_name']}")
        print()
        
        # 测试2: 放宽scan条件（去除空格）
        print("   测试2: scan规范化（去除空格、统一括号）")
        scan_normalized = ['尿路造影成像(CTU)'.replace(' ', '').replace('（', '(').replace('）', ')')]
        mask2 = (
            df_std['three_level_name'].isin(bodies) &
            df_std['scan_name'].str.replace(' ', '').str.replace('（', '(').str.replace('）', ')').isin(scan_normalized) &
            ((df_std['post_processing_name'] == '') | df_std['post_processing_name'].isna())
        )
        result2 = df_std[mask2]
        print(f"     结果: {len(result2)} 项")
        if not result2.empty:
            for _, row in result2.iterrows():
                print(f"       [{row['checkitem_code']}] {row['checkitem_name']}")
        print()
        
        # 测试3: 模糊匹配
        print("   测试3: 模糊匹配（包含'尿路造影'）")
        mask3 = (
            df_std['three_level_name'].isin(bodies) &
            df_std['scan_name'].str.contains('尿路造影', na=False)
        )
        result3 = df_std[mask3]
        print(f"     结果: {len(result3)} 项")
        if not result3.empty:
            for _, row in result3.iterrows():
                print(f"       [{row['checkitem_code']}] {row['checkitem_name']}")
        print()
        
        # 测试4: 检查标准表中实际存储的值
        print("   测试4: 检查标准表中的实际值")
        for _, row in urinary_items.iterrows():
            three_level = row['three_level_name']
            scan_val = row['scan_name']
            post_val = row['post_processing_name']
            
            print(f"   标准项: {row['checkitem_name']}")
            print(f"     three_level_name: '{three_level}' (type: {type(three_level)})")
            print(f"     scan_name: '{scan_val}' (type: {type(scan_val)})")
            print(f"     post_processing_name: '{post_val}' (type: {type(post_val)})")
            print(f"     比较结果:")
            print(f"       three_level in bodies: {three_level in bodies}")
            print(f"       scan in scan: {scan_val in scan}")
            print(f"       '全腹部' == three_level: {'全腹部' == three_level}")
            print(f"       '尿路造影成像(CTU)' == scan_val: {'尿路造影成像(CTU)' == scan_val}")
            print()
    
    await holder.dispose()


if __name__ == "__main__":
    asyncio.run(debug_ctu_lookup())

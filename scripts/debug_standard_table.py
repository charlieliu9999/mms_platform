#!/usr/bin/env python3
"""调试查表逻辑 - 检查标准表数据和查询逻辑"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from match_service.core.engine_holder import EngineHolder
import pandas as pd


async def debug_standard_table():
    """检查标准表数据结构和查询逻辑"""
    
    # 初始化引擎
    holder = EngineHolder()
    await holder.initialize()
    engine = holder.match_engine
    
    print(f"{'='*80}")
    print("检查标准表数据结构")
    print(f"{'='*80}\n")
    
    # 1. 检查CT标准表
    df_std = engine.data_loader.df_standard.get('CT', {}).get('v1', None)
    if df_std is None:
        print("错误: 无法加载CT标准表")
        return
    
    print(f"1. CT标准表总数: {len(df_std)} 项")
    print(f"   字段: {list(df_std.columns)}")
    print()
    
    # 2. 查找"CT尿路造影"相关项
    print("2. 查找'CT尿路造影'相关项:")
    mask = df_std['checkitem_name'].str.contains('尿路', na=False)
    urinary_items = df_std[mask]
    
    if urinary_items.empty:
        print("   未找到包含'尿路'的标准项")
    else:
        print(f"   找到 {len(urinary_items)} 项:")
        for idx, row in urinary_items.iterrows():
            print(f"\n   [{row['checkitem_code']}] {row['checkitem_name']}")
            print(f"     three_level_name: '{row['three_level_name']}'")
            print(f"     scan_name: '{row['scan_name']}'")
            print(f"     post_processing_name: '{row['post_processing_name']}'")
    print()
    
    # 3. 测试查表逻辑
    print("3. 测试查表逻辑:")
    
    # 假设引擎应该解析出的值
    test_cases = [
        {
            'name': '测试1: 全腹部 + 尿路造影成像(CTU)',
            'bodies': ['全腹部'],
            'scan': ['尿路造影成像(CTU)'],
            'post': []
        },
        {
            'name': '测试2: 无部位 + 尿路造影成像(CTU)',
            'bodies': [],
            'scan': ['尿路造影成像(CTU)'],
            'post': []
        },
        {
            'name': '测试3: 全腹部 + CTU (缩写)',
            'bodies': ['全腹部'],
            'scan': ['CTU'],
            'post': []
        },
    ]
    
    for test_case in test_cases:
        print(f"\n   {test_case['name']}")
        bodies = test_case['bodies']
        scan = test_case['scan']
        post = test_case['post']
        
        print(f"     输入: bodies={bodies}, scan={scan}, post={post}")
        
        # 构造查询条件
        if bodies and scan:
            mask = (
                df_std['three_level_name'].isin(bodies) &
                df_std['scan_name'].isin(scan) &
                ((df_std['post_processing_name'] == '') | df_std['post_processing_name'].isna())
            )
        elif scan:
            mask = (
                df_std['scan_name'].isin(scan) &
                ((df_std['post_processing_name'] == '') | df_std['post_processing_name'].isna())
            )
        else:
            mask = df_std['checkitem_name'] == ''  # 空查询
        
        result = df_std[mask]
        print(f"     结果: {len(result)} 项")
        if not result.empty:
            for _, row in result.iterrows():
                print(f"       [{row['checkitem_code']}] {row['checkitem_name']}")
    
    # 4. 检查标准表中的值是否有空格或特殊字符
    print("\n4. 检查标准表中值的格式:")
    for idx, row in urinary_items.iterrows():
        scan_val = row['scan_name']
        body_val = row['three_level_name']
        post_val = row['post_processing_name']
        
        print(f"\n   [{row['checkitem_code']}] {row['checkitem_name']}")
        print(f"     three_level_name: '{body_val}'")
        print(f"       长度: {len(body_val)}")
        print(f"       repr: {repr(body_val)}")
        print(f"     scan_name: '{scan_val}'")
        print(f"       长度: {len(scan_val)}")
        print(f"       repr: {repr(scan_val)}")
        print(f"     post_processing_name: '{post_val}'")
        print(f"       是否为空: {post_val == '' or pd.isna(post_val)}")
        print(f"       repr: {repr(post_val)}")
    
    # 5. 执行实际匹配看trace
    print(f"\n{'='*80}")
    print("5. 执行实际匹配:")
    print(f"{'='*80}\n")
    
    test_name = "CT尿路造影(平扫+增强)"
    trace = {}
    result = engine.match(test_name, 'CT', trace=trace)
    
    print(f"   输入: {test_name}")
    print(f"   Tier: {result['tier']}")
    print(f"   匹配数: {result['num_standard']}")
    
    # 查看10-lookup_standard步骤的输出
    if '10-lookup_standard' in trace:
        lookup_nodes = trace['10-lookup_standard']
        print(f"\n   10-lookup_standard步骤输出:")
        if isinstance(lookup_nodes, list):
            for idx, node_info in enumerate(lookup_nodes):
                print(f"     Node {idx}: {node_info}")
    
    await holder.dispose()


if __name__ == "__main__":
    asyncio.run(debug_standard_table())

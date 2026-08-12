#!/usr/bin/env python3
"""追踪引擎解析出的实体值"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from match_service.core.engine_holder import EngineHolder


async def trace_entity_parsing():
    """追踪引擎解析出的实体"""
    
    # 初始化引擎
    holder = EngineHolder()
    await holder.initialize()
    engine = holder.match_engine
    
    test_cases = [
        "CT尿路造影(平扫+增强)",
        "CT小肠血管成像(CTA)",
        "CT肩关节(直接造影)",
        "MR关节(平扫)",
        "MR全身关节(平扫+STIR序列)",
    ]
    
    print(f"{'='*100}")
    print("追踪引擎解析出的实体值")
    print(f"{'='*100}\n")
    
    for test_name in test_cases:
        modality = 'CT' if test_name.startswith('CT') else 'MR'
        print(f"测试案例: {test_name}")
        print(f"模态: {modality}")
        
        # 匹配并获取trace
        trace = {}
        result = engine.match(test_name, modality, trace=trace)
        
        print(f"结果: tier={result['tier']}, num={result['num_standard']}")
        
        # 查看9-find_default_process步骤（查表前最后一步）
        if '9-find_default_process' in trace:
            nodes = trace['9-find_default_process']
            print(f"9-find_default_process节点数: {len(nodes)}")
            
            for idx, node_str in enumerate(nodes):
                print(f"\n  Node {idx}:")
                # node_str是字符串格式，尝试解析
                if 'std_names=' in node_str:
                    # 提取std_names部分
                    import re
                    std_names_match = re.search(r'std_names=\[(.*?)\]', node_str)
                    if std_names_match:
                        print(f"    std_names: [{std_names_match.group(1)}]")
                    
                    pos_dict_match = re.search(r'pos_dict=({.*?})', node_str)
                    if pos_dict_match:
                        print(f"    pos_dict: {pos_dict_match.group(1)}")
                
                print(f"    完整: {node_str[:200]}...")
        
        # 查看标准表中的相关项
        df_std = engine.data_loader.df_standard.get(modality, {}).get('V3.8.2', None)
        if df_std is not None:
            # 提取关键词查找
            keywords = []
            if '尿路' in test_name:
                keywords.append('尿路')
            if '小肠' in test_name:
                keywords.extend(['小肠', '腹部'])
            if '肩关节' in test_name:
                keywords.append('肩')
            if '关节' in test_name and '全身' in test_name:
                keywords.extend(['关节', '全身'])
            
            if keywords:
                mask = df_std['checkitem_name'].str.contains('|'.join(keywords), na=False)
                related = df_std[mask]
                print(f"\n  标准表中相关项（关键词: {keywords}）: {len(related)} 项")
                for _, row in related.head(3).iterrows():
                    print(f"    [{row['checkitem_code']}] {row['checkitem_name']}")
                    print(f"      body: {row['three_level_name']}, scan: {row['scan_name']}")
        
        print(f"{'-'*100}\n")
    
    await holder.dispose()


if __name__ == "__main__":
    asyncio.run(trace_entity_parsing())

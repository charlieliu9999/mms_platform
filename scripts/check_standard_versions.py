#!/usr/bin/env python3
"""检查标准表版本和数据加载"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from match_service.core.engine_holder import EngineHolder


async def check_standard_versions():
    """检查标准表版本"""
    
    # 初始化引擎
    holder = EngineHolder()
    await holder.initialize()
    engine = holder.match_engine
    
    print(f"{'='*80}")
    print("检查标准表版本和数据")
    print(f"{'='*80}\n")
    
    # 1. 检查df_standard的结构
    print("1. df_standard 结构:")
    print(f"   模态数: {len(engine.data_loader.df_standard)}")
    for modality, versions in engine.data_loader.df_standard.items():
        print(f"   {modality}: {list(versions.keys())}")
        for ver, df in versions.items():
            print(f"     版本 {ver}: {len(df)} 条")
    print()
    
    # 2. 查看CT标准表
    ct_data = engine.data_loader.df_standard.get('CT', {})
    print(f"2. CT标准表:")
    print(f"   可用版本: {list(ct_data.keys())}")
    
    if ct_data:
        # 取第一个版本
        first_ver = list(ct_data.keys())[0]
        df_ct = ct_data[first_ver]
        print(f"   使用版本: {first_ver}")
        print(f"   记录数: {len(df_ct)}")
        print(f"   字段: {list(df_ct.columns)}")
        
        # 查找尿路相关项
        mask = df_ct['checkitem_name'].str.contains('尿路', na=False)
        urinary = df_ct[mask]
        print(f"\n   包含'尿路'的项: {len(urinary)}")
        for _, row in urinary.iterrows():
            print(f"     [{row['checkitem_code']}] {row['checkitem_name']}")
            print(f"       three_level_name: '{row['three_level_name']}'")
            print(f"       scan_name: '{row['scan_name']}'")
            print(f"       post_processing_name: '{row['post_processing_name']}'")
    print()
    
    # 3. 测试匹配
    print("3. 测试匹配:")
    test_name = "CT尿路造影(平扫+增强)"
    trace = {}
    result = engine.match(test_name, 'CT', trace=trace)
    
    print(f"   输入: {test_name}")
    print(f"   预处理: {trace.get('1-preprocess', '')}")
    print(f"   Tier: {result['tier']}")
    print(f"   匹配数: {result['num_standard']}")
    print(f"   Has entity: {result.get('has_entity', False)}")
    
    await holder.dispose()


if __name__ == "__main__":
    asyncio.run(check_standard_versions())

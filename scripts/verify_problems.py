#!/usr/bin/env python3
"""验证问题并测试修复方案"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from match_service.core.engine_holder import EngineHolder


async def verify_problems():
    """验证已识别的问题"""
    
    holder = EngineHolder()
    await holder.initialize()
    engine = holder.match_engine
    
    print("="*80)
    print("问题验证：测试受影响的项目")
    print("="*80)
    
    # 测试案例：应该受影响的项目
    test_cases = [
        # 非血管造影（应该被错误识别为CTA）
        ("CT尿路造影(平扫+增强)", "CT", "应该匹配CTU，不应该匹配CTA"),
        ("CT关节造影", "CT", "应该匹配关节造影，不应该匹配CTA"),
        ("CT T管造影", "CT", "应该匹配T管造影，不应该匹配CTA"),
        
        # 血管造影（应该正确识别为CTA）
        ("CT主动脉造影", "CT", "应该匹配CTA"),
        ("CT动脉造影", "CT", "应该匹配CTA"),
        ("CT血管造影", "CT", "应该匹配CTA"),
        
        # 边界案例
        ("CT腹部平扫+增强", "CT", "不包含造影，不应该受影响"),
    ]
    
    for idx, (name, modality, expected) in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"测试 {idx}/{len(test_cases)}: {name}")
        print(f"预期: {expected}")
        print(f"{'='*80}")
        
        trace = {}
        result = engine.match(name, modality, trace=trace)
        
        print(f"结果: tier={result['tier']}, num={result['num_standard']}")
        
        # 查看实体识别结果
        if '9-find_default_process' in trace:
            nodes = trace['9-find_default_process']
            if nodes:
                node_str = str(nodes[0])
                print(f"实体节点: {node_str[:200]}...")
                
                # 检查是否包含CTA
                if 'CTA' in node_str or '动脉血管成像' in node_str:
                    print("⚠️  检测到CTA/动脉血管成像")
                if 'CTU' in node_str or '尿路造影' in node_str:
                    print("✓  检测到CTU/尿路造影")
        
        # 查看匹配结果
        if result['data']:
            print(f"匹配到的标准项:")
            for item in result['data'][:3]:
                for std in item.get('standard', [])[:2]:
                    name_matched = std.get('name', '')
                    print(f"  - {name_matched}")
                    if 'CTA' in name_matched or '动脉血管' in name_matched:
                        print("    ⚠️  包含CTA/动脉血管")
                    if 'CTU' in name_matched or '尿路' in name_matched:
                        print("    ✓  包含CTU/尿路")
    
    print(f"\n{'='*80}")
    print("验证总结")
    print(f"{'='*80}")
    print("如果看到：")
    print("  1. 'CT尿路造影' 检测到CTA → 问题确认 ❌")
    print("  2. 'CT关节造影' 检测到CTA → 问题确认 ❌")
    print("  3. 'CT主动脉造影' 检测到CTA → 预期行为 ✓")
    print("  4. 'CT腹部平扫+增强' 没有CTA → 预期行为 ✓")
    
    await holder.dispose()


if __name__ == "__main__":
    asyncio.run(verify_problems())

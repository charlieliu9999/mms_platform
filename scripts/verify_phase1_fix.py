#!/usr/bin/env python3
"""验证修复效果 - 使用已知未匹配项列表"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from match_service.core.engine_holder import EngineHolder


# 修复前的CT未匹配项（从之前的分析报告获取）
CT_UNMATCHED_BEFORE = [
    "CT尿路造影(平扫+增强)",
    "CT T管造影",
    "CT关节造影",
    "CTA腹部盆腔动脉血管成像(CTA)",
    "CT主动脉根部(心电门控增强多排螺旋CT)",
    "CT主动脉血管成像(平扫+增强)",
    "CT冠状动脉血管成像(平扫+增强)联合CT血流储备分数(CT-FFR)",
    "CT胸腰段脊髓动脉血管成像(CTA)",
    "CT腹部盆腔(多平面重建)",
    "CT颞骨及头颈部血管(双期增强+骨算法重建)",
]

# 预期受修复影响的项目
EXPECTED_FIX_ITEMS = [
    "CT尿路造影(平扫+增强)",  # 主要修复目标
]


async def verify_fix_effect():
    """验证修复效果"""
    
    holder = EngineHolder()
    await holder.initialize()
    engine = holder.match_engine
    
    print("="*80)
    print("Phase 1修复效果验证")
    print("="*80)
    print("\n目标: 修复非血管造影被误判为CTA的问题")
    print("预期: CT尿路造影从tier=none改善为tier=exact/partial/degraded")
    print("\n" + "="*80)
    
    stats = {
        'total': len(CT_UNMATCHED_BEFORE),
        'improved': 0,
        'still_none': 0,
        'improved_items': [],
        'still_none_items': [],
    }
    
    print(f"\n测试 {len(CT_UNMATCHED_BEFORE)} 项CT未匹配项:\n")
    
    for idx, name in enumerate(CT_UNMATCHED_BEFORE, 1):
        result = engine.match(name, 'CT')
        tier = result['tier']
        num = result['num_standard']
        
        status = "✅ 改善" if tier != 'none' else "⚪ 仍未匹配"
        marker = "🎯" if name in EXPECTED_FIX_ITEMS else "  "
        
        print(f"{marker} {idx:2d}. {status:8s} tier={tier:10s} num={num:2d}  {name}")
        
        if tier != 'none':
            stats['improved'] += 1
            stats['improved_items'].append((name, tier, num))
            
            # 显示匹配到的项目
            if result['data']:
                for item in result['data'][:2]:
                    for std in item.get('standard', [])[:2]:
                        std_name = std.get('name', '')
                        print(f"       → {std_name}")
        else:
            stats['still_none'] += 1
            stats['still_none_items'].append(name)
    
    print("\n" + "="*80)
    print("统计结果")
    print("="*80)
    print(f"\n总测试项: {stats['total']}项")
    print(f"改善项数: {stats['improved']}项 ({stats['improved']*100/stats['total']:.1f}%)")
    print(f"仍未匹配: {stats['still_none']}项 ({stats['still_none']*100/stats['total']:.1f}%)")
    
    # 验证核心目标
    print("\n" + "="*80)
    print("核心目标验证")
    print("="*80)
    
    target_result = engine.match("CT尿路造影(平扫+增强)", 'CT')
    target_tier = target_result['tier']
    
    print(f"\n🎯 CT尿路造影(平扫+增强):")
    print(f"   修复前: tier=none")
    print(f"   修复后: tier={target_tier}")
    
    if target_tier == 'exact':
        print("   状态: ✅ 完全修复 (exact)")
    elif target_tier in ['partial', 'degraded']:
        print(f"   状态: ✅ 部分修复 ({target_tier})")
    else:
        print("   状态: ❌ 未修复")
    
    if target_result['data']:
        print(f"\n   匹配到的标准项:")
        for item in target_result['data'][:3]:
            for std in item.get('standard', [])[:2]:
                print(f"     - {std.get('name', '')}")
    
    # 回归测试：确保血管造影仍正常
    print("\n" + "="*80)
    print("回归验证（血管造影应该仍正常）")
    print("="*80)
    
    regression_tests = [
        ("CT主动脉造影", "CT"),
        ("CT血管造影", "CT"),
        ("CT头颈部动脉造影", "CT"),
    ]
    
    all_regression_ok = True
    for name, modality in regression_tests:
        result = engine.match(name, modality)
        tier = result['tier']
        
        # 血管造影应该能匹配
        if tier in ['exact', 'partial', 'degraded']:
            print(f"✅ {name}: tier={tier}")
        else:
            print(f"❌ {name}: tier={tier} (应该能匹配)")
            all_regression_ok = False
    
    # 最终结论
    print("\n" + "="*80)
    print("最终结论")
    print("="*80)
    
    target_fixed = target_tier != 'none'
    has_improvement = stats['improved'] > 0
    no_regression = all_regression_ok
    
    print(f"\n✅ 核心目标(CT尿路造影): {'已修复' if target_fixed else '未修复'}")
    print(f"✅ 整体改善: {stats['improved']}项改善")
    print(f"✅ 回归测试: {'通过' if no_regression else '失败'}")
    
    if target_fixed and has_improvement and no_regression:
        print("\n🎉 Phase 1修复成功！")
        print(f"   - 核心目标达成: CT尿路造影已修复")
        print(f"   - 附加收益: {stats['improved']}项改善")
        print(f"   - 无副作用: 血管造影仍正常")
    elif target_fixed and has_improvement:
        print("\n⚠️  Phase 1部分成功")
        print(f"   - 核心目标达成")
        print(f"   - 但回归测试有问题")
    else:
        print("\n❌ Phase 1修复未达到预期")
    
    await holder.dispose()


if __name__ == "__main__":
    asyncio.run(verify_fix_effect())

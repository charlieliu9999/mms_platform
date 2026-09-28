#!/usr/bin/env python3
"""
分析639个未匹配项目
------------------
根因分类、优先级排序、优化建议
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter

# 加载最新的评估结果
result_files = sorted(Path('.').glob('evaluation_results_*.json'), reverse=True)
if not result_files:
    print("❌ 未找到评估结果文件")
    sys.exit(1)

latest_file = result_files[0]
print(f"📥 加载评估结果: {latest_file}")

with open(latest_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

unmatched_items = data.get('unmatched_items', [])
total = data['summary']['total']
unmatched_count = len(unmatched_items)

print(f"✅ 加载完成")
print(f"   总项目数: {total}")
print(f"   未匹配数: {unmatched_count}")
print()

# ========================================
# 1. 按模态分类统计
# ========================================
print("=" * 80)
print("📊 按模态分类统计")
print("=" * 80)

modality_stats = defaultdict(list)
for item in unmatched_items:
    modality = item.get('modality', 'Unknown')
    modality_stats[modality].append(item)

# 按未匹配数排序
sorted_modalities = sorted(modality_stats.items(), key=lambda x: len(x[1]), reverse=True)

print(f"\n{'模态':<15} {'未匹配数':>8} {'占比':>8}")
print("-" * 35)
for modality, items in sorted_modalities:
    count = len(items)
    percentage = count / unmatched_count * 100
    print(f"{modality:<15} {count:>8} {percentage:>7.2f}%")

# ========================================
# 2. 识别unmatchable项目（设计上不可匹配）
# ========================================
print("\n" + "=" * 80)
print("🚫 识别设计上不可匹配的项目（unmatchable）")
print("=" * 80)

# 定义unmatchable关键词
UNMATCHABLE_KEYWORDS = {
    'intervention': ['穿刺', '引流', '置管', '导管', '支架', '球囊', '栓塞', 
                     '活检', '抽吸', 'PICC', '造瘘', '扩张', 'PTA'],
    'surgery': ['手术', '切除', '缝合', '麻醉'],
    'endoscopy': ['内镜', '胃镜', '肠镜', '支气管镜', '腹腔镜'],
    'non_imaging': ['采血', '输液', '肠外营养', '心电图', '脑电图'],
    'nursing': ['护理', '消毒', '换药'],
}

unmatchable_items = []
for item in unmatched_items:
    name = item.get('name', '')
    modality = item.get('modality', '')
    
    # 检查是否包含unmatchable关键词
    is_unmatchable = False
    reason = None
    
    for category, keywords in UNMATCHABLE_KEYWORDS.items():
        if any(kw in name for kw in keywords):
            is_unmatchable = True
            reason = category
            break
    
    # SURG模态全部是手术
    if modality == 'SURG':
        is_unmatchable = True
        reason = 'surgery'
    
    # ES模态大部分是内镜
    if modality == 'ES':
        is_unmatchable = True
        reason = 'endoscopy'
    
    if is_unmatchable:
        item['unmatchable_reason'] = reason
        unmatchable_items.append(item)

print(f"\n识别出 {len(unmatchable_items)} 个unmatchable项目:")
unmatchable_by_reason = defaultdict(list)
for item in unmatchable_items:
    reason = item['unmatchable_reason']
    unmatchable_by_reason[reason].append(item)

for reason, items in sorted(unmatchable_by_reason.items(), key=lambda x: len(x[1]), reverse=True):
    print(f"  - {reason}: {len(items)}项")

# ========================================
# 3. 真正需要优化的项目
# ========================================
matchable_items = [item for item in unmatched_items if item not in unmatchable_items]

print("\n" + "=" * 80)
print("🎯 真正需要优化的项目")
print("=" * 80)
print(f"\n总未匹配: {unmatched_count}项")
print(f"  - unmatchable（设计上不可匹配）: {len(unmatchable_items)}项")
print(f"  - 需要优化: {len(matchable_items)}项")
print()

# 按模态统计需要优化的项目
matchable_by_modality = defaultdict(list)
for item in matchable_items:
    modality = item.get('modality', 'Unknown')
    matchable_by_modality[modality].append(item)

sorted_matchable = sorted(matchable_by_modality.items(), key=lambda x: len(x[1]), reverse=True)

print(f"{'模态':<15} {'需优化数':>8} {'占比':>8}")
print("-" * 35)
for modality, items in sorted_matchable:
    count = len(items)
    percentage = count / len(matchable_items) * 100
    print(f"{modality:<15} {count:>8} {percentage:>7.2f}%")

# ========================================
# 4. 样本分析（每个模态显示前5个）
# ========================================
print("\n" + "=" * 80)
print("📝 样本分析（每个模态TOP5）")
print("=" * 80)

for modality, items in sorted_matchable[:5]:  # 只看前5个模态
    print(f"\n【{modality}】未匹配项目样本:")
    for i, item in enumerate(items[:5], 1):
        name = item.get('name', '')
        print(f"  {i}. {name}")
    if len(items) > 5:
        print(f"  ... 还有 {len(items) - 5} 项")

# ========================================
# 5. 生成分析报告
# ========================================
print("\n" + "=" * 80)
print("💾 生成分析报告")
print("=" * 80)

report = {
    'summary': {
        'total_unmatched': unmatched_count,
        'unmatchable_count': len(unmatchable_items),
        'need_optimization_count': len(matchable_items),
        'unmatchable_percentage': len(unmatchable_items) / unmatched_count * 100,
    },
    'unmatchable_items': unmatchable_items,
    'matchable_items': matchable_items,
    'by_modality': {
        modality: {
            'count': len(items),
            'items': items
        }
        for modality, items in matchable_by_modality.items()
    }
}

output_file = 'unmatched_analysis.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"✅ 分析报告已保存: {output_file}")

# ========================================
# 6. 优化建议
# ========================================
print("\n" + "=" * 80)
print("💡 优化建议")
print("=" * 80)

print(f"""
基于{len(matchable_items)}个需要优化的项目，建议优先级：

【优先级1】OTHER模态优化
  - 未匹配数: {len(matchable_by_modality.get('OTHER', []))}项
  - 建议: 分析OTHER项目的具体内容，可能需要：
    1. 补充特殊检查的标准项
    2. 改进模态分类逻辑
    3. 添加映射规则

【优先级2】DSA模态优化
  - 未匹配数: {len(matchable_by_modality.get('DSA', []))}项
  - 建议: 区分介入治疗vs影像检查
    1. 纯影像的DSA应该能匹配
    2. 介入治疗的DSA应标记为unmatchable

【优先级3】IR模态处理
  - 未匹配数: {len(matchable_by_modality.get('IR', []))}项
  - 建议: IR（介入放射）大部分应该是unmatchable
    1. 审查是否都是介入治疗
    2. 如果是，应该排除在评估之外

【优先级4】XR/RF模态补充
  - XR未匹配: {len(matchable_by_modality.get('XR', []))}项
  - RF未匹配: {len(matchable_by_modality.get('RF', []))}项
  - 建议: 补充标准库和词典

【优先级5】主要模态微调
  - US未匹配: {len(matchable_by_modality.get('US', []))}项
  - MR未匹配: {len(matchable_by_modality.get('MR', []))}项
  - CT未匹配: {len(matchable_by_modality.get('CT', []))}项
  - 建议: 逐项分析根因

【建议】调整评估口径
  - 当前: 4555项目 → 3916匹配 (85.97%)
  - 剔除unmatchable: {total - len(unmatchable_items)}项 → 3916匹配 ({3916 / (total - len(unmatchable_items)) * 100:.2f}%)
  - 这样更能反映算法的真实性能
""")

print("=" * 80)
print("✅ 分析完成")
print("=" * 80)

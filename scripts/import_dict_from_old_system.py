#!/usr/bin/env python3
"""
从原系统导入完整的医学词典
扩充当前系统的词汇覆盖，特别是新模态（US/SPECT/MG/RF）
"""
import csv
from pathlib import Path
from collections import defaultdict

# 源词典文件
SOURCE_DICT = "/Users/charlieliu/git_project_vscode/09_medical/acrac_web_mgmt/match_service/phase0-deliverables/finalized_medical_dict.csv"

# 当前系统词典
CURRENT_DICT = "data/lexicon/medical_dict.csv"

# 词汇类型映射
TYPE_MAP = {
    'body': 'body_part',      # 部位
    'scan': 'scan_method',     # 扫描方式
    'position': 'position',    # 体位
    'post': 'post_process',    # 后处理
    'other': 'modifier',       # 修饰词
    'rfscan': 'scan_method',   # RF扫描方式
    'mgscan': 'scan_method',   # MG扫描方式
    'device': 'device',        # 设备
}

# 关键词汇（优先导入）
PRIORITY_KEYWORDS = [
    # MG（乳腺钼靶）
    '钼靶', '导管造影', '乳腺导管', '术中定位', '定位钢丝',
    '乳腺压迫', '侧斜位', '轴位', '切线位',

    # US（超声）
    '超声', '彩超', '彩色多普勒', '多普勒', '常规超声',
    '床旁超声', '术中超声', '弹性成像', '造影超声',
    '浅表', '深部', '经腹', '经阴道', '经直肠',

    # SPECT（核医学）
    '灌注', '显像', '心肌灌注', 'SPECT', 'ECT',
    '静息', '负荷', '放射性', '核素', '示踪剂',
    '平面显像', '断层显像', '动态显像',

    # 介入（DSA/RF）
    '穿刺', '活检', '抽吸', '造影', '血管造影',
    '栓塞', '支架', '置管', '引流', '消融',
    '经皮', '介入', '导管',
]


def load_source_dict():
    """加载原系统词典"""
    words = []
    with open(SOURCE_DICT, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = row['word'].strip()
            word_type = row['type'].strip()
            enable = row['enable'].strip()

            # 只导入非禁用词汇
            if enable != '0':
                continue

            words.append({
                'word': word,
                'type': word_type,
                'enable': enable,
            })

    return words


def load_current_dict():
    """加载当前系统词典"""
    current_words = set()
    dict_file = Path(CURRENT_DICT)

    if not dict_file.exists():
        print(f"⚠️  当前词典文件不存在: {dict_file}")
        return current_words

    with open(dict_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            current_words.add(row['word'].strip())

    return current_words


def filter_priority_words(words):
    """筛选优先级词汇"""
    priority = []
    others = []

    for word_info in words:
        word = word_info['word']
        is_priority = any(kw in word for kw in PRIORITY_KEYWORDS)

        if is_priority:
            priority.append(word_info)
        else:
            others.append(word_info)

    return priority, others


def analyze_and_preview():
    """分析并预览导入数据"""
    print("📁 加载原系统词典...")
    source_words = load_source_dict()
    print(f"   原系统词典: {len(source_words)} 条（enable=0，即启用状态）")

    print("\n📁 加载当前系统词典...")
    current_words = load_current_dict()
    print(f"   当前系统词典: {len(current_words)} 条")

    # 筛选新词汇
    new_words = [w for w in source_words if w['word'] not in current_words]
    print(f"\n✅ 可导入的新词汇: {len(new_words)} 条")

    # 分优先级
    priority, others = filter_priority_words(new_words)
    print(f"   - 高优先级（含关键词）: {priority} 条")
    print(f"   - 普通优先级: {len(others)} 条")

    # 按类型统计
    print(f"\n📊 新词汇按类型分布:")
    type_stats = defaultdict(int)
    for w in new_words:
        type_stats[w['type']] += 1

    for word_type, count in sorted(type_stats.items(), key=lambda x: -x[1]):
        mapped_type = TYPE_MAP.get(word_type, word_type)
        print(f"   {word_type:<12} → {mapped_type:<15} : {count} 条")

    # 显示高优先级样例
    print(f"\n🎯 高优先级词汇样例（前30个）:")
    for i, word_info in enumerate(priority[:30], 1):
        word = word_info['word']
        word_type = word_info['type']
        mapped = TYPE_MAP.get(word_type, word_type)
        print(f"   {i:2}. {word:<30} [{word_type} → {mapped}]")

    if len(priority) > 30:
        print(f"   ... 还有 {len(priority) - 30} 个高优先级词汇")

    # 生成导入预览文件
    preview_file = Path("data/lexicon/import_preview.csv")
    preview_file.parent.mkdir(parents=True, exist_ok=True)

    with open(preview_file, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['word', 'source_type', 'mapped_type', 'priority']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for w in priority:
            writer.writerow({
                'word': w['word'],
                'source_type': w['type'],
                'mapped_type': TYPE_MAP.get(w['type'], w['type']),
                'priority': 'high',
            })

        for w in others:
            writer.writerow({
                'word': w['word'],
                'source_type': w['type'],
                'mapped_type': TYPE_MAP.get(w['type'], w['type']),
                'priority': 'normal',
            })

    print(f"\n✅ 导入预览已保存到: {preview_file}")
    print(f"\n💡 下一步:")
    print(f"   1. 检查预览文件: {preview_file}")
    print(f"   2. 运行实际导入: python scripts/import_dict_from_old_system.py --execute")

    return new_words, priority, others


if __name__ == "__main__":
    import sys

    if '--execute' in sys.argv:
        print("❌ 实际导入功能待实现")
        print("   请先检查预览文件，然后通过数据库SQL导入")
    else:
        analyze_and_preview()

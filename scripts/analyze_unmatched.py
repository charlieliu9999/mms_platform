#!/usr/bin/env python3
"""
分析未匹配数据，生成优化建议报告
"""
import requests
from collections import defaultdict
import json

API_BASE = "http://localhost:9100/api/evaluation"

def fetch_failures(task_id, limit=200):
    """获取失败案例（分批获取）"""
    all_cases = []
    offset = 0

    while True:
        url = f"{API_BASE}/tasks/{task_id}/failures?limit={limit}&offset={offset}"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()

        cases = data.get('cases', [])
        if not cases:
            break

        all_cases.extend(cases)
        offset += limit

        # 如果返回的数量少于limit，说明已经到最后了
        if len(cases) < limit:
            break

    return {'total': len(all_cases), 'cases': all_cases}

def analyze_by_modality(cases):
    """按模态分析"""
    stats = defaultdict(lambda: {
        'total': 0,
        'missing_word': [],
        'complex': [],
        'no_standard': []
    })

    for case in cases:
        modality = case['modality']
        reason = case['failure_reason']
        check_item = case['check_item']

        stats[modality]['total'] += 1
        stats[modality][reason].append(check_item)

    return stats

def extract_missing_words(cases):
    """提取缺失的关键词"""
    keywords = defaultdict(int)

    # 介入关键词
    dsa_keywords = ['穿刺', '活检', '抽吸', '置管', '造瘘', '导管', 'PICC', '栓塞', '球囊', '扩张']
    # 核医学关键词
    spect_keywords = ['PET', 'CT', '显像', '核素', '标记', '白细胞', '亲肿瘤']
    # 造影关键词
    rf_keywords = ['造影', '灌肠', '窦道', '瘘道', '吞咽', '排粪', '淋巴管', '输卵管']
    # DR关键词
    dr_keywords = ['正、侧位', '双髋', '双肩', '双踝', '双足', '双膝', '双肘', '双腕', '负重']
    # MR关键词
    mr_keywords = ['弹性成像', 'MRA', 'CE-MRA']
    # US关键词
    us_keywords = ['导管', '彩色多普勒']

    for case in cases:
        item = case['check_item']
        modality = case['modality']

        if modality == 'DSA':
            for kw in dsa_keywords:
                if kw in item:
                    keywords[f'DSA/{kw}'] += 1
        elif modality == 'SPECT':
            for kw in spect_keywords:
                if kw in item:
                    keywords[f'SPECT/{kw}'] += 1
        elif modality == 'RF':
            for kw in rf_keywords:
                if kw in item:
                    keywords[f'RF/{kw}'] += 1
        elif modality == 'DR':
            for kw in dr_keywords:
                if kw in item:
                    keywords[f'DR/{kw}'] += 1
        elif modality == 'MR':
            for kw in mr_keywords:
                if kw in item:
                    keywords[f'MR/{kw}'] += 1
        elif modality == 'US':
            for kw in us_keywords:
                if kw in item:
                    keywords[f'US/{kw}'] += 1

    return keywords

def main():
    task_id = 3

    print(f"📊 分析评测任务 {task_id} 的未匹配数据...\n")

    # 获取失败案例
    data = fetch_failures(task_id)
    cases = data['cases']
    total = data['total']

    print(f"总失败数: {total} 条\n")

    # 按模态统计
    stats = analyze_by_modality(cases)

    print("=" * 80)
    print("各模态失败分布")
    print("=" * 80)
    print(f"{'模态':<10} {'总数':<8} {'缺词':<8} {'复杂':<8} {'无标准':<8}")
    print("-" * 80)

    for modality in sorted(stats.keys()):
        s = stats[modality]
        print(f"{modality:<10} {s['total']:<8} {len(s['missing_word']):<8} "
              f"{len(s['complex']):<8} {len(s['no_standard']):<8}")

    print("\n")

    # 缺失词汇分析
    missing_cases = [c for c in cases if c['failure_reason'] == 'missing_word']
    keywords = extract_missing_words(missing_cases)

    print("=" * 80)
    print("缺失关键词TOP20（按频次）")
    print("=" * 80)

    sorted_kw = sorted(keywords.items(), key=lambda x: -x[1])[:20]
    for kw, count in sorted_kw:
        print(f"{kw:<30} {count:>3} 次")

    print("\n")

    # 各模态样例
    print("=" * 80)
    print("各模态失败样例（前5个）")
    print("=" * 80)

    for modality in sorted(stats.keys()):
        s = stats[modality]
        print(f"\n【{modality}】 总计 {s['total']} 条失败")

        if s['missing_word']:
            print(f"\n  缺少词汇 ({len(s['missing_word'])} 条):")
            for item in s['missing_word'][:5]:
                print(f"    - {item}")

        if s['complex']:
            print(f"\n  复杂表述 ({len(s['complex'])} 条):")
            for item in s['complex'][:5]:
                print(f"    - {item}")

        if s['no_standard']:
            print(f"\n  无标准项 ({len(s['no_standard'])} 条):")
            for item in s['no_standard'][:5]:
                print(f"    - {item}")

if __name__ == "__main__":
    main()

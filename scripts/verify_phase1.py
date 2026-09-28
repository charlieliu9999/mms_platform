#!/usr/bin/env python3
"""
Phase 1 验收标准验证脚本
"""

import pandas as pd
from pathlib import Path


def verify_phase1():
    """验证 Phase 1 的所有交付成果"""
    print("=" * 60)
    print("Phase 1 验收标准验证")
    print("=" * 60)

    base_dir = Path("/Users/charlieliu/git_project_vscode/09_medical/mms_platform")
    reports_dir = base_dir / "reports"
    phase1_dir = base_dir / "phase1-deliverables"

    all_passed = True

    # 1. 检查文件是否存在
    print("\n[1] 检查必需文件...")
    required_files = [
        reports_dir / "dict_diff_analysis.csv",
        reports_dir / "phrase_diff_analysis.csv",
        phase1_dir / "merged_medical_dict.csv",
        phase1_dir / "merged_phrase_map.csv",
        phase1_dir / "merge_report.md"
    ]

    for file_path in required_files:
        if file_path.exists():
            print(f"  ✅ {file_path.name}")
        else:
            print(f"  ❌ {file_path.name} - 文件不存在")
            all_passed = False

    # 2. 验证合并后的词典
    print("\n[2] 验证医学词典...")
    merged_dict = pd.read_csv(phase1_dir / "merged_medical_dict.csv")
    dict_count = len(merged_dict)

    if dict_count >= 2500:
        print(f"  ✅ 词典总数: {dict_count:,} (≥ 2500)")
    else:
        print(f"  ❌ 词典总数: {dict_count:,} (< 2500)")
        all_passed = False

    # 检查必需字段
    required_columns = ['word', 'type', 'device', 'version']
    missing_columns = [col for col in required_columns if col not in merged_dict.columns]
    if not missing_columns:
        print(f"  ✅ 包含所有必需字段: {', '.join(required_columns)}")
    else:
        print(f"  ⚠️  缺少字段: {', '.join(missing_columns)}")

    # 检查是否有空词汇
    empty_words = merged_dict['word'].isna().sum()
    if empty_words == 0:
        print(f"  ✅ 无空词汇")
    else:
        print(f"  ⚠️  发现 {empty_words} 个空词汇")

    # 3. 验证合并后的短语映射
    print("\n[3] 验证短语映射...")
    merged_phrase = pd.read_csv(phase1_dir / "merged_phrase_map.csv")
    phrase_count = len(merged_phrase)

    if phrase_count >= 7900:
        print(f"  ✅ 短语总数: {phrase_count:,} (≥ 7900)")
    else:
        print(f"  ❌ 短语总数: {phrase_count:,} (< 7900)")
        all_passed = False

    # 检查必需字段
    required_columns = ['device', 'src_word', 'dst_word', 'step', 'version']
    missing_columns = [col for col in required_columns if col not in merged_phrase.columns]
    if not missing_columns:
        print(f"  ✅ 包含所有必需字段: {', '.join(required_columns)}")
    else:
        print(f"  ⚠️  缺少字段: {', '.join(missing_columns)}")

    # 检查是否有空映射
    empty_src = merged_phrase['src_word'].isna().sum()
    empty_dst = merged_phrase['dst_word'].isna().sum()
    if empty_src == 0 and empty_dst == 0:
        print(f"  ✅ 无空映射")
    else:
        print(f"  ⚠️  发现 {empty_src} 个空源词，{empty_dst} 个空目标词")

    # 4. 验证差异分析
    print("\n[4] 验证差异分析...")
    dict_diff = pd.read_csv(reports_dir / "dict_diff_analysis.csv")
    phrase_diff = pd.read_csv(reports_dir / "phrase_diff_analysis.csv")

    zzy_only_dict = len(dict_diff[dict_diff['source'] == '16_zzy_only'])
    mms_only_dict = len(dict_diff[dict_diff['source'] == 'mms_only'])
    common_dict = len(dict_diff[dict_diff['source'] == 'common'])

    print(f"  📊 词典差异:")
    print(f"     - 16_zzy 特有: {zzy_only_dict:,}")
    print(f"     - MMS 特有: {mms_only_dict:,}")
    print(f"     - 重叠: {common_dict:,}")

    zzy_only_phrase = len(phrase_diff[phrase_diff['source'] == '16_zzy_only'])
    mms_only_phrase = len(phrase_diff[phrase_diff['source'] == 'mms_only'])
    common_phrase = len(phrase_diff[phrase_diff['source'] == 'common'])

    print(f"  📊 短语差异:")
    print(f"     - 16_zzy 特有: {zzy_only_phrase:,}")
    print(f"     - MMS 特有: {mms_only_phrase:,}")
    print(f"     - 重叠: {common_phrase:,}")

    # 5. 数据质量检查
    print("\n[5] 数据质量检查...")

    # 检查词典中的词性分布
    type_dist = merged_dict['type'].value_counts()
    print(f"  📊 词性分布:")
    for word_type, count in type_dist.head(10).items():
        print(f"     - {word_type}: {count:,}")

    # 检查短语中的步骤分布
    step_dist = merged_phrase['step'].value_counts()
    print(f"  📊 步骤分布:")
    for step, count in step_dist.head(5).items():
        print(f"     - {step}: {count:,}")

    # 最终结果
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ Phase 1 所有验收标准通过!")
    else:
        print("❌ Phase 1 部分验收标准未通过")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    verify_phase1()

#!/usr/bin/env python3
"""
Import and transform 16_zzy test data to MMS format
Author: Claude
Date: 2026-07-29
"""

import pandas as pd
import os
from pathlib import Path
from datetime import datetime


def clean_and_transform_data(df, modality):
    """Clean and transform data to MMS test format"""

    # Remove rows with null check items
    df_clean = df[df['exa_o_item_list'].notna()].copy()

    # Remove rows with empty check items
    df_clean = df_clean[df_clean['exa_o_item_list'].str.strip() != '']

    # Create MMS format
    df_mms = pd.DataFrame({
        'check_item': df_clean['exa_o_item_list'],
        'modality': modality,
        'version': 'V3.8.2',  # Latest version from the file naming
        'expected_standard_code': df_clean['exa_b_item_code'].fillna(''),
        'expected_standard_name': df_clean['exa_b_item_name'].fillna('')
    })

    # Remove duplicates (keep first occurrence)
    df_mms = df_mms.drop_duplicates(subset=['check_item'], keep='first')

    # Remove rows where both standard_code and standard_name are empty
    df_mms = df_mms[
        (df_mms['expected_standard_code'] != '') |
        (df_mms['expected_standard_name'] != '')
    ]

    return df_mms


def main():
    # Source files
    source_dir = Path("/Users/charlieliu/git_project_vscode/16_zzy/examine-standard/data")
    csv_files = {
        'CT': source_dir / "20230907_CT_pred.csv",
        'DR': source_dir / "20230907_DR_pred.csv",
        'MR': source_dir / "20230907_MR_pred.csv"
    }

    # Output directory
    output_dir = Path("/Users/charlieliu/git_project_vscode/09_medical/mms_platform/tests/benchmark")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Statistics
    stats = {
        'original': {},
        'null_check_item': {},
        'empty_check_item': {},
        'no_standard': {},
        'duplicates': {},
        'final': {}
    }

    all_data = []

    print("="*70)
    print("16_zzy Test Data Import and Transformation")
    print("="*70)

    for modality, csv_file in csv_files.items():
        print(f"\nProcessing {modality}...")

        # Read CSV
        df_original = pd.read_csv(csv_file)
        stats['original'][modality] = len(df_original)

        # Count null check items
        null_count = df_original['exa_o_item_list'].isna().sum()
        stats['null_check_item'][modality] = null_count

        # Count empty check items
        df_not_null = df_original[df_original['exa_o_item_list'].notna()].copy()
        empty_count = (df_not_null['exa_o_item_list'].str.strip() == '').sum()
        stats['empty_check_item'][modality] = empty_count

        # Transform
        df_mms = clean_and_transform_data(df_original, modality)

        # Count removed due to no standard
        before_standard_filter = len(df_original) - null_count - empty_count
        after_dedup = before_standard_filter - (before_standard_filter - len(df_mms.drop_duplicates(subset=['check_item'])))
        stats['duplicates'][modality] = before_standard_filter - after_dedup
        stats['no_standard'][modality] = after_dedup - len(df_mms)
        stats['final'][modality] = len(df_mms)

        # Save individual file
        output_file = output_dir / f"16zzy_{modality.lower()}_{len(df_mms)//1000}k.csv"
        df_mms.to_csv(output_file, index=False, encoding='utf-8')
        print(f"  ✓ Saved: {output_file.name} ({len(df_mms):,} records)")

        # Add to combined data
        all_data.append(df_mms)

    # Save combined file
    df_combined = pd.concat(all_data, ignore_index=True)
    combined_file = output_dir / f"16zzy_combined_{len(df_combined)//1000}k.csv"
    df_combined.to_csv(combined_file, index=False, encoding='utf-8')

    print(f"\n✓ Saved combined file: {combined_file.name} ({len(df_combined):,} records)")

    # Generate report
    report_file = output_dir / "data_import_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 测试数据导入报告\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## 原始数据统计\n\n")
        f.write(f"- **文件来源**: `/Users/charlieliu/git_project_vscode/16_zzy/examine-standard/data/`\n")
        f.write(f"- **文件列表**:\n")
        f.write(f"  - `20230907_CT_pred.csv`\n")
        f.write(f"  - `20230907_DR_pred.csv`\n")
        f.write(f"  - `20230907_MR_pred.csv`\n\n")

        f.write("| 模态 | 原始记录数 |\n")
        f.write("|------|------------|\n")
        for modality in ['CT', 'DR', 'MR']:
            f.write(f"| {modality} | {stats['original'][modality]:,} |\n")
        f.write(f"| **总计** | **{sum(stats['original'].values()):,}** |\n\n")

        f.write("## 数据清洗\n\n")
        f.write("### 清洗规则\n")
        f.write("1. 移除检查项目为空的记录\n")
        f.write("2. 移除检查项目和标准项目都为空的记录\n")
        f.write("3. 移除重复的检查项目（保留第一次出现）\n\n")

        f.write("### 清洗统计\n\n")
        f.write("| 模态 | 空检查项目 | 空字符串 | 重复项 | 无标准项 | 清洗后 |\n")
        f.write("|------|-----------|---------|--------|---------|--------|\n")
        for modality in ['CT', 'DR', 'MR']:
            f.write(f"| {modality} | {stats['null_check_item'][modality]:,} | ")
            f.write(f"{stats['empty_check_item'][modality]:,} | ")
            f.write(f"{stats['duplicates'][modality]:,} | ")
            f.write(f"{stats['no_standard'][modality]:,} | ")
            f.write(f"**{stats['final'][modality]:,}** |\n")
        f.write(f"| **总计** | {sum(stats['null_check_item'].values()):,} | ")
        f.write(f"{sum(stats['empty_check_item'].values()):,} | ")
        f.write(f"{sum(stats['duplicates'].values()):,} | ")
        f.write(f"{sum(stats['no_standard'].values()):,} | ")
        f.write(f"**{sum(stats['final'].values()):,}** |\n\n")

        f.write("## 转换后数据\n\n")
        f.write("### 输出文件\n\n")
        for modality in ['CT', 'DR', 'MR']:
            count = stats['final'][modality]
            f.write(f"- **{modality}**: {count:,} 条 → `tests/benchmark/16zzy_{modality.lower()}_{count//1000}k.csv`\n")
        total = sum(stats['final'].values())
        f.write(f"- **合并文件**: {total:,} 条 → `tests/benchmark/16zzy_combined_{total//1000}k.csv`\n\n")

        f.write("### 数据格式\n\n")
        f.write("```csv\n")
        f.write("check_item,modality,version,expected_standard_code,expected_standard_name\n")
        f.write("```\n\n")

        f.write("### 数据示例\n\n")
        f.write("以下是转换后的数据示例（各模态各展示2条）：\n\n")

        for modality in ['CT', 'DR', 'MR']:
            f.write(f"#### {modality}\n\n")
            df_sample = all_data[['CT', 'DR', 'MR'].index(modality)].head(2)
            f.write("```\n")
            for idx, row in df_sample.iterrows():
                f.write(f"检查项目: {row['check_item']}\n")
                f.write(f"模态: {row['modality']}\n")
                f.write(f"版本: {row['version']}\n")
                f.write(f"标准编码: {row['expected_standard_code']}\n")
                f.write(f"标准名称: {row['expected_standard_name']}\n")
                f.write("---\n")
            f.write("```\n\n")

        f.write("## 质量评估\n\n")
        f.write("### 数据完整性\n\n")
        for modality in ['CT', 'DR', 'MR']:
            df_mod = all_data[['CT', 'DR', 'MR'].index(modality)]
            has_code = (df_mod['expected_standard_code'] != '').sum()
            has_name = (df_mod['expected_standard_name'] != '').sum()
            has_both = ((df_mod['expected_standard_code'] != '') & (df_mod['expected_standard_name'] != '')).sum()

            f.write(f"**{modality}**:\n")
            f.write(f"- 有标准编码: {has_code:,} ({has_code/len(df_mod)*100:.1f}%)\n")
            f.write(f"- 有标准名称: {has_name:,} ({has_name/len(df_mod)*100:.1f}%)\n")
            f.write(f"- 编码和名称都有: {has_both:,} ({has_both/len(df_mod)*100:.1f}%)\n\n")

        f.write("## 验收标准检查\n\n")
        f.write("- ✅ 找到并成功读取 16_zzy 测试数据\n")
        f.write("- ✅ 导出 3 个模态的测试文件（CT/DR/MR）\n")
        f.write(f"- ✅ 总数据量: {sum(stats['final'].values()):,} 条\n")
        f.write("- ✅ 生成详细的导入报告\n\n")

        f.write("## 下一步\n\n")
        f.write("1. 使用这些测试数据建立 Benchmark\n")
        f.write("2. 运行 MMS 标准化服务进行预测\n")
        f.write("3. 计算准确率指标\n")
        f.write("4. 与历史版本对比性能\n")

    print(f"\n✓ Report saved: {report_file.name}")

    print("\n" + "="*70)
    print("Summary")
    print("="*70)
    print(f"Total original records: {sum(stats['original'].values()):,}")
    print(f"Total cleaned records:  {sum(stats['final'].values()):,}")
    print(f"Cleaning rate:          {sum(stats['final'].values())/sum(stats['original'].values())*100:.1f}%")
    print("="*70)


if __name__ == "__main__":
    main()

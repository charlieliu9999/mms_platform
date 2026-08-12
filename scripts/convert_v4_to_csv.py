#!/usr/bin/env python3
"""
v4.0.0 标准数据转换脚本

将 Excel 标准文件（多工作表）转换为可导入数据库的 CSV 格式

用法:
    python scripts/convert_v4_to_csv.py

输入文件:
    /Users/charlieliu/Desktop/01标准/09 医保版-标准/影像检查项目名称和编码V4.0.xlsx

输出文件:
    data/v4.0.0_standards_YYYYMMDD_HHMMSS.csv
"""

import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# 配置
INPUT_FILE = Path("/Users/charlieliu/Desktop/01标准/09 医保版-标准/影像检查项目名称和编码V4.0.xlsx")
OUTPUT_DIR = Path("data")
VERSION = "v4.0.0"
DEFAULT_PROVINCE = "江西"

# 需要处理的工作表及其字段映射
SHEET_CONFIGS = {
    'CT项目': {
        'field_mapping': {
            '模态': 'modality',
            '检查项目编码': 'checkitem_code',
            '检查项目名称': 'checkitem_name',
            '一级编码': 'body_part_l1_code',
            '一级部位': 'body_part_l1',
            '二级编码': 'body_part_l2_code',
            '二级部位': 'body_part_l2',
            '三级编码': 'body_part_l3_code',
            '三级部位': 'body_part_l3',
            '部位编码': 'body_part_code',
            '扫描方式': 'scan_method',
            '医保映射码': 'insurance_code',
            '医保扩展码': 'insurance_ext_code',
        }
    },
    'MR项目': {
        'field_mapping': {
            '模态': 'modality',
            '检查项目编码': 'checkitem_code',
            '检查项目名称': 'checkitem_name',
            '一级编码': 'body_part_l1_code',
            '一级部位': 'body_part_l1',
            '二级编码': 'body_part_l2_code',
            '二级部位': 'body_part_l2',
            '三级编码': 'body_part_l3_code',
            '三级部位': 'body_part_l3',
            '部位编码': 'body_part_code',
            '扫描方式': 'scan_method',
            '医保映射码': 'insurance_code',
            '医保扩展码': 'insurance_ext_code',
        }
    },
    'DR项目': {
        'field_mapping': {
            '模态': 'modality',
            '检查项目编码': 'checkitem_code',
            '检查项目名称': 'checkitem_name',
            '一级编码': 'body_part_l1_code',
            '一级部位': 'body_part_l1',
            '二级编码': 'body_part_l2_code',
            '二级部位': 'body_part_l2',
            '三级编码': 'body_part_l3_code',
            '三级部位': 'body_part_l3',
            '部位编码': 'body_part_code',
            '摄影体位': 'scan_method',
            '医保映射码': 'insurance_code',
        }
    },
    'MG项目': {
        'field_mapping': {
            '模态': 'modality',
            '检查项目编码': 'checkitem_code',
            '检查项目名称': 'checkitem_name',
            '一级编码': 'body_part_l1_code',
            '一级部位': 'body_part_l1',
            '二级编码': 'body_part_l2_code',
            '二级部位': 'body_part_l2',
            '三级编码': 'body_part_l3_code',
            '三级部位': 'body_part_l3',
            '部位编码': 'body_part_code',
            '摆位/技术': 'scan_method',
            '医保映射编码': 'insurance_code',
            '医保项目名称': 'insurance_name',
            '医保项目码': 'insurance_item_code',
        }
    }
}

def check_dependencies():
    """检查必需的依赖"""
    try:
        import pandas as pd
        import openpyxl
    except ImportError as e:
        print("❌ 缺少必需的 Python 包")
        print("\n请安装依赖:")
        print("  pip install pandas openpyxl")
        sys.exit(1)

def clean_code_field(value):
    """清理编码字段（移除单引号前缀）"""
    if pd.isna(value):
        return value
    s = str(value).strip()
    # 移除 Excel 中用于强制文本格式的单引号
    if s.startswith("'"):
        s = s[1:]
    return s

def read_sheet(file_path, sheet_name, field_mapping):
    """读取并处理单个工作表"""
    print(f"\n📄 读取工作表: {sheet_name}")

    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        print(f"  ✓ 读取 {len(df)} 行")

        # 检查列名
        missing_cols = [col for col in field_mapping.keys() if col not in df.columns]
        if missing_cols:
            print(f"  ⚠️  缺少列: {', '.join(missing_cols)}")

        # 映射字段
        mapped_data = {}
        for excel_col, db_field in field_mapping.items():
            if excel_col in df.columns:
                mapped_data[db_field] = df[excel_col]

        result_df = pd.DataFrame(mapped_data)

        # 清理编码字段中的单引号
        code_fields = ['checkitem_code', 'body_part_l1_code', 'body_part_l2_code',
                      'body_part_l3_code', 'body_part_code', 'insurance_code']
        for field in code_fields:
            if field in result_df.columns:
                result_df[field] = result_df[field].apply(clean_code_field)

        # 添加版本和省份
        result_df['version'] = VERSION
        result_df['province'] = DEFAULT_PROVINCE

        print(f"  ✓ 映射完成，共 {len(result_df.columns)} 个字段")

        return result_df

    except Exception as e:
        print(f"  ❌ 处理失败: {e}")
        return None

def validate_data(df):
    """验证数据完整性"""
    print(f"\n🔍 验证数据...")

    issues = []
    warnings = []

    # 必填字段
    required_fields = ['checkitem_code', 'checkitem_name', 'modality', 'version']
    for field in required_fields:
        if field not in df.columns:
            issues.append(f"缺少必填字段: {field}")
        else:
            null_count = df[field].isnull().sum()
            if null_count > 0:
                warnings.append(f"{field} 有 {null_count} 个空值")

    # 重复检查
    if 'checkitem_code' in df.columns:
        duplicates = df[df['checkitem_code'].duplicated()]
        if len(duplicates) > 0:
            issues.append(f"发现 {len(duplicates)} 条重复编码")

    # 模态统计
    if 'modality' in df.columns:
        modality_counts = df['modality'].value_counts()
        print(f"\n  📌 模态分布:")
        for modality, count in modality_counts.items():
            print(f"    {modality}: {count} 条")

    # 医保字段覆盖率
    insurance_fields = ['insurance_code', 'insurance_name']
    for field in insurance_fields:
        if field in df.columns:
            non_null = df[field].notnull().sum()
            coverage = (non_null / len(df)) * 100
            warnings.append(f"{field}: {non_null}/{len(df)} ({coverage:.1f}%) 有值")

    # 输出结果
    if warnings:
        print(f"\n  ℹ️  数据信息:")
        for warning in warnings:
            print(f"    {warning}")

    if issues:
        print(f"\n  ⚠️  发现问题:")
        for issue in issues:
            print(f"    ❌ {issue}")
        return False
    else:
        print(f"\n  ✅ 数据验证通过")
        return True

def export_csv(df, output_dir):
    """导出 CSV 文件"""
    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)

    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"v4.0.0_standards_{timestamp}.csv"

    print(f"\n💾 导出 CSV...")
    try:
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✅ 成功导出: {output_file}")
        print(f"  - 总行数: {len(df)}")
        print(f"  - 总列数: {len(df.columns)}")
        print(f"  - 文件大小: {output_file.stat().st_size / 1024:.2f} KB")
        return output_file
    except Exception as e:
        print(f"❌ 导出失败: {e}")
        sys.exit(1)

def main():
    """主函数"""
    print("="*60)
    print("v4.0.0 标准数据转换脚本")
    print("="*60)

    # 1. 检查依赖
    check_dependencies()

    # 2. 检查输入文件
    print(f"\n📖 输入文件: {INPUT_FILE}")
    if not INPUT_FILE.exists():
        print(f"❌ 文件不存在: {INPUT_FILE}")
        sys.exit(1)

    # 3. 读取所有工作表
    all_dataframes = []

    for sheet_name, config in SHEET_CONFIGS.items():
        df = read_sheet(INPUT_FILE, sheet_name, config['field_mapping'])
        if df is not None and len(df) > 0:
            all_dataframes.append(df)
        else:
            print(f"  ⚠️  跳过工作表: {sheet_name}")

    if not all_dataframes:
        print("\n❌ 没有成功读取任何数据")
        sys.exit(1)

    # 4. 合并所有数据
    print(f"\n🔗 合并数据...")
    combined_df = pd.concat(all_dataframes, ignore_index=True)
    print(f"  ✓ 合并完成，总计 {len(combined_df)} 条记录")

    # 5. 验证数据
    if not validate_data(combined_df):
        print("\n⚠️  数据验证未通过，但仍可导出")
        response = input("是否继续导出? (y/n): ")
        if response.lower() != 'y':
            print("取消导出")
            sys.exit(0)

    # 6. 导出 CSV
    output_file = export_csv(combined_df, OUTPUT_DIR)

    print("\n" + "="*60)
    print("✅ 转换完成！")
    print("="*60)
    print(f"\n下一步:")
    print(f"  1. 检查导出的 CSV 文件:")
    print(f"     head -5 {output_file}")
    print(f"     wc -l {output_file}")
    print(f"")
    print(f"  2. 备份数据库（重要！）:")
    print(f"     pg_dump -h localhost -U postgres -d mms_platform \\")
    print(f"       -t checkitem_standards > backups/backup_$(date +%Y%m%d_%H%M%S).sql")
    print(f"")
    print(f"  3. 参考快速开始指南继续操作:")
    print(f"     cat docs/quick-start-v4.md")
    print("")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

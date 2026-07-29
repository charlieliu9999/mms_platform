#!/usr/bin/env python3
"""
导入生产服务器的映射缓存到 MMS Platform

功能：
1. 读取导出的 da_checkitem_map.csv
2. 清洗和转换数据格式
3. 生成 SQL 迁移脚本
4. 导入到 MMS 数据库
"""
import pandas as pd
import hashlib
from datetime import datetime
from pathlib import Path

# 配置
INPUT_FILE = 'data/cache_mapping/da_checkitem_map.csv'
OUTPUT_CSV = 'data/cache_mapping/mms_cache_import.csv'
OUTPUT_SQL = 'data/cache_mapping/mms_cache_import.sql'

def clean_and_transform():
    """清洗和转换数据"""
    print("读取生产映射表...")
    df = pd.read_csv(INPUT_FILE)
    print(f"  总记录数: {len(df)}")

    # 1. 过滤有效记录
    df_valid = df[df['is_valid'] == 1].copy()
    print(f"  有效记录: {len(df_valid)}")

    # 2. 去除空值
    df_valid = df_valid[df_valid['original_checkitem'].notna()]
    df_valid = df_valid[df_valid['standard_checkitem_code'].notna()]
    print(f"  去除空值后: {len(df_valid)}")

    # 3. 转换为 MMS 格式
    df_mms = pd.DataFrame()

    # 基础字段映射（先转字符串再处理）
    df_mms['raw_check_item'] = df_valid['original_checkitem'].astype(str).str.strip()
    df_mms['modality'] = df_valid['modality'].fillna('').astype(str).str.strip()
    df_mms['standard_code'] = df_valid['standard_checkitem_code'].astype(str).str.strip()
    df_mms['standard_name'] = df_valid['standard_checkitem_name'].astype(str).str.strip()

    # 版本号处理（统一为 V3.8.2）
    df_mms['version'] = df_valid['standard_version'].fillna('V3.8.2')
    df_mms['version'] = df_mms['version'].replace('', 'V3.8.2')
    df_mms['version'] = df_mms['version'].replace('V1', 'V3.8.2')
    df_mms['version'] = df_mms['version'].replace('V3.0', 'V3.8.2')

    # MMS 特有字段
    df_mms['confidence'] = 1.0  # 人工审核，置信度 100%
    df_mms['source'] = 'import_production'
    df_mms['tier'] = 'exact'
    df_mms['compound_num'] = df_valid['compound_num'].fillna(1).astype(int)
    df_mms['unique_key'] = df_valid['unique_key'].fillna('')

    # 时间戳（转换为 datetime 类型）
    df_mms['created_at'] = pd.to_datetime(df_valid['create_time'], errors='coerce').fillna(datetime.now())
    df_mms['updated_at'] = pd.to_datetime(df_valid['update_time'], errors='coerce').fillna(datetime.now())

    # 4. 数据清洗
    # 去除模态为空的记录
    df_mms = df_mms[df_mms['modality'] != '']

    # 去除重复记录（保留最新的）
    df_mms = df_mms.sort_values('updated_at', ascending=False)
    df_mms = df_mms.drop_duplicates(
        subset=['raw_check_item', 'modality', 'version', 'standard_code'],
        keep='first'
    )

    print(f"  去重后: {len(df_mms)}")

    # 5. 按模态统计
    print("\n按模态统计:")
    modality_stats = df_mms.groupby('modality').size()
    for modality, count in modality_stats.items():
        print(f"  {modality}: {count} 条")

    # 6. 复合项目统计
    print("\n复合项目统计:")
    compound_stats = df_mms.groupby('compound_num').size()
    for num, count in compound_stats.items():
        print(f"  compound_num={num}: {count} 条")

    return df_mms

def generate_csv(df_mms):
    """生成 CSV 文件"""
    print(f"\n生成 CSV 文件: {OUTPUT_CSV}")
    df_mms.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print(f"  ✅ 已保存: {len(df_mms)} 条记录")

def generate_sql(df_mms):
    """生成 SQL 导入脚本"""
    print(f"\n生成 SQL 脚本: {OUTPUT_SQL}")

    sql_lines = []
    sql_lines.append("-- MMS Platform 生产缓存导入脚本")
    sql_lines.append("-- 生成时间: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    sql_lines.append(f"-- 记录数: {len(df_mms)}")
    sql_lines.append("")
    sql_lines.append("-- 创建临时表")
    sql_lines.append("CREATE TEMP TABLE IF NOT EXISTS temp_cache_import (")
    sql_lines.append("    raw_check_item VARCHAR(512),")
    sql_lines.append("    modality VARCHAR(32),")
    sql_lines.append("    standard_code VARCHAR(64),")
    sql_lines.append("    standard_name VARCHAR(128),")
    sql_lines.append("    version VARCHAR(32),")
    sql_lines.append("    confidence FLOAT,")
    sql_lines.append("    source VARCHAR(32),")
    sql_lines.append("    tier VARCHAR(32),")
    sql_lines.append("    compound_num INTEGER,")
    sql_lines.append("    unique_key VARCHAR(255)")
    sql_lines.append(");")
    sql_lines.append("")

    # 生成 INSERT 语句
    sql_lines.append("-- 插入数据")
    for idx, row in df_mms.iterrows():
        raw_item = row['raw_check_item'].replace("'", "''")
        std_name = row['standard_name'].replace("'", "''")
        unique_key = row['unique_key'].replace("'", "''") if row['unique_key'] else ''

        sql = f"""INSERT INTO temp_cache_import VALUES ('{raw_item}', '{row['modality']}', '{row['standard_code']}', '{std_name}', '{row['version']}', {row['confidence']}, '{row['source']}', '{row['tier']}', {row['compound_num']}, '{unique_key}');"""
        sql_lines.append(sql)

    sql_lines.append("")
    sql_lines.append("-- 合并到主表（去重）")
    sql_lines.append("""
INSERT INTO acr_standard_link (
    raw_check_item,
    modality,
    standard_code,
    standard_name,
    version,
    confidence,
    source,
    tier,
    created_at,
    updated_at
)
SELECT DISTINCT
    raw_check_item,
    modality,
    standard_code,
    standard_name,
    version,
    confidence,
    source,
    tier,
    NOW(),
    NOW()
FROM temp_cache_import
ON CONFLICT (raw_check_item, modality, version, standard_code)
DO UPDATE SET
    confidence = EXCLUDED.confidence,
    source = EXCLUDED.source,
    updated_at = NOW();
""")

    sql_lines.append("")
    sql_lines.append("-- 清理临时表")
    sql_lines.append("DROP TABLE temp_cache_import;")
    sql_lines.append("")
    sql_lines.append("-- 验证导入")
    sql_lines.append("SELECT ")
    sql_lines.append("    source,")
    sql_lines.append("    COUNT(*) as count,")
    sql_lines.append("    AVG(confidence) as avg_confidence")
    sql_lines.append("FROM acr_standard_link")
    sql_lines.append("WHERE source = 'import_production'")
    sql_lines.append("GROUP BY source;")

    # 写入文件
    with open(OUTPUT_SQL, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sql_lines))

    print(f"  ✅ 已保存: {OUTPUT_SQL}")

def generate_report(df_mms):
    """生成导入报告"""
    print("\n" + "="*60)
    print("生产缓存导入报告")
    print("="*60)

    print(f"\n数据源: {INPUT_FILE}")
    print(f"导入时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n总记录数: {len(df_mms)}")

    print("\n按模态分布:")
    modality_stats = df_mms.groupby('modality').agg({
        'raw_check_item': 'count',
        'confidence': 'mean'
    }).rename(columns={'raw_check_item': 'count'})
    print(modality_stats)

    print("\n数据示例（前5条）:")
    for idx, row in df_mms.head(5).iterrows():
        print(f"\n  [{idx+1}] {row['raw_check_item']} ({row['modality']})")
        print(f"      → {row['standard_name']} [{row['standard_code']}]")
        print(f"      置信度: {row['confidence']}, 来源: {row['source']}")

    print("\n" + "="*60)
    print("✅ 数据准备完成，可以执行以下步骤导入：")
    print("="*60)
    print("\n方式1: 使用 SQL 脚本导入")
    print(f"  psql -h <host> -U <user> -d <database> -f {OUTPUT_SQL}")

    print("\n方式2: 使用 Alembic 迁移")
    print("  1. poetry run alembic revision -m 'import_production_cache'")
    print(f"  2. 将 {OUTPUT_SQL} 内容复制到迁移文件的 upgrade() 函数")
    print("  3. poetry run alembic upgrade head")

    print("\n方式3: 使用 pandas 直接导入")
    print("  python scripts/direct_import_cache.py")

    print("\n" + "="*60)

def main():
    print("="*60)
    print("MMS Platform - 生产缓存导入工具")
    print("="*60)

    # 创建输出目录
    Path('data/cache_mapping').mkdir(parents=True, exist_ok=True)

    # 1. 清洗和转换
    df_mms = clean_and_transform()

    # 2. 生成 CSV
    generate_csv(df_mms)

    # 3. 生成 SQL
    generate_sql(df_mms)

    # 4. 生成报告
    generate_report(df_mms)

if __name__ == '__main__':
    main()

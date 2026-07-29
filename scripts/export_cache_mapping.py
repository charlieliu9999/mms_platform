#!/usr/bin/env python3
"""
从生产服务器数据库导出映射缓存表
"""
import pymysql
import pandas as pd
import sys

# 数据库配置
DB_CONFIG = {
    'host': '210.12.11.251',
    'port': 26306,
    'user': 'data',
    'password': 'rimag123456',
    'database': 'rimag_data',
    'charset': 'utf8mb4'
}

def export_mapping_table():
    """导出 da_checkitem_map 映射表"""
    print("连接数据库...")
    conn = pymysql.connect(**DB_CONFIG)

    try:
        # 1. 导出 da_checkitem_map (映射缓存表)
        print("\n导出 da_checkitem_map 表...")
        query_map = """
        SELECT
            id,
            unique_key,
            original_checkitem,
            modality,
            standard_checkitem_code,
            standard_checkitem_name,
            standard_modality,
            compound_num,
            standard_version,
            operate_user,
            is_valid,
            create_time,
            update_time
        FROM da_checkitem_map
        ORDER BY id
        """

        df_map = pd.read_sql(query_map, conn)
        output_file = 'data/cache_mapping/da_checkitem_map.csv'
        df_map.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✅ 导出完成: {output_file}")
        print(f"   总记录数: {len(df_map)}")
        print(f"   有效记录: {df_map['is_valid'].sum()}")

        # 按模态统计
        print("\n按模态统计:")
        modality_stats = df_map.groupby('modality').agg({
            'id': 'count',
            'is_valid': 'sum'
        }).rename(columns={'id': 'total', 'is_valid': 'valid'})
        print(modality_stats)

        # 显示示例数据
        print("\n数据示例（前5条有效记录）:")
        valid_samples = df_map[df_map['is_valid'] == 1].head(5)
        for idx, row in valid_samples.iterrows():
            print(f"\n  [{row['id']}] {row['original_checkitem']} ({row['modality']})")
            print(f"      → {row['standard_checkitem_name']} [{row['standard_checkitem_code']}]")

        # 2. 导出 s_standard_exam_rule_nlp (原始待匹配数据，供参考)
        print("\n\n导出 s_standard_exam_rule_nlp 表（待匹配数据）...")
        query_nlp = """
        SELECT
            md5_exa_o_item_list,
            exa_o_modality,
            exa_o_item_list,
            exa_b_modality,
            exa_b_item_name,
            exa_b_item_code
        FROM s_standard_exam_rule_nlp
        LIMIT 5000
        """

        df_nlp = pd.read_sql(query_nlp, conn)
        output_file_nlp = 'data/cache_mapping/s_standard_exam_rule_nlp_sample.csv'
        df_nlp.to_csv(output_file_nlp, index=False, encoding='utf-8-sig')
        print(f"✅ 导出完成: {output_file_nlp}")
        print(f"   总记录数: {len(df_nlp)}")

    finally:
        conn.close()
        print("\n数据库连接已关闭")

if __name__ == '__main__':
    try:
        export_mapping_table()
        print("\n✅ 所有导出任务完成！")
    except Exception as e:
        print(f"\n❌ 导出失败: {e}", file=sys.stderr)
        sys.exit(1)

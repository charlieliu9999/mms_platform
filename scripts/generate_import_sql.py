#!/usr/bin/env python3
"""
生成SQL脚本，将原系统词典导入到当前数据库
"""
import csv
from pathlib import Path

# 词汇类型到词性的映射
TYPE_TO_POS_MAP = {
    'body_part': 'n',
    'scan_method': 'n',
    'position': 'n',
    'post_process': 'n',
    'modifier': 'a',
    'device': 'n',
}

# 预览文件
PREVIEW_FILE = "data/lexicon/import_preview.csv"

# 输出SQL文件
OUTPUT_SQL = "data/lexicon/import_dict.sql"


def generate_sql():
    """生成导入SQL"""

    with open(PREVIEW_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        words = list(reader)

    print(f"📁 读取词汇: {len(words)} 条")

    # 分优先级
    high_priority = [w for w in words if w['priority'] == 'high']
    normal_priority = [w for w in words if w['priority'] == 'normal']

    print(f"   高优先级: {len(high_priority)} 条")
    print(f"   普通优先级: {len(normal_priority)} 条")

    sql_lines = []
    sql_lines.append("-- 导入医学词典（从原系统）")
    sql_lines.append("-- 生成时间: 2026-07-31")
    sql_lines.append(f"-- 总词条数: {len(words)}")
    sql_lines.append("")

    # 高优先级词汇
    sql_lines.append("-- ======================")
    sql_lines.append(f"-- 第一批：高优先级词汇 ({len(high_priority)}条)")
    sql_lines.append("-- 包含MG/US/SPECT/介入关键词")
    sql_lines.append("-- ======================")
    sql_lines.append("")
    sql_lines.append("INSERT INTO nlp_medical_dict (word, type, enable) VALUES")

    values = []
    for w in high_priority:
        word = w['word'].replace("'", "''")  # SQL转义
        word_type = w['mapped_type']

        values.append(f"  ('{word}', '{word_type}', 0)")

    sql_lines.append(",\n".join(values))
    sql_lines.append("ON CONFLICT (word) DO NOTHING;")
    sql_lines.append("")
    sql_lines.append("")

    # 普通优先级词汇
    sql_lines.append("-- ======================")
    sql_lines.append(f"-- 第二批：普通优先级词汇 ({len(normal_priority)}条)")
    sql_lines.append("-- ======================")
    sql_lines.append("")
    sql_lines.append("INSERT INTO nlp_medical_dict (word, type, enable) VALUES")

    values = []
    for w in normal_priority:
        word = w['word'].replace("'", "''")
        word_type = w['mapped_type']

        values.append(f"  ('{word}', '{word_type}', 0)")

    sql_lines.append(",\n".join(values))
    sql_lines.append("ON CONFLICT (word) DO NOTHING;")
    sql_lines.append("")

    # 写入文件
    sql_content = "\n".join(sql_lines)

    output_file = Path(OUTPUT_SQL)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(sql_content)

    print(f"\n✅ SQL脚本已生成: {output_file}")
    print(f"   文件大小: {output_file.stat().st_size / 1024:.1f} KB")
    print(f"\n💡 执行导入:")
    print(f"   psql -h localhost -p 5433 -U postgres -d mms_db -f {output_file}")

    return output_file


if __name__ == "__main__":
    generate_sql()

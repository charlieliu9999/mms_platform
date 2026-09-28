"""import_phase1_merged_lexicon

Revision ID: 3d97fd5e6377
Revises: 20260728_1055_load_finalized_lexicon
Create Date: 2026-07-29 17:35:50.708219

导入 Phase 1 合并后的词表数据：
- merged_medical_dict.csv (2,568 条)
- merged_phrase_map.csv (9,395 条)
"""
from typing import Sequence, Union
from pathlib import Path
import csv

from alembic import op
import sqlalchemy as sa


revision: str = '3d97fd5e6377'
down_revision: Union[str, None] = '99a81f998fcf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 获取项目根目录
    migrations_dir = Path(__file__).parent.parent.parent
    phase1_dir = migrations_dir / "phase1-deliverables"

    print(f"📁 Phase 1 数据目录: {phase1_dir}")

    # 1. 导入医学词典
    medical_dict_file = phase1_dir / "merged_medical_dict.csv"
    if medical_dict_file.exists():
        print(f"📖 导入医学词典: {medical_dict_file}")

        with open(medical_dict_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                # 转换 enable 字段为整数（0.0 -> 0, 1.0 -> 1）
                enable_val = 0
                if row.get('enable'):
                    try:
                        enable_val = int(float(row['enable']))
                    except (ValueError, TypeError):
                        enable_val = 0

                rows.append({
                    'word': row['word'],
                    'type': row.get('type', ''),
                    'enable': enable_val
                })

            if rows:
                # 先清空旧数据
                conn.execute(sa.text("TRUNCATE TABLE nlp_medical_dict CASCADE"))

                # 批量插入
                conn.execute(sa.text("""
                    INSERT INTO nlp_medical_dict (word, type, enable)
                    VALUES (:word, :type, :enable)
                """), rows)
                print(f"   ✅ 导入 {len(rows)} 条医学词典")
    else:
        print(f"   ⚠️  文件不存在: {medical_dict_file}")

    # 2. 导入短语映射
    phrase_map_file = phase1_dir / "merged_phrase_map.csv"
    if phrase_map_file.exists():
        print(f"📖 导入短语映射: {phrase_map_file}")

        with open(phrase_map_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                # 转换 enable 字段
                enable_val = 0
                if row.get('enable'):
                    try:
                        enable_val = int(float(row['enable']))
                    except (ValueError, TypeError):
                        enable_val = 0

                rows.append({
                    'modality': row.get('device', 'ALL'),
                    'src_word': row.get('src_word', ''),
                    'dst_word': row.get('dst_word', ''),
                    'step': row.get('step', ''),
                    'version': row.get('version', 'V3.8'),
                    'enable': enable_val
                })

            if rows:
                # 先清空旧数据
                conn.execute(sa.text("TRUNCATE TABLE nlp_phrase_map CASCADE"))

                # 批量插入
                conn.execute(sa.text("""
                    INSERT INTO nlp_phrase_map (modality, src_word, dst_word, step, version, enable)
                    VALUES (:modality, :src_word, :dst_word, :step, :version, :enable)
                """), rows)
                print(f"   ✅ 导入 {len(rows)} 条短语映射")
    else:
        print(f"   ⚠️  文件不存在: {phrase_map_file}")

    print("✅ Phase 1 词表导入完成")


def downgrade() -> None:
    conn = op.get_bind()

    # 清空导入的数据
    conn.execute(sa.text("TRUNCATE TABLE nlp_medical_dict CASCADE"))
    conn.execute(sa.text("TRUNCATE TABLE nlp_phrase_map CASCADE"))

    print("✅ Phase 1 词表已清空")

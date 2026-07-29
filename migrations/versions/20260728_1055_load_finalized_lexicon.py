"""Load finalized lexicon data

Revision ID: 20260728_1055_load_finalized_lexicon
Revises: 99a81f998fcf
Create Date: 2026-07-28 10:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import csv
from pathlib import Path

# revision identifiers, used by Alembic.
revision: str = '20260728_1055_load_finalized_lexicon'
down_revision: Union[str, None] = '99a81f998fcf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """导入定稿词表数据（Phase 0-4 裁定结果）"""

    # 数据文件路径（相对于 match_service 根目录）
    base_path = Path(__file__).parent.parent.parent / "phase0-deliverables"

    conn = op.get_bind()

    # 1. 导入 nlp_medical_dict
    print(f"导入 medical_dict...")
    medical_dict_path = base_path / "finalized_medical_dict.csv"
    if medical_dict_path.exists():
        with open(medical_dict_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if rows:
                conn.execute(sa.text("""
                    INSERT INTO nlp_medical_dict (word, type, enable)
                    VALUES (:word, :type, :enable)
                    ON CONFLICT (word, type) DO UPDATE SET
                        enable = EXCLUDED.enable
                """), rows)
        print(f"  ✅ 已导入 {len(rows)} 条")
    else:
        print(f"  ⚠️ 文件不存在: {medical_dict_path}")

    # 2. 导入 nlp_phrase_map
    print(f"导入 phrase_map...")
    phrase_map_path = base_path / "finalized_phrase_map.csv"
    if phrase_map_path.exists():
        with open(phrase_map_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if rows:
                conn.execute(sa.text("""
                    INSERT INTO nlp_phrase_map (modality, src_word, dst_word, step, version, enable)
                    VALUES (:modality, :src_word, :dst_word, :step, :version, :enable)
                    ON CONFLICT (modality, src_word, dst_word, step, version) DO UPDATE SET
                        enable = EXCLUDED.enable
                """), rows)
        print(f"  ✅ 已导入 {len(rows)} 条")
    else:
        print(f"  ⚠️ 文件不存在: {phrase_map_path}")

    # 3. 导入 nlp_ambiguity
    print(f"导入 ambiguity...")
    ambiguity_path = base_path / "finalized_ambiguity.csv"
    if ambiguity_path.exists():
        with open(ambiguity_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if rows:
                conn.execute(sa.text("""
                    INSERT INTO nlp_ambiguity (src_body, src_process, dst_body, dst_process, version, modality, enable)
                    VALUES (:src_body, :src_process, :dst_body, :dst_process, :version, :modality, :enable)
                    ON CONFLICT (src_body, src_process, dst_body, dst_process, version, modality) DO UPDATE SET
                        enable = EXCLUDED.enable
                """), rows)
        print(f"  ✅ 已导入 {len(rows)} 条")
    else:
        print(f"  ⚠️ 文件不存在: {ambiguity_path}")

    print("定稿词表导入完成")


def downgrade() -> None:
    """回滚：清空词表数据"""
    conn = op.get_bind()
    conn.execute(sa.text("TRUNCATE TABLE nlp_medical_dict CASCADE"))
    conn.execute(sa.text("TRUNCATE TABLE nlp_phrase_map CASCADE"))
    conn.execute(sa.text("TRUNCATE TABLE nlp_ambiguity CASCADE"))
    print("已清空词表数据")

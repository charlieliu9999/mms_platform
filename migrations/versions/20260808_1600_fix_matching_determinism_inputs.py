"""Fix MR normalization rules and persist effective modality.

Revision ID: 20260808_1600
Revises: 20260808_1500
Create Date: 2026-08-08 16:00:00

- 修正与 V3.8.2 标准库命名冲突的 MR 肝脏/垂体归一化规则
- procedure_match_results 记录文本路由后的实际匹配模态
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260808_1600"
down_revision: Union[str, None] = "20260808_1500"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 旧规则面向已归档标准表；统一标准表使用“肝脏”“垂体”。反向映射会让
    # 完全同名项目无法查表，并且“肝→肝脏 / 肝脏→肝”形成归一化环。
    op.execute("""
        UPDATE nlp_phrase_map
        SET dst_word = src_word
        WHERE modality = 'MR'
          AND step = 'normalize'
          AND version = 'V3.8.2'
          AND src_word IN ('肝脏', '垂体')
          AND enable = 0
    """)

    op.add_column(
        "procedure_match_results",
        sa.Column("effective_modality", sa.String(length=32), nullable=True),
    )
    op.execute("""
        UPDATE procedure_match_results pmr
        SET effective_modality = CASE UPPER(COALESCE(pd.modality, ''))
            WHEN 'MRI' THEN 'MR'
            WHEN 'XR' THEN 'DR'
            WHEN 'CR' THEN 'DR'
            WHEN 'X线' THEN 'DR'
            WHEN 'AN' THEN 'DSA'
            WHEN 'ANGIO' THEN 'DSA'
            WHEN 'NM' THEN 'SPECT'
            WHEN 'PET' THEN 'PET/CT'
            WHEN 'PET-CT' THEN 'PET/CT'
            WHEN 'PET-MR' THEN 'PET/MR'
            WHEN 'CBCT' THEN 'CT'
            WHEN 'CT-DE' THEN 'CT'
            WHEN 'CT-4D' THEN 'CT'
            ELSE UPPER(COALESCE(pd.modality, ''))
        END
        FROM procedure_dictionary pd
        WHERE pd.id = pmr.procedure_id
    """)


def downgrade() -> None:
    op.drop_column("procedure_match_results", "effective_modality")
    op.execute("""
        UPDATE nlp_phrase_map
        SET dst_word = CASE src_word
            WHEN '肝脏' THEN '肝'
            WHEN '垂体' THEN '鞍区'
            ELSE dst_word
        END
        WHERE modality = 'MR'
          AND step = 'normalize'
          AND version = 'V3.8.2'
          AND src_word IN ('肝脏', '垂体')
          AND enable = 0
    """)

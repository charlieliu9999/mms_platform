"""nuclear_keyword_rule_improvements

Revision ID: 20260820_2100
Revises: 20260820_2000
Create Date: 2026-08-20 21:00:00

核医学关键词规则修复：
1. SPECT 全身骨显像/局部骨显像 → 精确 bp2（全身骨/局部骨），避免多候选
2. SPECT 静脉显像 → 静脉（命中 SPECT放射性核素静脉显像）
3. PET 新增 肾上腺 → 局部（腹部）
4. PET 新增 原发灶及转移灶 → 躯干+头部+四肢
5. PET 模拟定位 → unmatchable（放疗定位排除）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260820_2100'
down_revision: Union[str, None] = '20260820_2000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text(
        "UPDATE keyword_match_rules SET dst_value='全身骨' "
        "WHERE modality='SPECT' AND rule_type='body' AND keywords='全身骨显像;全身骨' AND enable=0"
    ))
    conn.execute(sa.text(
        "UPDATE keyword_match_rules SET dst_value='局部骨' "
        "WHERE modality='SPECT' AND rule_type='body' AND keywords='局部骨显像;局部骨' AND enable=0"
    ))
    conn.execute(sa.text(
        "UPDATE keyword_match_rules SET dst_value='静脉' "
        "WHERE modality='SPECT' AND rule_type='body' AND keywords='静脉显像' AND enable=0"
    ))

    exists = conn.execute(sa.text(
        "SELECT 1 FROM keyword_match_rules WHERE modality='PET' AND rule_type='body' AND keywords='肾上腺' AND enable=0"
    )).first()
    if exists is None:
        conn.execute(sa.text(
            "INSERT INTO keyword_match_rules (modality, rule_type, keywords, dst_value, priority, enable) "
            "VALUES ('PET','body','肾上腺','局部（腹部）',11,0)"
        ))

    exists = conn.execute(sa.text(
        "SELECT 1 FROM keyword_match_rules WHERE modality='PET' AND rule_type='body' AND keywords LIKE '%原发灶%' AND enable=0"
    )).first()
    if exists is None:
        conn.execute(sa.text(
            "INSERT INTO keyword_match_rules (modality, rule_type, keywords, dst_value, priority, enable) "
            "VALUES ('PET','body','原发灶及转移灶;转移灶','躯干+头部+四肢',1,0)"
        ))

    exists = conn.execute(sa.text(
        "SELECT 1 FROM keyword_match_rules WHERE modality='PET' AND rule_type='unmatchable' AND keywords='模拟定位' AND enable=0"
    )).first()
    if exists is None:
        conn.execute(sa.text(
            "INSERT INTO keyword_match_rules (modality, rule_type, keywords, dst_value, priority, enable) "
            "VALUES ('PET','unmatchable','模拟定位',NULL,5,0)"
        ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "UPDATE keyword_match_rules SET dst_value='骨' "
        "WHERE modality='SPECT' AND rule_type='body' AND keywords IN ('全身骨显像;全身骨','局部骨显像;局部骨') AND enable=0"
    ))
    conn.execute(sa.text(
        "UPDATE keyword_match_rules SET dst_value='血管' "
        "WHERE modality='SPECT' AND rule_type='body' AND keywords='静脉显像' AND enable=0"
    ))
    conn.execute(sa.text(
        "DELETE FROM keyword_match_rules WHERE modality='PET' AND enable=0 AND ("
        "keywords='肾上腺' OR keywords LIKE '%原发灶%' OR keywords='模拟定位')"
    ))

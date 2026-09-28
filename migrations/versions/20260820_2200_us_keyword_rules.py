"""us_keyword_rules_and_matcher

Revision ID: 20260820_2200
Revises: 20260820_2100
Create Date: 2026-08-20 22:00:00

US 关键词规则补充（配合 us_spect_pet_matcher 单候选收敛）：
1. US body: 胃充盈排空;胃排空 → 胃
2. US body: 外周神经 → 外周神经
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260820_2200'
down_revision: Union[str, None] = '20260820_2100'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    for kw, dst in [("胃充盈排空;胃排空", "胃"), ("外周神经", "外周神经")]:
        exists = conn.execute(sa.text(
            "SELECT 1 FROM keyword_match_rules WHERE modality='US' AND rule_type='body' "
            "AND keywords=:k AND enable=0"
        ), {"k": kw}).first()
        if exists is None:
            conn.execute(sa.text(
                "INSERT INTO keyword_match_rules (modality, rule_type, keywords, dst_value, priority, enable) "
                "VALUES ('US','body',:k,:d,200,0)"
            ), {"k": kw, "d": dst})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "DELETE FROM keyword_match_rules WHERE modality='US' AND rule_type='body' "
        "AND keywords IN ('胃充盈排空;胃排空','外周神经') AND enable=0"
    ))

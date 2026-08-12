"""Restore standard position metadata and version procedure matching state.

Revision ID: 20260808_1500
Revises: 20260804_1400
Create Date: 2026-08-08 15:00:00

- standard_check_items 恢复 DR/MG 查询所需的独立体位、设备字段
- match_cache 增加 rule_version，并失效迁移前无法校验版本的旧缓存
- procedure_match_results 持久化匹配测试中心最近一次运行结果
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260808_1500"
down_revision: Union[str, None] = "20260804_1400"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "standard_check_items",
        sa.Column("position_name", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "standard_check_items",
        sa.Column("position_code", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "standard_check_items",
        sa.Column("device_type_name", sa.String(length=50), nullable=True),
    )

    # B-08 统一标准表时丢失了 position/device 维度。归档表仍保留这些字段，
    # 按 item_code 选择最近一条非空体位记录回填；DR 设备字段可由模态可靠推导。
    op.execute("""
        WITH archived AS (
            SELECT DISTINCT ON (checkitem_code)
                checkitem_code, position_name, position_code, device_type_name
            FROM nlp_checkitem_standard_deprecated
            WHERE checkitem_code IS NOT NULL
              AND COALESCE(position_name, '') <> ''
            ORDER BY checkitem_code, id DESC
        )
        UPDATE standard_check_items current
        SET position_name = archived.position_name,
            position_code = archived.position_code,
            device_type_name = COALESCE(NULLIF(archived.device_type_name, ''), current.modality)
        FROM archived
        WHERE current.item_code = archived.checkitem_code
    """)
    op.execute("""
        UPDATE standard_check_items
        SET device_type_name = 'DR'
        WHERE modality = 'DR' AND COALESCE(device_type_name, '') = ''
    """)

    op.add_column(
        "match_cache",
        sa.Column("rule_version", sa.String(length=80), nullable=True),
    )
    op.create_index(
        "ix_match_cache_rule_version", "match_cache", ["rule_version"], unique=False
    )

    # 旧缓存没有规则版本，不能证明与当前词表/标准库一致。统一失效但保留记录，
    # 后续同 key 匹配会由 CacheService.store 覆盖并刷新 TTL。
    op.execute("UPDATE match_cache SET expires_at = NOW(), rule_version = NULL")

    op.create_table(
        "procedure_match_results",
        sa.Column("procedure_id", sa.Integer(), nullable=False),
        sa.Column("matched", sa.Boolean(), nullable=False),
        sa.Column("tier", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column(
            "standards_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("reason_code", sa.String(length=50), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("rule_version", sa.String(length=80), nullable=False),
        sa.Column(
            "evaluated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["procedure_id"], ["procedure_dictionary.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("procedure_id"),
    )
    op.create_index(
        "ix_procedure_match_results_matched",
        "procedure_match_results",
        ["matched"],
        unique=False,
    )
    op.create_index(
        "ix_procedure_match_results_rule_version",
        "procedure_match_results",
        ["rule_version"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_procedure_match_results_rule_version",
        table_name="procedure_match_results",
    )
    op.drop_index(
        "ix_procedure_match_results_matched",
        table_name="procedure_match_results",
    )
    op.drop_table("procedure_match_results")

    op.drop_index("ix_match_cache_rule_version", table_name="match_cache")
    op.drop_column("match_cache", "rule_version")

    op.drop_column("standard_check_items", "device_type_name")
    op.drop_column("standard_check_items", "position_code")
    op.drop_column("standard_check_items", "position_name")

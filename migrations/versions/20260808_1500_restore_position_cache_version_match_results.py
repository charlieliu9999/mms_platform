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


_OWNERSHIP_TAG = "alembic:20260808_1500"
_RESIZE_TAG_PREFIX = f"{_OWNERSHIP_TAG};restore-varchar="


def _column_info(table_name: str, column_name: str) -> dict | None:
    for column in sa.inspect(op.get_bind()).get_columns(table_name):
        if column["name"] == column_name:
            return column
    return None


def _ensure_string_column(
    table_name: str, column_name: str, length: int
) -> None:
    existing = _column_info(table_name, column_name)
    if existing is not None:
        existing_type = existing["type"]
        if not isinstance(existing_type, sa.String) or existing_type.length is None:
            raise RuntimeError(
                f"Schema drift: {table_name}.{column_name} exists as "
                f"{existing_type}, expected VARCHAR({length})"
            )
        if existing_type.length < length:
            if _column_comment(table_name, column_name) is not None:
                raise RuntimeError(
                    f"Schema drift: cannot widen commented column "
                    f"{table_name}.{column_name} safely"
                )
            op.alter_column(
                table_name,
                column_name,
                existing_type=existing_type,
                type_=sa.String(length=length),
                existing_nullable=existing["nullable"],
            )
            op.execute(
                f"COMMENT ON COLUMN {table_name}.{column_name} IS "
                f"'{_RESIZE_TAG_PREFIX}{existing_type.length}'"
            )
        return

    op.add_column(
        table_name,
        sa.Column(column_name, sa.String(length=length), nullable=True),
    )
    op.execute(
        f"COMMENT ON COLUMN {table_name}.{column_name} IS '{_OWNERSHIP_TAG}'"
    )


def _index_info(table_name: str, index_name: str) -> dict | None:
    for index in sa.inspect(op.get_bind()).get_indexes(table_name):
        if index["name"] == index_name:
            return index
    return None


def _ensure_index(
    table_name: str, index_name: str, columns: list[str]
) -> None:
    existing = _index_info(table_name, index_name)
    if existing is not None:
        if existing["column_names"] != columns or existing.get("unique", False):
            raise RuntimeError(
                f"Schema drift: index {index_name} exists with unexpected definition"
            )
        return

    op.create_index(index_name, table_name, columns, unique=False)
    op.execute(f"COMMENT ON INDEX {index_name} IS '{_OWNERSHIP_TAG}'")


def _object_is_owned(object_name: str) -> bool:
    return bool(
        op.get_bind()
        .execute(
            sa.text(
                "SELECT obj_description(to_regclass(:name), 'pg_class') = :tag"
            ),
            {"name": object_name, "tag": _OWNERSHIP_TAG},
        )
        .scalar()
    )


def _column_comment(table_name: str, column_name: str) -> str | None:
    return (
        op.get_bind()
        .execute(
            sa.text(
                """
                SELECT col_description(CAST(:table_name AS regclass), attribute.attnum)
                FROM pg_attribute AS attribute
                WHERE attribute.attrelid = CAST(:table_name AS regclass)
                  AND attribute.attname = :column_name
                  AND NOT attribute.attisdropped
                """
            ),
            {"table_name": table_name, "column_name": column_name},
        )
        .scalar()
    )


def _column_is_owned(table_name: str, column_name: str) -> bool:
    return _column_comment(table_name, column_name) == _OWNERSHIP_TAG


def _restore_resized_column(table_name: str, column_name: str) -> None:
    comment = _column_comment(table_name, column_name)
    if not comment or not comment.startswith(_RESIZE_TAG_PREFIX):
        return
    original_length = int(comment.removeprefix(_RESIZE_TAG_PREFIX))
    existing = _column_info(table_name, column_name)
    if existing is None:
        raise RuntimeError(f"Schema drift: {table_name}.{column_name} disappeared")
    op.alter_column(
        table_name,
        column_name,
        existing_type=existing["type"],
        type_=sa.String(length=original_length),
        existing_nullable=existing["nullable"],
    )
    op.execute(f"COMMENT ON COLUMN {table_name}.{column_name} IS NULL")


def _require_table_columns(table_name: str, required_columns: set[str]) -> None:
    actual_columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }
    missing = required_columns - actual_columns
    if missing:
        raise RuntimeError(
            f"Schema drift: {table_name} is missing columns {sorted(missing)}"
        )


def upgrade() -> None:
    # Some historical databases already contain a subset of this revision's
    # schema while alembic_version still points to 33a6ffc77484. Reconcile
    # compatible objects and fail closed on incompatible definitions.
    _ensure_string_column("standard_check_items", "position_name", 200)
    _ensure_string_column("standard_check_items", "position_code", 100)
    _ensure_string_column("standard_check_items", "device_type_name", 50)

    # B-08 统一标准表时丢失了 position/device 维度。归档表仍保留这些字段，
    # 按 item_code 选择最近一条非空体位记录回填；DR 设备字段可由模态可靠推导。
    # Bug #8 修复：device_type_name 是 DR 专用字段，不应用 COALESCE 回填到其他模态
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
            device_type_name = CASE
                WHEN current.modality = 'DR'
                THEN COALESCE(NULLIF(archived.device_type_name, ''), 'DR')
                ELSE NULL
            END
        FROM archived
        WHERE current.item_code = archived.checkitem_code
    """)
    op.execute("""
        UPDATE standard_check_items
        SET device_type_name = 'DR'
        WHERE modality = 'DR' AND COALESCE(device_type_name, '') = ''
    """)

    _ensure_string_column("match_cache", "rule_version", 80)
    _ensure_index("match_cache", "ix_match_cache_rule_version", ["rule_version"])

    # 旧缓存没有规则版本，不能证明与当前词表/标准库一致。统一失效但保留记录，
    # 后续同 key 匹配会由 CacheService.store 覆盖并刷新 TTL。
    # Bug #2 修复：rule_version 列定义为 NOT NULL，不能设为 NULL，使用空字符串标记失效
    op.execute("UPDATE match_cache SET expires_at = NOW(), rule_version = ''")

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("procedure_match_results"):
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
        op.execute(
            f"COMMENT ON TABLE procedure_match_results IS '{_OWNERSHIP_TAG}'"
        )

    _require_table_columns(
        "procedure_match_results",
        {
            "procedure_id",
            "matched",
            "tier",
            "confidence",
            "source",
            "standards_json",
            "reason_code",
            "detail",
            "rule_version",
            "evaluated_at",
        },
    )
    _ensure_index(
        "procedure_match_results",
        "ix_procedure_match_results_matched",
        ["matched"],
    )
    _ensure_index(
        "procedure_match_results",
        "ix_procedure_match_results_rule_version",
        ["rule_version"],
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("procedure_match_results"):
        for index_name in (
            "ix_procedure_match_results_rule_version",
            "ix_procedure_match_results_matched",
        ):
            if _index_info("procedure_match_results", index_name) and _object_is_owned(
                index_name
            ):
                op.drop_index(index_name, table_name="procedure_match_results")
        if _object_is_owned("procedure_match_results"):
            op.drop_table("procedure_match_results")

    if _index_info("match_cache", "ix_match_cache_rule_version") and _object_is_owned(
        "ix_match_cache_rule_version"
    ):
        op.drop_index("ix_match_cache_rule_version", table_name="match_cache")
    if _column_is_owned("match_cache", "rule_version"):
        op.drop_column("match_cache", "rule_version")
    else:
        # Bug #14 修复：只在列存在时才尝试恢复
        if _column_info("match_cache", "rule_version") is not None:
            _restore_resized_column("match_cache", "rule_version")

    for column_name in ("device_type_name", "position_code", "position_name"):
        if _column_is_owned("standard_check_items", column_name):
            op.drop_column("standard_check_items", column_name)
        else:
            # Bug #14 修复：只在列存在时才尝试恢复
            if _column_info("standard_check_items", column_name) is not None:
                _restore_resized_column("standard_check_items", column_name)

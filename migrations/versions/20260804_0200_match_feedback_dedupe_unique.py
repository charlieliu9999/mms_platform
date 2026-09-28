"""match_feedback 按 (text_hash, modality) 去重并加唯一约束

Revision ID: 20260804_0200
Revises: 20260731_0930
Create Date: 2026-08-04 02:00:00.000000

背景（B-16/D-03）：
    /api/feedback 对同一 (text_hash, modality) 反复 INSERT，导致 match_feedback
    出现约 3 倍重复（6891 行 / 2287 唯一键）。本迁移：
      1. 清理历史重复，每组仅保留 id 最大（最新）的一条；
      2. 建立 (text_hash, modality) 唯一索引，配合接口层
         INSERT ... ON CONFLICT DO UPDATE 实现幂等 upsert。
"""
from typing import Sequence, Union

from alembic import op


revision: str = '20260804_0200'
down_revision: Union[str, None] = '20260731_0930'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) 清理重复：同一 (text_hash, modality) 仅保留 id 最大的一条
    op.execute(
        """
        DELETE FROM match_feedback a
        USING match_feedback b
        WHERE a.text_hash = b.text_hash
          AND a.modality = b.modality
          AND a.id < b.id
        """
    )

    # 2) 建立唯一索引（去重后才不会冲突）
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_match_feedback_text_hash_modality
        ON match_feedback (text_hash, modality)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_match_feedback_text_hash_modality")

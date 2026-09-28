"""B-19: 补充 SPECT/PET/OCT 的 unmatchable 规则组

Revision ID: 20260804_1400
Revises: 20260804_1300
Create Date: 2026-08-04 14:00:00.000000

背景（B-19）：
    keyword_match_rules 表中 SPECT/PET/OCT 缺少 unmatchable 规则，
    导致 USSpectPetMatcher._load_rules_from_db() 初始化时记录 logger.error
    告警，且 _spect_unmatchable / _pet_unmatchable / _oct_unmatchable 始终
    为空 tuple，无法过滤非影像检查医嘱（临床操作、科研、院际会诊等）。

    US 和 DSA 已有 unmatchable 规则；本迁移为剩余三个模态补种同一套
    通用排除词（与 US_UNMATCHABLE 对齐的子集，仅取跨模态通用词）。
"""
from typing import Sequence, Union

from alembic import op

revision: str = '20260804_1400'
down_revision: Union[str, None] = '20260804_1300'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 通用跨模态排除词（与 US_UNMATCHABLE 对齐的子集）
_COMMON_UNMATCHABLE = [
    '临床操作',
    'GCP专用',
    '科研',
    '院际会诊',
    '人工智能',
]


def upgrade() -> None:
    # 幂等：先删除已有（防重复运行），再插入
    op.execute(
        "DELETE FROM keyword_match_rules "
        "WHERE modality IN ('SPECT', 'PET', 'OCT') AND rule_type = 'unmatchable'"
    )

    rows = []
    for modality in ('SPECT', 'PET', 'OCT'):
        for priority, kw in enumerate(_COMMON_UNMATCHABLE):
            rows.append(
                f"('{modality}', 'unmatchable', '{kw}', NULL, {priority}, 0)"
            )

    op.execute(
        "INSERT INTO keyword_match_rules "
        "(modality, rule_type, keywords, dst_value, priority, enable) VALUES "
        + ", ".join(rows)
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM keyword_match_rules "
        "WHERE modality IN ('SPECT', 'PET', 'OCT') AND rule_type = 'unmatchable'"
    )

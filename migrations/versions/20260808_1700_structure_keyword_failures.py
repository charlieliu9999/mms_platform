"""Add high-confidence keyword aliases and explicit medical entities.

Revision ID: 20260808_1700
Revises: 20260808_1600
Create Date: 2026-08-08 17:00:00

- 补充可唯一映射到现有标准维度的 US 肝胆胰、胃部别名
- 对已有医学实体但标准库尚无结构化项目的 US/SPECT 描述显式建词
- 补充 DSA 机械性血栓切除治疗排除词

运行时以 keyword_match_rules 为单一真相，故规则变更必须通过迁移进入数据库。
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260808_1700"
down_revision: Union[str, None] = "20260808_1600"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_REMARK = "P2-structured-keyword-failure-20260808"

# priority 使用负数，确保特异词先于历史通用规则。不存在对应结构化标准的
# dst_value 只用于证明医学实体已识别，查询会明确落入 standard_lib_gap。
_RULES = [
    ("US", "body", "肝胆胰", "肝胆脾胰", -100),
    ("US", "body", "胃幽门部;胃部", "胃", -99),
    ("US", "body", "双胎输血综合征;双胎隔膜与胎盘", "双胎及胎盘", -98),
    # 不新增“脐动脉/胎盘/大脑中动脉”优先规则：这些词常作为现有“胎儿”
    # 标准项的子维度，提前截获会让原本有效的胎儿检查退化为缺库。
    ("US", "body", "静脉导管", "胎儿静脉导管", -95),
    ("US", "body", "腹直肌", "腹直肌", -93),
    ("US", "body", "指(趾)甲;指甲;趾甲", "指(趾)甲", -92),
    ("US", "body", "眼前节超声生物显微镜;UBM", "眼前节", -91),
    ("US", "body", "全脊柱", "全脊柱", -90),
    ("SPECT", "body", "膀胱", "膀胱", -100),
    ("SPECT", "body", "颅底", "颅底", -99),
    ("SPECT", "body", "颈胸部;颈部及上纵隔;颈部及纵隔", "颈部及纵隔", -98),
    ("SPECT", "body", "全身显像;全身放射性同位素示踪法;131I-WBS", "全身", -97),
    ("DSA", "unmatchable", "机械性血栓切除", None, -100),
]


def _quote(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def upgrade() -> None:
    op.execute(
        "DELETE FROM keyword_match_rules WHERE remark = " + _quote(_REMARK)
    )
    values = []
    for modality, rule_type, keywords, dst_value, priority in _RULES:
        values.append(
            "(" + ", ".join([
                _quote(modality), _quote(rule_type), _quote(keywords),
                _quote(dst_value), str(priority), "0", _quote(_REMARK),
            ]) + ")"
        )
    op.execute(
        "INSERT INTO keyword_match_rules "
        "(modality, rule_type, keywords, dst_value, priority, enable, remark) VALUES "
        + ", ".join(values)
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM keyword_match_rules WHERE remark = " + _quote(_REMARK)
    )

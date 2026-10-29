"""US neck vessel generic body rules.

Revision ID: 20261028_1200
Revises: 20260911_0300
Create Date: 2026-10-28 12:00:00

问题（t385，ACR 4555 实测）：US 标准库中"颈部"区域只有
``US颈部(包块)`` 一条标准项，泛称"颈部血管/颈部动脉/颈部多普勒"的医嘱
先命中 ``颈部`` 区域规则（priority 28），再被 ``match()`` 的血管安全过滤器
（``血管|动脉|静脉|多普勒`` 且非包块/肿块 → 剔除包块类候选）剥空，
退化为 ``standard_semantic_conflict``。ACR 4555 中有 4 条此类项目：
``US颈部血管多普勒超声检查``、``US颈部(彩色多普勒超声检查)``（各 2 条语义重复）。

业务决策（2026-10-28，人工确认）：泛指颈部血管检查按既有词表惯例
映射到 ``双侧颈动脉``（与 "颈动脉"→双侧颈动脉、"颈动静脉"→双侧颈动脉
一致）；显式"颈部静脉"映射 ``双侧颈静脉``。

保留人工复核路径的项目（前缀 ``^(?!.*…)`` 排除）：
- ``包块/肿块``：非血管检查，仍归"颈部"区域；
- ``淋巴结``：淋巴结规则（priority 12）优先级更高，不能被血管规则抢注；
- ``上肢/下肢/上腔静脉/锁骨下/头臂``：颈部与其他血管的联合检查不整体改判
  （如 ``US颈部及上腔静脉多普勒超声检查``、``超声多普勒（上肢及颈部静脉）``）；
- ``瘤``：``颈部血管瘤`` / ``颈部动脉瘤`` 不是血管通畅性检查。

规则用负数优先级排在 ``颈部``(28) 之前（该段既有 -100…-87 用于必须最先
生效的特例）。本库约定 ``enable=0`` 表示启用。

配套代码改动：``us_spect_pet_matcher._extract_us_body`` 新增 ``regex_text``
参数，让含 ".*" 的规则针对原始医嘱求值——标准化会剥离
"彩色多普勒/超声检查"等后缀，否则 ``US颈部(彩色多普勒超声检查)``
只能剩下"颈部"。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261028_1200"
down_revision: Union[str, None] = "20260911_0300"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_EXCLUDE = "^(?!.*(?:上肢|下肢|上腔静脉|锁骨下|头臂|包块|肿块|淋巴结|瘤))"

NEW_RULES = [
    (-84, _EXCLUDE + ".*颈部静脉.*", "双侧颈静脉"),
    (-83, _EXCLUDE + ".*颈部(?:血管|动脉|动静脉)", "双侧颈动脉"),
    (-82, _EXCLUDE + ".*颈部.*多普勒", "双侧颈动脉"),
]


def upgrade() -> None:
    conn = op.get_bind()
    for priority, keywords, dst in NEW_RULES:
        exists = conn.execute(sa.text(
            "SELECT 1 FROM keyword_match_rules WHERE modality='US' AND rule_type='body' "
            "AND keywords=:k"
        ), {"k": keywords}).first()
        if exists is None:
            conn.execute(sa.text(
                "INSERT INTO keyword_match_rules "
                "(modality, rule_type, keywords, dst_value, priority, enable) "
                "VALUES ('US','body',:k,:d,:p,0)"
            ), {"k": keywords, "d": dst, "p": priority})


def downgrade() -> None:
    conn = op.get_bind()
    for _, keywords, _ in NEW_RULES:
        conn.execute(sa.text(
            "DELETE FROM keyword_match_rules WHERE modality='US' AND rule_type='body' "
            "AND keywords=:k"
        ), {"k": keywords})

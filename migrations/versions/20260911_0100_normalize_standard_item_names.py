"""Normalize standard item names by removing the ``*`` display prefix.

Revision ID: 20260911_0100
Revises: 20260820_2300
Create Date: 2026-09-11 01:00:00

理由（见 analysis/20260911/REPORT.md 缺陷②）：
``standard_check_items.item_name`` 的 ``*`` 前缀历史上被当作「权威/当前版本」
标记使用，但实际数据里它并不稳定：
  - 全部历史版本（V3.0/V3.5/V3.6/V3.7/V3.8/V2.0 等 3688 行）都带 ``* ``
  - 当前版本 v3.8.2 内部存在三种写法：``* ``(1472)、``*``(无空格, 443 US)、无 ``*``(30)
  - 引擎侧 ``data_loader`` 用 ``item_name LIKE '* %'`` 当权威过滤器，
    结果把 443 条 US 与 30 条 DSA/OCT/SPECT 排除在匹配之外

因此 ``*`` 不带可靠语义，且直接导致标准项不可达。本迁移统一去除 ``*`` 前缀，
版本身份完全交由 ``version`` 字段表达（当前匹配版本 = ``v3.8.2``）。

同时同步 ``technical_detail_candidates.target_item_name``，
避免技术详情侧继续引用带 ``*`` 的名称。
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260911_0100"
down_revision: Union[str, None] = "20260820_2300"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ``^*`` 后允许 0 个或多个空白，覆盖 "*名称" 与 "* 名称" 两种写法。
    op.execute(r"""
        UPDATE standard_check_items
        SET item_name = regexp_replace(item_name, '^\*\s*', '')
        WHERE item_name LIKE '*%'
    """)
    op.execute(r"""
        UPDATE technical_detail_candidates
        SET target_item_name = regexp_replace(target_item_name, '^\*\s*', '')
        WHERE target_item_name LIKE '*%'
    """)


def downgrade() -> None:
    # ``*`` 前缀不承载语义，去前缀不可逆；此处不做恢复，仅记录。
    # 如需回滚，应从迁移前备份恢复 item_name 列。
    pass

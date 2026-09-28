"""Add CT CTA combination standards approved for the ACR 4555 cohort.

Revision ID: 20260911_0300
Revises: 20260911_0200
Create Date: 2026-09-11 03:00:00

业务决策（2026-09-11，人工逐条确认）：
``CT小肠血管成像(CTA)`` 与 ``CT脊髓动脉血管成像(CTA)`` 在 v3.8.2 中
只有平扫/增强等常规组合，缺 CTA 组合项；而 ``v4.0.0`` 里的
``CT颈/胸/腰段脊髓动脉(血管成像CTA)`` 按决策①不参与匹配。
因此按 v3.8.2 CTA 系列（``动脉血管成像(CTA)``，scan_method_code=33）
补齐组合项。

命名与编码严格沿用同系列既有项（参照 ``20080707330000
CT肠系膜上动脉血管成像(CTA)``）：
    item_code = '20' + body_part_l2_code(4) + l3_code(末2位) + scan_code(2) + '0000'

技术详情字段（scan_scope/临床意义/解剖结构等）**不在此写入**，
按项目约定交由技术详情 Agent 通过 ``technical_detail_candidates`` 构建，
避免绕过候选审核流程。

review_status 保持 ``pending_review`` / supplement_status 保持 ``proposed``，
与 source='acr_4555_optimization_phase2' 的既有补齐项一致，
等待技术详情补齐后再发布。
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260911_0300"
down_revision: Union[str, None] = "20260911_0200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SOURCE = "acr_4555_optimization_phase3"

NEW_ITEMS = [
    {
        "item_code": "20080708330000",
        "item_name": "CT小肠血管成像(CTA)",
        "modality": "CT", "modality_code": "20",
        "body_part_l1": "血管", "body_part_l1_code": "08",
        "body_part_l2": "腹部血管", "body_part_l2_code": "0807",
        "body_part_l3": "小肠血管", "body_part_l3_code": "080708",
        "scan_method": "动脉血管成像(CTA)", "scan_method_code": "33",
    },
    {
        "item_code": "20081000330000",
        "item_name": "CT脊髓动脉血管成像(CTA)",
        "modality": "CT", "modality_code": "20",
        "body_part_l1": "血管", "body_part_l1_code": "08",
        "body_part_l2": "脊髓血管", "body_part_l2_code": "0810",
        "body_part_l3": "脊髓动脉", "body_part_l3_code": "081000",
        "scan_method": "动脉血管成像(CTA)", "scan_method_code": "33",
    },
]


def upgrade() -> None:
    for item in NEW_ITEMS:
        op.execute(f"""
            INSERT INTO standard_check_items (
                item_code, item_name, modality, modality_code,
                body_part_l1, body_part_l1_code,
                body_part_l2, body_part_l2_code,
                body_part_l3, body_part_l3_code,
                scan_method, scan_method_code,
                post_processing, post_processing_code,
                source, version, coverage_status,
                review_status, supplement_status, is_active
            ) SELECT
                '{item["item_code"]}', '{item["item_name"]}',
                '{item["modality"]}', '{item["modality_code"]}',
                '{item["body_part_l1"]}', '{item["body_part_l1_code"]}',
                '{item["body_part_l2"]}', '{item["body_part_l2_code"]}',
                '{item["body_part_l3"]}', '{item["body_part_l3_code"]}',
                '{item["scan_method"]}', '{item["scan_method_code"]}',
                '-', '00',
                '{SOURCE}', 'v3.8.2', 'gap_fill',
                'pending_review', 'proposed', true
            WHERE NOT EXISTS (
                SELECT 1 FROM standard_check_items
                WHERE item_code = '{item["item_code"]}'
            )
        """)


def downgrade() -> None:
    codes = ", ".join(f"'{i['item_code']}'" for i in NEW_ITEMS)
    op.execute(f"""
        DELETE FROM standard_check_items
        WHERE item_code IN ({codes}) AND source = '{SOURCE}'
    """)

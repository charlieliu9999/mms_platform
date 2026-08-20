"""algorithm_matching_improvements

Revision ID: 20260820_2000
Revises: 20260808_1900
Create Date: 2026-08-20 20:00:00

血管组合匹配 + DR 无体位 + 序列归一化配套的词表改动：
1. nlp_medical_dict: 能谱扫描 post→scan（标准库 scan_method=能量扫描）
2. nlp_medical_dict: 新增 骨密度测定（scan 类型，支撑 DR骨密度测定 匹配）
3. nlp_phrase_map: 能谱扫描 → 能量扫描（normalize 步）
4. nlp_phrase_map: 删除 CT 语境 乳腺→胸部 的错误映射（CT乳腺≠CT胸部）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260820_2000'
down_revision: Union[str, None] = '20260808_1900'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text(
        "UPDATE nlp_medical_dict SET type='scan' "
        "WHERE word='能谱扫描' AND enable=0"
    ))

    exists = conn.execute(sa.text(
        "SELECT 1 FROM nlp_medical_dict WHERE word='骨密度测定'"
    )).first()
    if exists is None:
        conn.execute(sa.text(
            "INSERT INTO nlp_medical_dict (word, type, enable) "
            "VALUES ('骨密度测定','scan',0)"
        ))
    else:
        conn.execute(sa.text(
            "UPDATE nlp_medical_dict SET type='scan', enable=0 "
            "WHERE word='骨密度测定'"
        ))

    conn.execute(sa.text(
        "UPDATE nlp_phrase_map SET dst_word='能量扫描' "
        "WHERE src_word='能谱扫描' AND step='normalize' AND enable=0"
    ))

    conn.execute(sa.text(
        "DELETE FROM nlp_phrase_map "
        "WHERE modality='CT' AND enable=0 AND step='normalize' "
        "AND src_word IN ('乳腺','单侧乳腺','双侧乳腺') AND dst_word='胸部'"
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "UPDATE nlp_medical_dict SET type='post' "
        "WHERE word='能谱扫描' AND enable=0"
    ))
    conn.execute(sa.text(
        "DELETE FROM nlp_medical_dict WHERE word='骨密度测定'"
    ))
    conn.execute(sa.text(
        "UPDATE nlp_phrase_map SET dst_word='能谱扫描' "
        "WHERE src_word='能谱扫描' AND step='normalize' AND enable=0"
    ))
    conn.execute(sa.text(
        "INSERT INTO nlp_phrase_map "
        "(modality, src_word, dst_word, step, version, enable) "
        "VALUES ('CT','乳腺','胸部','normalize','V3.8.2',0), "
        "('CT','单侧乳腺','胸部','normalize','V3.8.2',0), "
        "('CT','双侧乳腺','胸部','normalize','V3.8.2',0)"
    ))

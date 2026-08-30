"""Restore governed exact-name standard targets required by the fixed cohort.

Revision ID: 20260820_2300
Revises: 20260820_2200
Create Date: 2026-08-31 00:20:00

- Recover the historical SPECT duplicate code that was absent from the live
  partially migrated database, so exact-name collisions remain explicit.
- Add three CBBCT breast targets present in the frozen ACR 4555 authority set.
  They replace the old clinically incorrect fallback to CT chest standards.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260820_2300"
down_revision: Union[str, None] = "20260820_2200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE standard_check_items
        SET version = 'v3.8.2'
        WHERE item_code IN ('20041400010000', '20041400020000', '20041400030000')
          AND version = 'V3.0'
          AND source = 'migrated_from_nlp_checkitem_standard'
    """)
    op.execute("""
        INSERT INTO standard_check_items (
            item_code, item_name, modality, modality_code,
            body_part_l1, body_part_l3, scan_method,
            source, version, coverage_status, supplement_status,
            review_status, is_active
        ) VALUES
            (
                '50100000110000', 'SPECT放射性核素大动脉显像',
                'SPECT', '5', NULL, NULL, '平扫',
                'historical_b08_recovery', 'V3.8.2', 'migrated', 'migrated',
                'historical_verified', true
            ),
            (
                '120990000110000', 'MR眼前节光学相干断层扫描(AS-OCT)',
                'OCT', '12', NULL, NULL, '平扫',
                'historical_b08_recovery', 'V3.8.2', 'migrated', 'migrated',
                'historical_verified', true
            ),
            (
                'ACR-PR1183', '* CT乳腺锥形束CT(平扫)',
                'CT', 'CBBCT', '乳腺', '乳腺', '平扫',
                'acr_4555_manifest', 'v3.8.2', 'cohort_gap_fill', 'candidate',
                'dataset_verified', true
            ),
            (
                'ACR-PR1184', '* CT乳腺锥形束CT(增强)',
                'CT', 'CBBCT', '乳腺', '乳腺', '增强',
                'acr_4555_manifest', 'v3.8.2', 'cohort_gap_fill', 'candidate',
                'dataset_verified', true
            ),
            (
                'ACR-PR1182', '* CT乳腺锥形束CT(平扫+增强)',
                'CT', 'CBBCT', '乳腺', '乳腺', '平扫+增强',
                'acr_4555_manifest', 'v3.8.2', 'cohort_gap_fill', 'candidate',
                'dataset_verified', true
            )
        ON CONFLICT (item_code) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM standard_check_items
        WHERE (item_code IN ('50100000110000', '120990000110000')
               AND source = 'historical_b08_recovery')
           OR (item_code IN ('ACR-PR1182', 'ACR-PR1183', 'ACR-PR1184')
               AND source = 'acr_4555_manifest')
    """)
    op.execute("""
        UPDATE standard_check_items
        SET version = 'V3.0'
        WHERE item_code IN ('20041400010000', '20041400020000', '20041400030000')
          AND version = 'v3.8.2'
          AND source = 'migrated_from_nlp_checkitem_standard'
    """)

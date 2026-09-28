"""Unify standard tables: migrate nlp_checkitem_standard to standard_check_items

Revision ID: 20260804_1200
Revises: 20260804_0200
Create Date: 2026-08-04 12:00:00

B-08 修复：标准库双真相源统一
- 将 nlp_checkitem_standard 独有的67个编码迁移到 standard_check_items
- 保留旧表作为归档（重命名为 _deprecated）
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260804_1200'
down_revision = '20260804_0200'
branch_labels = None
depends_on = None


def upgrade():
    """
    迁移策略：
    1. 将旧表独有的67个编码补充到新表
    2. 字段映射：旧表37字段 → 新表26字段
    3. 模态标准化：NM→SPECT, PET→PET/CT
    4. 重复处理：每个编码只取最新版本（按 id DESC）
    """

    # Step 1: 迁移旧表独有的编码（处理重复：每个编码只取最新的一条）
    op.execute("""
        WITH ranked_items AS (
            SELECT
                old.*,
                ROW_NUMBER() OVER (
                    PARTITION BY old.checkitem_code
                    ORDER BY old.id DESC  -- 取最新的记录
                ) as rn
            FROM nlp_checkitem_standard old
            WHERE old.is_deleted = 0
              AND old.checkitem_code IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM standard_check_items new
                  WHERE new.item_code = old.checkitem_code
              )
        )
        INSERT INTO standard_check_items (
            item_code,
            item_name,
            modality,
            modality_code,
            body_part_l1,
            body_part_l1_code,
            body_part_l2,
            body_part_l2_code,
            body_part_l3,
            body_part_l3_code,
            scan_method,
            scan_method_code,
            post_processing,
            post_processing_code,
            source,
            version,
            coverage_status,
            supplement_status,
            is_active
        )
        SELECT
            checkitem_code,
            checkitem_name,
            -- 模态标准化
            CASE
                WHEN modality_name = 'NM' THEN 'SPECT'
                WHEN modality_name = 'PET' THEN 'PET/CT'
                ELSE modality_name
            END,
            modality_code,
            three_level_name,
            three_level_code,
            position_name,
            position_code,
            scope_name,
            NULL,  -- body_part_l3_code (旧表无对应)
            scan_name,
            scan_code,
            post_processing_name,
            post_processing_code,
            'migrated_from_nlp_checkitem_standard',
            version,
            'migrated',
            'migrated',
            true
        FROM ranked_items
        WHERE rn = 1  -- 只取每个编码的第一条（最新）
    """)

    # Step 2: 记录迁移统计
    op.execute("""
        DO $$
        DECLARE
            migrated_count INT;
            duplicate_count INT;
        BEGIN
            SELECT COUNT(*) INTO migrated_count
            FROM standard_check_items
            WHERE source = 'migrated_from_nlp_checkitem_standard';

            SELECT COUNT(*) INTO duplicate_count
            FROM (
                SELECT checkitem_code
                FROM nlp_checkitem_standard
                WHERE is_deleted = 0
                  AND checkitem_code IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM standard_check_items
                      WHERE item_code = checkitem_code
                        AND source != 'migrated_from_nlp_checkitem_standard'
                  )
                GROUP BY checkitem_code
                HAVING COUNT(*) > 1
            ) dups;

            RAISE NOTICE '✅ 迁移 % 个唯一编码 (旧表中有 % 个编码存在重复)',
                migrated_count, duplicate_count;
        END $$;
    """)

    # Step 3: 归档旧表（重命名，不删除）
    op.rename_table('nlp_checkitem_standard', 'nlp_checkitem_standard_deprecated')

    # Step 4: 添加注释标记
    op.execute("""
        COMMENT ON TABLE nlp_checkitem_standard_deprecated IS
        '已废弃：2026-08-04 统一到 standard_check_items，保留作为历史归档。注意：此表存在大量重复编码（最多481次），迁移时已去重。'
    """)

    print("✅ B-08 修复完成：标准库已统一到 standard_check_items")


def downgrade():
    """回滚：恢复旧表，删除迁移数据"""

    # Step 1: 恢复旧表名称
    op.rename_table('nlp_checkitem_standard_deprecated', 'nlp_checkitem_standard')

    # Step 2: 删除迁移的数据
    op.execute("""
        DELETE FROM standard_check_items
        WHERE source = 'migrated_from_nlp_checkitem_standard'
    """)

    print("⏮️ B-08 修复已回滚")

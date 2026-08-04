"""Retag non-ACR modality standard items to V3.8.2

Revision ID: 20260804_1300
Revises: 20260804_1200
Create Date: 2026-08-04 13:00:00

修复"标准表 SPECT 等非 ACR 模态在最新版本 V3.8.2 下标准项为 0"的问题：
- standard_check_items 以 item_code 为全局唯一键，version 仅为导入批次标签
- US/SPECT/PET/CT/PET/MR/OCT/ES 等非 ACR 模态不在 ACR V3.8.2 标准库中，
  数据分散在 V1.0-imported / V1.1 / V2.0 等旧版本标签下
- 将这些模态的行统一标记为 V3.8.2，使 V3.8.2 成为完整的当前标准库视图
- 匹配引擎（关键词引擎）按 modality + is_active 加载、不按 version 过滤，
  NLP 引擎仅对 CT/MR/DR/RF/MG 使用版本回退，故匹配行为不受影响
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '20260804_1300'
down_revision = '20260804_1200'
branch_labels = None
depends_on = None

NON_ACR_MODALITIES = "('US','SPECT','PET/CT','PET/MR','OCT','ES')"
BACKUP_TABLE = 'standard_items_version_backup_20260804'


def upgrade():
    """统一非 ACR 模态版本标签到 V3.8.2（先备份原标签以支持回滚）"""

    # Step 1: 备份受影响行的原始版本标签
    op.execute(f"""
        CREATE TABLE {BACKUP_TABLE} AS
        SELECT item_code, version AS old_version
        FROM standard_check_items
        WHERE modality IN {NON_ACR_MODALITIES}
          AND version IS DISTINCT FROM 'V3.8.2'
    """)

    # Step 2: 统一版本标签
    op.execute(f"""
        UPDATE standard_check_items
        SET version = 'V3.8.2'
        WHERE modality IN {NON_ACR_MODALITIES}
          AND version IS DISTINCT FROM 'V3.8.2'
    """)

    # Step 3: 输出迁移统计
    op.execute(f"""
        DO $$
        DECLARE n INT;
        BEGIN
            SELECT COUNT(*) INTO n FROM {BACKUP_TABLE};
            RAISE NOTICE '✅ 已将 % 条非 ACR 模态标准项的版本标签统一到 V3.8.2', n;
        END $$;
    """)


def downgrade():
    """回滚：从备份表恢复原始版本标签"""
    op.execute(f"""
        UPDATE standard_check_items s
        SET version = b.old_version
        FROM {BACKUP_TABLE} b
        WHERE s.item_code = b.item_code
    """)
    op.execute(f"DROP TABLE IF EXISTS {BACKUP_TABLE}")

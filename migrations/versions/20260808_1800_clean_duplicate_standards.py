"""Clean duplicate and incorrect standard codes

Revision ID: 20260808_1800
Revises: 20260808_1700
Create Date: 2026-08-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260808_1800'
down_revision = '20260808_1700'
branch_labels = None
depends_on = None


def upgrade():
    """
    清理标准库污染数据和模态错误：
    1. 停用自定义重复编码 CT_0551, CT_0554（与ACR标准冲突）
    2. 修正 30990001110000 模态错误（CT → MR）
    """
    conn = op.get_bind()
    
    # 1. 停用自定义污染编码
    result = conn.execute(sa.text("""
        UPDATE standard_check_items
        SET is_active = false, updated_at = NOW()
        WHERE item_code IN ('CT_0551', 'CT_0554')
          AND is_active = true
    """))
    print(f"✓ 已停用 {result.rowcount} 条自定义重复编码")
    
    # 2. 修正模态错误（30开头应为MR，不是CT）
    result = conn.execute(sa.text("""
        UPDATE standard_check_items
        SET modality = 'MR', updated_at = NOW()
        WHERE item_code = '30990001110000'
          AND modality = 'CT'
    """))
    print(f"✓ 已修正 {result.rowcount} 条模态错误（30990001110000: CT → MR）")


def downgrade():
    """恢复被停用的编码和模态"""
    conn = op.get_bind()
    
    # 恢复自定义编码
    conn.execute(sa.text("""
        UPDATE standard_check_items
        SET is_active = true, updated_at = NOW()
        WHERE item_code IN ('CT_0551', 'CT_0554')
    """))
    
    # 恢复模态错误
    conn.execute(sa.text("""
        UPDATE standard_check_items
        SET modality = 'CT', updated_at = NOW()
        WHERE item_code = '30990001110000'
          AND modality = 'MR'
    """))

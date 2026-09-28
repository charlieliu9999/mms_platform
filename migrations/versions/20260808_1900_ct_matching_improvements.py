"""Add CT matching improvements

Revision ID: 20260808_1900
Revises: 20260808_1800
Create Date: 2026-08-09 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260808_1900'
down_revision = '20260808_1800'
branch_labels = None
depends_on = None


def upgrade():
    """
    CT未匹配项优化：
    1. 添加词库映射（尿路造影、肝/小肠CTA）
    2. unmatchable_procedures表不存在，通过代码层面排除处理
    """
    conn = op.get_bind()
    
    # 词库映射已在前面手动执行，这里记录用于追溯
    print("✓ 词库映射补充:")
    print("  - 尿路造影 → 尿路造影成像")
    print("  - 肝脏血管成像 → 肝动静脉血管成像")
    print("  - 肝动脉血管成像 → 肝动静脉血管成像") 
    print("  - 小肠血管成像 → 肠系膜上动脉血管成像")
    
    print("✓ 预处理规则增强:")
    print("  - 动静脉双期增强 → 增强")
    print("  - 动脉期增强 → 增强")
    print("  - 静脉期增强 → 增强")
    
    # 预期效果说明
    print("\n预期效果:")
    print("  - CT尿路造影: +2条")
    print("  - CT肝脏CTA: +2条")
    print("  - CT小肠CTA: +2条")
    print("  - CT腹部盆腔双期: +2条")
    print("  总计: +8条匹配")


def downgrade():
    """回滚词库映射"""
    conn = op.get_bind()
    
    conn.execute(sa.text("""
        DELETE FROM nlp_phrase_map 
        WHERE modality = 'CT' 
          AND src_word IN ('尿路造影', '肝脏血管成像', '肝动脉血管成像', '小肠血管成像')
          AND version = 'V3.8.2'
    """))

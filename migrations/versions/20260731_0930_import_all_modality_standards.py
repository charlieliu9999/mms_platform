"""import_all_modality_standards

Revision ID: 20260731_0930
Revises: 3d97fd5e6377
Create Date: 2026-07-31 09:30:00.000000

从原系统导入完整的标准项目数据（包含US、PET、SPECT等所有模态）
数据来源：acrac_web_mgmt/scratch/phase0-lexicon-baseline/local/local_standard_check_items.csv
"""
from typing import Sequence, Union
from pathlib import Path
import csv

from alembic import op
import sqlalchemy as sa


revision: str = '20260731_0930'
down_revision: Union[str, None] = '33a6ffc77484'  # 最新的评测系统迁移
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 模态代码映射（根据原系统的映射规则）
MODALITY_CODE_MAP = {
    'CT': 2,
    'MR': 3,
    'DR': 4,  # X线的数字代码
    'DSA': 9,
    'US': 1,
    'PET/CT': 10,
    'PET/MR': 11,
    'SPECT': 12,
    'RF': 13,
    'MG': 14,
    'OCT': 15,
}


def upgrade() -> None:
    conn = op.get_bind()

    # 数据文件路径
    source_file = Path("/Users/charlieliu/git_project_vscode/09_medical/acrac_web_mgmt/scratch/phase0-lexicon-baseline/local/local_standard_check_items.csv")

    if not source_file.exists():
        print(f"❌ 数据文件不存在: {source_file}")
        return

    print(f"📁 读取数据文件: {source_file}")

    with open(source_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = []

        for row in reader:
            modality_name = row['modality']
            modality_code = MODALITY_CODE_MAP.get(modality_name, 99)

            # 处理版本号
            version = row.get('version', 'V3.8.2')

            # 处理scope_name（来源）
            scope_name = row.get('source', '基础版本')

            rows.append({
                'modality_code': str(modality_code),  # 转换为字符串
                'modality_name': modality_name,
                'one_level_name': row.get('body_part_l1', ''),
                'two_level_name': row.get('body_part_l2', ''),
                'three_level_name': row.get('body_part_l3', ''),
                'scan_name': row.get('scan_method', ''),
                'post_processing_name': row.get('post_processing', '-') if row.get('post_processing') != '-' else None,
                'checkitem_code': row.get('item_code', ''),
                'checkitem_name': row.get('item_name', ''),
                'version': version,
                'scope_name': scope_name,
                'is_deleted': 0 if row.get('is_active') == 't' else 1,
            })

    if not rows:
        print("⚠️  没有读取到数据")
        return

    # 统计各模态数量
    modality_stats = {}
    for row in rows:
        modality = row['modality_name']
        modality_stats[modality] = modality_stats.get(modality, 0) + 1

    print(f"\n📊 准备导入 {len(rows)} 条标准项目记录")
    print("\n按模态分布:")
    for modality, count in sorted(modality_stats.items(), key=lambda x: -x[1]):
        print(f"   {modality}: {count} 条")

    # 先删除现有数据
    print("\n🗑️  清空现有标准项目数据...")
    conn.execute(sa.text("TRUNCATE TABLE nlp_checkitem_standard RESTART IDENTITY CASCADE"))

    # 批量插入
    print("📥 开始批量导入...")
    conn.execute(sa.text("""
        INSERT INTO nlp_checkitem_standard (
            modality_code, modality_name,
            one_level_name, two_level_name, three_level_name,
            scan_name, post_processing_name,
            checkitem_code, checkitem_name,
            version, scope_name, is_deleted
        ) VALUES (
            :modality_code, :modality_name,
            :one_level_name, :two_level_name, :three_level_name,
            :scan_name, :post_processing_name,
            :checkitem_code, :checkitem_name,
            :version, :scope_name, :is_deleted
        )
    """), rows)

    print(f"\n✅ 成功导入 {len(rows)} 条标准项目记录")
    print("✅ 包含模态: CT, MR, US, DR, DSA, PET/CT, PET/MR, SPECT, RF, MG, OCT")


def downgrade() -> None:
    conn = op.get_bind()

    # 回滚：删除新导入的数据，恢复到只有CT/MR/X线/DSA的状态
    print("🔄 回滚：删除US、PET、SPECT等模态的标准项目数据")
    conn.execute(sa.text("""
        DELETE FROM nlp_checkitem_standard
        WHERE modality_name NOT IN ('CT', 'MR', 'X线', 'DSA')
    """))
    print("✅ 回滚完成")

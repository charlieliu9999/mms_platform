#!/usr/bin/env python3
"""
清理旧版本数据 - 每个模态只保留最新版本
策略：
- CT/MR/DR/RF/DSA: 保留 V3.8.2
- US/MG/NM/PET/OCT/ES: 保留 V1.0-imported
- 删除所有其他版本
"""

import asyncio
import asyncpg

DATABASE_URL = "postgresql://postgres:password@127.0.0.1:15432/acrac_db"

# 每个模态保留的版本
KEEP_VERSIONS = {
    'CT': 'V3.8.2',
    'MR': 'V3.8.2',
    'DR': 'V3.8.2',
    'RF': 'V3.8.2',
    'DSA': 'V3.8.2',
    'US': 'V1.0-imported',
    'MG': 'V1.0-imported',
    'NM': 'V1.0-imported',
    'PET': 'V1.0-imported',
    'OCT': 'V1.0-imported',
    'ES': 'V1.0-imported',
}


async def main(dry_run=True):
    conn = await asyncpg.connect(DATABASE_URL)

    print("=" * 80)
    print("清理旧版本 - 每个模态只保留一个最新版本")
    print("=" * 80)
    print(f"模式: {'DRY RUN (预览)' if dry_run else '实际执行'}\n")

    # 统计需要删除的数据
    for modality, keep_version in sorted(KEEP_VERSIONS.items()):
        # 统计该模态的版本分布
        versions = await conn.fetch("""
            SELECT version, COUNT(*) as count
            FROM nlp_checkitem_standard
            WHERE modality_name = $1 AND is_deleted = 0
            GROUP BY version
            ORDER BY version DESC
        """, modality)

        if not versions:
            continue

        print(f"模态 {modality}:")
        print(f"  保留版本: {keep_version}")

        total_keep = 0
        total_delete = 0

        for row in versions:
            if row['version'] == keep_version:
                print(f"    ✅ 保留 {row['version']}: {row['count']} 条")
                total_keep += row['count']
            else:
                print(f"    ❌ 删除 {row['version']}: {row['count']} 条")
                total_delete += row['count']

        print(f"  小计: 保留 {total_keep} 条, 删除 {total_delete} 条\n")

    # 执行删除
    if not dry_run:
        print("\n" + "=" * 80)
        print("开始执行删除...")
        print("=" * 80)

        total_deleted = 0
        for modality, keep_version in KEEP_VERSIONS.items():
            result = await conn.execute("""
                UPDATE nlp_checkitem_standard
                SET is_deleted = 1, update_time = NOW()
                WHERE modality_name = $1
                  AND version != $2
                  AND is_deleted = 0
            """, modality, keep_version)

            affected = int(result.split()[-1]) if result else 0
            if affected > 0:
                print(f"  {modality}: 删除 {affected} 条旧版本")
            total_deleted += affected

        print(f"\n✅ 总计删除 {total_deleted} 条旧版本记录")

        # 验证结果
        final_count = await conn.fetchval("""
            SELECT COUNT(*) FROM nlp_checkitem_standard WHERE is_deleted = 0
        """)
        print(f"✅ 剩余激活数据: {final_count} 条")

    await conn.close()


if __name__ == "__main__":
    import sys

    dry_run = "--execute" not in sys.argv

    if dry_run:
        print("\n⚠️  预览模式")
        print("   实际执行: poetry run python scripts/cleanup_by_modality.py --execute\n")
    else:
        print("\n🚀 实际执行模式\n")

    asyncio.run(main(dry_run=dry_run))

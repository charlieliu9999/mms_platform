#!/usr/bin/env python3
"""
标准项目版本清理工具
- 分析各版本的数据分布
- 建议清理方案
- 为旧版本数据添加 is_deleted 标记
"""

import asyncio
import asyncpg

DATABASE_URL = "postgresql://postgres:password@127.0.0.1:15432/acrac_db"


async def analyze_versions():
    """分析版本数据分布"""
    conn = await asyncpg.connect(DATABASE_URL)

    print("=" * 80)
    print("版本数据分布分析")
    print("=" * 80)

    # 统计各版本数据量
    result = await conn.fetch("""
        SELECT
            version,
            COUNT(*) as total,
            COUNT(DISTINCT modality_name) as modality_count,
            MIN(create_time) as first_created,
            MAX(create_time) as last_created
        FROM nlp_checkitem_standard
        WHERE is_deleted = 0
        GROUP BY version
        ORDER BY
            CASE
                WHEN version LIKE 'V%' THEN 1
                ELSE 2
            END,
            version DESC
    """)

    print(f"\n{'版本':<20} {'数据量':<10} {'模态数':<10} {'创建时间范围':<40}")
    print("-" * 80)

    for row in result:
        first = row['first_created'].strftime('%Y-%m-%d') if row['first_created'] else 'N/A'
        last = row['last_created'].strftime('%Y-%m-%d') if row['last_created'] else 'N/A'
        print(f"{row['version']:<20} {row['total']:<10} {row['modality_count']:<10} {first} ~ {last}")

    # 统计重复的检查项目（同一个checkitem_code有多个版本）
    print("\n" + "=" * 80)
    print("重复项目分析（同一检查项目存在多个版本）")
    print("=" * 80)

    result = await conn.fetch("""
        SELECT
            checkitem_code,
            checkitem_name,
            COUNT(DISTINCT version) as version_count,
            STRING_AGG(DISTINCT version, ', ') as versions
        FROM nlp_checkitem_standard
        WHERE is_deleted = 0 AND checkitem_code IS NOT NULL
        GROUP BY checkitem_code, checkitem_name
        HAVING COUNT(DISTINCT version) > 1
        ORDER BY version_count DESC
        LIMIT 10
    """)

    if result:
        print(f"\n{'检查编码':<20} {'检查名称':<40} {'版本数':<10} {'版本列表':<30}")
        print("-" * 120)
        for row in result:
            name = row['checkitem_name'][:38] if row['checkitem_name'] else ''
            versions = row['versions'][:28] if row['versions'] else ''
            print(f"{row['checkitem_code']:<20} {name:<40} {row['version_count']:<10} {versions}")

        dup_count = await conn.fetchval("""
            SELECT COUNT(*)
            FROM (
                SELECT checkitem_code
                FROM nlp_checkitem_standard
                WHERE is_deleted = 0 AND checkitem_code IS NOT NULL
                GROUP BY checkitem_code
                HAVING COUNT(DISTINCT version) > 1
            ) sub
        """)
        print(f"\n总计有 {dup_count} 个检查项目存在多版本重复")
    else:
        print("\n无重复项目")

    # 统计每个模态的最新版本
    print("\n" + "=" * 80)
    print("各模态推荐保留的版本")
    print("=" * 80)

    result = await conn.fetch("""
        WITH version_priority AS (
            SELECT
                modality_name,
                version,
                COUNT(*) as count,
                ROW_NUMBER() OVER (
                    PARTITION BY modality_name
                    ORDER BY
                        CASE
                            WHEN version LIKE 'V%' THEN 1
                            ELSE 2
                        END,
                        version DESC
                ) as priority
            FROM nlp_checkitem_standard
            WHERE is_deleted = 0
            GROUP BY modality_name, version
        )
        SELECT
            modality_name,
            version,
            count,
            priority
        FROM version_priority
        WHERE priority <= 3
        ORDER BY modality_name, priority
    """)

    current_modality = None
    for row in result:
        if current_modality != row['modality_name']:
            current_modality = row['modality_name']
            print(f"\n模态: {current_modality}")

        status = "✅ 推荐保留" if row['priority'] == 1 else "⚠️ 可删除"
        print(f"  {status:<15} {row['version']:<20} ({row['count']:>5} 条)")

    await conn.close()


async def generate_cleanup_plan():
    """生成清理方案"""
    conn = await asyncpg.connect(DATABASE_URL)

    print("\n" + "=" * 80)
    print("清理方案（将旧版本标记为 is_deleted=1）")
    print("=" * 80)

    # 查找需要删除的记录（保留每个checkitem_code的最新版本）
    result = await conn.fetch("""
        WITH latest_versions AS (
            SELECT
                id,
                checkitem_code,
                version,
                ROW_NUMBER() OVER (
                    PARTITION BY checkitem_code
                    ORDER BY
                        CASE
                            WHEN version LIKE 'V%' THEN 1
                            ELSE 2
                        END,
                        version DESC
                ) as rn
            FROM nlp_checkitem_standard
            WHERE is_deleted = 0 AND checkitem_code IS NOT NULL
        )
        SELECT
            version,
            COUNT(*) as delete_count
        FROM latest_versions
        WHERE rn > 1
        GROUP BY version
        ORDER BY delete_count DESC
    """)

    total_delete = 0
    print("\n将要删除的版本数据：")
    print(f"{'版本':<20} {'删除数量':<15}")
    print("-" * 40)

    for row in result:
        print(f"{row['version']:<20} {row['delete_count']:<15}")
        total_delete += row['delete_count']

    print(f"\n总计删除: {total_delete} 条旧版本记录")

    # 统计保留的数据
    keep_count = await conn.fetchval("""
        WITH latest_versions AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY checkitem_code
                    ORDER BY
                        CASE
                            WHEN version LIKE 'V%' THEN 1
                            ELSE 2
                        END,
                        version DESC
                ) as rn
            FROM nlp_checkitem_standard
            WHERE is_deleted = 0 AND checkitem_code IS NOT NULL
        )
        SELECT COUNT(*) FROM latest_versions WHERE rn = 1
    """)

    print(f"保留最新版本: {keep_count} 条")

    await conn.close()

    return total_delete


async def execute_cleanup(dry_run: bool = True):
    """执行清理"""
    conn = await asyncpg.connect(DATABASE_URL)

    if dry_run:
        print("\n⚠️  DRY RUN 模式 - 不会实际修改数据")
    else:
        print("\n🚀 执行清理...")

    # 标记旧版本为 is_deleted=1
    sql = """
        WITH latest_versions AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY checkitem_code
                    ORDER BY
                        CASE
                            WHEN version LIKE 'V%' THEN 1
                            ELSE 2
                        END,
                        version DESC
                ) as rn
            FROM nlp_checkitem_standard
            WHERE is_deleted = 0 AND checkitem_code IS NOT NULL
        )
        UPDATE nlp_checkitem_standard
        SET is_deleted = 1, update_time = NOW()
        WHERE id IN (SELECT id FROM latest_versions WHERE rn > 1)
    """

    if not dry_run:
        result = await conn.execute(sql)
        affected = int(result.split()[-1]) if result else 0
        print(f"✅ 已标记 {affected} 条旧版本记录为已删除")
    else:
        # 预览将要删除的数据
        preview_sql = """
            WITH latest_versions AS (
                SELECT
                    id,
                    checkitem_code,
                    checkitem_name,
                    version,
                    ROW_NUMBER() OVER (
                        PARTITION BY checkitem_code
                        ORDER BY
                            CASE
                                WHEN version LIKE 'V%' THEN 1
                                ELSE 2
                            END,
                            version DESC
                    ) as rn
                FROM nlp_checkitem_standard
                WHERE is_deleted = 0 AND checkitem_code IS NOT NULL
            )
            SELECT checkitem_code, checkitem_name, version
            FROM latest_versions
            WHERE rn > 1
            LIMIT 10
        """
        preview = await conn.fetch(preview_sql)

        print("\n预览将要删除的数据（前10条）：")
        print(f"{'检查编码':<20} {'检查名称':<40} {'版本':<15}")
        print("-" * 80)

        for row in preview:
            name = row['checkitem_name'][:38] if row['checkitem_name'] else ''
            print(f"{row['checkitem_code']:<20} {name:<40} {row['version']:<15}")

    await conn.close()


async def main():
    import sys

    # 分析版本分布
    await analyze_versions()

    # 生成清理方案
    total_delete = await generate_cleanup_plan()

    # 执行清理
    if total_delete > 0:
        dry_run = "--execute" not in sys.argv

        if dry_run:
            print("\n" + "=" * 80)
            print("如需执行清理，请运行：")
            print("  poetry run python scripts/cleanup_old_versions.py --execute")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            confirm = input(f"确认删除 {total_delete} 条旧版本记录？(yes/no): ")
            if confirm.lower() == 'yes':
                await execute_cleanup(dry_run=False)
                print("\n✅ 清理完成")
            else:
                print("\n❌ 已取消")
    else:
        print("\n✅ 无需清理")


if __name__ == "__main__":
    asyncio.run(main())

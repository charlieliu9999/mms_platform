#!/usr/bin/env python3
"""统一标准版本命名格式"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

async def main():
    # 从环境变量获取数据库配置
    db_url = os.getenv('MATCH_SVC_DATABASE_URL', 'postgresql://postgres:password@127.0.0.1:15432/acrac_db')

    # 解析连接参数
    db_url_sync = db_url.replace('postgresql+asyncpg://', 'postgresql://')

    print("🔗 连接数据库...")
    conn = await asyncpg.connect(db_url_sync)

    try:
        # 查看当前版本分布
        print("\n📊 更新前的版本分布:")
        rows = await conn.fetch("SELECT version, COUNT(*) as count FROM standard_check_items GROUP BY version ORDER BY version")
        for row in rows:
            print(f"  {row['version']}: {row['count']} 条")

        # 统一版本命名
        print("\n🔄 开始统一版本命名...")

        updates = [
            ('V3.8.2', 'v3.8.2'),
            ('V2.0', 'v2.0'),
            ('V1.0-imported', 'v1.0-imported'),
        ]

        for old_ver, new_ver in updates:
            result = await conn.execute(
                "UPDATE standard_check_items SET version = $1 WHERE version = $2",
                new_ver, old_ver
            )
            affected = int(result.split()[-1])
            if affected > 0:
                print(f"  ✅ {old_ver} → {new_ver}: 更新了 {affected} 条")

        # 查看更新后的版本分布
        print("\n📊 更新后的版本分布:")
        rows = await conn.fetch("SELECT version, COUNT(*) as count FROM standard_check_items GROUP BY version ORDER BY version")
        for row in rows:
            print(f"  {row['version']}: {row['count']} 条")

        print("\n✅ 版本命名统一完成！")

    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())

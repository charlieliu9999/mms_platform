#!/usr/bin/env python3
"""对比 Excel 文件和数据库的 v4.0.0 数据"""
import pandas as pd
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    excel_path = "/Users/charlieliu/Desktop/01标准/09 医保版-标准/影像检查项目名称和编码V4.0.xlsx"

    print("📖 读取 Excel 文件...")
    try:
        # 读取 Excel，尝试不同的 sheet
        xl = pd.ExcelFile(excel_path)
        print(f"  可用的 sheets: {xl.sheet_names}")

        # 读取各个模态的 sheet
        sheets_to_read = ['CT项目', 'MR项目', 'DR项目', 'MG项目']
        all_data = []

        for sheet_name in sheets_to_read:
            if sheet_name in xl.sheet_names:
                df_sheet = pd.read_excel(excel_path, sheet_name=sheet_name)
                print(f"\n  读取 {sheet_name}: {len(df_sheet)} 行")
                print(f"    列: {list(df_sheet.columns)[:5]}")
                all_data.append(df_sheet)

        # 合并所有数据
        if all_data:
            df = pd.concat(all_data, ignore_index=True)
            print(f"\n  合并后总行数: {len(df)}")
        else:
            print("  ❌ 未找到数据 sheets")
            return

    except Exception as e:
        print(f"  ❌ 读取失败: {e}")
        return

    # 连接数据库
    db_url = os.getenv('MATCH_SVC_DATABASE_URL', 'postgresql://postgres:password@127.0.0.1:15432/acrac_db')
    db_url_sync = db_url.replace('postgresql+asyncpg://', 'postgresql://')

    print("\n🔗 连接数据库...")
    conn = await asyncpg.connect(db_url_sync)

    try:
        db_count = await conn.fetchval("SELECT COUNT(*) FROM standard_check_items WHERE version = 'v4.0.0'")
        print(f"  数据库记录数: {db_count}")

        # 按检查方式对比
        print("\n📊 按检查方式对比:")
        db_modalities = await conn.fetch("""
            SELECT modality, COUNT(*) as count
            FROM standard_check_items
            WHERE version = 'v4.0.0'
            GROUP BY modality
            ORDER BY modality
        """)

        print("  数据库:")
        for row in db_modalities:
            print(f"    {row['modality']}: {row['count']}")

        print("\n" + "="*60)
        print(f"Excel 总行数: {len(df)}")
        print(f"数据库总数: {db_count}")
        print(f"差异: {len(df) - db_count} 条")

        if len(df) > db_count:
            print(f"\n⚠️  数据库缺少 {len(df) - db_count} 条数据")
            print("建议：重新导入 v4.0.0 数据")

    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())

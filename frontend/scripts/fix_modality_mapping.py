#!/usr/bin/env python3
"""
修复标准项目模态映射问题
将数据库中的中文模态名称转换为国际标准代码
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from sqlalchemy import text
from match_service.db import get_session_factory


async def fix_modality_mapping():
    """修复模态映射"""
    factory = get_session_factory()

    async with factory() as session:
        print("=" * 60)
        print("MMS平台模态映射修复脚本")
        print("=" * 60)
        print()

        # 1. 查看当前模态分布
        print("[1/4] 查看当前模态分布...")
        result = await session.execute(text("""
            SELECT modality_name, COUNT(*) as count
            FROM nlp_checkitem_standard
            GROUP BY modality_name
            ORDER BY count DESC
        """))
        print("\n修复前的模态分布:")
        for row in result:
            print(f"  {row.modality_name}: {row.count}条")
        print()

        # 2. 执行修复
        print("[2/4] 执行模态映射修复...")
        update_sql = text("""
            UPDATE nlp_checkitem_standard
            SET modality_name = CASE
                -- X线分为DR和RF
                WHEN modality_name = 'X线' AND (
                    scan_name LIKE '%透视%' OR
                    scan_name LIKE '%造影%' OR
                    scan_name LIKE '%食管%' OR
                    scan_name LIKE '%胃肠%' OR
                    scan_name LIKE '%钡餐%'
                ) THEN 'RF'
                WHEN modality_name = 'X线' THEN 'DR'

                -- 超声类
                WHEN modality_name = '超声' OR modality_name = '彩超' THEN 'US'

                -- 乳腺X线
                WHEN modality_name = '乳腺X线摄影' OR modality_name = '乳腺X线' THEN 'MG'

                -- 核医学
                WHEN modality_name = 'SPECT' OR modality_name = '单光子' THEN 'SPECT'
                WHEN modality_name = 'PET' OR modality_name = '正电子' THEN 'PET/CT'

                -- 保持原有标准代码
                ELSE modality_name
            END
        """)

        result = await session.execute(update_sql)
        affected_rows = result.rowcount
        await session.commit()
        print(f"  ✓ 已更新 {affected_rows} 条记录")
        print()

        # 3. 验证修复结果
        print("[3/4] 验证修复结果...")
        result = await session.execute(text("""
            SELECT modality_name, COUNT(*) as count
            FROM nlp_checkitem_standard
            GROUP BY modality_name
            ORDER BY count DESC
        """))

        print("\n修复后的模态分布:")
        modality_map = {}
        for row in result:
            print(f"  {row.modality_name}: {row.count}条")
            modality_map[row.modality_name] = row.count
        print()

        # 4. 生成统计报告
        print("[4/4] 生成统计报告...")
        total = sum(modality_map.values())
        print(f"\n总计: {total} 条标准项目")
        print(f"覆盖模态: {len(modality_map)} 种")
        print()

        # 检查预期模态
        expected_modalities = ['CT', 'MR', 'US', 'DR', 'RF', 'MG', 'SPECT', 'DSA', 'OCT', 'PET/CT', 'PET/MR']
        missing = [m for m in expected_modalities if m not in modality_map]

        if missing:
            print(f"⚠️  以下模态在数据库中不存在: {', '.join(missing)}")
        else:
            print("✓ 所有预期模态都已覆盖")

        print()
        print("=" * 60)
        print("修复完成！")
        print("=" * 60)
        print()
        print("下一步:")
        print("  1. 重启后端服务以刷新缓存")
        print("  2. 刷新前端页面查看效果")
        print("  3. 测试模态筛选功能")
        print()


if __name__ == "__main__":
    asyncio.run(fix_modality_mapping())

#!/usr/bin/env python3
"""
分析未匹配项目的失败原因
运行：poetry run python scripts/analyze_unmatched_items.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from match_service.core.engine_holder import EngineHolder
from match_service.config import get_settings

async def analyze_unmatched():
    """分析未匹配项目并分类失败原因"""

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    # 初始化匹配引擎
    print("正在初始化匹配引擎...")
    engine_holder = EngineHolder()
    match_engine = engine_holder.get_engine()

    async with engine.connect() as conn:
        # 获取所有未匹配项目
        result = await conn.execute(text('''
            SELECT hci.id, hci.order_name, hci.modality_hint
            FROM hospital_check_items hci
            LEFT JOIN standard_hospital_mapping shm ON hci.id = shm.hospital_item_id
            WHERE hci.is_active = true
              AND hci.modality_hint IN ('CT', 'MR', 'DR', 'US')
              AND shm.id IS NULL
            ORDER BY hci.modality_hint, hci.id
        '''))

        unmatched_items = result.fetchall()
        print(f"\n找到 {len(unmatched_items)} 个未匹配项目\n")

        # 分类统计
        categories = {
            'A_设计不可匹配': [],  # 引导/穿刺/定位/消融
            'B_方括号修饰语': [],  # 面神经[颅外段]
            'C_扫描组合': [],      # 平扫+DWI/DCE
            'D_血管成像': [],      # MRA/CTA/MRV
            'E_新技术': [],        # 能谱/双能/4D
            'F_多项记录': [],      # 部分失配
            'G_特殊序列': [],      # Haste/STIR/MPR
            'H_标准库缺口': [],    # 部位+扫描无对应
            'Z_其他': [],
        }

        tier_stats = {'none': 0, 'ambiguous': 0, 'degraded': 0, 'exact': 0}

        for item_id, order_name, modality in unmatched_items:
            # 用匹配引擎重新匹配
            try:
                result = match_engine.match(order_name, modality, "V3.8.2")
                tier = result.get('tier', 'none')
                tier_stats[tier] = tier_stats.get(tier, 0) + 1

                # 根据内容和tier分类
                order_lower = order_name.lower()

                if any(x in order_lower for x in ['引导', '穿刺', '定位', '消融', '伽玛刀', '放疗']):
                    categories['A_设计不可匹配'].append((item_id, order_name, tier))
                elif '[' in order_name and ']' in order_name:
                    categories['B_方括号修饰语'].append((item_id, order_name, tier))
                elif '+' in order_name and any(x in order_name for x in ['DWI', 'DCE', 'MRS', 'PWI']):
                    categories['C_扫描组合'].append((item_id, order_name, tier))
                elif any(x in order_name for x in ['MRA', 'CTA', 'MRV', 'CTV', '血管']):
                    categories['D_血管成像'].append((item_id, order_name, tier))
                elif any(x in order_name for x in ['能谱', '双能', '4D', 'PET', '化学位移']):
                    categories['E_新技术'].append((item_id, order_name, tier))
                elif any(x in order_name for x in ['Haste', 'STIR', 'MPR', 'VR', '水成像']):
                    categories['G_特殊序列'].append((item_id, order_name, tier))
                elif tier == 'none' and not result.get('items'):
                    categories['H_标准库缺口'].append((item_id, order_name, tier))
                else:
                    categories['Z_其他'].append((item_id, order_name, tier))

            except Exception as e:
                print(f"  匹配失败 ID {item_id}: {e}")
                categories['Z_其他'].append((item_id, order_name, 'error'))

        # 输出统计
        print("\n=== Tier 分布 ===")
        for tier, count in sorted(tier_stats.items()):
            print(f"  {tier:12s}: {count:3d} ({count/len(unmatched_items)*100:5.1f}%)")

        print("\n=== 失败原因分类 ===")
        for category, items in sorted(categories.items()):
            if items:
                print(f"\n{category} ({len(items)}项):")
                for item_id, order_name, tier in items[:5]:  # 只显示前5个
                    print(f"  [{tier:8s}] ID {item_id:5d}: {order_name}")
                if len(items) > 5:
                    print(f"  ... 还有 {len(items)-5} 项")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(analyze_unmatched())

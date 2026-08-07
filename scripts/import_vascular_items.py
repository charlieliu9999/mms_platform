"""
P2任务：导入血管成像标准项到数据库

执行方式:
poetry run python scripts/import_vascular_items.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from sqlalchemy import text
from match_service.db import get_engine, get_session_factory


# 从 vascular_items_plan.py 导入数据
vascular_items_to_add = [
    # ========== MRA 平扫缺口 ==========
    {
        "modality": "MR",
        "name": "MR肺动脉血管成像(MRA平扫)",
        "body_part_l1": "胸部",
        "body_part_l2": "肺动脉",
        "scan_method": "MRA",
        "category": "血管成像",
        "note": "补充平扫MRA，现仅有CE-MRA"
    },
    {
        "modality": "MR",
        "name": "MR头颈部动脉血管成像(MRA平扫)",
        "body_part_l1": "头颈部",
        "body_part_l2": "头颈部动脉",
        "scan_method": "MRA",
        "category": "血管成像",
        "note": "补充平扫MRA，现仅有CE-MRA"
    },
    {
        "modality": "MR",
        "name": "MR上肢动脉血管成像(MRA平扫)",
        "body_part_l1": "四肢及关节",
        "body_part_l2": "上肢动脉",
        "scan_method": "MRA",
        "category": "血管成像",
        "note": "补充平扫MRA"
    },
    {
        "modality": "MR",
        "name": "MR下肢动脉血管成像(MRA平扫)",
        "body_part_l1": "四肢及关节",
        "body_part_l2": "下肢动脉",
        "scan_method": "MRA",
        "category": "血管成像",
        "note": "补充平扫MRA"
    },
    {
        "modality": "MR",
        "name": "MR主动脉血管成像(MRA平扫)",
        "body_part_l1": "胸部",
        "body_part_l2": "主动脉全长",
        "scan_method": "MRA",
        "category": "血管成像",
        "note": "补充平扫MRA"
    },
    # ========== MRV 静脉缺口 ==========
    {
        "modality": "MR",
        "name": "MR上肢静脉血管成像(MRV)",
        "body_part_l1": "四肢及关节",
        "body_part_l2": "上肢静脉",
        "scan_method": "MRV",
        "category": "血管成像",
        "note": "补充静脉MRV，现仅有动脉MRA"
    },
    {
        "modality": "MR",
        "name": "MR下肢静脉血管成像(MRV)",
        "body_part_l1": "四肢及关节",
        "body_part_l2": "下肢静脉",
        "scan_method": "MRV",
        "category": "血管成像",
        "note": "补充静脉MRV"
    },
    {
        "modality": "MR",
        "name": "MR颈部静脉血管成像(MRV)",
        "body_part_l1": "头颈部",
        "body_part_l2": "颈部静脉",
        "scan_method": "MRV",
        "category": "血管成像",
        "note": "补充静脉MRV"
    },
    {
        "modality": "MR",
        "name": "MR头颈部静脉血管成像(MRV)",
        "body_part_l1": "头颈部",
        "body_part_l2": "头颈部静脉",
        "scan_method": "MRV",
        "category": "血管成像",
        "note": "补充静脉MRV"
    },
    {
        "modality": "MR",
        "name": "MR肺静脉血管成像(MRV)",
        "body_part_l1": "胸部",
        "body_part_l2": "肺静脉",
        "scan_method": "MRV",
        "category": "血管成像",
        "note": "补充肺静脉MRV"
    },
    # ========== CTA 平扫/增强缺口 ==========
    {
        "modality": "CT",
        "name": "CT肺动脉血管成像(CTA平扫)",
        "body_part_l1": "胸部",
        "body_part_l2": "肺动脉",
        "scan_method": "CTA",
        "category": "血管成像",
        "note": "补充平扫CTA"
    },
    {
        "modality": "CT",
        "name": "CT上肢动脉血管成像(CTA)",
        "body_part_l1": "四肢及关节",
        "body_part_l2": "上肢动脉",
        "scan_method": "CTA",
        "category": "血管成像",
        "note": "补充上肢CTA"
    },
    {
        "modality": "CT",
        "name": "CT下肢动脉血管成像(CTA)",
        "body_part_l1": "四肢及关节",
        "body_part_l2": "下肢动脉",
        "scan_method": "CTA",
        "category": "血管成像",
        "note": "补充下肢CTA"
    },
    {
        "modality": "CT",
        "name": "CT主动脉血管成像(CTA)",
        "body_part_l1": "胸部",
        "body_part_l2": "主动脉全长",
        "scan_method": "CTA",
        "category": "血管成像",
        "note": "补充主动脉CTA"
    },
    {
        "modality": "CT",
        "name": "CT颅内血管成像(CTA)",
        "body_part_l1": "头颈部",
        "body_part_l2": "颅内血管",
        "scan_method": "CTA",
        "category": "血管成像",
        "note": "补充颅内CTA"
    },
    # ========== 特定部位血管成像 ==========
    {
        "modality": "MR",
        "name": "MR肾动脉血管成像(MRA)",
        "body_part_l1": "腹部",
        "body_part_l2": "肾动脉",
        "scan_method": "MRA",
        "category": "血管成像",
        "note": "补充肾动脉MRA"
    },
    {
        "modality": "MR",
        "name": "MR肾动脉血管成像(CE-MRA)",
        "body_part_l1": "腹部",
        "body_part_l2": "肾动脉",
        "scan_method": "CE-MRA",
        "category": "血管成像",
        "note": "补充肾动脉增强MRA"
    },
    {
        "modality": "CT",
        "name": "CT肾动脉血管成像(CTA)",
        "body_part_l1": "腹部",
        "body_part_l2": "肾动脉",
        "scan_method": "CTA",
        "category": "血管成像",
        "note": "补充肾动脉CTA"
    },
    {
        "modality": "MR",
        "name": "MR肝脏动脉血管成像(MRA)",
        "body_part_l1": "腹部",
        "body_part_l2": "肝脏动脉",
        "scan_method": "MRA",
        "category": "血管成像",
        "note": "补充肝脏动脉MRA"
    },
    {
        "modality": "MR",
        "name": "MR门静脉血管成像(MRV)",
        "body_part_l1": "腹部",
        "body_part_l2": "门静脉",
        "scan_method": "MRV",
        "category": "血管成像",
        "note": "补充门静脉MRV"
    },
    {
        "modality": "CT",
        "name": "CT门静脉血管成像(CTV)",
        "body_part_l1": "腹部",
        "body_part_l2": "门静脉",
        "scan_method": "CTV",
        "category": "血管成像",
        "note": "补充门静脉CTV"
    },
    # ========== 其他重要血管 ==========
    {
        "modality": "MR",
        "name": "MR椎-基底动脉血管成像(MRA)",
        "body_part_l1": "头颈部",
        "body_part_l2": "椎-基底动脉",
        "scan_method": "MRA",
        "category": "血管成像",
        "note": "补充椎基底动脉MRA"
    },
    {
        "modality": "MR",
        "name": "MR颈动脉血管成像(MRA)",
        "body_part_l1": "头颈部",
        "body_part_l2": "颈动脉",
        "scan_method": "MRA",
        "category": "血管成像",
        "note": "补充颈动脉MRA平扫"
    },
    {
        "modality": "CT",
        "name": "CT颈动脉血管成像(CTA)",
        "body_part_l1": "头颈部",
        "body_part_l2": "颈动脉",
        "scan_method": "CTA",
        "category": "血管成像",
        "note": "补充颈动脉CTA"
    },
    {
        "modality": "MR",
        "name": "MR腹部血管成像(MRA)",
        "body_part_l1": "腹部",
        "body_part_l2": "腹部血管",
        "scan_method": "MRA",
        "category": "血管成像",
        "note": "补充腹部血管MRA"
    },
    {
        "modality": "CT",
        "name": "CT腹部血管成像(CTA)",
        "body_part_l1": "腹部",
        "body_part_l2": "腹部血管",
        "scan_method": "CTA",
        "category": "血管成像",
        "note": "补充腹部血管CTA"
    },
    {
        "modality": "MR",
        "name": "MR盆腔血管成像(MRA)",
        "body_part_l1": "盆腔",
        "body_part_l2": "盆腔血管",
        "scan_method": "MRA",
        "category": "血管成像",
        "note": "补充盆腔血管MRA"
    },
]


async def import_vascular_items():
    """导入血管成像标准项"""
    engine = get_engine()
    session_factory = get_session_factory()

    async with session_factory() as session:
        print(f"开始导入 {len(vascular_items_to_add)} 项血管成像标准项...")

        added_count = 0
        skipped_count = 0

        for item_data in vascular_items_to_add:
            # 检查是否已存在（通过item_name）
            result = await session.execute(
                text("""
                    SELECT id FROM standard_check_items
                    WHERE modality = :modality AND item_name = :item_name
                """),
                {"modality": item_data["modality"], "item_name": item_data["name"]}
            )
            existing = result.fetchone()

            if existing:
                print(f"  ⏭️  已存在: {item_data['name']}")
                skipped_count += 1
                continue

            # 生成item_code（格式：modality_序号）
            result = await session.execute(
                text("SELECT COUNT(*) FROM standard_check_items WHERE modality = :modality"),
                {"modality": item_data["modality"]}
            )
            count = result.scalar()
            item_code = f"{item_data['modality']}_{count + 1:04d}"

            # 插入新标准项
            await session.execute(
                text("""
                    INSERT INTO standard_check_items (
                        item_code, item_name, modality,
                        body_part_l1, body_part_l2, scan_method,
                        source, version,
                        coverage_status, supplement_status, is_active
                    ) VALUES (
                        :item_code, :item_name, :modality,
                        :body_part_l1, :body_part_l2, :scan_method,
                        :source, :version,
                        :coverage_status, :supplement_status, :is_active
                    )
                """),
                {
                    "item_code": item_code,
                    "item_name": item_data["name"],
                    "modality": item_data["modality"],
                    "body_part_l1": item_data.get("body_part_l1"),
                    "body_part_l2": item_data.get("body_part_l2"),
                    "scan_method": item_data.get("scan_method"),
                    "source": "P2补充-血管成像",
                    "version": "1.0",
                    "coverage_status": "full",
                    "supplement_status": "completed",
                    "is_active": True
                }
            )

            print(f"  ✅ 添加: {item_data['name']} (code: {item_code})")
            added_count += 1

        await session.commit()

        print(f"\n导入完成:")
        print(f"  新增: {added_count} 项")
        print(f"  跳过: {skipped_count} 项")
        print(f"  总计: {len(vascular_items_to_add)} 项")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(import_vascular_items())

"""
P2任务：补充血管成像标准项

根据 ct-mr-unmatched-algorithm-analysis.md D类缺口分析，需补充27项血管成像标准库：
- MRA/CTA平扫项
- MRV静脉项
- 特定部位血管成像

执行方式：
1. 启动数据库: docker-compose up -d postgres (或使用现有数据库)
2. 运行此脚本: poetry run python scripts/add_vascular_items.py
"""

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

# 估算：27项 (实际列表28项，可根据实际需要调整)
print(f"计划补充血管成像标准项: {len(vascular_items_to_add)} 项")
print("\n分类统计:")
print(f"- MRA平扫: {len([x for x in vascular_items_to_add if 'MRA' in x['scan_method'] and 'CE' not in x['scan_method']])}")
print(f"- CE-MRA增强: {len([x for x in vascular_items_to_add if 'CE-MRA' in x['scan_method']])}")
print(f"- MRV静脉: {len([x for x in vascular_items_to_add if 'MRV' in x['scan_method']])}")
print(f"- CTA: {len([x for x in vascular_items_to_add if 'CTA' in x['scan_method']])}")
print(f"- CTV: {len([x for x in vascular_items_to_add if 'CTV' in x['scan_method']])}")

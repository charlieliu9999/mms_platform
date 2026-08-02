#!/usr/bin/env python3
"""
从 procedure_dictionary 导入数据到 nlp_checkitem_standard
处理字段映射和模态转换
"""

import asyncio
import asyncpg
from datetime import datetime

DATABASE_URL = "postgresql://postgres:password@127.0.0.1:15432/acrac_db"

# 模态映射（原系统 -> MMS系统）
MODALITY_MAPPING = {
    'US': ('4', 'US', '40'),      # (modality_code, modality_name, device_type_code)
    'RF': ('6', 'RF', '60'),
    'MG': ('7', 'MG', '70'),
    'DSA': ('8', 'DSA', '80'),
    'ES': ('9', 'ES', '90'),
    'PET': ('10', 'PET', '100'),
    'NM': ('5', 'NM', '50'),
    'SPECT': ('5', 'NM', '50'),   # SPECT映射到核医学
    'OCT': ('12', 'OCT', '120'),
    'XR': ('3', 'DR', '40'),      # XR映射到DR
    'PET/CT': ('10', 'PET', '100'),
    'PET/MR': ('10', 'PET', '100'),
}

# 部位映射（简化版）
BODY_PART_MAPPING = {
    '头部': ('01', '头部'),
    '颈部': ('02', '颈部'),
    '脊柱': ('03', '脊柱'),
    '胸部': ('04', '胸部'),
    '腹部': ('05', '腹部'),
    '盆腔': ('06', '盆腔'),
    '四肢': ('07', '四肢及关节'),
    '乳腺': ('08', '乳腺'),
    '心脏': ('09', '心脏'),
    '血管': ('10', '血管'),
}

# 扫描方式映射
SCAN_MAPPING = {
    '平扫': ('11', '平扫'),
    '增强': ('12', '增强'),
    '平扫+增强': ('13', '平扫+增强'),
}


def parse_body_part(body_part_str: str):
    """解析部位字符串，返回一级编码和名称"""
    if not body_part_str:
        return ('99', '其他')

    # 简单匹配
    for key, value in BODY_PART_MAPPING.items():
        if key in body_part_str:
            return value

    return ('99', '其他')


def parse_scan_type(name_zh: str, contrast_used):
    """从检查名称和对比剂标志推断扫描方式"""
    if contrast_used is True:
        return ('12', '增强')
    elif contrast_used is False:
        return ('11', '平扫')
    elif '增强' in name_zh:
        if '平扫' in name_zh:
            return ('13', '平扫+增强')
        return ('12', '增强')
    elif '平扫' in name_zh:
        return ('11', '平扫')
    else:
        return ('11', '平扫')  # 默认


def generate_checkitem_code(modality_code: str, one_level_code: str, scan_code: str):
    """生成检查项目编码
    格式: device_type_code(2) + one_level_code(2) + two_level(2) + three_level(2) + scan_code(2) + post(2) + position(2) + special(2)
    简化版: device_type_code + one_level_code + "0000" + scan_code + "0000"
    """
    device_type_code = {
        '1': '10', '2': '20', '3': '40', '4': '40', '5': '50',
        '6': '60', '7': '70', '8': '80', '9': '90', '10': '100', '12': '120'
    }.get(modality_code, '00')

    return f"{device_type_code}{one_level_code}0000{scan_code}0000"


async def import_modality_data(conn, modality: str, dry_run: bool = True):
    """导入指定模态的数据"""

    if modality not in MODALITY_MAPPING:
        print(f"  ⚠️  模态 {modality} 未配置映射，跳过")
        return 0

    modality_code, modality_name, device_type_code = MODALITY_MAPPING[modality]

    # 查询原系统数据
    source_data = await conn.fetch("""
        SELECT
            id,
            semantic_id,
            name_en,
            name_zh,
            modality,
            body_part,
            contrast_used,
            standard_code
        FROM procedure_dictionary
        WHERE modality = $1 AND is_active = true
    """, modality)

    if not source_data:
        print(f"  ⚠️  模态 {modality} 无数据")
        return 0

    print(f"  📊 模态 {modality} -> code {modality_code} ({modality_name}): {len(source_data)} 条")

    if dry_run:
        # 预览前3条
        for i, row in enumerate(source_data[:3], 1):
            one_level_code, one_level_name = parse_body_part(row['body_part'])
            scan_code, scan_name = parse_scan_type(row['name_zh'], row['contrast_used'])
            checkitem_code = generate_checkitem_code(modality_code, one_level_code, scan_code)

            print(f"     [{i}] {row['name_zh'][:40]}")
            print(f"         code={checkitem_code}, 部位={one_level_name}, 扫描={scan_name}")

        print(f"     [DRY RUN] 跳过实际导入")
        return 0

    # 实际导入
    inserted = 0
    skipped = 0
    errors = 0

    for row in source_data:
        # 检查是否已存在（通过原始ID + 模态组合）
        exists = await conn.fetchval("""
            SELECT COUNT(*) FROM nlp_checkitem_standard
            WHERE checkitem_name = $1 AND modality_code = $2
        """, row['name_zh'], modality_code)

        if exists:
            skipped += 1
            continue

        # 解析字段
        one_level_code, one_level_name = parse_body_part(row['body_part'])
        scan_code, scan_name = parse_scan_type(row['name_zh'], row['contrast_used'])
        checkitem_code = generate_checkitem_code(modality_code, one_level_code, scan_code)

        try:
            await conn.execute("""
                INSERT INTO nlp_checkitem_standard (
                    modality_code,
                    modality_name,
                    device_type_code,
                    device_type_name,
                    one_level_code,
                    one_level_name,
                    scan_code,
                    scan_name,
                    checkitem_code,
                    checkitem_name,
                    version,
                    is_deleted,
                    create_time,
                    update_time
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
                modality_code,
                modality_name,
                device_type_code,
                modality_name,  # device_type_name 使用模态名
                one_level_code,
                one_level_name,
                scan_code,
                scan_name,
                checkitem_code,
                row['name_zh'],
                'V1.0-imported',
                0,
                datetime.now(),
                datetime.now()
            )
            inserted += 1
        except Exception as e:
            print(f"     ❌ 插入失败: {row['name_zh'][:30]} - {e}")
            errors += 1

    result_str = f"✅ 成功 {inserted}" if inserted > 0 else ""
    result_str += f", 跳过 {skipped}" if skipped > 0 else ""
    result_str += f", ❌ 失败 {errors}" if errors > 0 else ""

    print(f"     {result_str}")
    return inserted


async def main(dry_run: bool = True):
    conn = await asyncpg.connect(DATABASE_URL)

    print("=" * 80)
    print("从 procedure_dictionary 导入到 nlp_checkitem_standard")
    print("=" * 80)
    print(f"模式: {'DRY RUN (仅预览前3条)' if dry_run else '实际导入'}")
    print()

    total_inserted = 0

    # 按模态排序导入
    sorted_modalities = sorted(MODALITY_MAPPING.keys())

    for modality in sorted_modalities:
        try:
            inserted = await import_modality_data(conn, modality, dry_run)
            total_inserted += inserted
        except Exception as e:
            print(f"  ❌ 模态 {modality} 处理失败: {e}")

    print()
    print("=" * 80)
    if dry_run:
        print("预览完成，如需实际导入请运行: --execute")
    else:
        print(f"导入完成: {total_inserted} 条新记录")
    print("=" * 80)

    await conn.close()


if __name__ == "__main__":
    import sys

    dry_run = "--execute" not in sys.argv

    if dry_run:
        print("\n⚠️  预览模式（仅显示前3条转换示例）")
        print("   实际导入: poetry run python scripts/import_all_modalities.py --execute\n")
    else:
        print("\n🚀 实际导入模式\n")

    asyncio.run(main(dry_run=dry_run))

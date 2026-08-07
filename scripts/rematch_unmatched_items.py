#!/usr/bin/env python3
"""
对未匹配项目执行批量重匹配
验证P1算法优化效果并更新 standard_hospital_mapping
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from match_service.config import get_settings
from match_service.core.engine_holder import EngineHolder

async def rematch_unmatched():
    """重新匹配未匹配项目"""
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # 初始化匹配引擎
    print("正在初始化匹配引擎...")
    engine_holder = EngineHolder()
    await engine_holder.initialize()
    match_engine = engine_holder.match_engine

    async with async_session() as db:
        # 获取所有未匹配项目
        result = await db.execute(text('''
            SELECT hci.id, hci.order_name, hci.modality_hint, hci.hospital_id
            FROM hospital_check_items hci
            LEFT JOIN standard_hospital_mapping shm ON hci.id = shm.hospital_item_id
            WHERE hci.is_active = true
              AND hci.modality_hint IN ('CT', 'MR', 'DR', 'US')
              AND shm.id IS NULL
            ORDER BY hci.modality_hint, hci.id
        '''))

        unmatched_items = result.fetchall()
        print(f"\n找到 {len(unmatched_items)} 个未匹配项目")

        # 统计
        matched_count = 0
        degraded_count = 0
        failed_count = 0
        modality_stats = {}

        for idx, (item_id, order_name, modality, hospital_id) in enumerate(unmatched_items, 1):
            if idx % 10 == 0:
                print(f"  处理进度: {idx}/{len(unmatched_items)} ({idx/len(unmatched_items)*100:.1f}%)")

            try:
                # 执行匹配
                match_result = match_engine.match(order_name, modality, "V3.8.2")
                tier = match_result.get('tier', 'none')
                confidence = match_result.get('confidence', 0.0)
                data = match_result.get('data', [])

                # 记录统计
                if modality not in modality_stats:
                    modality_stats[modality] = {'total': 0, 'matched': 0, 'degraded': 0}
                modality_stats[modality]['total'] += 1

                # 如果匹配成功（exact/partial/degraded），写入 standard_hospital_mapping
                # data 结构: [{'raw': '...', 'standard': [{'code': 'xxx', 'name': 'xxx'}, ...]}, ...]
                if tier in ('exact', 'partial', 'degraded') and data:
                    # 取第一个data项的第一个standard结果
                    first_data = data[0]
                    standards = first_data.get('standard', [])
                    if not standards:
                        failed_count += 1
                        continue

                    first_standard = standards[0]
                    standard_code = first_standard.get('code')

                    # 通过 standard_code 查找 standard_item_id
                    result_query = await db.execute(text('''
                        SELECT id FROM standard_check_items
                        WHERE checkitem_code = :code
                        LIMIT 1
                    '''), {'code': standard_code})
                    row = result_query.fetchone()

                    if not row:
                        failed_count += 1
                        if idx <= 20:
                            print(f"  ✗ [no_std  ] ID {item_id:5d} ({modality}): 标准项不存在 {standard_code}")
                        continue

                    standard_item_id = row[0]

                    # 插入映射记录
                    await db.execute(text('''
                        INSERT INTO standard_hospital_mapping
                        (standard_item_id, hospital_item_id, hospital_id,
                         mapping_type, confidence, created_at, updated_at)
                        VALUES (:std_id, :hosp_id, :hospital_id,
                                :mapping_type, :confidence, :now, :now)
                        ON CONFLICT DO NOTHING
                    '''), {
                        'std_id': standard_item_id,
                        'hosp_id': item_id,
                        'hospital_id': hospital_id,
                        'mapping_type': 'algorithm' if tier == 'exact' else 'algorithm_degraded',
                        'confidence': confidence,
                        'now': datetime.now()
                    })

                    matched_count += 1
                    modality_stats[modality]['matched'] += 1

                    if tier == 'degraded':
                        degraded_count += 1
                        modality_stats[modality]['degraded'] += 1

                    if idx <= 20:  # 只显示前20个成功项
                        print(f"  ✓ [{tier:8s}] ID {item_id:5d} ({modality}): {order_name[:50]}")
                else:
                    failed_count += 1
                    if idx <= 20:  # 只显示前20个失败项
                        print(f"  ✗ [none    ] ID {item_id:5d} ({modality}): {order_name[:50]}")

            except Exception as e:
                print(f"  ✗ [error   ] ID {item_id:5d} ({modality}): {e}")
                failed_count += 1

        # 提交所有变更
        await db.commit()

        # 输出统计
        print("\n" + "=" * 80)
        print("重匹配结果统计:")
        print("=" * 80)
        print(f"总处理: {len(unmatched_items)} 项")
        print(f"匹配成功: {matched_count} 项 ({matched_count/len(unmatched_items)*100:.1f}%)")
        print(f"  其中降级: {degraded_count} 项")
        print(f"仍未匹配: {failed_count} 项 ({failed_count/len(unmatched_items)*100:.1f}%)")

        print("\n各模态统计:")
        for modality in sorted(modality_stats.keys()):
            stats = modality_stats[modality]
            rate = stats['matched'] / stats['total'] * 100 if stats['total'] > 0 else 0
            print(f"  {modality}: {stats['matched']:3d}/{stats['total']:3d} ({rate:5.1f}%) | 降级: {stats['degraded']:2d}")

        # 查询新的匹配率
        print("\n" + "=" * 80)
        print("更新后的总体匹配率:")
        print("=" * 80)

        result = await db.execute(text('''
            SELECT
                hci.modality_hint as modality,
                COUNT(DISTINCT hci.id) as total,
                COUNT(DISTINCT CASE WHEN shm.standard_item_id IS NOT NULL THEN hci.id END) as mapped,
                ROUND(100.0 * COUNT(DISTINCT CASE WHEN shm.standard_item_id IS NOT NULL THEN hci.id END) / COUNT(DISTINCT hci.id), 1) as rate
            FROM hospital_check_items hci
            LEFT JOIN standard_hospital_mapping shm ON hci.id = shm.hospital_item_id
            WHERE hci.is_active = true AND hci.modality_hint IN ('CT', 'MR', 'DR', 'US')
            GROUP BY hci.modality_hint
            ORDER BY hci.modality_hint
        '''))

        total_all = 0
        matched_all = 0

        for row in result.fetchall():
            modality, total, mapped, rate = row
            total_all += total
            matched_all += mapped
            gap = 90 - rate
            status = '✅ 达标' if rate >= 90 else '❌ 未达标'
            print(f"{modality:3s}: {mapped:4d}/{total:4d} ({rate:5.1f}%) {status} | 距90%: {gap:+5.1f}%")

        overall_rate = matched_all / total_all * 100 if total_all > 0 else 0
        print("=" * 80)
        print(f"总计: {matched_all:4d}/{total_all:4d} ({overall_rate:.1f}%)")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(rematch_unmatched())

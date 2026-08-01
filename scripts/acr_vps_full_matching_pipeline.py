#!/usr/bin/env python3
"""
从 VPS 导出 4555 条 ACR 项目并执行完整匹配流程

使用方法：
1. 在 VPS 服务器上执行此脚本导出数据
2. 将导出的 JSON 文件复制到本地
3. 在本地执行导入和匹配

或者：
直接在本地执行，通过 SSH 隧道连接到 VPS 数据库
"""

import asyncio
import json
import sys
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# VPS 数据库连接（请根据实际情况修改）
VPS_DATABASE_URL = "postgresql+asyncpg://postgres:你的密码@220.154.3.166:5432/acrac_db"
# 或者通过 SSH 隧道：
# VPS_DATABASE_URL = "postgresql+asyncpg://postgres:密码@127.0.0.1:5433/acrac_db"

async def export_from_vps():
    """从 VPS 导出完整的 ACR 项目数据"""

    print("=" * 80)
    print("步骤 1/5: 从 VPS 导出 ACR 项目数据")
    print("=" * 80)

    engine = create_async_engine(VPS_DATABASE_URL)

    try:
        async with engine.begin() as conn:
            # 导出 procedure_dictionary
            result = await conn.execute(text("""
                SELECT
                    id,
                    semantic_id,
                    name_en,
                    name_zh,
                    modality,
                    body_part,
                    contrast_used,
                    radiation_level,
                    exam_duration,
                    standard_code,
                    description_zh,
                    is_active
                FROM procedure_dictionary
                WHERE is_active = true
                ORDER BY id
            """))

            rows = result.fetchall()
            print(f"\n✅ 成功导出 {len(rows)} 条 ACR 项目")

            # 转换为字典
            procedures = []
            for row in rows:
                procedures.append({
                    'id': row[0],
                    'semantic_id': row[1],
                    'name_en': row[2],
                    'name_zh': row[3],
                    'modality': row[4],
                    'body_part': row[5],
                    'contrast_used': row[6],
                    'radiation_level': row[7],
                    'exam_duration': row[8],
                    'standard_code': row[9],
                    'description_zh': row[10],
                    'is_active': row[11]
                })

            # 统计模态分布
            modality_stats = {}
            for proc in procedures:
                mod = proc['modality'] or 'NULL'
                modality_stats[mod] = modality_stats.get(mod, 0) + 1

            print(f"\n模态分布:")
            for mod, count in sorted(modality_stats.items(), key=lambda x: -x[1])[:20]:
                print(f"  {mod}: {count}")

            return procedures

    finally:
        await engine.dispose()


async def filter_imaging_procedures(procedures):
    """过滤非影像类项目"""

    print("\n" + "=" * 80)
    print("步骤 2/5: 过滤非影像类项目")
    print("=" * 80)

    # 影像类模态
    IMAGING_MODALITIES = {
        'CT', 'MR', 'MRI', 'US', 'XR', 'DR', 'CR', 'MG', 'RF', 'FL',
        'DSA', 'ANGIO', 'PET', 'SPECT', 'NM', 'OCT', 'CBCT', 'CT-DE',
        'PET-CT', 'PET-MR', 'PET/CT', 'PET/MR', 'PET/MRI'
    }

    # 非影像类模态
    NON_IMAGING_MODALITIES = {
        'IR', 'THERAPY', 'SURG', 'ENDO', 'Other', 'ASSESS', 'ES', 'AN'
    }

    imaging_procedures = []
    filtered_out = []

    for proc in procedures:
        modality = proc['modality']
        name = proc['name_zh'] or ''

        # 影像模态
        if modality in IMAGING_MODALITIES:
            imaging_procedures.append(proc)
        # 非影像模态
        elif modality in NON_IMAGING_MODALITIES:
            filtered_out.append(proc)
        # NULL 或未知模态 - 根据名称判断
        elif not modality or modality == 'NULL':
            surgery_keywords = ['穿刺', '活检', '抽吸', '引流', '置管', '切除', '手术', '治疗', '造瘘']
            if any(kw in name for kw in surgery_keywords):
                filtered_out.append(proc)
            else:
                imaging_procedures.append(proc)
        else:
            # 未知模态，保留
            imaging_procedures.append(proc)

    print(f"\n✅ 影像检查项目: {len(imaging_procedures)} 条")
    print(f"❌ 过滤掉（非影像）: {len(filtered_out)} 条")

    # 统计保留的模态分布
    modality_stats = {}
    for proc in imaging_procedures:
        mod = proc['modality'] or 'NULL'
        modality_stats[mod] = modality_stats.get(mod, 0) + 1

    print(f"\n保留的影像项目模态分布:")
    for mod, count in sorted(modality_stats.items(), key=lambda x: -x[1]):
        print(f"  {mod}: {count}")

    return imaging_procedures, filtered_out


async def import_to_mms(imaging_procedures, local_db_url):
    """导入到 MMS 评测系统"""

    print("\n" + "=" * 80)
    print("步骤 3/5: 导入到 MMS 评测系统")
    print("=" * 80)

    engine = create_async_engine(local_db_url)

    try:
        async with engine.begin() as conn:
            # 创建评测任务
            task_name = f"ACR推荐项目全量匹配评测（VPS完整数据{len(imaging_procedures)}条）"
            task_desc = f"从VPS导出的{len(imaging_procedures)}条ACR推荐检查项目，用于评估MMS引擎对学术规范表述的匹配能力。导入时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            result = await conn.execute(text("""
                INSERT INTO mms_eval_tasks (
                    name,
                    description,
                    status,
                    total_count,
                    matched_count,
                    correct_count,
                    wrong_count,
                    no_match_count,
                    progress,
                    created_at
                ) VALUES (
                    :name,
                    :description,
                    'pending',
                    :total_count,
                    0, 0, 0, 0, 0,
                    NOW()
                )
                RETURNING id
            """), {
                'name': task_name,
                'description': task_desc,
                'total_count': len(imaging_procedures)
            })

            task_id = result.scalar()
            print(f"\n✅ 评测任务已创建，ID: {task_id}")
            print(f"   任务名称: {task_name}")

            # 批量导入数据
            print(f"\n正在导入 {len(imaging_procedures)} 条评测数据...")
            imported = 0

            for proc in imaging_procedures:
                await conn.execute(text("""
                    INSERT INTO mms_eval_details (
                        task_id,
                        check_item,
                        modality,
                        expected_code,
                        expected_name,
                        created_at
                    ) VALUES (
                        :task_id,
                        :check_item,
                        :modality,
                        NULL,
                        NULL,
                        NOW()
                    )
                """), {
                    'task_id': task_id,
                    'check_item': proc['name_zh'],
                    'modality': proc['modality']
                })
                imported += 1

                if imported % 500 == 0:
                    print(f"  进度: {imported}/{len(imaging_procedures)} ({imported*100//len(imaging_procedures)}%)")

            print(f"\n✅ 数据导入完成! 共 {imported} 条")

            return task_id

    finally:
        await engine.dispose()


async def run_matching(task_id, local_db_url):
    """执行匹配评测"""

    print("\n" + "=" * 80)
    print("步骤 4/5: 执行全量匹配")
    print("=" * 80)
    print(f"\n任务 ID: {task_id}")
    print(f"预计耗时: 5-10 分钟\n")

    engine = create_async_engine(local_db_url)

    # 导入匹配引擎
    import sys
    sys.path.insert(0, 'src')
    from match_service.core.engine_holder import get_engine_holder

    try:
        async with engine.begin() as conn:
            # 更新任务状态
            await conn.execute(text("""
                UPDATE mms_eval_tasks
                SET status = 'running', started_at = NOW(), progress = 0
                WHERE id = :task_id
            """), {'task_id': task_id})

            # 获取待匹配数据
            result = await conn.execute(text("""
                SELECT id, check_item, modality
                FROM mms_eval_details
                WHERE task_id = :task_id
                ORDER BY id
            """), {'task_id': task_id})

            items = result.fetchall()
            total = len(items)

            print(f"开始匹配 {total} 条数据...")

            # 获取匹配引擎
            engine_holder = get_engine_holder()

            matched_count = 0
            no_match_count = 0

            for idx, (item_id, check_item, modality) in enumerate(items, 1):
                try:
                    # 调用匹配引擎
                    match_result = await engine_holder.match_one(
                        check_item_name=check_item,
                        modality=modality
                    )

                    is_matched = match_result.get('matched', False)
                    if is_matched:
                        matched_count += 1
                    else:
                        no_match_count += 1

                    # 更新匹配结果
                    await conn.execute(text("""
                        UPDATE mms_eval_details
                        SET
                            actual_code = :actual_code,
                            actual_name = :actual_name,
                            confidence = :confidence,
                            response_time = :response_time,
                            is_matched = :is_matched,
                            match_type = :match_type,
                            failure_reason = :failure_reason,
                            failure_detail = :failure_detail
                        WHERE id = :id
                    """), {
                        'id': item_id,
                        'actual_code': match_result.get('standard_code'),
                        'actual_name': match_result.get('standard_name'),
                        'confidence': match_result.get('confidence'),
                        'response_time': match_result.get('response_time_ms'),
                        'is_matched': is_matched,
                        'match_type': match_result.get('match_type'),
                        'failure_reason': match_result.get('failure_reason'),
                        'failure_detail': match_result.get('failure_detail')
                    })

                    # 更新进度
                    if idx % 100 == 0:
                        progress = int(idx * 100 / total)
                        await conn.execute(text("""
                            UPDATE mms_eval_tasks
                            SET progress = :progress
                            WHERE id = :task_id
                        """), {'task_id': task_id, 'progress': progress})

                        print(f"  进度: {idx}/{total} ({progress}%) | 已匹配: {matched_count} | 未匹配: {no_match_count}")

                except Exception as e:
                    print(f"  ⚠️  项目 {item_id} 匹配失败: {e}")
                    no_match_count += 1

            # 计算最终统计
            match_rate = (matched_count / total * 100) if total > 0 else 0

            # 更新任务状态
            await conn.execute(text("""
                UPDATE mms_eval_tasks
                SET
                    status = 'completed',
                    progress = 100,
                    matched_count = :matched_count,
                    no_match_count = :no_match_count,
                    match_rate = :match_rate,
                    completed_at = NOW()
                WHERE id = :task_id
            """), {
                'task_id': task_id,
                'matched_count': matched_count,
                'no_match_count': no_match_count,
                'match_rate': match_rate
            })

            print(f"\n✅ 匹配完成!")
            print(f"   总数: {total}")
            print(f"   匹配成功: {matched_count}")
            print(f"   未匹配: {no_match_count}")
            print(f"   匹配率: {match_rate:.2f}%")

            return {
                'total': total,
                'matched': matched_count,
                'no_match': no_match_count,
                'match_rate': match_rate
            }

    finally:
        await engine.dispose()


async def analyze_results(task_id, local_db_url):
    """分析匹配结果"""

    print("\n" + "=" * 80)
    print("步骤 5/5: 全量分析匹配结果")
    print("=" * 80)

    engine = create_async_engine(local_db_url)

    try:
        async with engine.begin() as conn:
            # 1. 按模态统计
            result = await conn.execute(text("""
                SELECT
                    modality,
                    COUNT(*) as total,
                    SUM(CASE WHEN is_matched THEN 1 ELSE 0 END) as matched,
                    AVG(CASE WHEN is_matched THEN confidence ELSE NULL END) as avg_confidence,
                    AVG(response_time) as avg_response_time
                FROM mms_eval_details
                WHERE task_id = :task_id
                GROUP BY modality
                ORDER BY total DESC
            """), {'task_id': task_id})

            print(f"\n📊 按模态统计:")
            print(f"{'模态':<10} {'总数':>6} {'匹配':>6} {'匹配率':>8} {'平均置信度':>10} {'平均响应时间':>12}")
            print("-" * 70)

            modality_stats = []
            for row in result:
                modality = row[0] or 'NULL'
                total = row[1]
                matched = row[2]
                avg_conf = row[3] or 0
                avg_time = row[4] or 0
                match_rate = (matched / total * 100) if total > 0 else 0

                print(f"{modality:<10} {total:>6} {matched:>6} {match_rate:>7.1f}% {avg_conf:>9.3f} {avg_time:>11.1f}ms")

                modality_stats.append({
                    'modality': modality,
                    'total': total,
                    'matched': matched,
                    'match_rate': match_rate,
                    'avg_confidence': float(avg_conf),
                    'avg_response_time': float(avg_time)
                })

            # 2. 失败原因统计
            result = await conn.execute(text("""
                SELECT
                    failure_reason,
                    COUNT(*) as count
                FROM mms_eval_details
                WHERE task_id = :task_id AND is_matched = false
                GROUP BY failure_reason
                ORDER BY count DESC
            """), {'task_id': task_id})

            print(f"\n📊 失败原因统计:")
            print(f"{'原因':<20} {'数量':>8} {'占比':>8}")
            print("-" * 40)

            failure_stats = []
            total_failures = 0
            for row in result:
                reason = row[0] or 'unknown'
                count = row[1]
                total_failures += count

                failure_stats.append({
                    'reason': reason,
                    'count': count
                })

            for stat in failure_stats:
                ratio = (stat['count'] / total_failures * 100) if total_failures > 0 else 0
                print(f"{stat['reason']:<20} {stat['count']:>8} {ratio:>7.1f}%")

            # 3. 高频未匹配项目
            result = await conn.execute(text("""
                SELECT
                    check_item,
                    modality,
                    failure_reason,
                    COUNT(*) as freq
                FROM mms_eval_details
                WHERE task_id = :task_id AND is_matched = false
                GROUP BY check_item, modality, failure_reason
                ORDER BY freq DESC, check_item
                LIMIT 50
            """), {'task_id': task_id})

            print(f"\n📊 高频未匹配项目 (Top 50):")
            print(f"{'项目名称':<50} {'模态':<8} {'原因':<20} {'频次':>6}")
            print("-" * 90)

            frequent_failures = []
            for row in result:
                check_item = row[0]
                modality = row[1] or 'NULL'
                reason = row[2] or 'unknown'
                freq = row[3]

                # 截断过长的名称
                display_name = check_item[:47] + '...' if len(check_item) > 50 else check_item
                print(f"{display_name:<50} {modality:<8} {reason:<20} {freq:>6}")

                frequent_failures.append({
                    'check_item': check_item,
                    'modality': modality,
                    'failure_reason': reason,
                    'frequency': freq
                })

            # 保存分析结果
            analysis_result = {
                'task_id': task_id,
                'timestamp': datetime.now().isoformat(),
                'modality_stats': modality_stats,
                'failure_stats': failure_stats,
                'frequent_failures': frequent_failures
            }

            output_file = f'data/acr_vps_analysis_{task_id}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, ensure_ascii=False, indent=2)

            print(f"\n✅ 分析结果已保存到: {output_file}")

            return analysis_result

    finally:
        await engine.dispose()


async def main():
    """主流程"""

    print("\n" + "=" * 80)
    print("ACR 推荐项目全量匹配任务")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 本地 MMS 数据库
    LOCAL_DB_URL = 'postgresql+asyncpg://postgres:password@127.0.0.1:15432/acrac_db'

    # 步骤 1: 从 VPS 导出数据
    try:
        procedures = await export_from_vps()
    except Exception as e:
        print(f"\n❌ VPS 导出失败: {e}")
        print(f"\n💡 请检查:")
        print(f"   1. VPS 数据库连接串是否正确")
        print(f"   2. 网络是否可达")
        print(f"   3. 数据库密码是否正确")
        print(f"\n💡 备选方案: 手动在 VPS 上运行导出脚本")
        return

    # 保存原始数据
    with open('data/acr_vps_procedures_full.json', 'w', encoding='utf-8') as f:
        json.dump(procedures, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 原始数据已保存到: data/acr_vps_procedures_full.json")

    # 步骤 2: 过滤非影像类项目
    imaging_procedures, filtered_out = await filter_imaging_procedures(procedures)

    # 保存过滤后的数据
    with open('data/acr_vps_imaging_procedures.json', 'w', encoding='utf-8') as f:
        json.dump(imaging_procedures, f, ensure_ascii=False, indent=2)
    with open('data/acr_vps_filtered_out.json', 'w', encoding='utf-8') as f:
        json.dump(filtered_out, f, ensure_ascii=False, indent=2)

    # 步骤 3: 导入到 MMS
    task_id = await import_to_mms(imaging_procedures, LOCAL_DB_URL)

    # 步骤 4: 执行匹配
    match_result = await run_matching(task_id, LOCAL_DB_URL)

    # 步骤 5: 分析结果
    analysis = await analyze_results(task_id, LOCAL_DB_URL)

    # 最终总结
    print("\n" + "=" * 80)
    print("任务完成总结")
    print("=" * 80)
    print(f"\n✅ 任务 ID: {task_id}")
    print(f"✅ 总项目数: {match_result['total']}")
    print(f"✅ 匹配成功: {match_result['matched']}")
    print(f"✅ 未匹配: {match_result['no_match']}")
    print(f"✅ 匹配率: {match_result['match_rate']:.2f}%")
    print(f"\n生成的文件:")
    print(f"  - data/acr_vps_procedures_full.json (原始数据)")
    print(f"  - data/acr_vps_imaging_procedures.json (影像项目)")
    print(f"  - data/acr_vps_filtered_out.json (过滤项目)")
    print(f"  - data/acr_vps_analysis_{task_id}.json (分析结果)")
    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")


if __name__ == '__main__':
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print(__doc__)
        sys.exit(0)

    asyncio.run(main())

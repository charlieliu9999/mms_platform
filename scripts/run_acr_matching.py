#!/usr/bin/env python3
"""
执行本地 ACR 项目（2167条）的完整匹配和分析

快速验证流程，无需从 VPS 导出数据
"""

import asyncio
import json
import sys
sys.path.insert(0, 'src')

from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from match_service.core.engine_holder import get_engine_holder
from match_service.core.dispatcher import MatchDispatcher
from match_service.db import get_session_factory

DATABASE_URL = 'postgresql+asyncpg://postgres:password@127.0.0.1:15432/acrac_db'

async def run_matching_task(task_id):
    """执行匹配评测"""

    print("=" * 80)
    print(f"执行匹配评测 - 任务 #{task_id}")
    print("=" * 80)

    engine = create_async_engine(DATABASE_URL)

    try:
        async with engine.begin() as conn:
            # 获取任务信息
            result = await conn.execute(text("""
                SELECT name, total_count FROM mms_eval_tasks WHERE id = :task_id
            """), {'task_id': task_id})

            task_info = result.first()
            if not task_info:
                print(f"❌ 任务 #{task_id} 不存在")
                return None

            print(f"\n任务名称: {task_info[0]}")
            print(f"数据条数: {task_info[1]}")
            print(f"开始时间: {datetime.now().strftime('%H:%M:%S')}\n")

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

            # 获取匹配引擎
            engine_holder = get_engine_holder()

            # 初始化引擎（如果未就绪）
            if not engine_holder.is_ready:
                print("正在初始化匹配引擎...")
                await engine_holder.initialize()
                print("✅ 引擎初始化完成")

            matched_count = 0
            no_match_count = 0
            total_confidence = 0
            total_time = 0

            print("开始匹配...")

            for idx, (item_id, check_item, modality) in enumerate(items, 1):
                try:
                    # 创建 session 并使用 MatchDispatcher
                    session_factory = get_session_factory()
                    async with session_factory() as session:
                        dispatcher = MatchDispatcher(session, engine_holder)
                        match_result = await dispatcher.match(
                            text=check_item,
                            modality=modality,
                            version="V3.8.2"
                        )

                    # 解析匹配结果
                    data = match_result.get('data', [])
                    confidence = match_result.get('confidence', 0)
                    tier = match_result.get('tier', '')
                    reason = match_result.get('reason', '')

                    # 判断是否匹配成功
                    is_matched = False
                    actual_code = None
                    actual_name = None

                    if data and len(data) > 0 and 'standard' in data[0]:
                        standards = data[0]['standard']
                        if standards and len(standards) > 0:
                            is_matched = True
                            actual_code = standards[0].get('code')
                            actual_name = standards[0].get('name')

                    if is_matched:
                        matched_count += 1
                        total_confidence += confidence
                    else:
                        no_match_count += 1

                    # 更新匹配结果
                    await conn.execute(text("""
                        UPDATE mms_eval_details
                        SET
                            actual_code = :actual_code,
                            actual_name = :actual_name,
                            confidence = :confidence,
                            response_time = 0,
                            is_matched = :is_matched,
                            match_type = :match_type,
                            failure_reason = :failure_reason,
                            failure_detail = :failure_detail
                        WHERE id = :id
                    """), {
                        'id': item_id,
                        'actual_code': actual_code,
                        'actual_name': actual_name,
                        'confidence': confidence,
                        'is_matched': is_matched,
                        'match_type': tier,
                        'failure_reason': 'no_standard' if not is_matched else None,
                        'failure_detail': reason if not is_matched else None
                    })

                    # 显示进度
                    if idx % 100 == 0:
                        progress = int(idx * 100 / total)
                        avg_time = total_time / idx
                        await conn.execute(text("""
                            UPDATE mms_eval_tasks
                            SET progress = :progress
                            WHERE id = :task_id
                        """), {'task_id': task_id, 'progress': progress})

                        print(f"  [{datetime.now().strftime('%H:%M:%S')}] {idx}/{total} ({progress}%) | "
                              f"已匹配:{matched_count} | 未匹配:{no_match_count} | 平均:{avg_time:.1f}ms")

                except Exception as e:
                    print(f"  ⚠️  项目 #{item_id} 匹配失败: {e}")
                    no_match_count += 1

            # 计算统计指标
            match_rate = (matched_count / total * 100) if total > 0 else 0
            avg_confidence = (total_confidence / matched_count) if matched_count > 0 else 0
            avg_response_time = total_time / total if total > 0 else 0

            # 更新任务状态
            await conn.execute(text("""
                UPDATE mms_eval_tasks
                SET
                    status = 'completed',
                    progress = 100,
                    matched_count = :matched_count,
                    no_match_count = :no_match_count,
                    match_rate = :match_rate,
                    avg_confidence = :avg_confidence,
                    avg_response_time = :avg_response_time,
                    completed_at = NOW()
                WHERE id = :task_id
            """), {
                'task_id': task_id,
                'matched_count': matched_count,
                'no_match_count': no_match_count,
                'match_rate': match_rate,
                'avg_confidence': avg_confidence,
                'avg_response_time': avg_response_time
            })

            print(f"\n✅ 匹配完成!")
            print(f"   结束时间: {datetime.now().strftime('%H:%M:%S')}")
            print(f"   总数: {total}")
            print(f"   匹配成功: {matched_count} ({match_rate:.2f}%)")
            print(f"   未匹配: {no_match_count}")
            print(f"   平均置信度: {avg_confidence:.3f}")
            print(f"   平均响应时间: {avg_response_time:.2f}ms")

            return {
                'total': total,
                'matched': matched_count,
                'no_match': no_match_count,
                'match_rate': match_rate,
                'avg_confidence': avg_confidence,
                'avg_response_time': avg_response_time
            }

    finally:
        await engine.dispose()


async def analyze_results(task_id):
    """分析匹配结果"""

    print("\n" + "=" * 80)
    print("全量分析匹配结果")
    print("=" * 80)

    engine = create_async_engine(DATABASE_URL)

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
                failure_stats.append({'reason': reason, 'count': count})

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
            frequent_failures = []
            for row in result:
                check_item = row[0]
                modality = row[1] or 'NULL'
                reason = row[2] or 'unknown'
                freq = row[3]

                display_name = check_item[:47] + '...' if len(check_item) > 50 else check_item
                print(f"  [{modality:<8}] {display_name:<50} ({reason}, x{freq})")

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

            output_file = f'data/acr_analysis_task{task_id}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, ensure_ascii=False, indent=2)

            print(f"\n✅ 分析结果已保存到: {output_file}")

            return analysis_result

    finally:
        await engine.dispose()


async def main():
    task_id = 7  # 已创建的任务ID

    print("\n" + "=" * 80)
    print("ACR 项目全量匹配与分析")
    print("=" * 80)
    print(f"任务 ID: {task_id}")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 执行匹配
    match_result = await run_matching_task(task_id)

    if match_result:
        # 分析结果
        analysis = await analyze_results(task_id)

        # 总结
        print("\n" + "=" * 80)
        print("✅ 任务完成")
        print("=" * 80)
        print(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"匹配率: {match_result['match_rate']:.2f}%")
        print(f"准确率: 无标准答案，待人工审核")
        print("=" * 80 + "\n")


if __name__ == '__main__':
    asyncio.run(main())

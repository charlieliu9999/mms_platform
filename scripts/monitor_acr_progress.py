#!/usr/bin/env python3
"""
监控 ACR 匹配任务进度
"""

import asyncio
import sys
sys.path.insert(0, 'src')

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from datetime import datetime

DATABASE_URL = 'postgresql+asyncpg://postgres:password@127.0.0.1:15432/acrac_db'

async def monitor_progress(task_id):
    engine = create_async_engine(DATABASE_URL)

    try:
        while True:
            async with engine.begin() as conn:
                # 查询任务状态
                result = await conn.execute(text("""
                    SELECT
                        status,
                        progress,
                        total_count,
                        matched_count,
                        no_match_count,
                        started_at,
                        completed_at
                    FROM mms_eval_tasks
                    WHERE id = :task_id
                """), {'task_id': task_id})

                task = result.first()
                if not task:
                    print(f"任务 #{task_id} 不存在")
                    break

                status = task[0]
                progress = task[1] or 0
                total = task[2]
                matched = task[3] or 0
                no_match = task[4] or 0
                started_at = task[5]
                completed_at = task[6]

                # 计算已处理数量
                processed = matched + no_match

                # 估算剩余时间
                if started_at and processed > 0:
                    elapsed = (datetime.now() - started_at).total_seconds()
                    avg_time_per_item = elapsed / processed
                    remaining_items = total - processed
                    eta_seconds = avg_time_per_item * remaining_items
                    eta_minutes = int(eta_seconds / 60)
                    eta_seconds = int(eta_seconds % 60)
                    eta_str = f"{eta_minutes}分{eta_seconds}秒"
                else:
                    eta_str = "计算中..."

                # 显示进度
                print(f"\r[{datetime.now().strftime('%H:%M:%S')}] "
                      f"进度: {processed}/{total} ({progress}%) | "
                      f"已匹配: {matched} | 未匹配: {no_match} | "
                      f"预计剩余: {eta_str}", end='', flush=True)

                if status == 'completed':
                    print(f"\n\n✅ 任务完成!")
                    print(f"   总数: {total}")
                    print(f"   匹配成功: {matched} ({matched/total*100:.1f}%)")
                    print(f"   未匹配: {no_match} ({no_match/total*100:.1f}%)")
                    if started_at and completed_at:
                        duration = (completed_at - started_at).total_seconds()
                        print(f"   耗时: {int(duration/60)}分{int(duration%60)}秒")
                    break

            await asyncio.sleep(2)  # 每2秒刷新一次

    finally:
        await engine.dispose()

if __name__ == '__main__':
    task_id = 7
    print(f"监控任务 #{task_id} 的执行进度...")
    print(f"按 Ctrl+C 停止监控\n")

    try:
        asyncio.run(monitor_progress(task_id))
    except KeyboardInterrupt:
        print(f"\n\n监控已停止")

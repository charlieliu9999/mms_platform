#!/usr/bin/env python3
"""
Phase 1: 全量匹配脚本

对 24.6 万条基准数据执行批量匹配，保存到 mms_eval_tasks + mms_eval_details。

特性：
- 断点续跑：以 DB 中已有记录数为准，不依赖进度文件
- 批量提交：每 100 条一个事务，控制内存与事务体积
- 异常容错：单条失败也写 DB，标记 failure_reason='algorithm'
- 进度监控：终端日志 + mms_eval_tasks.progress 字段

Usage:
    # 冒烟测试（1000 条）
    poetry run python scripts/bulk_match_and_import.py --sample 1000

    # 全量执行（246k）
    poetry run python scripts/bulk_match_and_import.py --full

    # 恢复中断的任务
    poetry run python scripts/bulk_match_and_import.py --resume <task_id>
"""
import argparse
import asyncio
import sys
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import select

# 添加 src 到路径
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from match_service.core.engine_holder import EngineHolder
from match_service.db import get_engine, dispose_engine, get_session_factory
from match_service.models.evaluation import EvalTask, EvalDetail

# 导入共享工具
from bulk_match_common import (
    setup_logging, logger, normalize_code, extract_confidence,
    judge_correctness, classify_failure, DEFAULT_DATASET, MIN_CONFIDENCE
)

BATCH_SIZE = 100
PROGRESS_INTERVAL = 10  # 每 N 批次更新进度


async def create_task(name: str, test_file: str, sample_size: int = None) -> int:
    """创建评测任务记录"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        task = EvalTask(
            name=name,
            description=f"全量匹配 {sample_size or '全部'} 条基准数据",
            test_file_path=test_file,
            sample_size=sample_size,
            status='pending',
            progress=0,
            created_at=datetime.utcnow(),
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        logger.info(f"✓ 创建评测任务 #{task.id}: {task.name}")
        return task.id


async def get_existing_count(task_id: int) -> int:
    """获取已处理的记录数（断点续跑依据）"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(EvalDetail).where(EvalDetail.task_id == task_id)
        )
        count = len(result.scalars().all())
        return count


async def update_task_progress(task_id: int, processed: int, total: int,
                                metrics: dict) -> None:
    """更新任务进度"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        task = await session.get(EvalTask, task_id)
        if task:
            task.progress = int(processed / total * 100) if total > 0 else 0
            task.total_count = total
            task.matched_count = metrics.get('matched', 0)
            task.correct_count = metrics.get('correct', 0)
            task.wrong_count = metrics.get('wrong', 0)
            task.no_match_count = metrics.get('no_match', 0)
            await session.commit()


async def save_detail_batch(task_id: int, details: list[dict]) -> None:
    """批量保存评测明细"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        records = []
        for d in details:
            records.append(EvalDetail(
                task_id=task_id,
                check_item=d['check_item'],
                modality=d['modality'],
                expected_code=d['expected_code'],
                expected_name=d['expected_name'],
                actual_code=d.get('actual_code'),
                actual_name=d.get('actual_name'),
                confidence=Decimal(str(d['confidence'])) if d.get('confidence') else None,
                response_time=Decimal(str(d['response_time'])) if d.get('response_time') else None,
                is_matched=d['is_matched'],
                is_correct=d['is_correct'],
                match_type=d['match_type'],
                failure_reason=d.get('failure_reason'),
                failure_detail=d.get('failure_detail'),
                created_at=datetime.utcnow(),
            ))
        session.add_all(records)
        await session.commit()


async def run_bulk_match(task_id: int, csv_path: str, sample_size: int = None) -> dict:
    """执行批量匹配"""
    # 初始化引擎
    engine_holder = EngineHolder()
    await engine_holder.initialize()

    if not engine_holder.match_engine or not engine_holder.match_engine.is_ready:
        raise RuntimeError("匹配引擎未就绪")

    logger.info(f"✓ 引擎就绪, 规则版本: {engine_holder.rule_version}")

    # 读取数据
    df = pd.read_csv(csv_path)
    logger.info(f"✓ 读取数据集: {len(df)} 条")

    if sample_size and len(df) > sample_size:
        df = df.sample(n=sample_size, random_state=42)
        logger.info(f"  采样: {sample_size} 条")

    # 检查断点续跑
    existing_count = await get_existing_count(task_id)
    if existing_count > 0:
        logger.info(f"✓ 检测到已处理 {existing_count} 条，从断点继续")
        df = df.iloc[existing_count:]

    if len(df) == 0:
        logger.info("  全部已处理，无需继续")
        return {}

    total = existing_count + len(df)

    # 更新任务状态
    session_factory = get_session_factory()
    async with session_factory() as session:
        task = await session.get(EvalTask, task_id)
        task.status = 'running'
        task.started_at = datetime.utcnow()
        task.total_count = total
        await session.commit()

    logger.info(f"✓ 开始匹配: {len(df)} 条待处理")
    logger.info("=" * 70)

    # 统计指标
    metrics = {
        'total': existing_count,
        'matched': 0,
        'correct': 0,
        'wrong': 0,
        'no_match': 0,
        'total_confidence': 0.0,
        'total_response_time': 0.0,
    }

    # 批量处理
    start_time = time.time()
    batch_buffer = []
    batch_num = 0

    orchestrator = engine_holder.match_engine

    for idx, row in df.iterrows():
        metrics['total'] += 1

        check_item = str(row.get('check_item', '')).strip()
        modality = str(row.get('modality', '')).strip()
        expected_code = normalize_code(row.get('expected_standard_code', ''))
        expected_name = str(row.get('expected_standard_name', '')).strip()

        detail = {
            'check_item': check_item,
            'modality': modality,
            'expected_code': expected_code,
            'expected_name': expected_name,
            'is_matched': False,
            'is_correct': False,
            'match_type': 'none',
            'confidence': 0.0,
            'response_time': 0.0,
        }

        if not check_item:
            detail['failure_reason'] = 'empty_input'
            detail['failure_detail'] = '输入为空'
            metrics['no_match'] += 1
            batch_buffer.append(detail)
            continue

        # 执行匹配
        try:
            match_start = time.time()
            match_result = orchestrator.match(check_item, modality)
            response_time = (time.time() - match_start) * 1000

            detail['response_time'] = response_time
            metrics['total_response_time'] += response_time

            # 解析结果
            if match_result and match_result.get('num_standard', 0) > 0:
                metrics['matched'] += 1

                confidence = extract_confidence(match_result)
                detail['confidence'] = confidence
                metrics['total_confidence'] += confidence

                is_correct, match_method, actual_code, actual_name = judge_correctness(
                    match_result, expected_name
                )

                detail['is_matched'] = True
                detail['is_correct'] = is_correct
                detail['match_type'] = match_method
                detail['actual_code'] = actual_code
                detail['actual_name'] = actual_name

                if is_correct:
                    metrics['correct'] += 1
                else:
                    metrics['wrong'] += 1
                    detail['failure_reason'] = 'wrong_match'
                    detail['failure_detail'] = f"期望: {expected_name}, 实际: {actual_name}"
            else:
                # 未匹配
                metrics['no_match'] += 1
                failure_reason = classify_failure(check_item)
                detail['failure_reason'] = failure_reason
                detail['failure_detail'] = f"未匹配到标准项目: {check_item[:50]}"

        except Exception as e:
            logger.error(f"匹配异常: {check_item[:50]}... - {e}", exc_info=False)
            metrics['no_match'] += 1
            detail['failure_reason'] = 'algorithm'
            detail['failure_detail'] = f"算法异常: {str(e)[:200]}"

        batch_buffer.append(detail)

        # 批量提交
        if len(batch_buffer) >= BATCH_SIZE:
            await save_detail_batch(task_id, batch_buffer)
            batch_buffer.clear()
            batch_num += 1

            # 定期更新进度
            if batch_num % PROGRESS_INTERVAL == 0:
                await update_task_progress(task_id, metrics['total'], total, metrics)

                elapsed = time.time() - start_time
                rate = metrics['total'] / elapsed if elapsed > 0 else 0
                eta = (total - metrics['total']) / rate if rate > 0 else 0

                logger.info(
                    f"[{metrics['total']}/{total}] "
                    f"匹配率: {metrics['matched']/metrics['total']*100:.1f}%, "
                    f"准确率: {metrics['correct']/max(metrics['matched'],1)*100:.1f}%, "
                    f"速率: {rate:.1f}/s, "
                    f"ETA: {eta/60:.1f}min"
                )

    # 提交剩余记录
    if batch_buffer:
        await save_detail_batch(task_id, batch_buffer)

    # 最终更新
    await update_task_progress(task_id, metrics['total'], total, metrics)

    # 完成任务
    duration = time.time() - start_time
    match_rate = metrics['matched'] / metrics['total'] * 100 if metrics['total'] > 0 else 0
    accuracy = metrics['correct'] / metrics['matched'] * 100 if metrics['matched'] > 0 else 0

    async with session_factory() as session:
        task = await session.get(EvalTask, task_id)
        task.status = 'completed'
        task.progress = 100
        task.completed_at = datetime.utcnow()
        task.match_rate = Decimal(str(round(match_rate, 2)))
        task.accuracy = Decimal(str(round(accuracy, 2)))
        await session.commit()

    logger.info("=" * 70)
    logger.info(f"✓ 匹配完成: {metrics['total']} 条, 耗时 {duration/60:.1f} 分钟")
    logger.info(f"  匹配率: {match_rate:.2f}%")
    logger.info(f"  准确率: {accuracy:.2f}%")
    logger.info(f"  平均响应: {metrics['total_response_time']/metrics['total']:.1f}ms")

    return {
        'task_id': task_id,
        'total': metrics['total'],
        'matched': metrics['matched'],
        'correct': metrics['correct'],
        'duration': duration,
    }


async def main():
    parser = argparse.ArgumentParser(description="Phase 1: 全量匹配")
    parser.add_argument('--sample', type=int, help='采样数量（冒烟测试用）')
    parser.add_argument('--full', action='store_true', help='全量执行')
    parser.add_argument('--resume', type=int, metavar='TASK_ID', help='恢复中断的任务')
    parser.add_argument('--csv', default=DEFAULT_DATASET, help='CSV 数据路径')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细日志')

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.resume:
        logger.info(f"恢复任务 #{args.resume}")
        task_id = args.resume
    else:
        if not (args.sample or args.full):
            logger.error("请指定 --sample <N> 或 --full")
            return 1

        sample_size = args.sample if args.sample else None
        name = f"Bulk Match {sample_size or '246k'} Benchmark"
        task_id = await create_task(name, args.csv, sample_size)

    await run_bulk_match(task_id, args.csv, args.sample)
    await dispose_engine()

    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))

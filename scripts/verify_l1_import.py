#!/usr/bin/env python3
"""
Phase 4: 导入验证脚本

验证 L1 缓存导入的正确性。

验证项:
1. 数量核对 - match_cache 中 benchmark 记录数
2. 抽样核对 - 随机抽取 1% 逐条验证
3. 冲突记录核对 - match_feedback 的 cache_conflict 记录数
4. 过期时间有效性 - 检查 expires_at 在合理范围
5. 缓存命中测试 - 验证 L1 查询能正确返回
6. Hash 碰撞检测 - 报告碰撞案例

Usage:
    poetry run python scripts/verify_l1_import.py --task-id <id>
"""
import argparse
import asyncio
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select, func, and_

# 添加 src 到路径
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from match_service.cache.models import MatchCache, MatchFeedback
from match_service.cache.service import CacheService
from match_service.config import get_settings
from match_service.db import get_session_factory, dispose_engine
from match_service.models.evaluation import EvalDetail

from bulk_match_common import setup_logging, logger, MIN_CONFIDENCE, OUTPUT_DIR


async def verify_count() -> dict:
    """验证 1: 数量核对"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        # match_cache 中 benchmark 记录数
        cache_result = await session.execute(
            select(func.count(MatchCache.id)).where(MatchCache.source == 'benchmark')
        )
        cache_count = cache_result.scalar()

        # import_summary.json 的记录数
        summary_file = OUTPUT_DIR / "import_summary.json"
        if summary_file.exists():
            summary = json.loads(summary_file.read_text())
            expected = summary.get('inserted', 0) + summary.get('updated', 0)
        else:
            expected = None

        return {
            'cache_count': cache_count,
            'expected': expected,
            'passed': cache_count == expected if expected is not None else None,
        }


async def verify_samples(task_id: int, sample_rate: float = 0.01) -> dict:
    """验证 2: 抽样核对"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        # 获取符合条件的记录
        query = select(EvalDetail).where(
            and_(
                EvalDetail.task_id == task_id,
                EvalDetail.is_correct == True,
                EvalDetail.confidence >= MIN_CONFIDENCE,
                EvalDetail.actual_code.isnot(None),
            )
        )
        result = await session.execute(query)
        details = result.scalars().all()

        sample_size = max(1, int(len(details) * sample_rate))
        samples = random.sample(list(details), min(sample_size, len(details)))

        passed = 0
        failed = 0
        errors = []

        for d in samples:
            text_hash = MatchCache.compute_hash(d.check_item, d.modality)
            cache_result = await session.execute(
                select(MatchCache).where(
                    and_(
                        MatchCache.text_hash == text_hash,
                        MatchCache.modality == d.modality.upper(),
                    )
                )
            )
            cache_row = cache_result.scalar_one_or_none()

            if cache_row is None:
                failed += 1
                errors.append(f"记录不存在: {d.check_item[:50]}")
                continue

            # 验证字段
            result_json = json.loads(cache_row.result_json)
            expected_code = d.actual_code

            if not result_json.get('data'):
                failed += 1
                errors.append(f"result_json.data 为空: {d.check_item[:50]}")
                continue

            actual_code = result_json['data'][0]['standard'][0]['code']

            if actual_code != expected_code:
                failed += 1
                errors.append(
                    f"编码不匹配: {d.check_item[:30]} - "
                    f"期望 {expected_code}, 实际 {actual_code}"
                )
            else:
                passed += 1

        return {
            'total_samples': len(samples),
            'passed': passed == len(samples) and failed == 0,
            'passed_count': passed,
            'failed': failed,
            'errors': errors[:10],  # 最多显示 10 条错误
        }


async def verify_conflicts() -> dict:
    """验证 3: 冲突记录核对"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        # match_feedback 中 cache_conflict 记录数
        feedback_result = await session.execute(
            select(func.count(MatchFeedback.id)).where(
                MatchFeedback.feedback_type == 'cache_conflict'
            )
        )
        feedback_count = feedback_result.scalar()

        # import_summary.json 的冲突数
        summary_file = OUTPUT_DIR / "import_summary.json"
        if summary_file.exists():
            summary = json.loads(summary_file.read_text())
            expected = summary.get('conflicts', 0)
        else:
            expected = None

        return {
            'feedback_count': feedback_count,
            'expected': expected,
            'passed': feedback_count == expected if expected is not None else None,
        }


async def verify_expires_at() -> dict:
    """验证 4: 过期时间有效性"""
    settings = get_settings()
    ttl = settings.MATCH_CACHE_TTL
    session_factory = get_session_factory()

    async with session_factory() as session:
        query = select(MatchCache).where(
            MatchCache.source == 'benchmark'
        ).limit(10)

        result = await session.execute(query)
        samples = result.scalars().all()

        passed = 0
        failed = 0
        errors = []

        now = datetime.utcnow()
        max_expires = now + timedelta(seconds=ttl)

        for row in samples:
            if row.expires_at is None:
                failed += 1
                errors.append(f"expires_at 为空: {row.original_text[:30]}")
            elif row.expires_at <= now:
                failed += 1
                errors.append(f"已过期: {row.original_text[:30]}")
            elif row.expires_at > max_expires + timedelta(hours=1):
                failed += 1
                errors.append(f"过期时间异常: {row.original_text[:30]}")
            else:
                passed += 1

        return {
            'total_samples': len(samples),
            'passed': passed == len(samples) and failed == 0,
            'passed_count': passed,
            'failed': failed,
            'errors': errors,
        }


async def verify_cache_hit(task_id: int, sample_size: int = 20) -> dict:
    """验证 5: 缓存命中测试"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        # 获取已导入的记录样本
        query = select(EvalDetail).where(
            and_(
                EvalDetail.task_id == task_id,
                EvalDetail.is_correct == True,
                EvalDetail.confidence >= MIN_CONFIDENCE,
                EvalDetail.actual_code.isnot(None),
            )
        ).limit(sample_size)

        result = await session.execute(query)
        details = result.scalars().all()

        cache_service = CacheService(session)
        passed = 0
        failed = 0
        errors = []

        for d in details:
            cached = await cache_service.lookup(d.check_item, d.modality)

            if cached is None:
                failed += 1
                errors.append(f"未命中: {d.check_item[:50]}")
            elif not cached.get('_cache_hit'):
                failed += 1
                errors.append(f"_cache_hit=False: {d.check_item[:50]}")
            elif cached.get('_cache_source') != 'benchmark':
                failed += 1
                errors.append(f"source 错误: {d.check_item[:50]}")
            else:
                passed += 1

        return {
            'total_samples': len(details),
            'passed': passed == len(details) and failed == 0,
            'passed_count': passed,
            'failed': failed,
            'errors': errors,
        }


async def verify_hash_collisions() -> dict:
    """验证 6: Hash 碰撞检测"""
    summary_file = OUTPUT_DIR / "import_summary.json"
    if not summary_file.exists():
        return {'collisions': None, 'passed': None}

    summary = json.loads(summary_file.read_text())
    collisions = summary.get('hash_collisions', 0)

    return {
        'collisions': collisions,
        'passed': collisions == 0,
    }


async def main():
    parser = argparse.ArgumentParser(description="Phase 4: 导入验证")
    parser.add_argument('--task-id', type=int, required=True, help='评测任务 ID')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细日志')

    args = parser.parse_args()
    setup_logging(args.verbose)

    logger.info(f"开始验证 L1 导入结果: Task #{args.task_id}")
    logger.info("=" * 70)

    # 执行所有验证
    results = {}

    logger.info("验证 1: 数量核对...")
    results['count'] = await verify_count()
    if results['count']['passed']:
        logger.info(f"  ✓ 通过 - cache={results['count']['cache_count']}, expected={results['count']['expected']}")
    else:
        logger.error(f"  ✗ 失败 - cache={results['count']['cache_count']}, expected={results['count']['expected']}")

    logger.info("验证 2: 抽样核对 (1%)...")
    results['samples'] = await verify_samples(args.task_id, 0.01)
    if results['samples']['passed']:
        logger.info(f"  ✓ 通过 - {results['samples']['passed_count']}/{results['samples']['total_samples']} 条")
    else:
        logger.error(f"  ✗ 失败 - {results['samples']['failed']} 条有误")
        for err in results['samples']['errors']:
            logger.error(f"    {err}")

    logger.info("验证 3: 冲突记录核对...")
    results['conflicts'] = await verify_conflicts()
    if results['conflicts']['passed']:
        logger.info(f"  ✓ 通过 - feedback={results['conflicts']['feedback_count']}, expected={results['conflicts']['expected']}")
    else:
        logger.error(f"  ✗ 失败 - feedback={results['conflicts']['feedback_count']}, expected={results['conflicts']['expected']}")

    logger.info("验证 4: 过期时间有效性...")
    results['expires'] = await verify_expires_at()
    if results['expires']['passed']:
        logger.info(f"  ✓ 通过 - {results['expires']['passed_count']}/{results['expires']['total_samples']} 条")
    else:
        logger.error(f"  ✗ 失败 - {results['expires']['failed']} 条有误")
        for err in results['expires']['errors']:
            logger.error(f"    {err}")

    logger.info("验证 5: 缓存命中测试...")
    results['cache_hit'] = await verify_cache_hit(args.task_id, 20)
    if results['cache_hit']['passed']:
        logger.info(f"  ✓ 通过 - {results['cache_hit']['passed_count']}/{results['cache_hit']['total_samples']} 条")
    else:
        logger.error(f"  ✗ 失败 - {results['cache_hit']['failed']} 条有误")
        for err in results['cache_hit']['errors']:
            logger.error(f"    {err}")

    logger.info("验证 6: Hash 碰撞检测...")
    results['collisions'] = await verify_hash_collisions()
    if results['collisions']['passed']:
        logger.info(f"  ✓ 通过 - 无碰撞")
    elif results['collisions']['collisions'] is not None:
        logger.warning(f"  ⚠ {results['collisions']['collisions']} 次碰撞")
    else:
        logger.warning(f"  ⚠ 无摘要文件，跳过检查")

    # 总结
    logger.info("=" * 70)

    # 调试：输出所有结果
    for key, val in results.items():
        logger.debug(f"验证项 {key}: passed={val.get('passed')}, type={type(val.get('passed'))}")

    passed_count = sum(1 for r in results.values() if r.get('passed') is True)
    total_count = sum(1 for r in results.values() if r.get('passed') is not None)

    if passed_count == total_count:
        logger.info(f"✓ 全部验证通过 ({passed_count}/{total_count})")
        exit_code = 0
    else:
        logger.error(f"✗ 部分验证失败 ({passed_count}/{total_count})")
        exit_code = 1

    await dispose_engine()
    return exit_code


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))

#!/usr/bin/env python3
"""
Phase 3: L1 缓存导入脚本

从 mms_eval_details 筛选高质量记录导入 match_cache。

筛选条件:
- is_correct = true
- confidence >= 0.8
- actual_code 非空

冲突处理:
- 记录存在且未过期 → 保留旧值，写 match_feedback
- 记录存在但已过期 → 更新为新值
- 记录不存在 → 插入新值

Usage:
    poetry run python scripts/import_to_l1_cache.py --task-id <id>
    poetry run python scripts/import_to_l1_cache.py --task-id 1 --dry-run
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select, and_

# 添加 src 到路径
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from match_service.cache.models import MatchCache, MatchFeedback
from match_service.config import get_settings
from match_service.db import get_session_factory, dispose_engine
from match_service.models.evaluation import EvalDetail

from bulk_match_common import (
    setup_logging, logger, MIN_CONFIDENCE,
    build_result_json, OUTPUT_DIR
)


async def fetch_qualified_records(task_id: int) -> list[dict]:
    """
    筛选符合导入条件的记录

    条件: is_correct=true AND confidence>=0.8 AND actual_code IS NOT NULL
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
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

        records = []
        for d in details:
            records.append({
                'check_item': d.check_item,
                'modality': d.modality,
                'actual_code': d.actual_code,
                'actual_name': d.actual_name,
                'confidence': float(d.confidence),
                'match_type': d.match_type,
            })

        return records


async def import_to_cache(records: list[dict], dry_run: bool = False) -> dict:
    """
    导入到 match_cache

    Returns:
        统计摘要: {inserted, updated, skipped, conflicts, hash_collisions}
    """
    settings = get_settings()
    ttl = settings.MATCH_CACHE_TTL  # 默认 30 天

    stats = {
        'total': len(records),
        'inserted': 0,
        'updated': 0,
        'skipped': 0,
        'conflicts': 0,
        'hash_collisions': 0,
    }

    if dry_run:
        logger.info("DRY RUN 模式：仅模拟，不实际写入")

    session_factory = get_session_factory()
    async with session_factory() as session:
        for i, rec in enumerate(records, 1):
            check_item = rec['check_item']
            modality = rec['modality']
            text_hash = MatchCache.compute_hash(check_item, modality)

            # 查询是否存在
            existing = await session.execute(
                select(MatchCache).where(
                    and_(
                        MatchCache.text_hash == text_hash,
                        MatchCache.modality == modality.upper(),
                    )
                )
            )
            existing_row = existing.scalar_one_or_none()

            # 构造 result_json
            result_json_data = build_result_json(
                check_item,
                rec['actual_code'],
                rec['actual_name'],
                rec['confidence'],
                rec['match_type']
            )
            result_json_str = MatchCache.make_result_json(result_json_data)

            if existing_row is None:
                # 情况 1: 不存在，插入
                if not dry_run:
                    new_row = MatchCache(
                        text_hash=text_hash,
                        modality=modality.upper(),
                        original_text=check_item,
                        result_json=result_json_str,
                        confidence=rec['confidence'],
                        source='benchmark',
                        expires_at=datetime.utcnow() + timedelta(seconds=ttl),
                    )
                    session.add(new_row)
                stats['inserted'] += 1

            elif existing_row.expires_at and existing_row.expires_at <= datetime.utcnow():
                # 情况 3: 存在但已过期，更新
                if not dry_run:
                    existing_row.result_json = result_json_str
                    existing_row.confidence = rec['confidence']
                    existing_row.source = 'benchmark'
                    existing_row.confirmed_at = datetime.utcnow()
                    existing_row.expires_at = datetime.utcnow() + timedelta(seconds=ttl)
                stats['updated'] += 1

            else:
                # 情况 2: 存在且未过期，保留旧值，记录冲突
                stats['skipped'] += 1

                # 检查是否 hash 碰撞（不同原文映射到同一 hash）
                if existing_row.original_text.strip().lower().replace(" ", "") != \
                   check_item.strip().lower().replace(" ", ""):
                    stats['hash_collisions'] += 1
                    logger.warning(
                        f"Hash 碰撞: [{check_item}] vs [{existing_row.original_text}]"
                    )

                # 写入 match_feedback
                if not dry_run:
                    conflict_feedback = MatchFeedback(
                        text_hash=text_hash,
                        modality=modality.upper(),
                        original_text=check_item,
                        engine_result_json=result_json_str,
                        engine_tier=rec['match_type'],
                        feedback_type='cache_conflict',
                        suggested_fix=json.dumps({
                            'old_source': existing_row.source,
                            'old_confidence': existing_row.confidence,
                            'new_confidence': rec['confidence'],
                            'new_tier': rec['match_type'],
                        }, ensure_ascii=False),
                        status='pending',
                    )
                    session.add(conflict_feedback)
                stats['conflicts'] += 1

            # 批量提交
            if i % 100 == 0:
                if not dry_run:
                    await session.commit()
                logger.info(
                    f"进度: {i}/{len(records)} - "
                    f"插入={stats['inserted']}, 更新={stats['updated']}, "
                    f"跳过={stats['skipped']}, 冲突={stats['conflicts']}"
                )

        # 最终提交
        if not dry_run:
            await session.commit()

    return stats


async def main():
    parser = argparse.ArgumentParser(description="Phase 3: L1 缓存导入")
    parser.add_argument('--task-id', type=int, required=True, help='评测任务 ID')
    parser.add_argument('--dry-run', action='store_true', help='仅模拟，不实际写入')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细日志')

    args = parser.parse_args()
    setup_logging(args.verbose)

    logger.info(f"筛选高质量记录: Task #{args.task_id}")
    records = await fetch_qualified_records(args.task_id)
    logger.info(f"✓ 符合条件: {len(records)} 条 (confidence >= {MIN_CONFIDENCE}, is_correct = true)")

    if len(records) == 0:
        logger.warning("无符合条件的记录，跳过导入")
        return 0

    logger.info("开始导入 match_cache...")
    logger.info("=" * 70)
    stats = await import_to_cache(records, args.dry_run)

    logger.info("=" * 70)
    logger.info(f"✓ 导入完成")
    logger.info(f"  符合条件: {stats['total']}")
    logger.info(f"  插入新记录: {stats['inserted']}")
    logger.info(f"  更新过期记录: {stats['updated']}")
    logger.info(f"  跳过未过期: {stats['skipped']}")
    logger.info(f"  冲突记录: {stats['conflicts']}")
    if stats['hash_collisions'] > 0:
        logger.warning(f"  Hash 碰撞: {stats['hash_collisions']} (见上方详情)")

    # 保存摘要
    if not args.dry_run:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        summary_file = OUTPUT_DIR / "import_summary.json"
        summary_file.write_text(
            json.dumps(stats, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        logger.info(f"✓ 摘要已保存: {summary_file}")

    await dispose_engine()
    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))

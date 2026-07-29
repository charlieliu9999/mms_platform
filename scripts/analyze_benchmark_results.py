#!/usr/bin/env python3
"""
Phase 2: 结果分析脚本

从 mms_eval_details 生成 Markdown 分析报告。

Usage:
    poetry run python scripts/analyze_benchmark_results.py --task-id <id>
    poetry run python scripts/analyze_benchmark_results.py --task-id 1 --output custom_report.md
"""
import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, func, and_

# 添加 src 到路径
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from match_service.db import get_session_factory, dispose_engine
from match_service.models.evaluation import EvalTask, EvalDetail

from bulk_match_common import setup_logging, logger, percentile


async def load_task_summary(task_id: int) -> dict:
    """加载任务摘要"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        task = await session.get(EvalTask, task_id)
        if not task:
            raise ValueError(f"Task #{task_id} not found")

        return {
            'id': task.id,
            'name': task.name,
            'total': task.total_count or 0,
            'matched': task.matched_count or 0,
            'correct': task.correct_count or 0,
            'wrong': task.wrong_count or 0,
            'no_match': task.no_match_count or 0,
            'match_rate': float(task.match_rate) if task.match_rate else 0.0,
            'accuracy': float(task.accuracy) if task.accuracy else 0.0,
            'created_at': task.created_at,
            'completed_at': task.completed_at,
        }


async def analyze_by_modality(task_id: int) -> list[dict]:
    """按模态统计"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        query = select(
            EvalDetail.modality,
            func.count(EvalDetail.id).label('total'),
            func.sum(func.cast(EvalDetail.is_matched, func.Integer)).label('matched'),
            func.sum(func.cast(EvalDetail.is_correct, func.Integer)).label('correct'),
            func.avg(EvalDetail.confidence).label('avg_conf'),
        ).where(EvalDetail.task_id == task_id).group_by(EvalDetail.modality)

        result = await session.execute(query)
        rows = result.all()

        stats = []
        for row in rows:
            total = row.total or 0
            matched = row.matched or 0
            correct = row.correct or 0

            match_rate = matched / total * 100 if total > 0 else 0
            accuracy = correct / matched * 100 if matched > 0 else 0
            recall = correct / total * 100 if total > 0 else 0
            precision = correct / matched * 100 if matched > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            stats.append({
                'modality': row.modality,
                'total': total,
                'matched': matched,
                'correct': correct,
                'match_rate': match_rate,
                'accuracy': accuracy,
                'f1': f1,
                'avg_conf': float(row.avg_conf) if row.avg_conf else 0.0,
            })

        return sorted(stats, key=lambda x: x['total'], reverse=True)


async def analyze_failure_reasons(task_id: int) -> list[dict]:
    """失败原因分类统计"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        query = select(
            EvalDetail.failure_reason,
            func.count(EvalDetail.id).label('count'),
        ).where(
            and_(
                EvalDetail.task_id == task_id,
                EvalDetail.is_correct == False,
            )
        ).group_by(EvalDetail.failure_reason).order_by(func.count(EvalDetail.id).desc())

        result = await session.execute(query)
        rows = result.all()

        total_failures = sum(row.count for row in rows)
        return [
            {
                'reason': row.failure_reason or 'unknown',
                'count': row.count,
                'percent': row.count / total_failures * 100 if total_failures > 0 else 0,
            }
            for row in rows
        ]


async def get_top_failures(task_id: int, limit: int = 20) -> list[dict]:
    """Top N 高频失败案例"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        query = select(
            EvalDetail.check_item,
            EvalDetail.modality,
            EvalDetail.expected_name,
            EvalDetail.actual_name,
            EvalDetail.failure_reason,
            func.count(EvalDetail.id).label('count'),
        ).where(
            and_(
                EvalDetail.task_id == task_id,
                EvalDetail.is_correct == False,
            )
        ).group_by(
            EvalDetail.check_item,
            EvalDetail.modality,
            EvalDetail.expected_name,
            EvalDetail.actual_name,
            EvalDetail.failure_reason,
        ).order_by(func.count(EvalDetail.id).desc()).limit(limit)

        result = await session.execute(query)
        rows = result.all()

        return [
            {
                'check_item': row.check_item,
                'modality': row.modality,
                'expected': row.expected_name,
                'actual': row.actual_name or '(未匹配)',
                'reason': row.failure_reason,
                'count': row.count,
            }
            for row in rows
        ]


async def analyze_confidence_distribution(task_id: int) -> list[dict]:
    """置信度分布"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        query = select(EvalDetail.confidence).where(
            and_(
                EvalDetail.task_id == task_id,
                EvalDetail.is_matched == True,
            )
        )
        result = await session.execute(query)
        confidences = [float(row[0]) for row in result.all() if row[0] is not None]

        bins = [
            ('0.0-0.2', 0.0, 0.2),
            ('0.2-0.4', 0.2, 0.4),
            ('0.4-0.6', 0.4, 0.6),
            ('0.6-0.8', 0.6, 0.8),
            ('0.8-1.0', 0.8, 1.0),
        ]

        distribution = []
        for label, low, high in bins:
            count = sum(1 for c in confidences if low <= c < high)
            if label == '0.8-1.0':  # 闭区间
                count = sum(1 for c in confidences if low <= c <= high)
            distribution.append({'range': label, 'count': count})

        return distribution


async def analyze_response_time(task_id: int) -> dict:
    """响应时间分析"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        query = select(EvalDetail.response_time).where(
            and_(
                EvalDetail.task_id == task_id,
                EvalDetail.response_time.isnot(None),
            )
        ).order_by(EvalDetail.response_time)

        result = await session.execute(query)
        times = [float(row[0]) for row in result.all()]

        if not times:
            return {'avg': 0, 'p50': 0, 'p95': 0, 'slowest': []}

        return {
            'avg': sum(times) / len(times),
            'p50': percentile(times, 0.5),
            'p95': percentile(times, 0.95),
            'slowest': times[-10:],  # 最慢的10条
        }


async def generate_report(task_id: int, output_path: str) -> None:
    """生成 Markdown 报告"""
    logger.info(f"生成分析报告: Task #{task_id}")

    # 收集数据
    task_summary = await load_task_summary(task_id)
    modality_stats = await analyze_by_modality(task_id)
    failure_reasons = await analyze_failure_reasons(task_id)
    top_failures = await get_top_failures(task_id, 20)
    confidence_dist = await analyze_confidence_distribution(task_id)
    response_time = await analyze_response_time(task_id)

    # 生成报告
    lines = []
    lines.append(f"# 24.6万条全量匹配分析报告")
    lines.append(f"")
    lines.append(f"**任务**: #{task_summary['id']} - {task_summary['name']}")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**执行时间**: {task_summary['created_at']} ~ {task_summary['completed_at']}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # 1. 总体指标
    lines.append(f"## 1. 总体指标")
    lines.append(f"")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 总记录数 | {task_summary['total']:,} |")
    lines.append(f"| 匹配成功 | {task_summary['matched']:,} ({task_summary['match_rate']:.2f}%) |")
    lines.append(f"| 匹配正确 | {task_summary['correct']:,} ({task_summary['accuracy']:.2f}%) |")
    lines.append(f"| 匹配错误 | {task_summary['wrong']:,} |")
    lines.append(f"| 未匹配 | {task_summary['no_match']:,} |")
    lines.append(f"")

    # 2. 按模态统计
    lines.append(f"## 2. 按模态统计")
    lines.append(f"")
    lines.append(f"| 模态 | 数量 | 匹配率 | 准确率 | F1 | 平均置信度 |")
    lines.append(f"|------|------|--------|--------|-----|------------|")
    for s in modality_stats:
        lines.append(
            f"| {s['modality']} | {s['total']:,} | {s['match_rate']:.1f}% | "
            f"{s['accuracy']:.1f}% | {s['f1']:.2f} | {s['avg_conf']:.3f} |"
        )
    lines.append(f"")

    # 3. 失败原因分类
    lines.append(f"## 3. 失败原因分类")
    lines.append(f"")
    lines.append(f"| 原因 | 数量 | 占比 |")
    lines.append(f"|------|------|------|")
    for r in failure_reasons:
        lines.append(f"| {r['reason']} | {r['count']:,} | {r['percent']:.1f}% |")
    lines.append(f"")

    # 4. Top 20 高频失败案例
    lines.append(f"## 4. Top 20 高频失败案例")
    lines.append(f"")
    for i, f in enumerate(top_failures, 1):
        lines.append(f"{i}. **{f['check_item'][:60]}** ({f['modality']})")
        lines.append(f"   - 期望: {f['expected']}")
        lines.append(f"   - 实际: {f['actual']}")
        lines.append(f"   - 原因: {f['reason']}")
        lines.append(f"")

    # 5. 置信度分布
    lines.append(f"## 5. 置信度分布")
    lines.append(f"")
    lines.append(f"| 区间 | 数量 |")
    lines.append(f"|------|------|")
    for d in confidence_dist:
        lines.append(f"| {d['range']} | {d['count']:,} |")
    lines.append(f"")

    # 6. 响应时间分析
    lines.append(f"## 6. 性能分析")
    lines.append(f"")
    lines.append(f"| 指标 | 数值 (ms) |")
    lines.append(f"|------|----------|")
    lines.append(f"| 平均响应时间 | {response_time['avg']:.1f} |")
    lines.append(f"| P50 | {response_time['p50']:.1f} |")
    lines.append(f"| P95 | {response_time['p95']:.1f} |")
    lines.append(f"")
    lines.append(f"**最慢10条**: {', '.join(f'{t:.0f}ms' for t in response_time['slowest'][-10:])}")
    lines.append(f"")

    # 写入文件
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text('\n'.join(lines), encoding='utf-8')

    logger.info(f"✓ 报告已保存: {output_file}")


async def main():
    parser = argparse.ArgumentParser(description="Phase 2: 结果分析")
    parser.add_argument('--task-id', type=int, required=True, help='评测任务 ID')
    parser.add_argument('--output', default='docs/reports/2026-07-29-bulk-match-246k-report.md',
                        help='输出报告路径')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细日志')

    args = parser.parse_args()
    setup_logging(args.verbose)

    await generate_report(args.task_id, args.output)
    await dispose_engine()

    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))

#!/usr/bin/env python3
"""
分析评测任务的失败案例
生成详细的失败分析报告
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from collections import defaultdict
import json

# 数据库连接
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/mms_db"


async def analyze_failures(task_id: int):
    """分析失败案例"""

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 查询所有未匹配的案例
        result = await session.execute(text("""
            SELECT
                id, check_item, modality,
                expected_code, expected_name,
                actual_code, actual_name,
                match_status, confidence
            FROM evaluation_test_cases
            WHERE task_id = :task_id AND match_status = 'no_match'
            ORDER BY modality, check_item
        """), {'task_id': task_id})

        no_match_cases = [dict(row._mapping) for row in result]

        print(f"\n📊 未匹配案例总数: {len(no_match_cases)}")

        # 按模态分组统计
        by_modality = defaultdict(list)
        for case in no_match_cases:
            by_modality[case['modality']].append(case)

        print(f"\n📋 按模态分布:")
        print(f"{'模态':<10} {'未匹配数':<10} {'样例'}")
        print("-" * 80)
        for modality in sorted(by_modality.keys(), key=lambda x: len(by_modality[x]), reverse=True):
            cases = by_modality[modality]
            sample = cases[0]['check_item'][:30]
            print(f"{modality:<10} {len(cases):<10} {sample}")

        # 查询所有匹配成功的案例
        result = await session.execute(text("""
            SELECT
                modality,
                COUNT(*) as total,
                COUNT(CASE WHEN match_status = 'matched' THEN 1 END) as matched,
                COUNT(CASE WHEN match_status = 'matched' AND actual_code = expected_code THEN 1 END) as correct
            FROM evaluation_test_cases
            WHERE task_id = :task_id
            GROUP BY modality
            ORDER BY total DESC
        """), {'task_id': task_id})

        modality_stats = [dict(row._mapping) for row in result]

        print(f"\n\n📈 各模态匹配表现:")
        print(f"{'模态':<10} {'总数':<8} {'匹配数':<8} {'正确数':<8} {'匹配率':<10} {'准确率':<10}")
        print("-" * 80)

        for stat in modality_stats:
            modality = stat['modality']
            total = stat['total']
            matched = stat['matched']
            correct = stat['correct']

            match_rate = matched / total * 100 if total > 0 else 0
            accuracy = correct / matched * 100 if matched > 0 else 0

            print(f"{modality:<10} {total:<8} {matched:<8} {correct:<8} {match_rate:>6.1f}%    {accuracy:>6.1f}%")

        # 查找高频未匹配项目
        print(f"\n\n🔍 高频未匹配项目（出现次数>=3）:")
        result = await session.execute(text("""
            SELECT
                check_item, modality, COUNT(*) as count
            FROM evaluation_test_cases
            WHERE task_id = :task_id AND match_status = 'no_match'
            GROUP BY check_item, modality
            HAVING COUNT(*) >= 3
            ORDER BY count DESC, modality, check_item
            LIMIT 30
        """), {'task_id': task_id})

        freq_items = [dict(row._mapping) for row in result]

        print(f"{'项目名称':<40} {'模态':<8} {'出现次数'}")
        print("-" * 80)
        for item in freq_items:
            name = item['check_item'][:38]
            print(f"{name:<40} {item['modality']:<8} {item['count']}")

        # 生成JSON报告
        report = {
            'task_id': task_id,
            'summary': {
                'total_no_match': len(no_match_cases),
                'modalities': len(by_modality),
            },
            'by_modality': {
                modality: {
                    'count': len(cases),
                    'samples': [c['check_item'] for c in cases[:5]]
                }
                for modality, cases in by_modality.items()
            },
            'modality_performance': [
                {
                    'modality': s['modality'],
                    'total': s['total'],
                    'matched': s['matched'],
                    'correct': s['correct'],
                    'match_rate': round(s['matched'] / s['total'] * 100, 2) if s['total'] > 0 else 0,
                    'accuracy': round(s['correct'] / s['matched'] * 100, 2) if s['matched'] > 0 else 0,
                }
                for s in modality_stats
            ],
            'frequent_failures': [
                {
                    'check_item': item['check_item'],
                    'modality': item['modality'],
                    'count': item['count']
                }
                for item in freq_items
            ]
        }

        # 保存报告
        with open('data/eval_tasks/failure_analysis_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n\n✅ 详细报告已保存到: data/eval_tasks/failure_analysis_report.json")

    await engine.dispose()
    return report


if __name__ == "__main__":
    report = asyncio.run(analyze_failures(task_id=2))

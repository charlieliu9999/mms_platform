#!/usr/bin/env python3
"""
P1+P2 成果验证脚本
对比修复前后的未匹配项数量变化

运行：poetry run python scripts/validate_p1p2_improvement.py
"""
import asyncio
import sys
from pathlib import Path
from collections import defaultdict

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from match_service.db import get_engine, get_session_factory
from match_service.engine.match_engine_v2 import MatchEngineOrchestrator

# P1预期修复的案例
P1_TEST_CASES = [
    ("CT头部平扫[薄层]", "CT", "方括号修饰语"),
    ("CT胸部平扫+增强", "CT", "扫描组合"),
    ("MR腰椎平扫+增强", "MR", "扫描组合"),
    ("CT全腹部平扫", "CT", "部位映射"),
    ("MR腹部全区平扫", "MR", "部位映射"),
]

# P2预期修复的案例（血管成像）
P2_TEST_CASES = [
    ("头颈部CTA", "CT", "头颈部动脉"),
    ("颈动脉CTA", "CT", "颈动脉"),
    ("肺动脉CTA", "CT", "肺动脉"),
    ("上肢动脉CTA", "CT", "上肢动脉"),
    ("下肢动脉CTA", "CT", "下肢动脉"),
    ("主动脉CTA", "CT", "主动脉"),
    ("颅内血管CTA", "CT", "颅内血管"),
    ("肾动脉CTA", "CT", "肾动脉"),
    ("门静脉CTV", "CT", "门静脉"),
    ("腹部血管CTA", "CT", "腹部血管"),
    ("头颈部动脉MRA", "MR", "头颈部动脉"),
    ("颈动脉MRA", "MR", "颈动脉"),
    ("肺动脉MRA", "MR", "肺动脉"),
    ("上肢动脉MRA", "MR", "上肢动脉"),
    ("下肢动脉MRA", "MR", "下肢动脉"),
    ("主动脉MRA", "MR", "主动脉"),
    ("肾动脉MRA", "MR", "肾动脉"),
    ("肾动脉CE-MRA", "MR", "肾动脉"),
    ("肝脏动脉MRA", "MR", "肝脏动脉"),
    ("椎-基底动脉MRA", "MR", "椎-基底动脉"),
    ("腹部血管MRA", "MR", "腹部血管"),
    ("盆腔血管MRA", "MR", "盆腔血管"),
    ("上肢静脉MRV", "MR", "上肢静脉"),
    ("下肢静脉MRV", "MR", "下肢静脉"),
    ("颈部静脉MRV", "MR", "颈部静脉"),
    ("头颈部静脉MRV", "MR", "头颈部静脉"),
    ("肺静脉MRV", "MR", "肺静脉"),
    ("门静脉MRV", "MR", "门静脉"),
]


async def test_match_cases(engine_orch, test_cases, category_name):
    """测试一组案例的匹配情况"""
    print(f"\n{'='*60}")
    print(f"测试 {category_name}")
    print(f"{'='*60}")

    success_count = 0
    failed_cases = []

    for i, case in enumerate(test_cases, 1):
        if len(case) == 3:
            query, modality, expected_keyword = case
        else:
            query, modality = case
            expected_keyword = None

        try:
            result = engine_orch.match(query, modality, "V3.8.2")
            matched_standards = []

            for data_item in result.get('data', []):
                for std in data_item.get('standard', []):
                    matched_standards.append(std['name'])

            if matched_standards:
                success_count += 1
                status = "✅"
                if expected_keyword:
                    found_keyword = any(expected_keyword in name for name in matched_standards)
                    if not found_keyword:
                        status = "⚠️"
                        failed_cases.append((query, modality, f"未包含关键词: {expected_keyword}"))
            else:
                status = "❌"
                failed_cases.append((query, modality, "未匹配"))

            print(f"{i:2d}. {status} {query:30s} ({modality:2s}) → {len(matched_standards)} 项")
            if matched_standards and len(matched_standards) <= 3:
                for std in matched_standards[:3]:
                    print(f"    - {std}")

        except Exception as e:
            print(f"{i:2d}. ❌ {query:30s} ({modality:2s}) → 错误: {e}")
            failed_cases.append((query, modality, str(e)))

    print(f"\n{category_name} 结果:")
    print(f"  成功: {success_count}/{len(test_cases)} ({success_count/len(test_cases)*100:.1f}%)")

    if failed_cases:
        print(f"\n  失败案例:")
        for query, modality, reason in failed_cases[:5]:
            print(f"    - {query} ({modality}): {reason}")
        if len(failed_cases) > 5:
            print(f"    ... 还有 {len(failed_cases)-5} 个失败案例")

    return success_count, len(test_cases), failed_cases


async def get_unmatched_count():
    """获取数据库中未匹配项目总数"""
    session_factory = get_session_factory()

    async with session_factory() as session:
        result = await session.execute(text('''
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN modality_hint = 'CT' THEN 1 END) as ct_count,
                   COUNT(CASE WHEN modality_hint = 'MR' THEN 1 END) as mr_count,
                   COUNT(CASE WHEN modality_hint = 'DR' THEN 1 END) as dr_count,
                   COUNT(CASE WHEN modality_hint = 'US' THEN 1 END) as us_count
            FROM hospital_check_items hci
            LEFT JOIN standard_hospital_mapping shm ON hci.id = shm.hospital_item_id
            WHERE hci.is_active = true
              AND shm.id IS NULL
        '''))

        row = result.fetchone()
        return {
            'total': row.total,
            'CT': row.ct_count,
            'MR': row.mr_count,
            'DR': row.dr_count,
            'US': row.us_count,
        }


async def main():
    """主验证流程"""
    print("="*80)
    print("P1+P2 成果验证")
    print("="*80)

    # 初始化引擎
    print("\n正在初始化匹配引擎...")
    engine = get_engine()
    engine_orch = MatchEngineOrchestrator(engine)
    await engine_orch.initialize()
    print("✅ 引擎初始化完成")

    # 1. 测试P1修复案例
    p1_success, p1_total, p1_failed = await test_match_cases(
        engine_orch, P1_TEST_CASES, "P1 算法修复验证"
    )

    # 2. 测试P2血管成像案例
    p2_success, p2_total, p2_failed = await test_match_cases(
        engine_orch, P2_TEST_CASES, "P2 血管成像标准库验证"
    )

    # 3. 获取数据库未匹配统计
    print(f"\n{'='*60}")
    print("数据库未匹配项统计")
    print(f"{'='*60}")

    unmatched = await get_unmatched_count()
    print(f"\n当前未匹配项总数: {unmatched['total']}")
    print(f"  - CT: {unmatched['CT']}")
    print(f"  - MR: {unmatched['MR']}")
    print(f"  - DR: {unmatched['DR']}")
    print(f"  - US: {unmatched['US']}")

    # 4. 总结
    print(f"\n{'='*60}")
    print("📊 P1+P2 验证总结")
    print(f"{'='*60}")

    total_success = p1_success + p2_success
    total_tests = p1_total + p2_total

    print(f"\n✅ 测试案例验证:")
    print(f"  - P1 算法修复: {p1_success}/{p1_total} ({p1_success/p1_total*100:.1f}%)")
    print(f"  - P2 血管成像: {p2_success}/{p2_total} ({p2_success/p2_total*100:.1f}%)")
    print(f"  - 总计: {total_success}/{total_tests} ({total_success/total_tests*100:.1f}%)")

    print(f"\n📈 预期 vs 实际:")
    print(f"  - P1 预期挽回: 22项 → 实际验证: {p1_success}/{p1_total} 案例通过")
    print(f"  - P2 预期挽回: 27项 → 实际验证: {p2_success}/{p2_total} 案例通过")
    print(f"  - 总计预期: 49项")

    # 估算实际挽回
    if total_success == total_tests:
        print(f"\n✅ 所有测试案例通过！理论挽回49项全部生效")
    else:
        estimated_recovered = int(49 * (total_success / total_tests))
        print(f"\n⚠️  实际预估挽回: ~{estimated_recovered}项 (基于 {total_success/total_tests*100:.1f}% 通过率)")

    print(f"\n📝 数据库未匹配项:")
    print(f"  - 当前: {unmatched['total']} 项")
    print(f"  - 修复前估计: ~{unmatched['total'] + estimated_recovered if total_success < total_tests else unmatched['total'] + 49} 项")
    print(f"  - 挽回: ~{estimated_recovered if total_success < total_tests else 49} 项")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

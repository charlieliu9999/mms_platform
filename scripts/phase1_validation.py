#!/usr/bin/env python3
"""
Phase 1 验证脚本：快速止血效果验证

测试 SPECIAL_ITEM_MARKERS 扩展后的过滤效果：
1. 非影像检查识别率
2. 介入治疗识别率
3. 口腔专科识别率
4. 未匹配原因分类准确性
"""
import asyncio
import logging
from collections import Counter
from datetime import datetime

from sqlalchemy import text

from match_service.db import get_engine
from match_service.engine.match_engine_v2.orchestrator import MatchEngineOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 测试用例：应该被正确识别为 unmatchable 的项目
TEST_CASES = [
    # 非影像检查
    {'modality': 'DR', 'name': 'X线 12导联心电图(动态监测)', 'expected_reason': 'non_imaging'},
    {'modality': 'DR', 'name': 'X线心电图(24小时动态心电图)', 'expected_reason': 'non_imaging'},
    {'modality': 'XR', 'name': 'X线干血斑串联质谱检测', 'expected_reason': 'non_imaging'},
    {'modality': 'CT', 'name': 'CT脑电图监测', 'expected_reason': 'non_imaging'},

    # 介入治疗
    {'modality': 'DSA', 'name': 'DSA经导管动脉栓塞术', 'expected_reason': 'intervention'},
    {'modality': 'DSA', 'name': 'DSA腹主动脉-髂动脉支架置入术', 'expected_reason': 'intervention'},
    {'modality': 'DSA', 'name': 'DSA溶栓/取栓', 'expected_reason': 'intervention'},
    {'modality': 'DSA', 'name': 'DSA支气管动脉栓塞术', 'expected_reason': 'intervention'},
    {'modality': 'DSA', 'name': 'DSA球囊扩张术', 'expected_reason': 'intervention'},

    # 口腔专科
    {'modality': 'XR', 'name': 'X线口内根尖周片(根尖片)', 'expected_reason': 'dental'},
    {'modality': 'XR', 'name': 'X线曲面体层摄影(全景片)', 'expected_reason': 'dental'},
    {'modality': 'CBCT', 'name': 'CBCT口内扫描', 'expected_reason': 'dental'},

    # 内镜检查
    {'modality': 'ES', 'name': 'ES胃镜检查', 'expected_reason': 'endoscopy'},
    {'modality': 'ES', 'name': 'ES肠镜检查', 'expected_reason': 'endoscopy'},

    # 手术相关
    {'modality': 'SURG', 'name': '手术导航定位', 'expected_reason': 'surgery'},
]


async def test_unmatchable_detection():
    """测试 unmatchable 标记识别"""
    logger.info("=" * 80)
    logger.info("Phase 1 验证：Unmatchable 标记识别测试")
    logger.info("=" * 80)

    engine = get_engine()
    match_engine = MatchEngineOrchestrator(engine)
    await match_engine.initialize()

    correct = 0
    total = len(TEST_CASES)
    failed_cases = []

    for case in TEST_CASES:
        result = match_engine.match(case['name'], case['modality'])
        actual_reason = result.get('reason', '')
        expected_reason = case['expected_reason']

        if actual_reason == expected_reason:
            correct += 1
            status = '✓'
        else:
            status = '✗'
            failed_cases.append({
                'name': case['name'],
                'modality': case['modality'],
                'expected': expected_reason,
                'actual': actual_reason
            })

        logger.info(f"{status} [{case['modality']}] {case['name'][:40]:<40} "
                    f"期望: {expected_reason:<15} 实际: {actual_reason or 'NONE':<15}")

    await engine.dispose()

    logger.info("")
    logger.info(f"测试结果：{correct}/{total} ({correct/total*100:.1f}%)")

    if failed_cases:
        logger.warning("")
        logger.warning("失败案例详情：")
        for fc in failed_cases:
            logger.warning(f"  [{fc['modality']}] {fc['name']}")
            logger.warning(f"    期望: {fc['expected']}, 实际: {fc['actual'] or 'NONE'}")

    return correct, total


async def analyze_full_dataset():
    """分析全量数据的 unmatchable 分类改进"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("Phase 1 验证：全量数据 Unmatchable 分类分析")
    logger.info("=" * 80)

    db_engine = get_engine()

    # 加载数据
    async with db_engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT id, modality, name_zh
            FROM procedure_dictionary
            WHERE is_active = true
            ORDER BY modality, id
        """))
        rows = result.fetchall()

    logger.info(f"加载数据: {len(rows)}条")

    # 批量匹配
    match_engine = MatchEngineOrchestrator(db_engine)
    await match_engine.initialize()

    items = [
        {'key': str(row[0]), 'modality': row[1] or '', 'name': row[2] or ''}
        for row in rows
    ]

    detailed_results = match_engine.batch_match_detailed(items, version="V3.8.2")

    # 统计 unmatchable 原因分布
    unmatchable_reasons = Counter()
    unmatchable_by_modality = {}

    for item in items:
        key = item['key']
        modality = item['modality']
        name = item['name']
        result = detailed_results.get(key, {})

        reason = result.get('reason', '')
        pairs = result.get('pairs', [])

        if reason:  # 有 unmatchable 标记
            unmatchable_reasons[reason] += 1

            if modality not in unmatchable_by_modality:
                unmatchable_by_modality[modality] = Counter()
            unmatchable_by_modality[modality][reason] += 1

    await db_engine.dispose()

    # 输出统计
    logger.info("")
    logger.info("Unmatchable 原因分布：")
    for reason, count in unmatchable_reasons.most_common():
        logger.info(f"  {reason:<25}: {count:>5}条")

    logger.info("")
    logger.info("按模态分类的 Unmatchable 分布：")
    for modality in sorted(unmatchable_by_modality.keys()):
        counts = unmatchable_by_modality[modality]
        total = sum(counts.values())
        logger.info(f"  {modality:<12}: {total:>5}条")
        for reason, count in counts.most_common():
            logger.info(f"    - {reason:<20}: {count:>4}条")

    # 生成报告
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f'docs/reports/phase1-validation-{timestamp}.txt'

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("Phase 1 验证报告：Unmatchable 标记扩展效果\n")
        f.write("=" * 80 + "\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"数据来源: procedure_dictionary 表\n")
        f.write("\n")

        f.write("## 1. Unmatchable 原因分布\n")
        for reason, count in unmatchable_reasons.most_common():
            f.write(f"  {reason:<25}: {count:>5}条\n")
        f.write("\n")

        f.write("## 2. 按模态分类的 Unmatchable 分布\n")
        for modality in sorted(unmatchable_by_modality.keys()):
            counts = unmatchable_by_modality[modality]
            total = sum(counts.values())
            f.write(f"  {modality:<12}: {total:>5}条\n")
            for reason, count in counts.most_common():
                f.write(f"    - {reason:<20}: {count:>4}条\n")

    logger.info(f"\n报告已保存: {report_file}")

    return unmatchable_reasons, unmatchable_by_modality


async def main():
    """主函数"""
    # 1. 测试预定义案例
    correct, total = await test_unmatchable_detection()

    # 2. 分析全量数据
    await analyze_full_dataset()

    # 3. 总结
    logger.info("")
    logger.info("=" * 80)
    logger.info("Phase 1 验证完成")
    logger.info("=" * 80)
    logger.info(f"预定义案例识别准确率: {correct}/{total} ({correct/total*100:.1f}%)")
    logger.info("全量数据分析已完成，详见报告文件")
    logger.info("")
    logger.info("下一步：")
    logger.info("  1. 检查失败案例，调整标记词")
    logger.info("  2. 确认 unmatchable 分类合理性")
    logger.info("  3. 进入 Phase 2: 标准库扩充")


if __name__ == '__main__':
    asyncio.run(main())

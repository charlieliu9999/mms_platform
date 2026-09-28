#!/usr/bin/env python3
"""
测试报告中提到的"标准库缺项"是否真的无法匹配

目的：区分"标准库真缺项"和"词库映射问题"
"""
import asyncio
import logging

from match_service.db import get_engine
from match_service.engine.match_engine_v2.orchestrator import MatchEngineOrchestrator

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


# 报告中标记为"标准库缺项"的测试案例
TEST_CASES = [
    # 复合增强方式
    {'modality': 'CT', 'name': 'CT肝动静脉血管成像(CTA+CTV)', 'category': '复合增强'},
    {'modality': 'CT', 'name': 'CT腹部盆腔(平扫+动静脉双期增强)', 'category': '复合增强'},
    {'modality': 'CT', 'name': 'CT原发部位及区域淋巴结(平扫+增强)', 'category': '复合增强'},

    # 血管专项成像
    {'modality': 'CT', 'name': 'CT小肠血管成像(CTA)', 'category': '血管专项'},
    {'modality': 'CT', 'name': 'CT肝脏血管成像(CTA)', 'category': '血管专项'},
    {'modality': 'CT', 'name': 'CT腹腔血管成像(CTA)', 'category': '血管专项'},

    # 特殊造影技术
    {'modality': 'CT', 'name': 'CT脊柱局部(脊髓造影)', 'category': '特殊造影'},
    {'modality': 'CT', 'name': 'CT肩关节(直接造影)', 'category': '特殊造影'},
    {'modality': 'MR', 'name': 'MR肩关节(直接造影)', 'category': '特殊造影'},

    # 高级成像模式
    {'modality': 'CT', 'name': 'CT颞骨(超高分辨率UHR模式)', 'category': '高级模式'},
]


async def test_matching():
    """测试匹配结果"""
    engine = get_engine()
    match_engine = MatchEngineOrchestrator(engine)
    await match_engine.initialize()

    logger.info("=" * 100)
    logger.info("测试报告中的'标准库缺项'实际匹配情况")
    logger.info("=" * 100)

    results_by_category = {}

    for case in TEST_CASES:
        result = match_engine.match(case['name'], case['modality'])

        tier = result.get('tier', 'none')
        confidence = result.get('confidence', 0.0)
        num_standard = result.get('num_standard', 0)
        has_entity = result.get('has_entity', None)

        # 提取匹配到的标准项
        matched_items = []
        for d in result.get('data', []):
            for std in d.get('standard', []):
                matched_items.append(std['name'])

        category = case['category']
        if category not in results_by_category:
            results_by_category[category] = {'matched': 0, 'unmatched': 0, 'cases': []}

        case_result = {
            'name': case['name'],
            'tier': tier,
            'confidence': confidence,
            'num_standard': num_standard,
            'has_entity': has_entity,
            'matched_items': matched_items
        }

        results_by_category[category]['cases'].append(case_result)

        if num_standard > 0:
            results_by_category[category]['matched'] += 1
            status = f'✓ {tier.upper()}'
            color = '\033[92m'  # 绿色
        else:
            results_by_category[category]['unmatched'] += 1
            status = f'✗ NONE'
            color = '\033[91m'  # 红色

        reset = '\033[0m'

        logger.info(f"\n{color}{status}{reset} [{case['modality']}] {case['name']}")
        logger.info(f"    置信度: {confidence:.2f} | 匹配数: {num_standard} | has_entity: {has_entity}")

        if matched_items:
            logger.info(f"    匹配到的标准项:")
            for item in matched_items[:3]:
                logger.info(f"      • {item}")
            if len(matched_items) > 3:
                logger.info(f"      ... 还有 {len(matched_items) - 3} 条")

    await engine.dispose()

    # 分类汇总
    logger.info("\n" + "=" * 100)
    logger.info("分类汇总")
    logger.info("=" * 100)

    for category, stats in results_by_category.items():
        total = stats['matched'] + stats['unmatched']
        match_rate = stats['matched'] / total * 100 if total > 0 else 0
        logger.info(f"\n{category}：{stats['matched']}/{total} ({match_rate:.1f}%)")

        # 显示未匹配项
        unmatched_cases = [c for c in stats['cases'] if c['num_standard'] == 0]
        if unmatched_cases:
            logger.info(f"  未匹配项：")
            for case in unmatched_cases:
                reason = "词库缺项" if case['has_entity'] is False else "标准库缺项" if case['has_entity'] else "未知"
                logger.info(f"    - {case['name'][:50]:<50} | 原因: {reason}")

    # 结论
    logger.info("\n" + "=" * 100)
    logger.info("结论")
    logger.info("=" * 100)

    total_matched = sum(s['matched'] for s in results_by_category.values())
    total = len(TEST_CASES)

    logger.info(f"整体匹配率: {total_matched}/{total} ({total_matched/total*100:.1f}%)")
    logger.info(f"\n如果匹配率 > 50%，说明主要问题在词库映射，而非标准库缺项")
    logger.info(f"如果匹配率 < 30%，说明确实需要补充标准库")


if __name__ == '__main__':
    asyncio.run(test_matching())

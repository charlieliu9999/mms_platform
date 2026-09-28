#!/usr/bin/env python3
"""
4555项目全量匹配分析脚本

功能：
1. 从 procedure_dictionary 读取全量数据
2. 调用匹配引擎进行全量匹配
3. 统计匹配率、置信度分布
4. 分析未匹配原因并分类
5. 输出详细报告
"""
import asyncio
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List

from sqlalchemy import text

from match_service.db import get_engine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def load_source_data():
    """从 procedure_dictionary 加载全量数据"""
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT
                id,
                modality,
                name_zh,
                body_part
            FROM procedure_dictionary
            WHERE is_active = true
            ORDER BY modality, id
        """))
        rows = result.fetchall()

    await engine.dispose()

    items = []
    for row in rows:
        items.append({
            'key': str(row[0]),
            'modality': row[1] or '',
            'name': row[2] or '',
            'part': row[3] or ''
        })

    logger.info(f"加载源数据: {len(items)}条")
    return items


async def batch_match_analysis(items: List[Dict]) -> Dict:
    """批量匹配并分析结果"""
    # 直接初始化匹配引擎
    from match_service.engine.match_engine_v2.orchestrator import MatchEngineOrchestrator

    db_engine = get_engine()
    match_engine = MatchEngineOrchestrator(db_engine)
    await match_engine.initialize()

    # 准备匹配输入
    match_items = [
        {
            'key': item['key'],
            'modality': item['modality'],
            'name': item['name']
        }
        for item in items
    ]

    logger.info("开始批量匹配...")
    detailed_results = match_engine.batch_match_detailed(match_items, version="V3.8.2")
    logger.info("匹配完成")

    # 统计分析
    stats = {
        'total': len(items),
        'matched': 0,
        'unmatched': 0,
        'by_modality': defaultdict(lambda: {
            'total': 0,
            'matched': 0,
            'unmatched': 0,
            'tier_dist': Counter(),
            'confidence_dist': Counter()
        }),
        'tier_distribution': Counter(),
        'confidence_distribution': Counter(),
        'unmatch_reasons': defaultdict(list),
        'sample_results': {
            'exact': [],
            'partial': [],
            'degraded': [],
            'ambiguous': [],
            'none': []
        }
    }

    for item in items:
        key = item['key']
        modality = item['modality']
        name = item['name']

        result = detailed_results.get(key, {})
        pairs = result.get('pairs', [])
        tier = result.get('tier', 'none')
        confidence = result.get('confidence', 0.0)
        reason = result.get('reason', '')
        has_entity = result.get('has_entity')

        # 总体统计
        if pairs:
            stats['matched'] += 1
        else:
            stats['unmatched'] += 1

        stats['tier_distribution'][tier] += 1

        # 置信度分段统计
        if confidence >= 0.8:
            conf_bin = '>=0.8'
        elif confidence >= 0.6:
            conf_bin = '0.6-0.8'
        elif confidence >= 0.4:
            conf_bin = '0.4-0.6'
        elif confidence > 0:
            conf_bin = '0.0-0.4'
        else:
            conf_bin = '0.0'
        stats['confidence_distribution'][conf_bin] += 1

        # 按模态统计
        mod_stats = stats['by_modality'][modality]
        mod_stats['total'] += 1
        if pairs:
            mod_stats['matched'] += 1
        else:
            mod_stats['unmatched'] += 1
        mod_stats['tier_dist'][tier] += 1
        mod_stats['confidence_dist'][conf_bin] += 1

        # 未匹配原因分类
        if not pairs:
            if reason:
                category = f"unmatchable:{reason}"
            elif tier == 'error':
                category = "engine_error"
            elif has_entity is False:
                category = "lexicon_gap"
            elif has_entity is True:
                category = "standard_lib_gap"
            elif has_entity is None:
                if modality in ('CT', 'MR', 'DR', 'RF', 'MG', 'US', 'SPECT', 'PET/CT', 'PET/MR', 'OCT', 'DSA'):
                    category = "lexicon_gap"
                else:
                    category = "unsupported_modality"
            else:
                category = "unknown"

            stats['unmatch_reasons'][category].append({
                'id': key,
                'modality': modality,
                'name': name,
                'tier': tier,
                'has_entity': has_entity
            })

        # 采样结果
        if len(stats['sample_results'][tier]) < 5:
            stats['sample_results'][tier].append({
                'id': key,
                'modality': modality,
                'name': name,
                'matched_count': len(pairs),
                'matched_items': [f"{code}:{name}" for code, name in pairs[:3]],
                'confidence': confidence
            })

    return stats


def generate_report(stats: Dict, output_file: str):
    """生成分析报告"""
    report_lines = []

    report_lines.append("=" * 80)
    report_lines.append("医学影像检查项目匹配引擎全量分析报告")
    report_lines.append("=" * 80)
    report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"数据来源: procedure_dictionary 表")
    report_lines.append("")

    # 总体统计
    total = stats['total']
    matched = stats['matched']
    unmatched = stats['unmatched']
    match_rate = (matched / total * 100) if total > 0 else 0

    report_lines.append("## 1. 总体匹配情况")
    report_lines.append(f"总项目数: {total}")
    report_lines.append(f"已匹配: {matched} ({match_rate:.2f}%)")
    report_lines.append(f"未匹配: {unmatched} ({100-match_rate:.2f}%)")
    report_lines.append("")

    # 置信度分布
    report_lines.append("## 2. 置信度等级分布")
    tier_dist = stats['tier_distribution']
    for tier in ['exact', 'partial', 'degraded', 'ambiguous', 'none', 'error']:
        count = tier_dist.get(tier, 0)
        pct = (count / total * 100) if total > 0 else 0
        report_lines.append(f"  {tier:12s}: {count:5d} ({pct:5.2f}%)")
    report_lines.append("")

    # 置信度数值分布
    report_lines.append("## 3. 置信度数值分布")
    conf_dist = stats['confidence_distribution']
    for conf_bin in ['>=0.8', '0.6-0.8', '0.4-0.6', '0.0-0.4', '0.0']:
        count = conf_dist.get(conf_bin, 0)
        pct = (count / total * 100) if total > 0 else 0
        report_lines.append(f"  {conf_bin:8s}: {count:5d} ({pct:5.2f}%)")
    report_lines.append("")

    # 按模态统计
    report_lines.append("## 4. 按模态分类统计")
    report_lines.append(f"{'模态':<12} {'总数':>6} {'已匹配':>8} {'匹配率':>8} {'未匹配':>8}")
    report_lines.append("-" * 60)

    by_modality = stats['by_modality']
    for modality in sorted(by_modality.keys()):
        mod_stats = by_modality[modality]
        mod_total = mod_stats['total']
        mod_matched = mod_stats['matched']
        mod_unmatched = mod_stats['unmatched']
        mod_rate = (mod_matched / mod_total * 100) if mod_total > 0 else 0
        report_lines.append(
            f"{modality:<12} {mod_total:>6} {mod_matched:>8} {mod_rate:>7.2f}% {mod_unmatched:>8}"
        )
    report_lines.append("")

    # 未匹配原因分析
    report_lines.append("## 5. 未匹配原因分析")
    unmatch_reasons = stats['unmatch_reasons']
    for category in sorted(unmatch_reasons.keys()):
        items = unmatch_reasons[category]
        count = len(items)
        pct = (count / unmatched * 100) if unmatched > 0 else 0
        report_lines.append(f"  {category}: {count}条 ({pct:.2f}%)")

        # 显示前3个示例
        for item in items[:3]:
            report_lines.append(f"    - [{item['modality']}] {item['name']}")
    report_lines.append("")

    # 匹配结果采样
    report_lines.append("## 6. 匹配结果采样（各置信度等级前5条）")
    for tier in ['exact', 'partial', 'degraded', 'ambiguous', 'none']:
        samples = stats['sample_results'][tier]
        if samples:
            report_lines.append(f"\n### {tier}:")
            for sample in samples:
                report_lines.append(
                    f"  [{sample['modality']}] {sample['name']} "
                    f"→ {sample['matched_count']}项 (conf={sample['confidence']:.2f})"
                )
                for matched_item in sample['matched_items']:
                    report_lines.append(f"    • {matched_item}")
    report_lines.append("")

    # 提升建议
    report_lines.append("## 7. 匹配率提升建议")
    report_lines.append("")

    # 基于统计分析生成建议
    suggestions = []

    # 词库缺项建议
    lexicon_gap_count = len(unmatch_reasons.get('lexicon_gap', []))
    if lexicon_gap_count > 0:
        suggestions.append(
            f"1. 词库扩充（{lexicon_gap_count}项）:\n"
            f"   - 分析词库缺项的高频关键词\n"
            f"   - 补充医学词典（medical_dict）和短语映射（phrase_map）\n"
            f"   - 优先处理高频模态的缺项"
        )

    # 标准库缺项建议
    std_gap_count = len(unmatch_reasons.get('standard_lib_gap', []))
    if std_gap_count > 0:
        suggestions.append(
            f"2. 标准库补充（{std_gap_count}项）:\n"
            f"   - 有医学实体但查不到标准项\n"
            f"   - 需要导入更多标准项目到 nlp_checkitem_standard\n"
            f"   - 检查是否需要新增部位+扫描方式组合"
        )

    # 降级匹配优化
    degraded_count = tier_dist.get('degraded', 0)
    if degraded_count > 100:
        suggestions.append(
            f"3. 降级匹配优化（{degraded_count}项）:\n"
            f"   - 分析降级原因（扫描方式/部位回退）\n"
            f"   - 补充缺失的精确匹配规则\n"
            f"   - 优化关键词引擎的规则优先级"
        )

    # 歧义项优化
    ambiguous_count = tier_dist.get('ambiguous', 0)
    if ambiguous_count > 50:
        suggestions.append(
            f"4. 歧义项消歧（{ambiguous_count}项）:\n"
            f"   - 部分子项解析出实体但查不到标准项\n"
            f"   - 增强消歧规则（ambiguity_rule）\n"
            f"   - 优化部位合并和分裂逻辑"
        )

    # unmatchable 项目审查
    unmatchable_items = []
    for key in unmatch_reasons:
        if key.startswith('unmatchable:'):
            unmatchable_items.extend(unmatch_reasons[key])
    if unmatchable_items:
        suggestions.append(
            f"5. Unmatchable 项目审查（{len(unmatchable_items)}项）:\n"
            f"   - 确认这些项目确实不应匹配（穿刺/介入/放疗等）\n"
            f"   - 检查是否有误判的正常检查项目\n"
            f"   - 优化 SPECIAL_ITEM_MARKERS 规则"
        )

    for suggestion in suggestions:
        report_lines.append(suggestion)
        report_lines.append("")

    report_lines.append("=" * 80)

    # 写入文件
    report_text = "\n".join(report_lines)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_text)

    # 同时输出到控制台
    print(report_text)

    return report_text


async def main():
    """主函数"""
    # 1. 加载数据
    items = await load_source_data()

    # 2. 批量匹配分析
    stats = await batch_match_analysis(items)

    # 3. 生成报告
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f'docs/reports/match-analysis-{timestamp}.txt'

    generate_report(stats, report_file)

    # 4. 保存详细统计数据（JSON格式）
    json_file = f'docs/reports/match-analysis-{timestamp}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        # 转换为可序列化的格式
        serializable_stats = {
            'total': stats['total'],
            'matched': stats['matched'],
            'unmatched': stats['unmatched'],
            'tier_distribution': dict(stats['tier_distribution']),
            'confidence_distribution': dict(stats['confidence_distribution']),
            'by_modality': {
                mod: {
                    'total': data['total'],
                    'matched': data['matched'],
                    'unmatched': data['unmatched'],
                    'tier_dist': dict(data['tier_dist']),
                    'confidence_dist': dict(data['confidence_dist'])
                }
                for mod, data in stats['by_modality'].items()
            },
            'unmatch_reasons': {
                category: [
                    {
                        'id': item['id'],
                        'modality': item['modality'],
                        'name': item['name']
                    }
                    for item in items[:100]  # 只保存前100条
                ]
                for category, items in stats['unmatch_reasons'].items()
            }
        }
        json.dump(serializable_stats, f, ensure_ascii=False, indent=2)

    logger.info(f"分析完成！")
    logger.info(f"报告文件: {report_file}")
    logger.info(f"详细数据: {json_file}")


if __name__ == '__main__':
    asyncio.run(main())

#!/usr/bin/env python3
"""
Phase 6 分析脚本：系统性诊断未匹配项并制定优化方案

分析维度：
1. 模态错误（modal_mismatch）- 需要修复模态路由
2. 真实词典缺口（true_lexicon_gap）- 需要补充医学词典
3. 解析歧义（parser_ambiguity）- 需要优化消歧规则
4. 标准库缺口（standard_lib_gap）- 需要补充标准项目库
"""

import asyncio
import re
from collections import defaultdict
from sqlalchemy import text
from match_service.db import get_session_factory


# 模态前缀映射（用于检测模态错误）
MODALITY_PREFIXES = {
    'CT': ['CT'],
    'MR': ['MRI', 'MR'],
    'DR': ['X线', 'DR'],
    'US': ['超声', '彩超', 'US'],
    'DSA': ['DSA', '血管造影'],
    'RF': ['透视', 'RF'],
    'MG': ['钼靶', 'MG'],
    'PET': ['PET'],
    'SPECT': ['SPECT'],
}


def detect_modality_mismatch(modality: str, order_name: str) -> bool:
    """检测模态不匹配（检查名称前缀与模态不符）"""
    if not order_name or modality not in MODALITY_PREFIXES:
        return False

    expected_prefixes = MODALITY_PREFIXES[modality]

    # 检查名称是否以预期前缀开头
    for prefix in expected_prefixes:
        if order_name.startswith(prefix):
            return False

    # 检查名称是否以其他模态前缀开头（说明模态错误）
    for other_modality, prefixes in MODALITY_PREFIXES.items():
        if other_modality != modality:
            for prefix in prefixes:
                if order_name.startswith(prefix):
                    return True

    return False


def extract_missing_terms(order_name: str) -> list[str]:
    """从检查名称中提取可能缺失的医学术语"""
    # 简单的规则：提取中文医学术语（2-6个字）
    terms = []

    # 提取解剖部位
    anatomy_pattern = r'([一-龥]{2,6})(部|区|段|叶|窦|腔|管|囊|腺|体|头|颈|胸|腹|盆|肢|关节)'
    for match in re.finditer(anatomy_pattern, order_name):
        terms.append(match.group(0))

    # 提取检查方式
    method_pattern = r'(平扫|增强|薄层|血管|造影|弥散|灌注|功能|动态)'
    for match in re.finditer(method_pattern, order_name):
        terms.append(match.group(0))

    return list(set(terms))


async def analyze_unmatched():
    factory = get_session_factory()
    async with factory() as session:
        # 查询所有 open 状态的未匹配项
        result = await session.execute(text('''
            SELECT
                ur.id,
                ur.modality,
                ur.reason_code,
                ur.detail,
                hci.order_name
            FROM unmatched_registry ur
            JOIN hospital_check_items hci ON ur.procedure_id = hci.id
            WHERE ur.status = 'open'
            ORDER BY ur.modality, ur.id
        '''))

        rows = result.fetchall()

        # 分类统计
        stats = {
            'modal_mismatch': defaultdict(list),  # 模态错误
            'true_lexicon_gap': defaultdict(list),  # 真实词典缺口
            'parser_ambiguity': defaultdict(list),  # 解析歧义
            'standard_lib_gap': defaultdict(list),  # 标准库缺口
            'other': defaultdict(list),  # 其他
        }

        missing_terms = defaultdict(int)  # 统计缺失的医学术语

        for row in rows:
            modality = row.modality
            order_name = row.order_name
            reason_code = row.reason_code

            # 检测模态错误
            if detect_modality_mismatch(modality, order_name):
                stats['modal_mismatch'][modality].append(order_name)
            elif reason_code == 'lexicon_gap':
                stats['true_lexicon_gap'][modality].append(order_name)
                # 提取可能缺失的术语
                terms = extract_missing_terms(order_name)
                for term in terms:
                    missing_terms[term] += 1
            elif reason_code == 'parser_ambiguity':
                stats['parser_ambiguity'][modality].append(order_name)
            elif reason_code == 'standard_lib_gap':
                stats['standard_lib_gap'][modality].append(order_name)
            else:
                stats['other'][modality].append(order_name)

        # 打印分析结果
        print('=' * 100)
        print('Phase 6 未匹配项系统分析报告')
        print('=' * 100)

        print('\n【1. 模态错误（需修复模态路由）】')
        total_modal_mismatch = sum(len(v) for v in stats['modal_mismatch'].values())
        print(f'总计: {total_modal_mismatch} 项')
        for modality, items in sorted(stats['modal_mismatch'].items()):
            print(f'\n{modality} ({len(items)} 项):')
            for item in items[:5]:
                print(f'  - {item}')
            if len(items) > 5:
                print(f'  ... 还有 {len(items) - 5} 项')

        print('\n【2. 真实词典缺口（需补充医学词典）】')
        total_lexicon_gap = sum(len(v) for v in stats['true_lexicon_gap'].values())
        print(f'总计: {total_lexicon_gap} 项')
        for modality, items in sorted(stats['true_lexicon_gap'].items()):
            print(f'\n{modality} ({len(items)} 项):')
            for item in items[:5]:
                print(f'  - {item}')
            if len(items) > 5:
                print(f'  ... 还有 {len(items) - 5} 项')

        print('\n【3. 高频缺失医学术语 TOP 20】')
        top_terms = sorted(missing_terms.items(), key=lambda x: x[1], reverse=True)[:20]
        for term, count in top_terms:
            print(f'  {term}: {count} 次')

        print('\n【4. 解析歧义（需优化消歧规则）】')
        total_ambiguity = sum(len(v) for v in stats['parser_ambiguity'].values())
        print(f'总计: {total_ambiguity} 项')
        for modality, items in sorted(stats['parser_ambiguity'].items()):
            print(f'\n{modality} ({len(items)} 项):')
            for item in items[:3]:
                print(f'  - {item}')

        print('\n【5. 标准库缺口（需补充标准项目库）】')
        total_std_gap = sum(len(v) for v in stats['standard_lib_gap'].values())
        print(f'总计: {total_std_gap} 项')
        for modality, items in sorted(stats['standard_lib_gap'].items()):
            print(f'{modality}: {len(items)} 项')

        print('\n【6. 其他问题】')
        total_other = sum(len(v) for v in stats['other'].values())
        print(f'总计: {total_other} 项')
        for modality, items in sorted(stats['other'].items()):
            print(f'{modality}: {len(items)} 项')

        # 优先级建议
        print('\n' + '=' * 100)
        print('Phase 6 & 7 优化建议')
        print('=' * 100)

        print('\n【优先级 P0 - 立即修复】')
        print(f'1. 模态错误修复: {total_modal_mismatch} 项')
        print('   - 这些案例是模态路由错误，不是匹配算法问题')
        print('   - 需要在数据导入时修复模态标注')

        print('\n【优先级 P1 - 短期优化】')
        print(f'2. 补充医学词典: {total_lexicon_gap} 项 (真实词典缺口)')
        print(f'   - 补充 TOP 20 高频术语可覆盖大部分案例')
        print(f'3. 优化消歧规则: {total_ambiguity} 项')

        print('\n【优先级 P2 - 中期优化】')
        print(f'4. 补充标准项目库: {total_std_gap} 项')
        print('   - 需要与医疗机构协作补充标准库')

        print('\n【Phase 7: 智能排序优化】')
        print('当前所有匹配结果按字母序排序，建议优化为：')
        print('1. 按匹配置信度降序')
        print('2. 同等置信度按使用频率降序')
        print('3. 最后按字母序')


if __name__ == '__main__':
    asyncio.run(analyze_unmatched())

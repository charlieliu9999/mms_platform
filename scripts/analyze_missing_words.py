#!/usr/bin/env python3
"""
分析 DR missing_word 失败项 - 提取需要补充的词库
"""
import asyncio
from collections import Counter
from match_service.db import get_session_factory
from sqlalchemy import text
import re


async def main():
    factory = get_session_factory()
    async with factory() as db:
        # 获取所有 DR missing_word 失败项
        query = text("""
            WITH latest_task AS (
                SELECT id
                FROM mms_eval_tasks
                WHERE status = 'completed'
                ORDER BY completed_at DESC
                LIMIT 1
            )
            SELECT
                check_item,
                expected_code,
                expected_name
            FROM mms_eval_details
            WHERE task_id = (SELECT id FROM latest_task)
            AND modality = 'DR'
            AND is_matched = false
            AND failure_reason = 'missing_word'
            ORDER BY check_item;
        """)
        result = await db.execute(query)
        rows = result.fetchall()

    total = len(rows)
    print('=' * 120)
    print(f'DR missing_word 失败项分析 (共 {total:,} 条)')
    print('=' * 120)

    # 数据结构：原始项目 -> 期望标准名称
    items = [(row[0], row[2]) for row in rows]

    # 1. 清理并提取核心检查名称
    print('\n1. 清理前后缀，提取核心名称...\n')

    cleaned_items = []
    for original, expected in items:
        # 去除常见前后缀
        cleaned = original

        # 去除 (DR) 前缀
        cleaned = re.sub(r'\(DR\)', '', cleaned)
        cleaned = re.sub(r'^\[?DR\]?', '', cleaned)

        # 去除后缀
        cleaned = re.sub(r'数字化摄影$', '', cleaned)
        cleaned = re.sub(r'DR摄影$', '', cleaned)
        cleaned = re.sub(r'摄影$', '', cleaned)

        cleaned = cleaned.strip()

        if cleaned and cleaned != original:
            cleaned_items.append((original, cleaned, expected))

    # 按清理后的名称分组统计
    cleaned_counter = Counter([item[1] for item in cleaned_items])

    print(f'清理后唯一名称数量: {len(cleaned_counter)}')
    print(f'\n前50个高频缺失项:')
    print('-' * 120)

    for i, (cleaned_name, count) in enumerate(cleaned_counter.most_common(50), 1):
        # 找到对应的期望标准名称
        expected_names = set()
        for orig, clean, exp in cleaned_items:
            if clean == cleaned_name:
                expected_names.add(exp)

        expected_str = ' / '.join(sorted(expected_names)[:3])
        if len(expected_names) > 3:
            expected_str += f' (+{len(expected_names)-3}个)'

        print(f'{i:3d}. [{count:5d}次] {cleaned_name:50s} → {expected_str}')

    # 2. 提取关键词模式
    print('\n\n2. 关键词模式分析...\n')
    print('-' * 120)

    # 部位关键词
    body_parts = Counter()
    # 体位关键词
    positions = Counter()
    # 其他特征
    features = Counter()

    # 常见部位词
    body_keywords = [
        '手掌', '手指', '手', '腕', '前臂', '肘', '上臂', '肱骨', '肩',
        '足', '踝', '小腿', '膝', '大腿', '股骨', '髋', '骨盆',
        '颈椎', '胸椎', '腰椎', '骶椎', '尾椎', '脊柱',
        '头颅', '颌骨', '面部', '鼻骨', '眼眶',
        '胸部', '肋骨', '锁骨', '胸骨',
        '双手', '双足', '双膝', '双踝', '双肩', '双肘', '双髋',
    ]

    # 常见体位词
    position_keywords = [
        '正位', '侧位', '斜位', '轴位', '切线位', '张口位',
        '正侧位', '正斜位', '侧斜位',
        '前后位', '后前位', '左侧位', '右侧位',
        '屈曲位', '伸直位', '内旋位', '外旋位',
    ]

    for cleaned_name in cleaned_counter.keys():
        # 统计部位
        for body in body_keywords:
            if body in cleaned_name:
                body_parts[body] += cleaned_counter[cleaned_name]

        # 统计体位
        for pos in position_keywords:
            if pos in cleaned_name:
                positions[pos] += cleaned_counter[cleaned_name]

    print('高频部位词 (前30):')
    for i, (word, count) in enumerate(body_parts.most_common(30), 1):
        print(f'  {i:2d}. {word:10s}: {count:6d}次')

    print('\n高频体位词 (前20):')
    for i, (word, count) in enumerate(positions.most_common(20), 1):
        print(f'  {i:2d}. {word:10s}: {count:6d}次')

    # 3. 按模式分类
    print('\n\n3. 缺失词汇分类...\n')
    print('-' * 120)

    # 分类统计
    categories = {
        '简单部位+体位': [],  # 如：右手掌正侧位
        '复合部位': [],       # 如：右尺桡骨正侧位
        '特殊体位': [],       # 如：张口位、切线位
        '双侧': [],           # 如：双手正位
        '脊柱相关': [],       # 如：颈椎前屈后伸位
        '头部相关': [],       # 如：下颌骨正侧位
        '其他': [],
    }

    for cleaned_name, count in cleaned_counter.items():
        if count < 50:  # 只关注高频项
            continue

        # 找对应的期望名称
        expected_names = set()
        for orig, clean, exp in cleaned_items:
            if clean == cleaned_name:
                expected_names.add(exp)
        expected = list(expected_names)[0] if expected_names else ''

        item = (cleaned_name, count, expected)

        # 分类逻辑
        if '双' in cleaned_name and any(x in cleaned_name for x in ['手', '足', '膝', '踝', '肩', '肘', '髋']):
            categories['双侧'].append(item)
        elif any(x in cleaned_name for x in ['颈椎', '胸椎', '腰椎', '骶椎', '脊柱']):
            categories['脊柱相关'].append(item)
        elif any(x in cleaned_name for x in ['头颅', '颌骨', '鼻骨', '眼眶', '面部']):
            categories['头部相关'].append(item)
        elif any(x in cleaned_name for x in ['张口位', '切线位', '轴位', '屈曲', '伸直', '内旋', '外旋']):
            categories['特殊体位'].append(item)
        elif any(x in cleaned_name for x in ['尺桡骨', '胫腓骨', '指骨', '趾骨']):
            categories['复合部位'].append(item)
        elif any(x in cleaned_name for x in ['正位', '侧位', '斜位', '正侧位']):
            categories['简单部位+体位'].append(item)
        else:
            categories['其他'].append(item)

    for category, items in categories.items():
        if not items:
            continue

        print(f'\n【{category}】(共 {len(items)} 项)')
        print('-' * 120)

        for name, count, expected in sorted(items, key=lambda x: x[1], reverse=True)[:20]:
            print(f'  [{count:5d}次] {name:40s} → {expected}')

    # 4. 生成补充建议
    print('\n\n4. 词库补充建议...\n')
    print('=' * 120)

    print('''
基于分析结果，建议补充以下词库内容：

【短语映射表】(phrase_map)
需要添加的映射关系：

1. 简化后缀映射：
   - "右手掌正侧位" → "右手正侧位"
   - "右前臂正侧位" → "右尺桡骨正侧位"
   - "右小腿正侧位" → "右胫腓骨正侧位"

2. 双侧映射：
   - "双手正位" → "双手正位" (已存在标准项)
   - "双膝正位" → "双膝关节正侧位" (已存在标准项)

3. 特殊体位映射：
   - "张口位" → "颈椎张口位"
   - "切线位" → 需确认具体部位

【医学词典】(medical_dict)
需要添加的词汇：

1. 解剖部位词：
   - 手掌、手指、小腿 (简化名称)

2. 复合部位词：
   - 尺桡骨、胫腓骨、掌骨、跖骨

3. 特殊体位词：
   - 张口位、切线位、轴位
   - 屈曲位、伸直位、内旋位、外旋位

【优先级排序】
根据出现频次，建议优先补充：
''')

    # 按频次排序，输出前50个需要补充的项
    print('\n优先级 TOP 50（按频次排序）:')
    print('-' * 120)

    for i, (cleaned_name, count) in enumerate(cleaned_counter.most_common(50), 1):
        # 找期望标准名称
        expected_names = set()
        for orig, clean, exp in cleaned_items:
            if clean == cleaned_name:
                expected_names.add(exp)

        expected = list(expected_names)[0] if expected_names else ''

        # 简单分析映射关系
        mapping_type = ''
        if cleaned_name in expected:
            mapping_type = '✓ 直接匹配'
        elif any(word in expected for word in cleaned_name.split()):
            mapping_type = '≈ 部分匹配'
        else:
            mapping_type = '✗ 需要映射'

        print(f'{i:3d}. [{count:5d}次] {cleaned_name:40s} → {expected:50s} {mapping_type}')

    print('\n✅ 分析完成！')


if __name__ == '__main__':
    asyncio.run(main())

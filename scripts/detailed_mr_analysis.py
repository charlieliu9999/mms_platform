#!/usr/bin/env python3
"""逐一分析MR未匹配项 - 确定是算法问题还是标准库问题"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import asyncpg
from match_service.core.engine_holder import EngineHolder
from collections import Counter


DB_DSN = "postgresql://postgres:password@127.0.0.1:15432/acrac_db"


async def analyze_mr_unmatched_items():
    """详细分析每个MR未匹配项"""
    conn = await asyncpg.connect(DB_DSN)
    
    # 获取MR未匹配项
    items = await conn.fetch("""
        SELECT DISTINCT p.name_zh, u.modality, u.reason_code
        FROM unmatched_registry u
        JOIN procedure_dictionary p ON p.id = u.procedure_id
        WHERE u.status='open' AND u.modality = 'MR'
        ORDER BY p.name_zh
    """)
    
    # 获取所有MR标准项（用于手动匹配建议）
    standards = await conn.fetch("""
        SELECT item_code, item_name, body_part_l2, scan_method
        FROM standard_check_items
        WHERE modality = 'MR' AND is_active = true
        ORDER BY item_name
    """)
    
    print(f"MR标准库规模: {len(standards)} 项")
    
    # 初始化引擎
    holder = EngineHolder()
    await holder.initialize()
    engine = holder.match_engine
    
    print("=" * 100)
    print(f"MR未匹配项逐一分析 - 算法问题 vs 标准库问题 (共{len(items)}项)")
    print("=" * 100)
    
    analysis_results = []
    
    for idx, item in enumerate(items, 1):
        name = item['name_zh']
        
        # 引擎匹配测试
        trace = {}
        result = engine.match(name, 'MR', trace=trace)
        tier = result.get('tier', 'none')
        matched = result.get('data', [])
        num_matched = result.get('num_standard', 0)
        reason = result.get('reason', '')
        has_entity = result.get('has_entity', False)
        
        print(f"\n{'='*100}")
        print(f"【{idx}/{len(items)}】 {name}")
        print(f"{'='*100}")
        
        # 显示引擎结果
        print(f"\n引擎匹配结果:")
        print(f"  Tier: {tier}")
        print(f"  匹配数: {num_matched}")
        print(f"  原因: {reason or '(无)'}")
        print(f"  有实体: {has_entity}")
        
        if matched:
            print(f"  匹配到的标准项:")
            for m in matched[:2]:
                for std in m.get('standard', [])[:2]:
                    print(f"    - [{std['code']}] {std['name']}")
        
        # 提取关键词
        keywords = []
        if '脑' in name or '颅' in name:
            keywords.append('脑')
        if '脊柱' in name or '脊髓' in name:
            keywords.append('脊')
        if '全身' in name:
            keywords.append('全身')
        if '血管' in name or 'MRA' in name or 'MRV' in name or 'CE-MRA' in name:
            keywords.append('血管')
        if '主动脉' in name:
            keywords.append('主动脉')
        if '盆腔' in name or '盆底' in name:
            keywords.append('盆腔')
        if '肝' in name:
            keywords.append('肝')
        if '肾' in name:
            keywords.append('肾')
        if '关节' in name:
            keywords.append('关节')
        if '肩' in name:
            keywords.append('肩')
        if 'DWI' in name or '弥散' in name or '扩散' in name:
            keywords.append('DWI')
        if 'FLAIR' in name:
            keywords.append('FLAIR')
        if 'STIR' in name:
            keywords.append('STIR')
        
        # 初始化 candidates
        candidates = []
        if keywords:
            candidates = [s for s in standards 
                         if any(kw in s['item_name'] for kw in keywords)]
            
            if candidates and len(candidates) <= 5:
                print(f"\n标准库中相关的项目 (关键词: {', '.join(keywords)}):")
                for c in candidates[:5]:
                    print(f"  - [{c['item_code']}] {c['item_name']} | {c['scan_method']}")
            elif candidates:
                print(f"\n标准库中相关项目: {len(candidates)} 项 (关键词: {', '.join(keywords)})")
        
        # 问题归因
        print(f"\n问题归因:")
        
        # 判断是否应该排除
        if '穿刺' in name or '活检' in name or '靶向穿刺' in name:
            diagnosis = "✅ 设计排除 - 有创操作，不是影像检查"
            category = "设计排除"
        elif '消融' in name:
            diagnosis = "✅ 设计排除 - 治疗性操作，非诊断检查"
            category = "设计排除"
        elif name.startswith('PET/MRI') or name.startswith('SPECT'):
            diagnosis = "⚠️  跨模态组合 - 需特殊处理"
            category = "跨模态"
        elif tier == 'exact':
            # 有些exact但在未匹配表中，可能是exact_name_collision
            if 'exact_name_collision' in reason:
                diagnosis = "⚠️  算法问题 - 同名多编码冲突"
                category = "算法问题-名称冲突"
            else:
                diagnosis = "✅ 已匹配 (可能是exact但有其他原因未入库)"
                category = "已匹配"
        elif tier == 'ambiguous':
            # 特殊序列修饰
            if any(seq in name for seq in ['FLAIR', 'DIR', 'Haste', 'Trufi', 'STIR', 'SWI', 'SPACE', '3D-', 'T1WI', 'T2WI']):
                diagnosis = "⚠️  算法问题 - 特殊序列修饰语干扰"
                category = "算法问题-序列修饰语"
            # 血管成像
            elif 'MRA' in name or 'MRV' in name or 'CE-MRA' in name or 'CE-MRV' in name:
                if not candidates or len(candidates) == 0:
                    diagnosis = "❌ 标准库缺口 - 缺少对应血管成像标准项"
                    category = "标准库缺口-血管"
                else:
                    diagnosis = "⚠️  算法问题 - 有相关标准项但未完全匹配"
                    category = "算法问题-匹配失败"
            # 多项组合
            elif ',' in name or '联合' in name or '或' in name:
                diagnosis = "⚠️  算法问题 - 多项拆分/组合不完善"
                category = "算法问题-多项拆分"
            else:
                diagnosis = "⚠️  待定 - 需人工审核"
                category = "待定"
        elif tier == 'none':
            if not has_entity:
                diagnosis = "⚠️  词库缺口 - 无法解析出医学实体"
                category = "词库缺口"
            elif not candidates or len(candidates) == 0:
                diagnosis = "❌ 标准库缺口 - 有医学实体但缺少对应标准项"
                category = "标准库缺口"
            else:
                diagnosis = "⚠️  算法问题 - 有相关标准项但完全未匹配"
                category = "算法问题-查表失败"
        else:
            diagnosis = "⚠️  其他"
            category = "其他"
        
        print(f"  {diagnosis}")
        print(f"  分类: {category}")
        
        analysis_results.append({
            'name': name,
            'tier': tier,
            'category': category,
            'has_candidates': len(candidates) > 0 if keywords else False,
            'num_matched': num_matched,
            'reason': reason
        })
    
    # 统计汇总
    print("\n" + "=" * 100)
    print("统计汇总")
    print("=" * 100)
    
    category_count = Counter(r['category'] for r in analysis_results)
    
    print(f"\n问题分类分布:")
    for cat, count in category_count.most_common():
        pct = count / len(analysis_results) * 100
        print(f"  {cat:<35} {count:>2} 项 ({pct:>5.1f}%)")
    
    # 分类统计
    algo_issues = sum(1 for r in analysis_results if '算法问题' in r['category'])
    std_gaps = sum(1 for r in analysis_results if '标准库缺口' in r['category'])
    excluded = sum(1 for r in analysis_results if '设计排除' in r['category'])
    cross_modal = sum(1 for r in analysis_results if '跨模态' in r['category'])
    lexicon_gap = sum(1 for r in analysis_results if '词库缺口' in r['category'])
    
    print(f"\n问题归类:")
    print(f"  算法问题: {algo_issues} 项 ({algo_issues/len(items)*100:.1f}%) - 需要代码改进")
    print(f"  标准库缺口: {std_gaps} 项 ({std_gaps/len(items)*100:.1f}%) - 需要补充标准项")
    print(f"  设计排除: {excluded} 项 ({excluded/len(items)*100:.1f}%) - 符合预期，无需处理")
    print(f"  跨模态: {cross_modal} 项 ({cross_modal/len(items)*100:.1f}%) - 需特殊处理")
    print(f"  词库缺口: {lexicon_gap} 项 ({lexicon_gap/len(items)*100:.1f}%) - 需补充词典")
    
    print(f"\n可改进的项目: {algo_issues + std_gaps + lexicon_gap} / {len(items)} ({(algo_issues + std_gaps + lexicon_gap)/len(items)*100:.1f}%)")
    
    # Tier分布
    print(f"\nTier分布:")
    tier_count = Counter(r['tier'] for r in analysis_results)
    for tier in ['exact', 'partial', 'degraded', 'ambiguous', 'none']:
        count = tier_count.get(tier, 0)
        pct = count / len(items) * 100
        print(f"  {tier:<12} {count:>2} 项 ({pct:>5.1f}%)")
    
    await holder.dispose()
    await conn.close()


if __name__ == "__main__":
    asyncio.run(analyze_mr_unmatched_items())

#!/usr/bin/env python3
"""逐一分析CT未匹配项 - 确定是算法问题还是标准库问题"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import asyncpg
from match_service.core.engine_holder import EngineHolder


DB_DSN = "postgresql://postgres:password@127.0.0.1:15432/acrac_db"


async def analyze_unmatched_items():
    """详细分析每个未匹配项"""
    conn = await asyncpg.connect(DB_DSN)
    
    # 获取CT未匹配项
    items = await conn.fetch("""
        SELECT DISTINCT p.name_zh, u.modality, u.reason_code
        FROM unmatched_registry u
        JOIN procedure_dictionary p ON p.id = u.procedure_id
        WHERE u.status='open' AND u.modality = 'CT'
        ORDER BY p.name_zh
    """)
    
    # 获取所有CT标准项（用于手动匹配建议）
    standards = await conn.fetch("""
        SELECT item_code, item_name, body_part_l2, scan_method
        FROM standard_check_items
        WHERE modality = 'CT' AND is_active = true
        ORDER BY item_name
    """)
    
    # 初始化引擎
    holder = EngineHolder()
    await holder.initialize()
    engine = holder.match_engine
    
    print("=" * 100)
    print("CT未匹配项逐一分析 - 算法问题 vs 标准库问题")
    print("=" * 100)
    
    analysis_results = []
    
    for idx, item in enumerate(items, 1):
        name = item['name_zh']
        
        # 引擎匹配测试
        trace = {}
        result = engine.match(name, 'CT', trace=trace)
        tier = result.get('tier', 'none')
        matched = result.get('data', [])
        num_matched = result.get('num_standard', 0)
        reason = result.get('reason', '')
        has_entity = result.get('has_entity', False)
        
        print(f"\n{'='*100}")
        print(f"【{idx}】 {name}")
        print(f"{'='*100}")
        
        # 显示引擎结果
        print(f"\n引擎匹配结果:")
        print(f"  Tier: {tier}")
        print(f"  匹配数: {num_matched}")
        print(f"  原因: {reason or '(无)'}")
        print(f"  有实体: {has_entity}")
        
        if matched:
            print(f"  匹配到的标准项:")
            for m in matched[:3]:
                for std in m.get('standard', [])[:3]:
                    print(f"    - [{std['code']}] {std['name']}")
        
        # 分析预处理
        if '1-preprocess' in trace:
            print(f"\n预处理后: {trace['1-preprocess']}")
        
        # 分析实体提取
        if '3-make_tree' in trace and trace['3-make_tree']:
            print(f"\n提取的实体节点:")
            for node_str in trace['3-make_tree'][:3]:
                print(f"  {node_str}")
        
        # 手动匹配建议（基于关键词）
        keywords = []
        if '主动脉' in name:
            keywords.append('主动脉')
        if '冠状动脉' in name:
            keywords.append('冠状动脉')
        if '血管' in name or 'CTA' in name or 'CTV' in name:
            keywords.append('血管')
        if '腹部' in name:
            keywords.append('腹部')
        if '盆腔' in name:
            keywords.append('盆腔')
        if '小肠' in name:
            keywords.append('小肠')
        if '肝脏' in name:
            keywords.append('肝脏')
        if '脊髓' in name or '脊柱' in name:
            keywords.append('脊')
        if '泪' in name:
            keywords.append('泪')
        if '尿路' in name:
            keywords.append('尿路')
        if '乳腺' in name:
            keywords.append('乳腺')
        if '肩关节' in name:
            keywords.append('肩')
        
        # 初始化 candidates
        candidates = []
        if keywords:
            candidates = [s for s in standards 
                         if any(kw in s['item_name'] for kw in keywords)]
            
            if candidates:
                print(f"\n标准库中可能相关的项目 (关键词: {', '.join(keywords)}):")
                for c in candidates[:5]:
                    print(f"  - [{c['item_code']}] {c['item_name']} | {c['body_part_l2']} | {c['scan_method']}")
        
        # 问题归因
        print(f"\n问题归因:")
        
        # 判断是否应该排除
        if '穿刺' in name or '活检' in name:
            diagnosis = "✅ 设计排除 - 有创操作，不是影像检查"
            category = "设计排除"
        elif '模拟定位' in name:
            diagnosis = "✅ 设计排除 - 放疗定位扫描，非诊断检查"
            category = "设计排除"
        elif name.startswith('ECT'):
            diagnosis = "❌ 数据质量问题 - 模态错误(应为SPECT)"
            category = "模态错误"
        elif name.startswith('US'):
            diagnosis = "❌ 数据质量问题 - 模态错误(应为US)"
            category = "模态错误"
        elif tier == 'ambiguous':
            if '心电门控' in name or 'MPR' in name or 'VR' in name or '三维重建' in name or '多平面' in name:
                diagnosis = "⚠️  算法问题 - 技术修饰语干扰，需增强预处理过滤"
                category = "算法问题-技术修饰语"
            elif 'CTA' in name or 'CTV' in name or '血管' in name:
                if not candidates or len(candidates) == 0:
                    diagnosis = "❌ 标准库缺口 - 缺少对应血管成像标准项"
                    category = "标准库缺口-血管"
                else:
                    diagnosis = "⚠️  算法问题 - 有相关标准项但未匹配成功"
                    category = "算法问题-匹配失败"
            elif '联合' in name or '+' in name:
                diagnosis = "⚠️  算法问题 - 多项拆分不完善，残留部分未匹配"
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
            diagnosis = "✅ 已匹配"
            category = "已匹配"
        
        print(f"  {diagnosis}")
        print(f"  分类: {category}")
        
        # 建议的标准项（仅对标准库缺口）
        if category.startswith("标准库缺口") and keywords:
            print(f"\n💡 建议补充标准项:")
            # 根据名称推断可能的标准项
            if 'CTA腹部盆腔' in name:
                print(f"  INSERT: CT腹部盆腔动脉血管成像 | 腹部盆腔 | CTA")
            elif 'CT小肠血管' in name or 'CT小肠' in name and 'CTA' in name:
                print(f"  INSERT: CT小肠血管成像 | 小肠 | CTA")
            elif 'CT肝脏血管' in name or 'CT肝脏' in name and 'CTA' in name:
                print(f"  INSERT: CT肝脏血管成像 | 肝脏 | CTA")
            elif '脊髓动脉' in name or '脊髓' in name and 'CTA' in name:
                print(f"  INSERT: CT脊髓动脉血管成像 | 脊髓 | CTA")
            elif '泪道造影' in name or '泪囊造影' in name:
                print(f"  INSERT: CT泪道造影 | 泪道 | 造影")
            elif '脊髓造影' in name or '脊柱脊髓造影' in name:
                print(f"  INSERT: CT脊髓造影 | 脊髓 | 造影")
            elif 'CT尿路造影' in name:
                print(f"  INSERT: CT尿路造影 | 尿路 | 造影")
            elif 'CT乳腺' in name:
                print(f"  INSERT: CT乳腺 | 乳腺 | 平扫+增强")
            elif '肩关节' in name and '造影' in name:
                print(f"  INSERT: CT肩关节造影 | 肩关节 | 造影")
        
        # 建议的算法改进
        if category.startswith("算法问题"):
            print(f"\n🔧 建议算法改进:")
            if "技术修饰语" in category:
                print(f"  修改 preprocess_service.py:")
                print(f"  - 增加技术修饰语过滤模式")
                print(f"  - 清理括号内的: 心电门控、多排螺旋、MPR、VR、三维重建、骨算法等")
            elif "多项拆分" in category:
                print(f"  修改 preprocess_service.py 的 split_record:")
                print(f"  - 移除无匹配价值的后缀: '联合.*FFR', '骨算法重建', '三维重建'")
            elif "匹配失败" in category or "查表失败" in category:
                print(f"  需要调试 lookup_standard_service.py:")
                print(f"  - 检查查询字段是否正确")
                print(f"  - 检查消歧规则是否覆盖")
        
        analysis_results.append({
            'name': name,
            'tier': tier,
            'category': category,
            'has_candidates': len(candidates) > 0 if keywords else False,
            'num_matched': num_matched
        })
    
    # 统计汇总
    print("\n" + "=" * 100)
    print("统计汇总")
    print("=" * 100)
    
    from collections import Counter
    category_count = Counter(r['category'] for r in analysis_results)
    
    print(f"\n问题分类分布:")
    for cat, count in category_count.most_common():
        pct = count / len(analysis_results) * 100
        print(f"  {cat:<30} {count:>2} 项 ({pct:>5.1f}%)")
    
    # 分类统计
    algo_issues = sum(1 for r in analysis_results if '算法问题' in r['category'])
    std_gaps = sum(1 for r in analysis_results if '标准库缺口' in r['category'])
    excluded = sum(1 for r in analysis_results if '设计排除' in r['category'])
    data_issues = sum(1 for r in analysis_results if '模态错误' in r['category'])
    
    print(f"\n问题归类:")
    print(f"  算法问题: {algo_issues} 项 ({algo_issues/len(items)*100:.1f}%) - 需要代码改进")
    print(f"  标准库缺口: {std_gaps} 项 ({std_gaps/len(items)*100:.1f}%) - 需要补充标准项")
    print(f"  设计排除: {excluded} 项 ({excluded/len(items)*100:.1f}%) - 符合预期，无需处理")
    print(f"  数据质量: {data_issues} 项 ({data_issues/len(items)*100:.1f}%) - 需要修正模态")
    
    print(f"\n可改进的项目: {algo_issues + std_gaps} / {len(items)} ({(algo_issues + std_gaps)/len(items)*100:.1f}%)")
    
    await holder.dispose()
    await conn.close()


if __name__ == "__main__":
    asyncio.run(analyze_unmatched_items())

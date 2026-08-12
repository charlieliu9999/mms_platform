#!/usr/bin/env python3
"""分析 CT/MR/DR 项目的匹配情况

从 procedure_dictionary 获取所有 CT/MR/DR 项目，
使用当前引擎进行匹配，并详细分析未匹配项的原因。
"""
import asyncio
import sys
from pathlib import Path
from collections import defaultdict, Counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from match_service.db import get_engine, AsyncSession
from sqlalchemy import text
from match_service.core.engine_holder import EngineHolder
from match_service.engine.modality_resolver import resolve_effective_modality


async def analyze_ct_mr_dr():
    """分析 CT/MR/DR 项目匹配情况"""
    
    # 初始化引擎
    holder = EngineHolder()
    await holder.initialize()
    engine = holder.match_engine
    print(f"引擎已加载: {engine.is_ready}\n")
    
    db_engine = get_engine()
    
    # 1. 获取所有 CT/MR/DR 项目
    async with AsyncSession(db_engine) as session:
        result = await session.execute(text("""
            SELECT 
                id,
                name_zh,
                name_en,
                modality,
                body_part
            FROM procedure_dictionary
            WHERE modality IN ('CT', 'MR', 'DR', 'CT-DE', 'CT-4D')
              AND is_active = true
            ORDER BY modality, name_zh
        """))
        all_items = result.fetchall()
    
    print(f"总记录数: {len(all_items)}")
    print(f"  CT系列: {sum(1 for x in all_items if x.modality.startswith('CT'))}")
    print(f"  MR: {sum(1 for x in all_items if x.modality == 'MR')}")
    print(f"  DR: {sum(1 for x in all_items if x.modality == 'DR')}\n")
    
    # 2. 对每个项目进行匹配
    results_by_modality = defaultdict(lambda: {
        'exact': [],
        'partial': [],
        'degraded': [],
        'ambiguous': [],
        'none': [],
        'error': []
    })
    
    none_reasons = defaultdict(list)
    ambiguous_patterns = defaultdict(list)
    
    for item in all_items:
        name = item.name_zh or item.name_en or ""
        modality = item.modality
        
        # 统一 CT 变体
        match_modality = 'CT' if modality.startswith('CT') else modality
        
        # 使用模态解析器纠正模态（如 DR 乳腺 → MG）
        match_modality = resolve_effective_modality(name, match_modality)
        
        try:
            result = engine.match(name, match_modality)
            tier = result.get('tier', 'none')
            reason = result.get('reason', '')
            
            results_by_modality[match_modality][tier].append({
                'name': name,
                'modality': modality,
                'body_part': item.body_part,
                'reason': reason,
                'result': result
            })
            
            # 分析未匹配原因
            if tier == 'none':
                if reason:
                    none_reasons[f"拦截:{reason}"].append((modality, name))
                elif result.get('entities'):
                    none_reasons["有实体但未命中标准项"].append((modality, name))
                else:
                    none_reasons["未解析出实体"].append((modality, name))
            
            # 分析 ambiguous 模式
            elif tier == 'ambiguous':
                pattern = classify_ambiguous(name)
                ambiguous_patterns[pattern].append((modality, name))
                
        except Exception as e:
            results_by_modality[match_modality]['error'].append({
                'name': name,
                'modality': modality,
                'error': str(e)
            })
    
    # 3. 输出总体统计
    print("=" * 80)
    print("一、匹配结果总体统计")
    print("=" * 80)
    
    for modality in ['CT', 'MR', 'DR']:
        results = results_by_modality[modality]
        total = sum(len(results[tier]) for tier in results)
        
        if total == 0:
            continue
            
        print(f"\n【{modality}】总计 {total} 项")
        for tier in ['exact', 'partial', 'degraded', 'ambiguous', 'none', 'error']:
            count = len(results[tier])
            if count > 0:
                pct = count * 100.0 / total
                print(f"  {tier:12s}: {count:4d} 项 ({pct:5.1f}%)")
    
    # 4. 详细列出未匹配项
    print("\n" + "=" * 80)
    print("二、未匹配项详细列表 (tier=none)")
    print("=" * 80)
    
    for modality in ['CT', 'MR', 'DR']:
        none_items = results_by_modality[modality]['none']
        if not none_items:
            continue
        
        print(f"\n【{modality} 未匹配】{len(none_items)} 项\n")
        for idx, item in enumerate(none_items[:50], 1):
            reason_str = f" [{item['reason']}]" if item['reason'] else ""
            print(f"{idx:3d}. {item['name']}{reason_str}")
        
        if len(none_items) > 50:
            print(f"     ... 还有 {len(none_items) - 50} 项")
    
    # 5. 未匹配原因分类
    print("\n" + "=" * 80)
    print("三、未匹配原因分类")
    print("=" * 80)
    
    for reason, items in sorted(none_reasons.items(), key=lambda x: -len(x[1])):
        print(f"\n【{reason}】{len(items)} 项")
        for modality, name in items[:20]:
            print(f"  {modality:7s} {name}")
        if len(items) > 20:
            print(f"  ... 还有 {len(items) - 20} 项")
    
    # 6. Ambiguous 项分析
    print("\n" + "=" * 80)
    print("四、Ambiguous 项模式分析")
    print("=" * 80)
    
    for modality in ['CT', 'MR', 'DR']:
        amb_items = results_by_modality[modality]['ambiguous']
        if not amb_items:
            continue
        
        print(f"\n【{modality} Ambiguous】{len(amb_items)} 项")
        for pattern, items in sorted(ambiguous_patterns.items(), 
                                    key=lambda x: -len([i for i in x[1] if i[0].startswith(modality)])):
            pattern_items = [(m, n) for m, n in items if m.startswith(modality)]
            if pattern_items:
                print(f"\n  {pattern} ({len(pattern_items)}项):")
                for mod, name in pattern_items[:10]:
                    print(f"    {name}")
    
    # 7. 成功匹配的示例
    print("\n" + "=" * 80)
    print("五、成功匹配示例")
    print("=" * 80)
    
    for modality in ['CT', 'MR', 'DR']:
        for tier in ['exact', 'partial']:
            items = results_by_modality[modality][tier]
            if items:
                print(f"\n【{modality} - {tier}】{len(items)} 项，示例:")
                for item in items[:5]:
                    matched = item['result'].get('matched_items', [])
                    if matched:
                        std_name = matched[0].get('standard_name', 'N/A')
                        print(f"  {item['name']}")
                        print(f"    → {std_name}")
    
    # 清理
    await holder.dispose()
    await db_engine.dispose()
    
    print("\n" + "=" * 80)
    print("分析完成")
    print("=" * 80)


def classify_ambiguous(name: str) -> str:
    """对 ambiguous 项按文本特征细分失败模式"""
    import re
    
    if re.search(r"CE-MR[AV]|MRA|MRV|CTA|CTV", name):
        return "血管成像(MRA/CTA)"
    if "[" in name and "]" in name:
        return "方括号修饰语"
    if re.search(r"三维重建|MPR|VR|薄层|多层", name):
        return "后处理/重建"
    if re.search(r"Haste|Trufi|FLAIR|DIR|心电门控|UHR|Quantum|功能|波谱|弥散|灌注|SWI|DTI|fMRI", name):
        return "特殊序列"
    if re.search(r"全脊柱|全脊髓|双侧|双肾|双髋|双肩|头颈部", name):
        return "复合部位"
    if "," in name or "、" in name or "+" in name:
        return "多项组合"
    if re.search(r"平扫\+增强|平扫并增强", name):
        return "增强组合"
    return "其他"


if __name__ == "__main__":
    asyncio.run(analyze_ct_mr_dr())

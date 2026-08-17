#!/usr/bin/env python3
"""分析1174个未匹配项目的详细信息"""
import asyncio
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text
from match_service.db import get_engine, get_session_factory

async def analyze_unmatched():
    engine = get_engine()
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # 获取所有未匹配项目
        result = await session.execute(text('''
            SELECT 
                pd.id,
                pd.semantic_id,
                pd.name_zh,
                UPPER(pd.modality) as modality,
                pmr.tier,
                pmr.reason_code,
                pmr.detail,
                ur.reason_code as ur_reason
            FROM procedure_dictionary pd
            LEFT JOIN procedure_match_results pmr ON pmr.procedure_id = pd.id
            LEFT JOIN unmatched_registry ur ON ur.procedure_id = pd.id
            WHERE pd.is_active = true 
              AND (pmr.matched = false OR pmr.matched IS NULL)
            ORDER BY UPPER(pd.modality), pd.id
        '''))
        unmatched_items = result.fetchall()
        
        print("=" * 80)
        print(f"未匹配项目详细分析 (共 {len(unmatched_items)} 项)")
        print("=" * 80)
        
        # 按模态分组
        by_modality = {}
        for item in unmatched_items:
            mod = item.modality or 'UNKNOWN'
            if mod not in by_modality:
                by_modality[mod] = []
            by_modality[mod].append(item)
        
        # 按失败原因分类
        reason_counter = Counter()
        for item in unmatched_items:
            reason = item.reason_code or item.ur_reason or 'unknown'
            reason_counter[reason] += 1
        
        print("\n失败原因分布:")
        for reason, count in reason_counter.most_common():
            print(f"  {reason}: {count} 项 ({count*100/len(unmatched_items):.1f}%)")
        
        # 重点模态详细分析
        for modality in ['CT', 'MR', 'US', 'DR']:
            if modality not in by_modality:
                continue
            
            items = by_modality[modality]
            print(f"\n{'=' * 80}")
            print(f"{modality} 未匹配项目 (共 {len(items)} 项)")
            print(f"{'=' * 80}")
            
            # 按原因分组
            reasons = Counter()
            for item in items:
                reason = item.reason_code or item.ur_reason or 'unknown'
                reasons[reason] += 1
            
            print("\n失败原因:")
            for reason, count in reasons.most_common():
                print(f"  {reason}: {count} 项")
            
            # 显示前20个示例
            print(f"\n前20个未匹配项目示例:")
            for i, item in enumerate(items[:20], 1):
                reason = item.reason_code or item.ur_reason or 'unknown'
                print(f"  {i}. [{item.semantic_id}] {item.name_zh}")
                print(f"     原因: {reason}")
                if item.detail:
                    print(f"     详情: {item.detail[:60]}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(analyze_unmatched())

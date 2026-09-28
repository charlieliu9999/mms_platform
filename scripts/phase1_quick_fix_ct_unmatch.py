#!/usr/bin/env python3
"""Phase 1 快速修复 - CT未匹配问题

改进项:
1. 增强技术修饰语过滤（解决4条ambiguous）
2. 修正模态错误数据（解决2条错误归类）
3. 验证改进效果

用法: 
    poetry run python scripts/phase1_quick_fix_ct_unmatch.py --dry-run  # 预览
    poetry run python scripts/phase1_quick_fix_ct_unmatch.py --apply    # 应用
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import asyncpg
from collections import Counter


DB_DSN = "postgresql://postgres:password@127.0.0.1:15432/acrac_db"


async def fix_modality_misrouting(conn, dry_run=True):
    """修正模态错误归类"""
    print("\n" + "="*78)
    print("任务1: 修正模态错误归类")
    print("="*78)
    
    # 检查 ECT 误归类
    ect_rows = await conn.fetch("""
        SELECT u.id, p.name_zh, u.modality
        FROM unmatched_registry u
        JOIN procedure_dictionary p ON p.id = u.procedure_id
        WHERE u.modality = 'CT' AND (p.name_zh LIKE '%ECT%' OR p.name_en LIKE '%ECT%')
    """)
    
    print(f"\n发现 {len(ect_rows)} 条 ECT 检查误归为 CT:")
    for r in ect_rows:
        print(f"  ID={r['id']:<5} {r['modality']} → SPECT: {r['name_zh']}")
    
    # 检查 US 误归类
    us_rows = await conn.fetch("""
        SELECT u.id, p.name_zh, u.modality
        FROM unmatched_registry u
        JOIN procedure_dictionary p ON p.id = u.procedure_id
        WHERE u.modality = 'CT' AND (p.name_zh LIKE 'US%' OR p.name_en LIKE 'US%')
    """)
    
    print(f"\n发现 {len(us_rows)} 条 US 检查误归为 CT:")
    for r in us_rows:
        print(f"  ID={r['id']:<5} {r['modality']} → US: {r['name_zh']}")
    
    if not dry_run:
        # 应用修正
        if ect_rows:
            ect_ids = [r['id'] for r in ect_rows]
            await conn.execute("""
                UPDATE unmatched_registry 
                SET modality = 'SPECT'
                WHERE id = ANY($1::int[])
            """, ect_ids)
            print(f"\n✅ 已修正 {len(ect_ids)} 条 ECT 记录")
        
        if us_rows:
            us_ids = [r['id'] for r in us_rows]
            await conn.execute("""
                UPDATE unmatched_registry 
                SET modality = 'US'
                WHERE id = ANY($1::int[])
            """, us_ids)
            print(f"✅ 已修正 {len(us_ids)} 条 US 记录")
    else:
        print("\n🔍 [DRY-RUN] 未应用修改，使用 --apply 参数执行修改")
    
    return len(ect_rows) + len(us_rows)


async def test_tech_modifier_filtering(conn):
    """测试技术修饰语过滤效果（模拟改进）"""
    print("\n" + "="*78)
    print("任务2: 验证技术修饰语过滤效果")
    print("="*78)
    
    # 获取 ambiguous 的技术修饰语相关项
    tech_modifier_items = [
        "CT主动脉根部(心电门控增强多排螺旋CT)",
        "CT主动脉根部及外周血管多期增强扫描(平扫+增强+三维重建)",
        "CT胸部腹部(多平面重组MPR)",
        "CT胸部腹部(容积再现VR)",
    ]
    
    from match_service.core.engine_holder import EngineHolder
    import re
    
    holder = EngineHolder()
    await holder.initialize()
    engine = holder.match_engine
    
    # 技术修饰语过滤规则（模拟改进）
    TECH_NOISE_PATTERNS = [
        r'\(心电门控[^)]*\)',
        r'\(多排螺旋[^)]*\)',
        r'\(多平面重[组建][^)]*\)',
        r'\(容积再现[^)]*\)',
        r'\(三维重建[^)]*\)',
        r'\(MPR[^)]*\)',
        r'\(VR[^)]*\)',
        r'\(骨算法[^)]*\)',
        r'多期增强扫描',
        r'双期增强',
    ]
    
    def clean_tech_modifiers(text):
        """模拟改进后的预处理"""
        for pattern in TECH_NOISE_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        return text.strip()
    
    print("\n对比测试（改进前 vs 改进后）:")
    print("-" * 78)
    
    improved_count = 0
    for item in tech_modifier_items:
        # 当前引擎结果
        result_before = engine.match(item, 'CT')
        tier_before = result_before.get('tier', 'none')
        num_before = result_before.get('num_standard', 0)
        
        # 模拟改进后
        cleaned = clean_tech_modifiers(item)
        result_after = engine.match(cleaned, 'CT')
        tier_after = result_after.get('tier', 'none')
        num_after = result_after.get('num_standard', 0)
        
        status = "✅ 改善" if tier_after in ('exact', 'partial') and tier_before == 'ambiguous' else "⚠️  无变化"
        if status == "✅ 改善":
            improved_count += 1
        
        print(f"\n原文: {item}")
        print(f"清洗后: {cleaned}")
        print(f"改进前: tier={tier_before}, 匹配数={num_before}")
        print(f"改进后: tier={tier_after}, 匹配数={num_after}")
        print(f"{status}")
    
    await holder.dispose()
    
    print(f"\n📊 改善统计: {improved_count}/{len(tech_modifier_items)} 条从 ambiguous 提升")
    return improved_count


async def verify_improvement(conn):
    """验证总体改善效果"""
    print("\n" + "="*78)
    print("任务3: 验证总体改善效果")
    print("="*78)
    
    # 统计 CT 未匹配分布
    ct_stats = await conn.fetch("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE modality = 'CT') as ct_count,
            COUNT(DISTINCT p.name_zh) FILTER (WHERE modality = 'CT') as ct_distinct
        FROM unmatched_registry u
        JOIN procedure_dictionary p ON p.id = u.procedure_id
        WHERE u.status = 'open'
    """)
    
    stats = ct_stats[0]
    print(f"\nCT 未匹配统计:")
    print(f"  总记录数: {stats['ct_count']}")
    print(f"  去重项数: {stats['ct_distinct']}")
    
    # 按原因分类
    reason_dist = await conn.fetch("""
        SELECT reason_code, COUNT(*) as cnt
        FROM unmatched_registry
        WHERE status = 'open' AND modality = 'CT'
        GROUP BY reason_code
        ORDER BY cnt DESC
    """)
    
    print(f"\n原因分布:")
    for r in reason_dist:
        print(f"  {r['reason_code']:<30} {r['cnt']:>3} 条")


async def run_full_rematch(conn):
    """重新匹配所有CT项（验证改进效果）"""
    print("\n" + "="*78)
    print("任务4: 重新匹配验证（可选）")
    print("="*78)
    
    from match_service.core.engine_holder import EngineHolder
    
    holder = EngineHolder()
    await holder.initialize()
    engine = holder.match_engine
    
    # 获取所有 CT distinct 项
    items = await conn.fetch("""
        SELECT DISTINCT p.name_zh, u.modality
        FROM unmatched_registry u
        JOIN procedure_dictionary p ON p.id = u.procedure_id
        WHERE u.status = 'open' AND u.modality = 'CT'
        ORDER BY p.name_zh
    """)
    
    print(f"\n重新匹配 {len(items)} 个CT项目...")
    
    tier_dist = Counter()
    improved_items = []
    
    for item in items:
        name = item['name_zh']
        result = engine.match(name, 'CT')
        tier = result.get('tier', 'none')
        tier_dist[tier] += 1
        
        if tier in ('exact', 'partial', 'degraded'):
            improved_items.append((name, tier, result.get('num_standard', 0)))
    
    print(f"\n重新匹配结果分布:")
    for tier in ('exact', 'partial', 'degraded', 'ambiguous', 'none'):
        count = tier_dist.get(tier, 0)
        pct = count / len(items) * 100 if items else 0
        print(f"  {tier:<12} {count:>3} ({pct:>5.1f}%)")
    
    if improved_items:
        print(f"\n✅ 发现 {len(improved_items)} 个可匹配项:")
        for name, tier, num in improved_items[:10]:
            print(f"  [{tier}] {name} → {num}项")
        if len(improved_items) > 10:
            print(f"  ... 还有 {len(improved_items)-10} 项")
    
    await holder.dispose()


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Phase 1 快速修复 - CT未匹配问题")
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际修改数据')
    parser.add_argument('--apply', action='store_true', help='应用修改到数据库')
    parser.add_argument('--verify-only', action='store_true', help='仅验证，不修改')
    parser.add_argument('--full-rematch', action='store_true', help='执行完整重匹配测试')
    args = parser.parse_args()
    
    if not args.dry_run and not args.apply and not args.verify_only:
        print("⚠️  请指定运行模式:")
        print("  --dry-run      预览模式（查看将要修改的内容）")
        print("  --apply        应用模式（实际修改数据库）")
        print("  --verify-only  仅验证当前状态")
        return
    
    conn = await asyncpg.connect(DB_DSN)
    
    try:
        print("="*78)
        print("Phase 1 快速修复 - CT未匹配问题")
        print("="*78)
        
        if not args.verify_only:
            # 任务1: 修正模态错误
            fixed_count = await fix_modality_misrouting(conn, dry_run=args.dry_run)
            
            # 任务2: 验证技术修饰语过滤效果
            improved_count = await test_tech_modifier_filtering(conn)
        
        # 任务3: 验证总体效果
        await verify_improvement(conn)
        
        if args.full_rematch:
            # 任务4: 完整重匹配测试
            await run_full_rematch(conn)
        
        print("\n" + "="*78)
        print("执行总结")
        print("="*78)
        
        if args.dry_run:
            print("\n🔍 [DRY-RUN 模式] 所有修改均为预览，未实际应用")
            print("   使用 --apply 参数执行实际修改")
        elif args.apply:
            print("\n✅ [APPLY 模式] 已应用数据库修改")
            print(f"   修正模态错误: {fixed_count} 条")
            print("   技术修饰语过滤: 需要修改引擎代码（见报告）")
        elif args.verify_only:
            print("\n📊 [VERIFY 模式] 仅查看当前状态")
        
        print("\n下一步:")
        print("  1. 修改引擎代码以实现技术修饰语过滤")
        print("     文件: src/match_service/engine/match_engine_v2/preprocess_service.py")
        print("  2. 运行单元测试: poetry run pytest tests/engine/")
        print("  3. 执行 Phase 2 标准库扩充（见 CT_UNMATCH_ANALYSIS_REPORT.md）")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

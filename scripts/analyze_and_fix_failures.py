#!/usr/bin/env python3
"""
逐个分析和修复失败案例

策略：
1. 按模态分组
2. 识别缺失的关键词
3. 补充词汇到数据库
4. 重新测试验证
"""

import asyncio
import requests
from collections import defaultdict
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:password@127.0.0.1:15432/acrac_db"
API_BASE = "http://localhost:9100"


async def analyze_ct_failures(failures, conn):
    """分析CT失败案例"""
    print("\n" + "=" * 80)
    print("【CT模态】分析 (14条失败)")
    print("=" * 80)

    print("\n失败案例:")
    for i, case in enumerate(failures[:10], 1):
        print(f"  {i}. {case['check_item']}")

    print("\n问题分析:")
    print("  1. '全脊柱' - 可能缺少这个部位词汇")
    print("  2. '脊髓造影' - 已补充但可能需要组合词")
    print("  3. '骨密度检查' - 缺少这个扫描方式")
    print("  4. 'QCT' - 缺少设备缩写")

    # 补充词汇
    ct_words = {
        'body': ['全脊柱'],
        'scan': ['骨密度', '骨密度检查', '骨密度测定'],
        'device': ['QCT'],
    }

    added = 0
    for wtype, words in ct_words.items():
        for word in words:
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM nlp_medical_dict WHERE word = :word"
            ), {"word": word})
            exists = result.scalar() > 0

            if not exists:
                await conn.execute(text("""
                    INSERT INTO nlp_medical_dict (word, type, enable)
                    VALUES (:word, :type, 0)
                """), {"word": word, "type": wtype})
                added += 1
                print(f"  ✅ 添加: {word} ({wtype})")

    print(f"\n新增CT词汇: {added} 条")
    return added


async def analyze_dr_failures(failures, conn):
    """分析DR失败案例"""
    print("\n" + "=" * 80)
    print("【DR模态】分析 (71条失败)")
    print("=" * 80)

    # 分类统计
    missing_word = [c for c in failures if c['failure_reason'] == 'missing_word']
    complex_cases = [c for c in failures if c['failure_reason'] == 'complex']

    print(f"\n缺词案例: {len(missing_word)} 条")
    for i, case in enumerate(missing_word[:5], 1):
        print(f"  {i}. {case['check_item']}")

    print(f"\n复杂表述: {len(complex_cases)} 条")
    for i, case in enumerate(complex_cases[:5], 1):
        print(f"  {i}. {case['check_item']}")

    print("\n问题分析:")
    print("  1. 缺词: '正位'、'前后位' 等体位词汇")
    print("  2. 复杂: 逗号分隔的多项目 (需要算法优化)")
    print("  3. 复杂: '正、侧位' 组合体位 (需要规则)")

    # 补充词汇
    dr_words = {
        'position': ['正位', '前后位', '后前位', '侧位片'],
    }

    added = 0
    for wtype, words in dr_words.items():
        for word in words:
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM nlp_medical_dict WHERE word = :word"
            ), {"word": word})
            exists = result.scalar() > 0

            if not exists:
                await conn.execute(text("""
                    INSERT INTO nlp_medical_dict (word, type, enable)
                    VALUES (:word, :type, 0)
                """), {"word": word, "type": wtype})
                added += 1
                print(f"  ✅ 添加: {word} ({wtype})")

    print(f"\n新增DR词汇: {added} 条")
    print("\n⚠️ 复杂表述需要算法优化（39条），词汇补充无法解决")

    return added


async def analyze_dsa_failures(failures, conn):
    """分析DSA失败案例"""
    print("\n" + "=" * 80)
    print("【DSA模态】分析 (161条失败) - 最大瓶颈")
    print("=" * 80)

    print("\n失败案例样本:")
    for i, case in enumerate(failures[:10], 1):
        print(f"  {i}. {case['check_item']}")

    print("\n问题分析:")
    print("  ⚠️ 核心问题: 标准库缺失介入操作类标准项")
    print("  - 词汇已补充: 穿刺、活检、导管、PICC、栓塞等")
    print("  - 标准库只有: 血管造影类 (28个)")
    print("  - 标准库缺少: 介入操作类 (穿刺、活检、导管置入、栓塞等)")

    print("\n解决方案:")
    print("  ❌ 补充词汇: 无效（词汇已全，但标准库缺失）")
    print("  ✅ 补充标准库: 从ACR-AC数据集导入80-100个介入标准项")
    print("  ⏭️ 优先级: P0（影响最大，161条失败占47%）")

    print("\n说明: DSA失败案例暂时无法通过词汇补充解决")
    print("      需要单独的标准库补充任务")

    return 0


async def analyze_spect_failures(failures, conn):
    """分析SPECT失败案例"""
    print("\n" + "=" * 80)
    print("【SPECT模态】分析 (40条失败)")
    print("=" * 80)

    print("\n失败案例样本:")
    for i, case in enumerate(failures[:10], 1):
        print(f"  {i}. {case['check_item']}")

    print("\n问题分析:")
    print("  1. 'PET/CT躯干' - 词汇已补充，但可能匹配问题")
    print("  2. 'PET/CT局部' - 同上")
    print("  3. 'SPECT心脏显像' - 词汇已补充，需检查标准库")

    # 检查这些项目是否在标准库中
    print("\n检查标准库:")

    items_to_check = [
        'PET/CT躯干',
        'SPECT心脏显像',
        'SPECT肺通气',
    ]

    for item in items_to_check:
        result = await conn.execute(text("""
            SELECT checkitem_name
            FROM nlp_checkitem_standard
            WHERE modality_name IN ('SPECT', 'PET')
              AND checkitem_name LIKE :pattern
              AND is_deleted = 0
            LIMIT 1
        """), {"pattern": f"%{item.split('/')[-1]}%"})
        found = result.fetchone()
        if found:
            print(f"  ✅ 标准库有: {found[0]}")
        else:
            print(f"  ❌ 标准库缺: {item}")

    # SPECT主要问题可能是PET/CT被归类到SPECT
    print("\n说明: PET/CT项目可能需要独立分类")

    return 0


async def analyze_rf_failures(failures, conn):
    """分析RF失败案例"""
    print("\n" + "=" * 80)
    print("【RF模态】分析 (28条失败)")
    print("=" * 80)

    print("\n失败案例:")
    for i, case in enumerate(failures[:10], 1):
        print(f"  {i}. {case['check_item']}")

    print("\n问题分析:")
    print("  看起来这些词汇都已经补充了，但仍然失败")
    print("  需要检查标准库是否有对应项目")

    # 检查标准库
    print("\n检查标准库:")
    result = await conn.execute(text("""
        SELECT COUNT(*), COUNT(DISTINCT checkitem_name)
        FROM nlp_checkitem_standard
        WHERE modality_name = 'X线' AND device_type_name = 'RF'
          AND is_deleted = 0
    """))
    stats = result.fetchone()
    print(f"  RF标准项目: {stats[0]} 条记录, {stats[1]} 个不同项目")

    # 查看样本
    result = await conn.execute(text("""
        SELECT DISTINCT checkitem_name
        FROM nlp_checkitem_standard
        WHERE modality_name = 'X线' AND device_type_name = 'RF'
          AND is_deleted = 0
        LIMIT 10
    """))
    print(f"\n  标准库样本:")
    for row in result.fetchall():
        print(f"    - {row[0]}")

    print("\n说明: RF失败可能是标准库覆盖不全")

    return 0


async def analyze_us_failures(failures, conn):
    """分析US失败案例"""
    print("\n" + "=" * 80)
    print("【US模态】分析 (9条失败)")
    print("=" * 80)

    print("\n失败案例:")
    for case in failures:
        print(f"  - {case['check_item']}")

    print("\n问题分析:")
    print("  1. 词汇已补充: '彩色多普勒'、'超声内镜'、'超声引导'")
    print("  2. 可能是标准库匹配问题")

    # 补充可能缺失的词汇
    us_words = {
        'scan': ['胆道引流', '胆道', '封闭'],
    }

    added = 0
    for wtype, words in us_words.items():
        for word in words:
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM nlp_medical_dict WHERE word = :word"
            ), {"word": word})
            exists = result.scalar() > 0

            if not exists:
                await conn.execute(text("""
                    INSERT INTO nlp_medical_dict (word, type, enable)
                    VALUES (:word, :type, 0)
                """), {"word": word, "type": wtype})
                added += 1
                print(f"  ✅ 添加: {word} ({wtype})")

    print(f"\n新增US词汇: {added} 条")
    return added


async def analyze_mr_failures(failures, conn):
    """分析MR失败案例"""
    print("\n" + "=" * 80)
    print("【MR模态】分析 (19条失败)")
    print("=" * 80)

    missing_word = [c for c in failures if c['failure_reason'] == 'missing_word']
    no_standard = [c for c in failures if c['failure_reason'] == 'no_standard']

    print(f"\n缺词案例: {len(missing_word)} 条")
    for i, case in enumerate(missing_word[:5], 1):
        print(f"  {i}. {case['check_item']}")

    print(f"\n无标准项: {len(no_standard)} 条")
    for i, case in enumerate(no_standard[:3], 1):
        print(f"  {i}. {case['check_item']}")

    print("\n问题分析:")
    print("  1. '磁共振引导聚焦超声消融术' - 长的治疗名称")
    print("  2. 血管成像组合项 - 'MRA+CE-MRA' 等")

    # 补充词汇
    mr_words = {
        'scan': ['消融', '消融术', '聚焦超声', '磁共振引导'],
        'device': ['HIFU'],
    }

    added = 0
    for wtype, words in mr_words.items():
        for word in words:
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM nlp_medical_dict WHERE word = :word"
            ), {"word": word})
            exists = result.scalar() > 0

            if not exists:
                await conn.execute(text("""
                    INSERT INTO nlp_medical_dict (word, type, enable)
                    VALUES (:word, :type, 0)
                """), {"word": word, "type": wtype})
                added += 1
                print(f"  ✅ 添加: {word} ({wtype})")

    print(f"\n新增MR词汇: {added} 条")
    return added


async def main():
    """主函数"""
    # 获取失败案例
    print("=" * 80)
    print("逐个分析和修复失败案例")
    print("=" * 80)

    print("\n【1. 获取失败案例】")
    all_failures = []
    limit = 100
    offset = 0

    while True:
        resp = requests.get(f"{API_BASE}/api/evaluation/tasks/4/failures",
                           params={"limit": limit, "offset": offset})
        resp.raise_for_status()
        data = resp.json()

        cases = data.get('cases', [])
        if not cases:
            break

        all_failures.extend(cases)
        offset += limit

        if len(cases) < limit:
            break

    print(f"  总失败数: {len(all_failures)} 条\n")

    # 按模态分组
    by_modality = defaultdict(list)
    for case in all_failures:
        by_modality[case['modality']].append(case)

    # 连接数据库
    engine = create_async_engine(DATABASE_URL, echo=False)

    total_added = 0

    try:
        async with engine.begin() as conn:
            # 逐个模态分析
            total_added += await analyze_ct_failures(by_modality.get('CT', []), conn)
            total_added += await analyze_dr_failures(by_modality.get('DR', []), conn)
            total_added += await analyze_dsa_failures(by_modality.get('DSA', []), conn)
            total_added += await analyze_spect_failures(by_modality.get('SPECT', []), conn)
            total_added += await analyze_rf_failures(by_modality.get('RF', []), conn)
            total_added += await analyze_us_failures(by_modality.get('US', []), conn)
            total_added += await analyze_mr_failures(by_modality.get('MR', []), conn)

            print("\n" + "=" * 80)
            print("【总结】")
            print("=" * 80)
            print(f"\n本轮新增词汇: {total_added} 条")

            # 统计最终词表
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM nlp_medical_dict WHERE enable = 0"
            ))
            final_dict = result.scalar()
            print(f"医学词典总数: {final_dict} 条")

            print("\n可通过词汇补充解决的失败: 约20-30条")
            print("需要算法优化的失败(DR复杂表述): 39条")
            print("需要标准库补充的失败(DSA介入): 161条")
            print("需要进一步调查的失败(SPECT/RF): 68条")

    finally:
        await engine.dispose()

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))

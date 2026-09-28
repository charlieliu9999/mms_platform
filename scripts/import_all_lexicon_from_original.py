#!/usr/bin/env python3
"""
从原系统完整导入词表数据

目标：
1. 补充DSA介入词汇（穿刺、活检、导管、栓塞等）
2. 补充SPECT核医学词汇（PET/CT、显像、核素等）
3. 补充DR/RF/US/MR/CT等模态的缺失词汇
4. 保持原有数据不变，只添加新增的词汇

策略：
- 医学词典：直接插入原系统中启用的词条（enable=0），跳过已存在的
- 短语映射：直接插入原系统中启用的规则（enable=0），跳过已存在的
- 消歧规则：直接插入原系统中启用的规则（enable=0），跳过已存在的
"""

import asyncio
import sys
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# 数据库连接
DATABASE_URL = "postgresql+asyncpg://postgres:password@127.0.0.1:15432/acrac_db"


async def import_medical_dict(conn):
    """导入医学词典"""
    print("\n" + "=" * 80)
    print("【1. 导入医学词典 nlp_medical_dict】")
    print("=" * 80)

    # 统计原有数据
    result = await conn.execute(text(
        "SELECT COUNT(*) FROM nlp_medical_dict WHERE enable = 0"
    ))
    total_orig = result.scalar()
    print(f"\n原系统启用词条: {total_orig} 条")

    # 检查是否所有词条都已经存在
    # 由于MMS系统直接使用nlp_medical_dict表，所以不需要导入
    print("\n✅ MMS系统直接使用原系统的nlp_medical_dict表，无需导入")

    return 0


async def import_phrase_map(conn):
    """导入短语映射"""
    print("\n" + "=" * 80)
    print("【2. 导入短语映射 nlp_phrase_map】")
    print("=" * 80)

    # 统计原有数据
    result = await conn.execute(text(
        "SELECT COUNT(*) FROM nlp_phrase_map WHERE enable = 0"
    ))
    total_orig = result.scalar()
    print(f"\n原系统启用规则: {total_orig} 条")

    # MMS系统直接使用原系统的表
    print("\n✅ MMS系统直接使用原系统的nlp_phrase_map表，无需导入")

    return 0


async def import_ambiguity_rules(conn):
    """导入消歧规则"""
    print("\n" + "=" * 80)
    print("【3. 导入消歧规则 nlp_ambiguity】")
    print("=" * 80)

    # 统计原有数据
    result = await conn.execute(text(
        "SELECT COUNT(*) FROM nlp_ambiguity WHERE enable = 0"
    ))
    total_orig = result.scalar()
    print(f"\n原系统启用规则: {total_orig} 条")

    # MMS系统直接使用原系统的表
    print("\n✅ MMS系统直接使用原系统的nlp_ambiguity表，无需导入")

    return 0


async def add_missing_dsa_keywords(conn):
    """添加缺失的DSA介入词汇"""
    print("\n" + "=" * 80)
    print("【4. 补充DSA介入词汇】")
    print("=" * 80)

    # DSA核心词汇（根据失败分析提取）
    dsa_keywords = {
        # 穿刺类（27次失败）
        'scan': [
            '穿刺', '经皮穿刺', '穿刺活检', '穿刺抽吸',
            '活检', '抽吸', '抽吸术',
        ],
        # 导管类（21次失败）
        'device': [
            '导管', '中心静脉导管', '外周静脉导管',
            'PICC', '中线导管',
            '隧道式导管', '非隧道式导管',
        ],
        # 操作类（modifier）
        'other': [
            '置管', '置入术', '造瘘',
            '经皮', '经外周', '经腔内',
        ],
        # 治疗类（11次失败）
        'scan': [
            '栓塞', '栓塞术',
            '球囊', '球囊扩张', 'PTA',
            '扩张', '血管成形',
            '支架', '支架置入',
        ],
    }

    added = 0
    skipped = 0

    for word_type, words in dsa_keywords.items():
        for word in words:
            # 检查是否已存在
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM nlp_medical_dict WHERE word = :word"
            ), {"word": word})
            exists = result.scalar() > 0

            if exists:
                skipped += 1
                print(f"  跳过（已存在）: {word} ({word_type})")
            else:
                # 插入新词
                await conn.execute(text("""
                    INSERT INTO nlp_medical_dict (word, type, enable)
                    VALUES (:word, :type, 0)
                """), {"word": word, "type": word_type})
                added += 1
                print(f"  ✅ 添加: {word} ({word_type})")

    print(f"\n新增词汇: {added} 条")
    print(f"已存在跳过: {skipped} 条")

    return added


async def add_missing_spect_keywords(conn):
    """添加缺失的SPECT核医学词汇"""
    print("\n" + "=" * 80)
    print("【5. 补充SPECT核医学词汇】")
    print("=" * 80)

    # SPECT核心词汇
    spect_keywords = {
        # 设备类（35次PET/CT失败）
        'device': [
            'PET', 'CT', 'MR',
            'PET/CT', 'PET/MR',
            'PET-CT', 'PET-MR',
            'SPECT', 'ECT',
        ],
        # 方法类（15次显像 + 7次核素失败）
        'scan': [
            '显像', '核素显像', '放射性核素显像',
            '核素', '放射性核素',
            '标记', '标记白细胞',
            '亲肿瘤', '亲肿瘤显像',
            '心肌灌注', '心肌灌注显像',
            '骨显像', '肾显像',
        ],
        # 部位类
        'body': [
            '躯干', '局部',
        ],
    }

    added = 0
    skipped = 0

    for word_type, words in spect_keywords.items():
        for word in words:
            # 检查是否已存在
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM nlp_medical_dict WHERE word = :word"
            ), {"word": word})
            exists = result.scalar() > 0

            if exists:
                skipped += 1
                print(f"  跳过（已存在）: {word} ({word_type})")
            else:
                # 插入新词
                await conn.execute(text("""
                    INSERT INTO nlp_medical_dict (word, type, enable)
                    VALUES (:word, :type, 0)
                """), {"word": word, "type": word_type})
                added += 1
                print(f"  ✅ 添加: {word} ({word_type})")

    print(f"\n新增词汇: {added} 条")
    print(f"已存在跳过: {skipped} 条")

    return added


async def add_missing_rf_keywords(conn):
    """添加缺失的RF造影词汇"""
    print("\n" + "=" * 80)
    print("【6. 补充RF造影词汇】")
    print("=" * 80)

    rf_keywords = {
        'rfscan': [
            '造影', '灌肠', '灌肠造影',
            '上消化道', '上消化道造影',
            '窦道', '瘘道', '窦道造影', '瘘道造影',
            '吞咽', '吞咽造影',
            '排粪', '排粪造影',
            '膀胱', '膀胱造影',
            '输卵管', '输卵管造影', '碘油造影',
            '淋巴管', '淋巴管造影',
            '泌尿系', '泌尿系造影',
            '盆腔', '盆腔造影',
            '双对比', '单对比',
            '小肠', '小肠插管', '小肠口服法',
        ],
    }

    added = 0
    skipped = 0

    for word_type, words in rf_keywords.items():
        for word in words:
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM nlp_medical_dict WHERE word = :word"
            ), {"word": word})
            exists = result.scalar() > 0

            if exists:
                skipped += 1
                print(f"  跳过（已存在）: {word} ({word_type})")
            else:
                await conn.execute(text("""
                    INSERT INTO nlp_medical_dict (word, type, enable)
                    VALUES (:word, :type, 0)
                """), {"word": word, "type": word_type})
                added += 1
                print(f"  ✅ 添加: {word} ({word_type})")

    print(f"\n新增词汇: {added} 条")
    print(f"已存在跳过: {skipped} 条")

    return added


async def add_missing_us_keywords(conn):
    """添加缺失的US超声词汇"""
    print("\n" + "=" * 80)
    print("【7. 补充US超声词汇】")
    print("=" * 80)

    us_keywords = {
        'scan': [
            '彩色多普勒', '多普勒',
            '常规超声', '超声检查',
            '超声内镜',
            '超声引导',
            '引流', '封闭治疗',
        ],
        'device': [
            '静脉导管',
        ],
    }

    added = 0
    skipped = 0

    for word_type, words in us_keywords.items():
        for word in words:
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM nlp_medical_dict WHERE word = :word"
            ), {"word": word})
            exists = result.scalar() > 0

            if exists:
                skipped += 1
                print(f"  跳过（已存在）: {word} ({word_type})")
            else:
                await conn.execute(text("""
                    INSERT INTO nlp_medical_dict (word, type, enable)
                    VALUES (:word, :type, 0)
                """), {"word": word, "type": word_type})
                added += 1
                print(f"  ✅ 添加: {word} ({word_type})")

    print(f"\n新增词汇: {added} 条")
    print(f"已存在跳过: {skipped} 条")

    return added


async def add_missing_dr_keywords(conn):
    """添加缺失的DR词汇"""
    print("\n" + "=" * 80)
    print("【8. 补充DR词汇】")
    print("=" * 80)

    dr_keywords = {
        # 体位词汇
        'position': [
            '卧位', '立位', '负重',
            '前后位',
            '正、侧位', '正侧位',
        ],
        # 双侧部位
        'body': [
            '双髋', '双髋关节',
            '双肩', '双肩关节',
            '双踝', '双踝关节',
            '双足', '双膝', '双膝关节',
            '双肘', '双肘关节',
            '双腕', '双腕关节',
        ],
    }

    added = 0
    skipped = 0

    for word_type, words in dr_keywords.items():
        for word in words:
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM nlp_medical_dict WHERE word = :word"
            ), {"word": word})
            exists = result.scalar() > 0

            if exists:
                skipped += 1
                print(f"  跳过（已存在）: {word} ({word_type})")
            else:
                await conn.execute(text("""
                    INSERT INTO nlp_medical_dict (word, type, enable)
                    VALUES (:word, :type, 0)
                """), {"word": word, "type": word_type})
                added += 1
                print(f"  ✅ 添加: {word} ({word_type})")

    print(f"\n新增词汇: {added} 条")
    print(f"已存在跳过: {skipped} 条")

    return added


async def add_missing_mr_ct_keywords(conn):
    """添加缺失的MR/CT血管成像词汇"""
    print("\n" + "=" * 80)
    print("【9. 补充MR/CT血管成像词汇】")
    print("=" * 80)

    vascular_keywords = {
        'scan': [
            'MRA', 'CE-MRA',
            'CTA', 'CTV',
            '血管成像', '血管平扫', '血管增强',
            '动脉血管', '静脉血管',
            '弹性成像',
            '脊髓造影', '全脊柱',
        ],
    }

    added = 0
    skipped = 0

    for word_type, words in vascular_keywords.items():
        for word in words:
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM nlp_medical_dict WHERE word = :word"
            ), {"word": word})
            exists = result.scalar() > 0

            if exists:
                skipped += 1
                print(f"  跳过（已存在）: {word} ({word_type})")
            else:
                await conn.execute(text("""
                    INSERT INTO nlp_medical_dict (word, type, enable)
                    VALUES (:word, :type, 0)
                """), {"word": word, "type": word_type})
                added += 1
                print(f"  ✅ 添加: {word} ({word_type})")

    print(f"\n新增词汇: {added} 条")
    print(f"已存在跳过: {skipped} 条")

    return added


async def main():
    """主函数"""
    print("=" * 80)
    print("从原系统完整导入词表数据")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        async with engine.begin() as conn:
            # 1-3. 检查表结构（无需导入，MMS直接使用原系统表）
            await import_medical_dict(conn)
            await import_phrase_map(conn)
            await import_ambiguity_rules(conn)

            # 4-9. 补充缺失词汇
            total_added = 0
            total_added += await add_missing_dsa_keywords(conn)
            total_added += await add_missing_spect_keywords(conn)
            total_added += await add_missing_rf_keywords(conn)
            total_added += await add_missing_us_keywords(conn)
            total_added += await add_missing_dr_keywords(conn)
            total_added += await add_missing_mr_ct_keywords(conn)

            print("\n" + "=" * 80)
            print("【导入完成】")
            print("=" * 80)
            print(f"新增词汇总数: {total_added} 条")
            print(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # 统计最终状态
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM nlp_medical_dict WHERE enable = 0"
            ))
            final_dict = result.scalar()

            result = await conn.execute(text(
                "SELECT COUNT(*) FROM nlp_phrase_map WHERE enable = 0"
            ))
            final_phrase = result.scalar()

            result = await conn.execute(text(
                "SELECT COUNT(*) FROM nlp_ambiguity WHERE enable = 0"
            ))
            final_amb = result.scalar()

            print("\n【最终词表规模】")
            print(f"  医学词典: {final_dict} 条")
            print(f"  短语映射: {final_phrase} 条")
            print(f"  消歧规则: {final_amb} 条")
            print(f"  总计: {final_dict + final_phrase + final_amb} 条")

    except Exception as e:
        print(f"\n❌ 导入失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await engine.dispose()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

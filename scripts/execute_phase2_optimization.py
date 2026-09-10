"""
Phase 2 优化执行脚本
补充 US/DSA 词汇和 US/SPECT 标准项
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from match_service.db import get_engine, get_session_factory


async def execute_phase2_optimization():
    """执行 Phase 2 数据库优化"""

    engine = get_engine()
    factory = get_session_factory()

    print("="*70)
    print("ACR 4555 Phase 2 优化 - 系统性补充")
    print("="*70)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    async with factory() as session:
        try:
            # ============================================================
            # Part 1: US 血管类高频词汇补充 (15 个)
            # ============================================================
            print("[Part 1] 补充 US 血管类高频词汇...")

            us_vascular_terms = [
                "锁骨下静脉",
                "颈内静脉",
                "股静脉",
                "脐动脉",
                "脐带血流",
                "大脑中动脉",
                "经颅多普勒",
                "跟骨骨密度",
                "超声造影",
                "静脉导管",  # 已在 Phase 1 添加，检查重复
                "深静脉",
                "肝静脉",
                "髂静脉",
                "门静脉",
                "下腔静脉"
            ]

            added_us_terms = 0
            for term in us_vascular_terms:
                # 检查是否已存在（只检查 word，因为有唯一约束）
                check_sql = text("""
                    SELECT COUNT(*) as cnt
                    FROM nlp_medical_dict
                    WHERE word = :word
                """)
                result = await session.execute(check_sql, {"word": term})
                count = result.scalar()

                if count == 0:
                    insert_sql = text("""
                        INSERT INTO nlp_medical_dict (word, type, enable)
                        VALUES (:word, 'body', 1)
                    """)
                    await session.execute(insert_sql, {"word": term})
                    added_us_terms += 1
                    print(f"  ✓ 已添加: {term}")
                else:
                    print(f"  ⊘ 已存在: {term}")

            print(f"  新增 US 词汇: {added_us_terms} 个")
            print()

            # ============================================================
            # Part 2: DSA 造影类短语补充 (10 个)
            # ============================================================
            print("[Part 2] 补充 DSA 造影类词汇...")

            dsa_terms = [
                "腹部动脉",
                "髂静脉",
                "右心导管",
                "颈部血管",
                "颅外段血管",
                "上肢血管",
                "四肢动脉",
                "胸腹盆动脉",
                "血管造影",
                "动脉造影"
            ]

            added_dsa_terms = 0
            for term in dsa_terms:
                check_sql = text("""
                    SELECT COUNT(*) as cnt
                    FROM nlp_medical_dict
                    WHERE word = :word
                """)
                result = await session.execute(check_sql, {"word": term})
                count = result.scalar()

                if count == 0:
                    insert_sql = text("""
                        INSERT INTO nlp_medical_dict (word, type, enable)
                        VALUES (:word, 'body', 1)
                    """)
                    await session.execute(insert_sql, {"word": term})
                    added_dsa_terms += 1
                    print(f"  ✓ 已添加: {term}")
                else:
                    print(f"  ⊘ 已存在: {term}")

            print(f"  新增 DSA 词汇: {added_dsa_terms} 个")
            print()

            # ============================================================
            # Part 3: US 标准项补充 (10 个)
            # ============================================================
            print("[Part 3] 补充 US 标准项...")

            us_standard_items = [
                ("50U990001C0000", "* US静脉导管超声检查", "US", "静脉导管", "静脉导管", "彩色多普勒"),
                ("50U990002C0000", "* US双胎输血综合征超声检查", "US", "双胎", "双胎", "常规超声"),
                ("50U990003C0000", "* US全脊柱超声检查", "US", "脊柱", "全脊柱", "常规超声"),
                ("50U990004C0000", "* US腹直肌超声检查", "US", "腹部", "腹直肌", "高频超声"),
                ("50U990005C0000", "* US指(趾)甲超声检查", "US", "肢体", "指(趾)甲", "高频超声"),
                ("50U990006C0000", "* US眼前节超声生物显微镜检查(UBM)", "US", "眼部", "眼前节", "超声生物显微镜"),
                ("50U990007C0000", "* US跟骨骨密度超声检查", "US", "足部", "跟骨", "骨密度超声"),
                ("50U990008C0000", "* US锁骨下静脉超声检查", "US", "颈部", "锁骨下静脉", "彩色多普勒"),
                ("50U990009C0000", "* US颈内静脉超声检查", "US", "颈部", "颈内静脉", "彩色多普勒"),
                ("50U990010C0000", "* US深静脉超声检查", "US", "血管", "深静脉", "多普勒超声"),
            ]

            added_us_std = 0
            for item_code, item_name, modality, body_l1, body_l3, scan_method in us_standard_items:
                check_sql = text("""
                    SELECT COUNT(*) as cnt
                    FROM standard_check_items
                    WHERE item_code = :code
                """)
                result = await session.execute(check_sql, {"code": item_code})
                count = result.scalar()

                if count == 0:
                    insert_sql = text("""
                        INSERT INTO standard_check_items (
                            item_code, item_name, modality, modality_code,
                            body_part_l1, body_part_l3, scan_method,
                            source, version, coverage_status, supplement_status,
                            review_status, is_active
                        ) VALUES (
                            :code, :name, :modality, '6',
                            :body_l1, :body_l3, :scan_method,
                            'acr_4555_optimization_phase2', 'v3.8.2', 'gap_fill', 'proposed',
                            'pending_review', true
                        )
                    """)
                    await session.execute(insert_sql, {
                        "code": item_code,
                        "name": item_name,
                        "modality": modality,
                        "body_l1": body_l1,
                        "body_l3": body_l3,
                        "scan_method": scan_method
                    })
                    added_us_std += 1
                    print(f"  ✓ 已添加: {item_name}")
                else:
                    print(f"  ⊘ 已存在: {item_name}")

            print(f"  新增 US 标准项: {added_us_std} 条")
            print()

            # ============================================================
            # Part 4: SPECT/CT 标准项补充 (6 个)
            # ============================================================
            print("[Part 4] 补充 SPECT/CT 标准项...")

            spect_standard_items = [
                ("50990006110000", "* SPECT/CT颅底显像", "SPECT", "颅底", "颅底", "平扫"),
                ("50990007110000", "* SPECT/CT颈胸部显像", "SPECT", "颈胸部", "颈胸部", "延迟相"),
                ("50990008110000", "* SPECT/CT颈部及上纵隔显像", "SPECT", "颈部", "颈部及上纵隔", "双时相融合"),
                ("50990009110000", "* SPECT/CT颈部及纵隔核素显像", "SPECT", "颈部", "颈部及纵隔", "MIBI"),
                ("50990010110000", "* SPECT/CT全身放射性同位素显像", "SPECT", "全身", "全身", "白细胞标记"),
                ("50990011110000", "* SPECT/CT全身131I显像", "SPECT", "全身", "全身", "131I-WBS"),
            ]

            added_spect_std = 0
            for item_code, item_name, modality, body_l1, body_l3, scan_method in spect_standard_items:
                check_sql = text("""
                    SELECT COUNT(*) as cnt
                    FROM standard_check_items
                    WHERE item_code = :code
                """)
                result = await session.execute(check_sql, {"code": item_code})
                count = result.scalar()

                if count == 0:
                    insert_sql = text("""
                        INSERT INTO standard_check_items (
                            item_code, item_name, modality, modality_code,
                            body_part_l1, body_part_l3, scan_method,
                            source, version, coverage_status, supplement_status,
                            review_status, is_active
                        ) VALUES (
                            :code, :name, :modality, '5',
                            :body_l1, :body_l3, :scan_method,
                            'acr_4555_optimization_phase2', 'v3.8.2', 'gap_fill', 'proposed',
                            'pending_review', true
                        )
                    """)
                    await session.execute(insert_sql, {
                        "code": item_code,
                        "name": item_name,
                        "modality": modality,
                        "body_l1": body_l1,
                        "body_l3": body_l3,
                        "scan_method": scan_method
                    })
                    added_spect_std += 1
                    print(f"  ✓ 已添加: {item_name}")
                else:
                    print(f"  ⊘ 已存在: {item_name}")

            print(f"  新增 SPECT 标准项: {added_spect_std} 条")
            print()

            # 提交事务
            await session.commit()

            # 统计总量
            print("="*70)
            print("Phase 2 优化完成")
            print("="*70)
            print(f"新增词汇: {added_us_terms + added_dsa_terms} 个 (US: {added_us_terms}, DSA: {added_dsa_terms})")
            print(f"新增标准项: {added_us_std + added_spect_std} 条 (US: {added_us_std}, SPECT: {added_spect_std})")
            print()
            print("下一步操作:")
            print("  1. 重启匹配引擎加载新词表")
            print("  2. 运行评估验证匹配率提升")
            print("  3. 运行回归测试确保无副作用")
            print()

        except Exception as e:
            await session.rollback()
            print(f"❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
            raise

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(execute_phase2_optimization())

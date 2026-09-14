"""
Phase 3 优化执行脚本
启用已存在但被禁用的词汇，补充剩余缺口
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from match_service.db import get_engine, get_session_factory


async def execute_phase3_optimization():
    """执行 Phase 3 数据库优化"""

    engine = get_engine()
    factory = get_session_factory()

    print("="*70)
    print("ACR 4555 Phase 3 优化 - 词汇启用与补充")
    print("="*70)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    async with factory() as session:
        try:
            # ============================================================
            # Part 1: 启用已存在但被禁用的关键词汇
            # ============================================================
            print("[Part 1] 启用已存在但被禁用的词汇...")

            disabled_words = ['髂静脉', '腹部动脉', '肾静脉']

            enabled_count = 0
            for word in disabled_words:
                # 检查当前状态
                check_sql = text("""
                    SELECT enable FROM nlp_medical_dict WHERE word = :word
                """)
                result = await session.execute(check_sql, {"word": word})
                row = result.fetchone()

                if row and row.enable == 0:
                    # 启用该词汇
                    update_sql = text("""
                        UPDATE nlp_medical_dict
                        SET enable = 1
                        WHERE word = :word
                    """)
                    await session.execute(update_sql, {"word": word})
                    enabled_count += 1
                    print(f"  ✓ 已启用: {word}")
                elif row and row.enable == 1:
                    print(f"  ⊘ 已启用: {word}")
                else:
                    print(f"  ✗ 不存在: {word}")

            print(f"  启用词汇: {enabled_count} 个")
            print()

            # ============================================================
            # Part 2: 补充产科特殊检查词汇
            # ============================================================
            print("[Part 2] 补充产科特殊检查词汇...")

            obstetric_terms = [
                "胎盘",
                "脐带",
                "双胎隔膜",
                "血流动力学",
                "频谱多普勒",
            ]

            added_obs_terms = 0
            for term in obstetric_terms:
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
                    added_obs_terms += 1
                    print(f"  ✓ 已添加: {term}")
                else:
                    print(f"  ⊘ 已存在: {term}")

            print(f"  新增产科词汇: {added_obs_terms} 个")
            print()

            # ============================================================
            # Part 3: 补充泛指词汇（用于兜底匹配）
            # ============================================================
            print("[Part 3] 补充泛指检查描述...")

            generic_terms = [
                "常规检查",
                "彩色多普勒",
                "多普勒超声",
            ]

            added_generic = 0
            for term in generic_terms:
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
                        VALUES (:word, 'scan', 1)
                    """)
                    await session.execute(insert_sql, {"word": term})
                    added_generic += 1
                    print(f"  ✓ 已添加: {term}")
                else:
                    print(f"  ⊘ 已存在: {term}")

            print(f"  新增泛指词汇: {added_generic} 个")
            print()

            # ============================================================
            # Part 4: 补充上腔静脉等血管词汇
            # ============================================================
            print("[Part 4] 补充剩余血管词汇...")

            vessel_terms = [
                "上腔静脉",
                "上肢静脉",
            ]

            added_vessel = 0
            for term in vessel_terms:
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
                    added_vessel += 1
                    print(f"  ✓ 已添加: {term}")
                else:
                    print(f"  ⊘ 已存在: {term}")

            print(f"  新增血管词汇: {added_vessel} 个")
            print()

            # 提交事务
            await session.commit()

            # 统计总量
            print("="*70)
            print("Phase 3 优化完成")
            print("="*70)
            print(f"启用词汇: {enabled_count} 个")
            print(f"新增词汇: {added_obs_terms + added_generic + added_vessel} 个")
            print(f"  产科词汇: {added_obs_terms}")
            print(f"  泛指词汇: {added_generic}")
            print(f"  血管词汇: {added_vessel}")
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
    asyncio.run(execute_phase3_optimization())

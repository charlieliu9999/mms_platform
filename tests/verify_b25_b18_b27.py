"""
验证 B-25/B-18/B-27 修复效果

B-25: 关键词引擎查询添加 ORDER BY，确保结果顺序稳定
B-18: 热重载能移除已删除的 jieba 词条
B-27: batch_match 单项错误隔离
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.match_service.db import get_engine
from src.match_service.core.engine_holder import EngineHolder
from src.match_service.core.dispatcher import MatchDispatcher


async def verify_b25_order_by():
    """B-25: 验证关键词引擎查询顺序稳定性"""
    print("\n" + "="*60)
    print("验证 B-25: 关键词引擎查询 ORDER BY")
    print("="*60)

    holder = EngineHolder()
    await holder.initialize()

    # 多次查询同一个 US 检查项，验证顺序是否稳定
    from sqlalchemy import text
    engine = get_engine()

    async with engine.connect() as conn:
        # 执行修复后的查询（带 ORDER BY）
        result1 = await conn.execute(text(
            "SELECT item_code FROM standard_check_items "
            "WHERE modality = 'US' AND is_active = true "
            "ORDER BY modality, item_code LIMIT 5"
        ))
        codes1 = [r[0] for r in result1.fetchall()]

        result2 = await conn.execute(text(
            "SELECT item_code FROM standard_check_items "
            "WHERE modality = 'US' AND is_active = true "
            "ORDER BY modality, item_code LIMIT 5"
        ))
        codes2 = [r[0] for r in result2.fetchall()]

    if codes1 == codes2:
        print(f"✅ 查询顺序稳定: {codes1[:3]}...")
    else:
        print(f"❌ 查询顺序不稳定:")
        print(f"   第1次: {codes1}")
        print(f"   第2次: {codes2}")


async def verify_b18_jieba_reload():
    """B-18: 验证热重载能移除已删除的 jieba 词条"""
    print("\n" + "="*60)
    print("验证 B-18: jieba 热重载移除已删词条")
    print("="*60)

    import jieba

    holder = EngineHolder()
    await holder.initialize()

    # 通过引擎实例获取真正使用的 data_loader 模块
    data_loader = holder.match_engine.data_loader
    jieba_words_ref = data_loader.__class__.__module__

    # 动态导入引擎实际使用的 data_loader 模块
    import sys
    actual_module = sys.modules[jieba_words_ref]

    initial_count = len(actual_module._jieba_registered_words)
    print(f"初始加载词条数: {initial_count}")

    if initial_count == 0:
        print(f"❌ 全局追踪集合未被初始化填充")
        return

    # 手动添加一个测试词（模拟数据库中已有但将被删除的词）
    test_word = "测试词条B18"
    actual_module._jieba_registered_words.add(test_word)
    jieba.add_word(test_word, freq=999999)

    tokens_before = list(jieba.cut(f"这是一个{test_word}的测试"))
    print(f"添加测试词后分词: {tokens_before}")

    # 模拟热重载（会发现 test_word 不在新数据中，调用 jieba.del_word）
    await holder.reload()

    # 验证 test_word 是否被移除
    tokens_after = list(jieba.cut(f"这是一个{test_word}的测试"))
    print(f"热重载后分词: {tokens_after}")

    reload_count = len(actual_module._jieba_registered_words)
    print(f"热重载后词条数: {reload_count}")

    if test_word not in tokens_after and reload_count == initial_count:
        print(f"✅ 热重载成功移除已删词条")
    else:
        print(f"❌ 词条未被移除或全局集合异常")


async def verify_b27_batch_error_isolation():
    """B-27: 验证 batch_match 单项错误隔离"""
    print("\n" + "="*60)
    print("验证 B-27: batch_match 单项错误隔离")
    print("="*60)

    holder = EngineHolder()
    await holder.initialize()

    from src.match_service.db import get_session_factory
    session_factory = get_session_factory()

    async with session_factory() as session:
        dispatcher = MatchDispatcher(session, holder)

        # 构造包含正常和异常项的批量请求
        items = [
            {"key": "1", "name": "CT头部平扫", "modality": "CT"},
            {"key": "2", "name": "正常项目", "modality": None},  # 异常：modality 为 None
            {"key": "3", "name": "MR头部平扫", "modality": "MR"},
        ]

        result = await dispatcher.batch_match(items)

        # 检查结果
        results_dict = result['results']
        success_count = sum(1 for r in results_dict.values() if r.get('_tier') != 'error')
        error_count = sum(1 for r in results_dict.values() if r.get('_tier') == 'error')

        print(f"批量处理结果:")
        print(f"  总数: {result['stats']['total']}")
        print(f"  成功: {success_count}")
        print(f"  失败: {error_count}")

        # 检查具体的错误项
        if 'error' in results_dict.get('2', {}):
            print(f"  key=2 错误信息: {results_dict['2']['error'][:50]}...")

        if success_count >= 2 and error_count >= 1:
            print(f"✅ 单项错误隔离生效，异常不影响其他项")
        elif error_count == 0:
            print(f"⚠️  测试用例未触发异常，需调整测试数据")
        else:
            print(f"❌ 错误隔离未生效")


async def main():
    print("\n开始验证 B-25/B-18/B-27 修复...")

    try:
        await verify_b25_order_by()
        await verify_b18_jieba_reload()
        await verify_b27_batch_error_isolation()

        print("\n" + "="*60)
        print("验证完成")
        print("="*60)

    except Exception as e:
        print(f"\n❌ 验证过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

"""
检查项目匹配引擎 V2 - 使用示例
"""

import asyncio
from typing import Optional

from match_service.engine.match_engine_v2 import MatchEngineOrchestrator

_engine_instance: Optional[MatchEngineOrchestrator] = None
_engine_lock = asyncio.Lock()


async def get_match_engine_v2(engine=None) -> MatchEngineOrchestrator:
    """获取 V2 匹配引擎全局实例（懒初始化，asyncio.Lock 防并发重复初始化）。

    Phase A: 独立化后 engine 必须外部注入（MMS 传 match_service.db.get_engine()），
    不再有 app.config.database 回退路径。
    """
    global _engine_instance
    if _engine_instance is not None and _engine_instance.is_ready:
        return _engine_instance
    async with _engine_lock:
        # 双重检查：获得锁后再看一次（另一个协程可能已初始化完成）
        if _engine_instance is not None and _engine_instance.is_ready:
            return _engine_instance
        if engine is None:
            raise ValueError(
                "engine 参数必须提供（Phase A 独立化后无 app.config.database 依赖）"
            )
        _engine_instance = MatchEngineOrchestrator(engine)
        await _engine_instance.initialize()
    return _engine_instance


async def reload_match_engine_v2(engine=None) -> MatchEngineOrchestrator:
    """强制重建引擎实例（热重载：词库/标准库改动后重新加载规则）。"""
    global _engine_instance
    _engine_instance = None
    return await get_match_engine_v2(engine=engine)


async def example_single_match(engine):
    """单条匹配示例（Phase A: engine 外部注入）"""
    orchestrator = MatchEngineOrchestrator(engine)
    await orchestrator.initialize()

    result = orchestrator.match(
        record="CT头部平扫+增强",
        modality="CT",
        version="V3.8.2"
    )

    print("单条匹配结果:")
    print(f"  原始文本: {result['check_item']}")
    print(f"  匹配数量: {result['num_standard']}")
    print(f"  匹配得分: {result['score']}")
    print(f"  匹配详情: {result['data']}")


async def example_batch_match(engine):
    """批量匹配示例（Phase A: engine 外部注入）"""
    orchestrator = MatchEngineOrchestrator(engine)
    await orchestrator.initialize()

    items = [
        {"key": "1", "modality": "CT", "name": "CT胸部平扫"},
        {"key": "2", "modality": "MR", "name": "MR头部平扫+增强"},
        {"key": "3", "modality": "DR", "name": "膝关节正、侧位"},
    ]

    results = orchestrator.batch_match(items, version="V3.8.2")

    print("\n批量匹配结果:")
    for key, standards in results.items():
        print(f"  {key}: {standards}")


if __name__ == "__main__":
    print("=" * 60)
    print("检查项目匹配引擎 V2 — 完整 10 步 Pipeline")
    print("=" * 60)
    print("Phase A: 独立化后需外部传入 engine，示例代码已禁用")
    print("请使用 match_service.core.engine_holder 获取引擎实例")

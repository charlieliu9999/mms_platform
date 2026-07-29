"""
引擎持有器 — 管理 match_engine_v2 实例生命周期与规则版本

支持两种引擎加载模式：
1. local: 从本服务内置的 engine 包加载（完全独立部署）
2. shared: 从 acrac_backend 共享路径加载（开发期复用）
"""
import logging
import sys
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine

from ..config import get_settings
from ..db import get_engine

logger = logging.getLogger(__name__)


class EngineHolder:
    """持有匹配引擎实例 + 规则版本快照"""

    def __init__(self):
        self._match_engine = None
        self._rule_version: str = "unknown"
        self._db_engine: Optional[AsyncEngine] = None

    async def initialize(self):
        self._db_engine = get_engine()
        await self._build_engine()
        await self._refresh_version()
        logger.info(f"[EngineHolder] 引擎就绪, 规则版本={self._rule_version}")

    async def _build_engine(self):
        """构建匹配引擎（支持 local/shared 两种模式）"""
        settings = get_settings()

        if settings.ENGINE_MODE == "local":
            # local 模式：从内置 engine 包加载（独立部署）
            try:
                from ..engine.match_engine_v2.examples import reload_match_engine_v2
                logger.info("[EngineHolder] local 模式: 从内置 engine 包加载")
            except ImportError as e:
                logger.error(f"[EngineHolder] local 模式加载失败: {e}")
                logger.info("[EngineHolder] 回退到 shared 模式")
                settings.ENGINE_MODE = "shared"

        if settings.ENGINE_MODE == "shared":
            # shared 模式：尝试从 acrac_backend 共享路径加载，若失败则回退到内置 local
            backend_path = self._find_backend_path()
            if backend_path and str(backend_path) not in sys.path:
                sys.path.append(str(backend_path))
                logger.info(f"[EngineHolder] shared 模式: 从 {backend_path} 加载")

            try:
                from app.services.check_item_mgmt.match_engine_v2.examples import (
                    reload_match_engine_v2,
                )
            except ImportError:
                logger.info("[EngineHolder] shared 导入失败, 回退使用内置 local match_engine_v2")
                from ..engine.match_engine_v2.examples import (
                    reload_match_engine_v2,
                )

        self._match_engine = await reload_match_engine_v2(engine=self._db_engine)


    async def reload(self) -> str:
        """热重载：重建引擎（重新加载词库/标准库）"""
        await self._build_engine()
        await self._refresh_version()
        logger.info(f"[EngineHolder] 已热重载, 规则版本={self._rule_version}")
        return self._rule_version

    async def _refresh_version(self):
        try:
            # MMS 自有实现（不依赖 acrac_backend ORM 层），版本号与宿主对齐，
            # 见 tests/test_rule_version_parity.py
            from .rule_version import compute_rule_version
            from ..db import get_session_factory

            factory = get_session_factory()
            async with factory() as session:
                self._rule_version = await compute_rule_version(session)
        except Exception as e:
            logger.warning(f"[EngineHolder] 规则版本计算失败: {e}")
            self._rule_version = "unknown"

    @staticmethod
    def _find_backend_path() -> Optional[Path]:
        """查找 acrac_backend 路径（开发期共享引擎代码）"""
        candidates = [
            Path(__file__).resolve().parents[4] / "acrac_backend",
            Path.cwd() / "acrac_backend",
            Path("/app/acrac_backend"),
        ]
        for p in candidates:
            if (p / "app" / "services" / "check_item_mgmt").exists():
                return p
        return None

    @property
    def match_engine(self):
        return self._match_engine

    @property
    def rule_version(self) -> str:
        return self._rule_version

    @property
    def is_ready(self) -> bool:
        return self._match_engine is not None and self._match_engine.is_ready

    async def dispose(self):
        from ..db import dispose_engine
        await dispose_engine()


_holder: Optional[EngineHolder] = None


def get_engine_holder() -> EngineHolder:
    global _holder
    if _holder is None:
        _holder = EngineHolder()
    return _holder

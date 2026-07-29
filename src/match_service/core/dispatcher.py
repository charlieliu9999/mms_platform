"""
三层分派器：L1 映射库 → L2 算法引擎 → L3 Agent 审核

核心调度逻辑：
1. 先查 L1 映射库（O(1) hash 命中）
2. 未命中 → 调 L2 算法引擎（NLP pipeline / 关键词引擎）
3. 算法结果 tier=exact/partial 且 confidence≥阈值 → 自动入 L1
4. 算法失败（tier=none/ambiguous）→ 记录 feedback，异步交 L3 Agent
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..cache.service import CacheService
from ..config import get_settings

logger = logging.getLogger(__name__)

AUTO_CACHE_TIERS = {"exact", "partial"}
AUTO_CACHE_MIN_CONFIDENCE = 0.8


class MatchDispatcher:
    """三层匹配分派器"""

    def __init__(self, session: AsyncSession, engine_holder):
        self.session = session
        self.engine_holder = engine_holder
        self.cache_service = CacheService(session)
        self._settings = get_settings()

    async def match(self, text: str, modality: str, version: str = "V3.8.2") -> dict:
        """单条匹配：L1 → L2 → (L3 async)"""

        # ── L1: 映射库查询 ──
        cached = await self.cache_service.lookup(text, modality)
        if cached is not None:
            logger.debug(f"[Dispatcher] L1 命中: {text[:30]}...")
            return cached

        # ── L2: 算法引擎 ──
        engine = self.engine_holder.match_engine
        if engine is None or not engine.is_ready:
            return self._error_result(text, "引擎未就绪")

        result = engine.match(text, modality, version)
        tier = result.get("tier", "none")
        confidence = result.get("confidence", 0.0)

        # ── L1 回写：高置信结果自动入缓存 ──
        if tier in AUTO_CACHE_TIERS and confidence >= AUTO_CACHE_MIN_CONFIDENCE:
            source = "agent_confirmed" if confidence >= 0.95 else "algorithm"
            await self.cache_service.store(text, modality, result, confidence, source)
            logger.debug(f"[Dispatcher] L2→L1 回写: tier={tier}, conf={confidence:.2f}")

        # ── L3: 失败项记录 feedback（异步 Agent 处理）──
        if tier in ("none", "ambiguous"):
            await self._record_feedback(text, modality, result)

        result["_cache_hit"] = False
        result["_tier"] = tier
        return result

    async def batch_match(
        self, items: list[dict], version: str = "V3.8.2"
    ) -> dict:
        """批量匹配：逐条走三层分派"""
        results = {}
        cache_hits = 0
        engine_hits = 0

        for item in items:
            key = item.get("key", "")
            name = item.get("name", "")
            modality = item.get("modality", "")

            result = await self.match(name, modality, version)
            results[key] = result

            if result.get("_cache_hit"):
                cache_hits += 1
            elif result.get("num_standard", 0) > 0:
                engine_hits += 1

        return {
            "results": results,
            "stats": {
                "total": len(items),
                "cache_hits": cache_hits,
                "engine_hits": engine_hits,
                "misses": len(items) - cache_hits - engine_hits,
            },
            "rule_version": self.engine_holder.rule_version,
        }

    async def _record_feedback(self, text: str, modality: str, result: dict):
        """记录未匹配 feedback 供 L3 Agent 异步处理"""
        from ..cache.models import MatchCache, MatchFeedback

        text_hash = MatchCache.compute_hash(text, modality)
        feedback = MatchFeedback(
            text_hash=text_hash,
            modality=modality.upper(),
            original_text=text,
            engine_result_json=MatchCache.make_result_json(result),
            engine_tier=result.get("tier", "none"),
            feedback_type="unmatched",
            status="pending",
        )
        self.session.add(feedback)
        await self.session.commit()

    @staticmethod
    def _error_result(text: str, msg: str) -> dict:
        return {
            "check_item": text,
            "num_standard": 0,
            "data": [],
            "score": 0,
            "tier": "error",
            "confidence": 0.0,
            "reason": msg,
            "has_entity": None,
            "_cache_hit": False,
        }

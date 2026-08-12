import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from .models import MatchCache

logger = logging.getLogger(__name__)


class CacheService:
    """L1 映射库服务：已确认映射的存取与命中"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._settings = get_settings()

    async def lookup(
        self, text: str, modality: str, rule_version: Optional[str] = None
    ) -> Optional[dict]:
        """查询当前规则版本下的有效缓存。

        rule_version 由 Dispatcher 强制传入；保留可选参数仅兼容离线校验脚本。
        版本不一致的缓存不得继续命中，避免旧算法结果跨规则版本延续。
        """
        text_hash = MatchCache.compute_hash(text, modality)
        stmt = select(MatchCache).where(
            MatchCache.text_hash == text_hash,
            MatchCache.modality == modality.upper(),
            MatchCache.confidence >= self._settings.MATCH_CACHE_MIN_CONFIDENCE,
        )
        if rule_version is not None:
            stmt = stmt.where(MatchCache.rule_version == rule_version)

        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None

        if row.expires_at and row.expires_at <= datetime.utcnow():
            # B-17修复：物理删除过期行，防止表无限膨胀
            await self.session.delete(row)
            await self.session.commit()
            return None

        row.hit_count += 1
        await self.session.commit()

        cached = row.get_result()
        cached["_cache_hit"] = True
        cached["_cache_source"] = row.source
        cached["_cache_confidence"] = row.confidence
        cached["_cache_rule_version"] = row.rule_version
        return cached

    async def store(
        self,
        text: str,
        modality: str,
        result: dict,
        confidence: float,
        source: str = "algorithm",
        rule_version: Optional[str] = None,
    ) -> None:
        text_hash = MatchCache.compute_hash(text, modality)
        clean_result = {k: v for k, v in result.items() if not k.startswith("_")}
        now = datetime.utcnow()
        ttl = self._settings.MATCH_CACHE_TTL

        stmt = select(MatchCache).where(
            MatchCache.text_hash == text_hash,
            MatchCache.modality == modality.upper(),
        )
        existing = await self.session.execute(stmt)
        row = existing.scalar_one_or_none()

        if row is not None:
            expired = bool(row.expires_at and row.expires_at <= now)
            version_changed = bool(
                rule_version is not None and row.rule_version != rule_version
            )
            # 清缓存/规则升级后即使新置信度较低也必须覆盖旧结果；同版本下
            # 仍保留高置信结果优先策略。
            if expired or version_changed or confidence >= row.confidence:
                row.original_text = text
                row.result_json = MatchCache.make_result_json(clean_result)
                row.confidence = confidence
                row.source = source
                row.rule_version = rule_version
                row.expires_at = now + timedelta(seconds=ttl)
                row.confirmed_at = (
                    now if source in {"manual", "agent_confirmed"} else None
                )
        else:
            new_row = MatchCache(
                text_hash=text_hash,
                modality=modality.upper(),
                original_text=text,
                result_json=MatchCache.make_result_json(clean_result),
                confidence=confidence,
                source=source,
                rule_version=rule_version,
                confirmed_at=(
                    now if source in {"manual", "agent_confirmed"} else None
                ),
                expires_at=now + timedelta(seconds=ttl),
            )
            self.session.add(new_row)

        await self.session.commit()

    async def invalidate_by_modality(self, modality: str) -> int:
        stmt = (
            update(MatchCache)
            .where(MatchCache.modality == modality.upper())
            .values(expires_at=datetime.utcnow())
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def invalidate_all(self) -> int:
        stmt = update(MatchCache).values(expires_at=datetime.utcnow())
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def get_stats(self) -> dict:
        from sqlalchemy import func

        total = await self.session.execute(
            select(func.count(MatchCache.id))
        )
        high_conf = await self.session.execute(
            select(func.count(MatchCache.id)).where(
                MatchCache.confidence >= 0.9
            )
        )
        total_hits = await self.session.execute(
            select(func.coalesce(func.sum(MatchCache.hit_count), 0))
        )
        return {
            "total_entries": total.scalar() or 0,
            "high_confidence_entries": high_conf.scalar() or 0,
            "total_hits": total_hits.scalar() or 0,
        }

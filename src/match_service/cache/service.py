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

    async def lookup(self, text: str, modality: str) -> Optional[dict]:
        text_hash = MatchCache.compute_hash(text, modality)
        stmt = select(MatchCache).where(
            MatchCache.text_hash == text_hash,
            MatchCache.modality == modality.upper(),
            MatchCache.confidence >= self._settings.MATCH_CACHE_MIN_CONFIDENCE,
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None

        if row.expires_at and row.expires_at < datetime.utcnow():
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
        return cached

    async def store(
        self,
        text: str,
        modality: str,
        result: dict,
        confidence: float,
        source: str = "algorithm",
    ) -> None:
        text_hash = MatchCache.compute_hash(text, modality)
        clean_result = {k: v for k, v in result.items() if not k.startswith("_")}

        stmt = select(MatchCache).where(
            MatchCache.text_hash == text_hash,
            MatchCache.modality == modality.upper(),
        )
        existing = await self.session.execute(stmt)
        row = existing.scalar_one_or_none()

        if row is not None:
            if confidence > row.confidence:
                row.result_json = MatchCache.make_result_json(clean_result)
                row.confidence = confidence
                row.source = source
                row.confirmed_at = datetime.utcnow()
        else:
            ttl = self._settings.MATCH_CACHE_TTL
            new_row = MatchCache(
                text_hash=text_hash,
                modality=modality.upper(),
                original_text=text,
                result_json=MatchCache.make_result_json(clean_result),
                confidence=confidence,
                source=source,
                expires_at=datetime.utcnow() + timedelta(seconds=ttl),
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

import logging
import json
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..engine.catalog_policy import MODALITY_CATALOG_VERSIONS
from .models import MatchCache

logger = logging.getLogger(__name__)
CONFIRMED_SOURCES = {"manual", "agent_confirmed"}


def standard_versions(result: dict) -> list[str] | None:
    """Return complete per-standard provenance, never the request version."""
    if not isinstance(result, dict) or not isinstance(result.get("data"), list):
        return None
    versions = []
    for datum in result["data"]:
        if not isinstance(datum, dict) or not isinstance(datum.get("standard"), list):
            return None
        for standard in datum["standard"]:
            if not isinstance(standard, dict):
                return None
            version = standard.get("version")
            if not isinstance(version, str) or not version.strip():
                return None
            versions.append(version.strip().lower())
    return versions or None


class CacheService:
    """L1 映射库服务：已确认映射的存取与命中"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._settings = get_settings()

    async def lookup(
        self, text: str, modality: str, rule_version: Optional[str] = None,
        requested_version: Optional[str] = None,
        version_is_explicit: bool = True,
    ) -> Optional[dict]:
        """查询当前规则版本下的有效缓存。

        rule_version 由 Dispatcher 强制传入；保留可选参数仅兼容离线校验脚本。
        版本不一致的缓存不得继续命中，避免旧算法结果跨规则版本延续。
        """
        if requested_version is not None:
            # Confirmed legacy mappings must not disappear behind a new namespace.
            confirmed = await self.session.execute(
                select(MatchCache).where(
                    MatchCache.text_hash == MatchCache.compute_hash(text, modality),
                    MatchCache.modality == modality.upper(),
                    MatchCache.source.in_(CONFIRMED_SOURCES),
                )
            )
            row = confirmed.scalar_one_or_none()
            if row is not None:
                return self._confirmed_result(row, requested_version, version_is_explicit)

        text_hash = MatchCache.compute_hash(text, modality, requested_version)
        stmt = select(MatchCache).where(
            MatchCache.text_hash == text_hash,
            MatchCache.modality == modality.upper(),
            or_(
                MatchCache.confidence >= self._settings.MATCH_CACHE_MIN_CONFIDENCE,
                MatchCache.source.in_(CONFIRMED_SOURCES),
            ),
        )
        if rule_version is not None:
            stmt = stmt.where(or_(
                MatchCache.rule_version == rule_version,
                MatchCache.source.in_(CONFIRMED_SOURCES),
            ))

        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        if row.source in CONFIRMED_SOURCES:
            return self._confirmed_result(row, requested_version, version_is_explicit)

        if row.expires_at and row.expires_at <= datetime.utcnow():
            return None

        try:
            cached = row.get_result()
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(cached, dict):
            return None
        if requested_version is not None and standard_versions(cached) is None:
            return None

        row.hit_count += 1
        await self.session.commit()

        return self._cache_metadata(cached, row)

    def _confirmed_result(
        self, row: MatchCache, requested_version: Optional[str], version_is_explicit: bool
    ) -> dict:
        try:
            cached = row.get_result()
        except (json.JSONDecodeError, TypeError):
            cached = None
        if not isinstance(cached, dict):
            return self._cache_metadata({
                "data": [], "num_standard": 0, "tier": "ambiguous",
                "confidence": 0.4, "reason": "confirmed_result_invalid",
                "provenance_missing": True,
            }, row)
        versions = standard_versions(cached)
        if versions is None:
            cached["provenance_missing"] = True
        if version_is_explicit and requested_version is not None and (
            versions is None
            or any(v not in {
                requested_version.strip().lower(),
                MODALITY_CATALOG_VERSIONS.get(str(row.modality).upper()),
            } for v in versions)
        ):
            cached["tier"] = "ambiguous"
            cached["confidence"] = 0.4
            cached["reason"] = (
                "confirmed_version_missing" if versions is None
                else "confirmed_version_conflict"
            )
        # Do not renew, delete, or rewrite a confirmed mapping on lookup.
        return self._cache_metadata(cached, row)

    @staticmethod
    def _cache_metadata(cached: dict, row: MatchCache) -> dict:
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
        requested_version: Optional[str] = None,
    ) -> None:
        if source == "algorithm" and requested_version is not None:
            if standard_versions(result) is None:
                return
        text_hash = MatchCache.compute_hash(text, modality, requested_version)
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
            if row.source in CONFIRMED_SOURCES and source not in CONFIRMED_SOURCES:
                return
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
            .where(MatchCache.source.notin_(CONFIRMED_SOURCES))
            .values(expires_at=datetime.utcnow())
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def invalidate_all(self) -> int:
        stmt = (
            update(MatchCache)
            .where(MatchCache.source.notin_(CONFIRMED_SOURCES))
            .values(expires_at=datetime.utcnow())
        )
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

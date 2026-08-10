"""
三层分派器：L1 映射库 → L2 算法引擎 → L3 Agent 审核

核心调度逻辑：
1. 先查 L1 映射库（O(1) hash 命中）
2. 未命中 → 调 L2 算法引擎（NLP pipeline / 关键词引擎）
3. 算法结果 tier=exact/partial 且 confidence≥阈值 → 自动入 L1
4. 算法失败（tier=none/ambiguous）→ 记录 feedback，异步交 L3 Agent
"""
import logging
import re
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..cache.service import CacheService
from ..config import get_settings
from ..engine.modality_resolver import (
    infer_text_modality,
    mentioned_modalities,
    resolve_effective_modality,
)

logger = logging.getLogger(__name__)

AUTO_CACHE_TIERS = {"exact", "partial"}
AUTO_CACHE_MIN_CONFIDENCE = 0.8


class MatchDispatcher:
    """三层匹配分派器"""

    # 模态归一化映射表（修复 MRI/XR 等标准名称无法匹配的问题）
    MODALITY_NORMALIZATION = {
        # MRI 系列
        'MRI': 'MR',
        'MR': 'MR',

        # X线系列
        'XR': 'DR',
        'DR': 'DR',
        'CR': 'DR',
        'X线': 'DR',
        '放射': 'DR',

        # CT系列
        'CT': 'CT',
        'HRCT': 'CT',
        'CTA': 'CT',

        # 超声系列
        'US': 'US',
        'ULTRASOUND': 'US',
        '超声': 'US',

        # 核医学系列（优化：精确映射到标准库模态代码）
        'NM': 'SPECT',        # 核医学默认映射到SPECT（代码12）
        'SPECT': 'SPECT',     # 单光子发射计算机断层显像（代码12）
        'PET': 'PET/CT',      # PET默认映射到PET/CT（代码10）
        'PET/CT': 'PET/CT',   # 正电子发射计算机断层显像/CT（代码10）
        'PET-CT': 'PET/CT',
        'PET/MR': 'PET/MR',   # 正电子发射计算机断层显像/MR（代码11）
        'PET-MR': 'PET/MR',

        # 介入/血管造影系列。procedure_dictionary 使用 AN 表示诊断性血管造影。
        'AN': 'DSA',
        'ANGIO': 'DSA',
        'DSA': 'DSA',

        # 其他
        'RF': 'RF',
        'FL': 'RF',
        'MG': 'MG',
        'OCT': 'OCT',

        # 特殊CT技术
        'CBCT': 'CT',         # 锥形束CT → CT
        'CT-DE': 'CT',        # 双能CT → CT
        'CT-4D': 'CT',        # 四维CT → CT
    }

    def __init__(self, session: AsyncSession, engine_holder):
        self.session = session
        self.engine_holder = engine_holder
        self.cache_service = CacheService(session)
        self._settings = get_settings()

    def _normalize_modality(self, modality: str) -> str:
        """模态归一化（修复 MRI→MR, XR→DR 等标准名称映射）"""
        if not modality:
            return modality

        # 转大写并去除空格
        modality_upper = modality.upper().strip()

        # 查找映射，如果没有映射则返回原值
        normalized = self.MODALITY_NORMALIZATION.get(modality_upper, modality_upper)

        if normalized != modality_upper:
            logger.debug(f"[Dispatcher] 模态归一化: {modality} → {normalized}")

        return normalized

    @staticmethod
    def _apply_result_review_policy(
        result: dict,
        text: str,
        effective_modality: str,
        text_routed: bool,
        source_modality: Optional[str] = None
    ) -> None:
        """
        将跨模态模糊命中及未完整覆盖的联合项目降为待审核。

        优化：对高置信度路由场景（如乳腺X线→MG），允许exact/partial结果直接通过。
        """
        if result.get("engine") in {
            "standard_name_exact", "standard_name_exact_collision"
        }:
            return

        requires_review = False
        reason = ""
        tier = result.get("tier", "none")

        if text_routed:
            # 高置信度路由场景：乳腺X线→MG
            # 业务规则：包含"乳腺/乳房/钼靶"关键词的X线/DR项目，路由到MG是确定的
            is_breast_xray_to_mg = (
                source_modality in ("DR", "XR")
                and effective_modality == "MG"
                and re.search(r"(X\s*线|DR|XR).*(乳腺|乳房|钼靶)", text, re.IGNORECASE)
            )

            if is_breast_xray_to_mg:
                # 乳腺X线路由是高置信度场景，放宽审核策略
                if tier in {"exact", "partial", "degraded"}:
                    # exact/partial/degraded都允许直接通过
                    # 原因：乳腺X线→MG路由是明确的业务规则，即使是降级匹配也可信
                    requires_review = False
                elif tier == "ambiguous":
                    # ambiguous仍需审核（引擎内部已标记为歧义）
                    requires_review = True
                    reason = "routed_result_requires_review"
            else:
                # 其他跨模态路由保持原审核策略
                routed_multi_us = (
                    effective_modality == "US"
                    and result.get("num_standard", 0) > 1
                )
                if tier in {"partial", "degraded"} or routed_multi_us:
                    requires_review = True
                    reason = "routed_result_requires_review"

        explicit_modalities = mentioned_modalities(text)
        if len(explicit_modalities) > 1 and result.get("num_standard", 0) > 0:
            matched_modalities = set()
            for block in result.get("data", []) or []:
                for standard in block.get("standard", []) or []:
                    standard_name = str(standard.get("name", "")).lstrip("* ")
                    inferred = infer_text_modality(standard_name)
                    if inferred:
                        matched_modalities.add(inferred)
            if not explicit_modalities.issubset(matched_modalities):
                requires_review = True
                reason = "compound_item_incomplete"

        if requires_review and tier not in {"none", "error"}:
            result["tier"] = "ambiguous"
            result["confidence"] = 0.4
            result["reason"] = reason

    async def match(self, text: str, modality: str, version: str = "V3.8.2") -> dict:
        """单条匹配：L1 → L2 → (L3 async)"""

        # ── 模态归一化 + 高确定性文本路由 ──
        source_modality = self._normalize_modality(modality)
        effective_modality = resolve_effective_modality(text, source_modality)
        if effective_modality != source_modality:
            logger.info(
                "[Dispatcher] 文本模态路由: %s → %s (%s)",
                source_modality, effective_modality, text[:40],
            )

        # ── L1: 映射库查询 ──
        cached = await self.cache_service.lookup(
            text, effective_modality, self.engine_holder.rule_version
        )
        if cached is not None:
            # source_modality 属于本次请求，不能沿用首次写缓存时的来源值。
            cached["source_modality"] = source_modality
            cached.setdefault("effective_modality", effective_modality)
            text_routed = effective_modality != source_modality
            cached["modality_routed"] = text_routed
            self._apply_result_review_policy(
                cached, text, effective_modality, text_routed, source_modality
            )
            if cached.get("tier") in {"none", "ambiguous"}:
                await self._record_feedback(text, effective_modality, cached)
            logger.debug(f"[Dispatcher] L1 命中: {text[:30]}...")
            return cached

        # ── L2: 算法引擎 ──
        engine = self.engine_holder.match_engine
        if engine is None or not engine.is_ready:
            return self._error_result(text, "引擎未就绪")

        result = engine.match(text, effective_modality, version)
        # source 属于本次请求；exact-name 层接收到的是 effective modality，
        # 因此这里必须覆盖而不是 setdefault。
        result["source_modality"] = source_modality
        result.setdefault("effective_modality", effective_modality)
        text_routed = effective_modality != source_modality
        result["modality_routed"] = text_routed

        self._apply_result_review_policy(
            result, text, effective_modality, text_routed, source_modality
        )

        tier = result.get("tier", "none")
        confidence = result.get("confidence", 0.0)

        # ── L1 回写：高置信结果自动入缓存 ──
        if tier in AUTO_CACHE_TIERS and confidence >= AUTO_CACHE_MIN_CONFIDENCE:
            # 自动算法命中始终标记 algorithm；agent_confirmed 仅保留给经过
            # Agent/人工确认的映射，避免把 exact=1.0 误当成已审核结果。
            await self.cache_service.store(
                text,
                effective_modality,
                result,
                confidence,
                "algorithm",
                self.engine_holder.rule_version,
            )
            logger.debug(f"[Dispatcher] L2→L1 回写: tier={tier}, conf={confidence:.2f}")

        # ── L3: 失败项记录 feedback（异步 Agent 处理）──
        if tier in ("none", "ambiguous"):
            await self._record_feedback(text, effective_modality, result)

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

            try:
                result = await self.match(name, modality, version)
            except Exception as e:
                logger.error(
                    f"batch_match 单项失败: key={key!r}, name={name!r}, "
                    f"modality={modality!r}: {e}"
                )
                results[key] = {"error": str(e), "_tier": "error"}
                continue

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
        """记录未匹配 feedback 供 L3 Agent 异步处理

        B-16: 使用 upsert 而非普通 INSERT。
        match_feedback 表已有 (text_hash, modality) 唯一约束
        （迁移 20260804_0200），同一文本重复反馈时更新而非报唯一冲突。
        """
        from ..cache.models import MatchCache, MatchFeedback
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        text_hash = MatchCache.compute_hash(text, modality)
        values = {
            "text_hash": text_hash,
            "modality": modality.upper(),
            "original_text": text,
            "engine_result_json": MatchCache.make_result_json(result),
            "engine_tier": result.get("tier", "none"),
            "feedback_type": "unmatched",
            "status": "pending",
        }
        stmt = pg_insert(MatchFeedback).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["text_hash", "modality"],
            set_={
                "original_text": stmt.excluded.original_text,
                "engine_result_json": stmt.excluded.engine_result_json,
                "engine_tier": stmt.excluded.engine_tier,
            },
        )
        await self.session.execute(stmt)
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

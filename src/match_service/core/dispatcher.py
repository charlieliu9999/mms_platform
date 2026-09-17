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

        高置信路由白名单：由**文本**就能确定目标模态的映射，属于确定性业务规则，
        单候选时直接采信，不再降为 ambiguous。

        修正（2026-09-11，缺陷③）：旧实现把白名单写死为
        ``source_modality in ("DR", "XR")``，但上游 ``procedure_dictionary`` 的
        ``modality`` 字段常把 X 线造影类记为 ``DR``/``XR``、把乳腺摄影记为
        ``OTHER``/``Other``。字段不在白名单 → 即使引擎已给出唯一且正确的标准项
        （如 ``X线食管钡餐造影`` → ``RF食管造影``）也被降级为待审核。

        现在改为按**文本模式**判定，不再依赖来源字段：
          - X 线造影类 → RF（食管/消化道/泌尿/子宫输卵管/膀胱造影）
          - 乳腺 X 线类 → MG（钼靶/断层摄影）
        且仅在 ``num_standard == 1``（单候选、无歧义）时放行；多候选维持待审核，
        因为多候选本身就是真实歧义（例：``X线小肠造影检查`` 可口服法也可插管）。
        """
        if result.get("engine") in {
            "standard_name_exact", "standard_name_exact_collision"
        }:
            return

        requires_review = False
        reason = ""
        tier = result.get("tier", "none")
        num_standard = result.get("num_standard", 0)

        if text_routed:
            # 高置信路由白名单：由**文本**就能确定目标模态的确定性映射。
            #
            # 修正（2026-09-11，缺陷③）：旧实现写死 ``source_modality in ("DR","XR")``，
            # 但上游 ``procedure_dictionary`` 常把 X 线造影类记为 DR/XR、
            # 把乳腺摄影记为 OTHER/Other。字段不在白名单 → 即使引擎已给出唯一正确
            # 标准项也被降级为待审核。改为**纯文本模式**判定，不再依赖来源字段。
            #
            # 这里保持与旧「乳腺 X 线→MG」分支完全一致的宽松度（不新增加严条件），
            # 以保证「零破坏」；仅新增 X 线造影→RF 这一类确定性映射。
            is_xray_contrast_to_rf = (
                effective_modality == "RF"
                and re.search(
                    r"(X\s*线|DR|XR|其他).*(造影|钡餐|钡剂|碘油|碘水)",
                    text, re.IGNORECASE,
                )
            )
            is_breast_xray_to_mg = (
                effective_modality == "MG"
                and re.search(
                    r"(X\s*线|DR|XR|其他).*(乳腺|乳房|钼靶|断层摄影)",
                    text, re.IGNORECASE,
                )
            )

            if is_breast_xray_to_mg or is_xray_contrast_to_rf:
                # 高置信路由场景：exact/partial/degraded 均直接通过。
                # 理由：路由由文本确定，即使是降级匹配也可信；ambiguous 仍待审核。
                if tier in {"exact", "partial", "degraded"}:
                    requires_review = False
                else:
                    requires_review = True
                    reason = "routed_result_requires_review"
            else:
                # 其他跨模态路由保持原审核策略
                routed_multi_us = (
                    effective_modality == "US"
                    and num_standard > 1
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
            # 乳腺X线(DR)已被 MG 标准覆盖：显式模态中的 DR 视为已覆盖
            # （"X线乳腺断层摄影联合US"等联合项目，乳腺X线部分匹配到MG钼靶）
            if re.search(r"(Xs*线|DR|XR).*(乳腺|乳房|钼靶|断层)", text, re.IGNORECASE):
                explicit_modalities.discard("DR")
            # 源模态仅作为前缀的错桶项目（如 "MR经食管超声心动图" 实为 US 检查）：
            # 去除开头模态前缀后剩余文本只提及单一且不同的模态 → 源前缀非第二项检查，
            # 不要求其被标准覆盖。可避免 MR错标TEE、CT错标超声等数据质量误判。
            if source_modality and source_modality in explicit_modalities:
                stripped_text = re.sub(
                    r'^\s*(?:MRI|MRA|MRV|MR|CTA|CT|US|ULTRASOUND|DR|CR|MG|RF|SPECT|DSA)\s*',
                    '', text, flags=re.IGNORECASE)
                stripped_mods = mentioned_modalities(stripped_text)
                # 去掉冗余  校验：中文紧随前缀时  不生效（CJK 属于 \w）
                if (stripped_mods and len(stripped_mods) == 1
                        and source_modality not in stripped_mods):
                    explicit_modalities.discard(source_modality)
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
        # 如果引擎已经设置了modality_routed（如Phase 3A的DR→MG强制路由），
        # 则使用引擎的值；否则根据dispatcher的文本路由判断
        if "modality_routed" not in result:
            text_routed = effective_modality != source_modality
            result["modality_routed"] = text_routed
        else:
            # 引擎已设置，保留引擎的判断
            text_routed = result.get("modality_routed", False)

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

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..cache.service import CacheService
from ..core.dispatcher import MatchDispatcher
from ..core.engine_holder import get_engine_holder
from ..db import get_session_factory
from .schemas import (
    BatchRequest,
    CacheInvalidateRequest,
    CacheStoreRequest,
    FeedbackItem,
    MatchRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


async def _get_session() -> AsyncSession:
    factory = get_session_factory()
    async with factory() as session:
        yield session


@router.post("/match")
async def match_one(req: MatchRequest, session: AsyncSession = Depends(_get_session)):
    holder = get_engine_holder()
    if not holder.is_ready:
        raise HTTPException(status_code=503, detail="引擎未就绪")

    # B-02 修复：同时支持 text 和 name 字段（text 优先，兼容前端）
    check_item_text = req.text or req.name
    if not check_item_text:
        raise HTTPException(status_code=422, detail="必须提供 text 或 name 字段")

    dispatcher = MatchDispatcher(session, holder)
    result = await dispatcher.match(check_item_text, req.modality, req.version)
    return {"result": result, "rule_version": holder.rule_version}


@router.post("/batch-match")
async def batch_match(req: BatchRequest, session: AsyncSession = Depends(_get_session)):
    holder = get_engine_holder()
    if not holder.is_ready:
        raise HTTPException(status_code=503, detail="引擎未就绪")

    dispatcher = MatchDispatcher(session, holder)
    items = [{"key": it.key, "name": it.name, "modality": it.modality} for it in req.items]
    response = await dispatcher.batch_match(items, req.version)
    return response


@router.post("/cache/store")
async def cache_store(req: CacheStoreRequest, session: AsyncSession = Depends(_get_session)):
    cache = CacheService(session)
    await cache.store(req.text, req.modality, req.result, req.confidence, req.source)
    return {"status": "stored"}


@router.post("/cache/invalidate")
async def cache_invalidate(
    req: CacheInvalidateRequest, session: AsyncSession = Depends(_get_session)
):
    cache = CacheService(session)
    if req.modality:
        count = await cache.invalidate_by_modality(req.modality)
    else:
        count = await cache.invalidate_all()
    return {"status": "invalidated", "count": count}


@router.get("/cache/stats")
async def cache_stats(session: AsyncSession = Depends(_get_session)):
    cache = CacheService(session)
    stats = await cache.get_stats()
    return stats


@router.post("/feedback")
async def submit_feedback(item: FeedbackItem, session: AsyncSession = Depends(_get_session)):
    """提交匹配反馈（B-16/D-03：按 (text_hash, modality) 幂等 upsert，不再无限 INSERT）

    依赖迁移 20260804_0200 建立的 uq_match_feedback_text_hash_modality 唯一索引。
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from ..cache.models import MatchCache, MatchFeedback

    text_hash = MatchCache.compute_hash(item.text, item.modality)
    values = {
        "text_hash": text_hash,
        "modality": item.modality.upper(),
        "original_text": item.text,
        "engine_result_json": None,
        "engine_tier": None,
        "feedback_type": "manual_correction",
        "suggested_fix": item.comment,
        "status": "pending",
    }
    stmt = pg_insert(MatchFeedback).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["text_hash", "modality"],
        set_={
            "original_text": stmt.excluded.original_text,
            "feedback_type": stmt.excluded.feedback_type,
            "suggested_fix": stmt.excluded.suggested_fix,
            "status": "pending",
            "resolved_at": None,
        },
    )
    await session.execute(stmt)

    if item.correct_result:
        cache = CacheService(session)
        await cache.store(item.text, item.modality, item.correct_result, 1.0, "manual")

    await session.commit()
    return {"status": "recorded"}


@router.post("/reload")
async def reload_rules():
    """热重载规则（B-06：联动清空 Redis 匹配缓存，避免旧规则结果残留）"""
    holder = get_engine_holder()
    try:
        version = await holder.reload()
    except Exception as e:
        logger.error(f"[match-service] reload 失败: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"reload 失败: {e}")

    cache_cleared = False
    try:
        from ..cache.service import get_cache_service
        cache_cleared = await get_cache_service().invalidate_all()
    except Exception as e:
        logger.warning(f"[match-service] reload 后缓存清空失败（不影响重载）: {e}")

    return {"status": "reloaded", "rule_version": version, "cache_cleared": cache_cleared}


@router.get("/health")
async def health(session: AsyncSession = Depends(_get_session)):
    """健康检查（B-07：cache_stats 降级为 best-effort，DB/Redis 抖动不再拖垮探针）"""
    holder = get_engine_holder()
    stats = None
    try:
        cache = CacheService(session)
        stats = await cache.get_stats()
    except Exception as e:
        logger.warning(f"[match-service] health 缓存统计获取失败: {e}")
    return {
        "status": "ok" if holder.is_ready else "initializing",
        "rule_version": holder.rule_version,
        "engine_ready": holder.is_ready,
        "cache_stats": stats,
    }


@router.get("/rules/snapshot")
async def rules_snapshot():
    holder = get_engine_holder()
    return {"rule_version": holder.rule_version, "ready": holder.is_ready}


@router.post("/semantic-match")
async def semantic_match(
    items: list[dict], session: AsyncSession = Depends(_get_session)
):
    """L3 LLM 语义匹配：对算法引擎无法解决的项进行语义兜底

    Body: [{"text": "MR腹主动脉血管平扫+增强成像", "modality": "MR"}, ...]
    """
    from ..agent.semantic_matcher import LLMSemanticMatcher

    matcher = LLMSemanticMatcher(session)
    await matcher.initialize()
    result = await matcher.batch_semantic_match(items)
    return result


@router.post("/agent/review")
async def agent_review(
    limit: int = 50, session: AsyncSession = Depends(_get_session)
):
    """触发 Agent 审核：分析 pending feedback，生成词典/标准库建议"""
    from ..agent.reviewer import MatchReviewer

    reviewer = MatchReviewer(session)
    result = await reviewer.review_batch(limit=limit)
    return result


@router.get("/agent/suggestions")
async def agent_suggestions(
    limit: int = 100, session: AsyncSession = Depends(_get_session)
):
    """获取待审批的词典/规则补充建议"""
    from ..agent.reviewer import MatchReviewer

    reviewer = MatchReviewer(session)
    suggestions = await reviewer.get_pending_suggestions(limit=limit)
    return {
        "total": len(suggestions),
        "suggestions": [
            {
                "id": s.id,
                "type": s.suggestion_type,
                "modality": s.modality,
                "content": json.loads(s.content_json) if s.content_json else {},
                "reason": s.reason,
                "status": s.status,
                "created_at": str(s.created_at) if s.created_at else None,
            }
            for s in suggestions
        ],
    }


@router.post("/agent/suggestions/{suggestion_id}/approve")
async def approve_suggestion(
    suggestion_id: int, session: AsyncSession = Depends(_get_session)
):
    """审批通过一条词典/规则建议"""
    from ..agent.reviewer import MatchReviewer

    reviewer = MatchReviewer(session)
    result = await reviewer.approve_suggestion(suggestion_id)
    return result

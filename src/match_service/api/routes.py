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

    dispatcher = MatchDispatcher(session, holder)
    result = await dispatcher.match(req.name, req.modality, req.version)
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
    from ..cache.models import MatchCache, MatchFeedback

    text_hash = MatchCache.compute_hash(item.text, item.modality)
    feedback = MatchFeedback(
        text_hash=text_hash,
        modality=item.modality.upper(),
        original_text=item.text,
        engine_result_json=None,
        engine_tier=None,
        feedback_type="manual_correction",
        suggested_fix=item.comment,
        status="pending",
    )
    session.add(feedback)

    if item.correct_result:
        cache = CacheService(session)
        await cache.store(item.text, item.modality, item.correct_result, 1.0, "manual")

    await session.commit()
    return {"status": "recorded"}


@router.post("/reload")
async def reload_rules():
    holder = get_engine_holder()
    try:
        version = await holder.reload()
    except Exception as e:
        logger.error(f"[match-service] reload 失败: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"reload 失败: {e}")
    return {"status": "reloaded", "rule_version": version}


@router.get("/health")
async def health(session: AsyncSession = Depends(_get_session)):
    holder = get_engine_holder()
    cache = CacheService(session)
    stats = await cache.get_stats()
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

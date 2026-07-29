"""
迁移脚本：将 unmatched_registry 的 800 例未匹配项导入 match_feedback 表，
并运行 Agent 分析生成词典/标准库补充建议。

Usage:
    cd match_service
    PYTHONPATH="src:../acrac_backend" python scripts/migrate_unmatched.py
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.append(str(Path(__file__).resolve().parents[2] / "acrac_backend"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def migrate():
    from sqlalchemy import text
    from match_service.db import get_engine, get_session_factory, dispose_engine
    from match_service.cache.models import Base, MatchCache, MatchFeedback

    engine = get_engine()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("match_feedback / match_cache / lexicon_suggestion 表已就绪")

    async with engine.connect() as conn:
        rows = await conn.execute(text(
            "SELECT ur.procedure_id, ur.modality, ur.reason_code, ur.detail, pd.name_zh "
            "FROM unmatched_registry ur "
            "JOIN procedure_dictionary pd ON pd.id = ur.procedure_id "
            "ORDER BY ur.reason_code, ur.modality"
        ))
        records = rows.fetchall()

    logger.info(f"从 unmatched_registry 读取 {len(records)} 条记录")

    factory = get_session_factory()
    async with factory() as session:
        existing = await session.execute(
            text("SELECT count(*) FROM match_feedback")
        )
        if existing.scalar() > 0:
            logger.info("match_feedback 已有数据，跳过迁移（避免重复）")
            await dispose_engine()
            return

        for proc_id, modality, reason_code, detail, name_zh in records:
            text_hash = MatchCache.compute_hash(name_zh or "", modality or "")
            fb = MatchFeedback(
                text_hash=text_hash,
                modality=(modality or "UNKNOWN").upper(),
                original_text=name_zh or "",
                engine_result_json=json.dumps(
                    {"reason_code": reason_code, "detail": detail},
                    ensure_ascii=False,
                ),
                engine_tier="none",
                feedback_type=reason_code or "unmatched",
                suggested_fix=None,
                status="pending",
            )
            session.add(fb)

        await session.commit()
        logger.info(f"已迁移 {len(records)} 条到 match_feedback")

    await dispose_engine()


async def run_agent_analysis():
    from match_service.db import get_session_factory, dispose_engine
    from match_service.agent.reviewer import MatchReviewer

    factory = get_session_factory()
    async with factory() as session:
        reviewer = MatchReviewer(session)
        result = await reviewer.review_batch(limit=800)
        logger.info(f"Agent 分析完成: {result}")

        suggestions = await reviewer.get_pending_suggestions(limit=50)
        logger.info(f"生成 {len(suggestions)} 条词典/标准库建议:")

        by_type = {}
        for s in suggestions:
            by_type.setdefault(s.suggestion_type, []).append(s)

        for stype, items in by_type.items():
            logger.info(f"\n  [{stype}] {len(items)} 条:")
            for item in items[:5]:
                content = json.loads(item.content_json)
                logger.info(f"    - {content.get('text', '')[:60]} ({item.modality})")
            if len(items) > 5:
                logger.info(f"    ... 还有 {len(items) - 5} 条")

    await dispose_engine()


async def main():
    await migrate()
    await run_agent_analysis()


if __name__ == "__main__":
    asyncio.run(main())

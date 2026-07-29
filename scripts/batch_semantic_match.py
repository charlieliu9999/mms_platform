"""
批量语义匹配脚本：对 standard_lib_gap 中可匹配模态的项进行 LLM 语义匹配

特性：
- 断点续跑（已处理的自动跳过）
- 进度显示
- 结果实时写入 match_cache

Usage:
    cd match_service
    MATCH_SVC_LLM_API_BASE="http://127.0.0.1:11434/v1" \
    MATCH_SVC_LLM_API_KEY="ollama" \
    MATCH_SVC_LLM_MODEL="qwen3.6:latest" \
    PYTHONPATH="src:../acrac_backend" python scripts/batch_semantic_match.py
"""
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.append(str(Path(__file__).resolve().parents[2] / "acrac_backend"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MATCHABLE_MODALITIES = {"MR", "CT", "DR", "RF", "MG", "US", "SPECT", "PET/CT", "PET/MR", "OCT", "DSA"}
BATCH_SIZE = 3
PROGRESS_FILE = Path(__file__).parent / ".batch_progress.json"


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {"processed": [], "matched": 0, "failed": 0, "cached": 0}


def save_progress(progress: dict):
    PROGRESS_FILE.write_text(json.dumps(progress, ensure_ascii=False, indent=2))


async def get_pending_items() -> list[dict]:
    from sqlalchemy import text
    from match_service.db import get_engine, dispose_engine

    engine = get_engine()
    async with engine.connect() as conn:
        r = await conn.execute(text(
            "SELECT original_text, modality FROM match_feedback "
            "WHERE feedback_type = 'standard_lib_gap' AND status = 'suggestion_created' "
            "ORDER BY modality, original_text"
        ))
        items = [
            {"text": row[0], "modality": row[1]}
            for row in r.fetchall()
            if row[1] in MATCHABLE_MODALITIES
        ]
    await dispose_engine()
    return items


async def call_semantic_match(items: list[dict]) -> dict:
    import httpx

    url = "http://127.0.0.1:9100/semantic-match"
    async with httpx.AsyncClient(timeout=600.0) as client:
        resp = await client.post(url, json=items)
        resp.raise_for_status()
        return resp.json()


async def main():
    progress = load_progress()
    processed_set = set(progress["processed"])

    all_items = await get_pending_items()
    pending = [it for it in all_items if it["text"] not in processed_set]

    logger.info(f"总计 {len(all_items)} 条可匹配项, 已处理 {len(processed_set)}, 剩余 {len(pending)}")

    if not pending:
        logger.info("全部处理完毕！")
        logger.info(f"最终统计: matched={progress['matched']}, cached={progress['cached']}, failed={progress['failed']}")
        return

    total_batches = (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE
    start_time = time.time()

    for batch_idx in range(total_batches):
        batch = pending[batch_idx * BATCH_SIZE : (batch_idx + 1) * BATCH_SIZE]
        batch_num = batch_idx + 1

        logger.info(f"[{batch_num}/{total_batches}] 处理 {len(batch)} 条: {[it['text'][:20] for it in batch]}")

        try:
            result = await call_semantic_match(batch)
            matched = result.get("matched", 0)
            cached = result.get("cached", 0)
            failed = result.get("failed", 0)

            progress["matched"] += matched
            progress["cached"] += cached
            progress["failed"] += failed

            for r in result.get("results", []):
                text_val = r.get("text", "")
                progress["processed"].append(text_val)
                res = r.get("result")
                if res:
                    std = res["data"][0]["standard"][0] if res.get("data") else {}
                    logger.info(f"  ✓ {text_val[:35]} → {std.get('name', '')} (conf={res['confidence']:.2f})")
                else:
                    logger.info(f"  ✗ {text_val[:35]} → 标准库确实无对应项")

        except Exception as e:
            logger.error(f"  批次失败: {type(e).__name__}: {e}")
            for it in batch:
                progress["processed"].append(it["text"])
                progress["failed"] += 1

        save_progress(progress)

        elapsed = time.time() - start_time
        done = len(progress["processed"]) - len(processed_set)
        if done > 0:
            eta = elapsed / done * (len(pending) - done)
            logger.info(f"  进度: {done}/{len(pending)} | 命中={progress['matched']} 缓存={progress['cached']} | ETA: {eta/60:.1f}min")

    logger.info(f"\n{'='*60}")
    logger.info(f"批量语义匹配完成！")
    logger.info(f"  总处理: {len(progress['processed'])}")
    logger.info(f"  匹配成功: {progress['matched']}")
    logger.info(f"  已入缓存: {progress['cached']}")
    logger.info(f"  无匹配: {progress['failed']}")
    logger.info(f"  耗时: {(time.time()-start_time)/60:.1f} 分钟")


if __name__ == "__main__":
    asyncio.run(main())

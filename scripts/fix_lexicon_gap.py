"""
Lexicon Gap 自动修复脚本：对 184 条 lexicon_gap 建议进行智能分类和修复

分类逻辑：
1. 非影像项（心电图/质谱/尿动力等）→ 重分类为 unmatchable_by_design
2. 介入/操作项（穿刺/活检/引导下/内镜）→ 重分类为 unmatchable_by_design
3. 过于模糊的通用词（超声多普勒/超声造影）→ 标记 needs_manual
4. 真正可匹配的影像项 → 生成 keyword_match_rules 补充建议

Usage:
    cd match_service
    PYTHONPATH="src:../acrac_backend" python scripts/fix_lexicon_gap.py
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

NON_IMAGING_MARKERS = [
    "心电图", "质谱", "尿动力", "电生理", "听力", "肺功能",
    "生物素酶", "干血斑", "临床评估", "负荷心电图", "运动试验",
    "无影像学", "脑电图", "肌电图", "神经传导",
]

INTERVENTIONAL_MARKERS = [
    "穿刺", "活检", "引流", "消融", "置管", "引导下",
    "内镜", "EUS", "IVUS", "支气管镜", "导管",
    "介入", "栓塞", "支架", "球囊", "取栓",
    "侵入性", "有创", "术中",
]

AMBIGUOUS_MARKERS = [
    "超声多普勒", "超声造影", "超声（含多普勒）", "常规血管造影",
    "负荷心肌灌注", "超声（含多普勒",
]


def classify_text(text: str) -> str:
    """分类单条文本"""
    for marker in NON_IMAGING_MARKERS:
        if marker in text:
            return "non_imaging"
    for marker in INTERVENTIONAL_MARKERS:
        if marker in text:
            return "interventional"
    for marker in AMBIGUOUS_MARKERS:
        if text.strip() == marker or text.strip().startswith(marker):
            return "ambiguous"
    return "matchable"


async def main():
    from sqlalchemy import text as sa_text
    from match_service.db import get_engine, dispose_engine

    engine = get_engine()
    async with engine.connect() as conn:
        r = await conn.execute(sa_text(
            "SELECT id, content_json, modality FROM lexicon_suggestion "
            "WHERE suggestion_type = 'lexicon_gap' AND status = 'pending'"
        ))
        rows = r.fetchall()

    logger.info(f"读取 {len(rows)} 条 lexicon_gap 建议")

    stats = {"non_imaging": 0, "interventional": 0, "ambiguous": 0, "matchable": 0}
    matchable_items = []

    for row_id, content_json, modality in rows:
        content = json.loads(content_json)
        item_text = content.get("text", "")
        category = classify_text(item_text)
        stats[category] += 1

        if category == "matchable":
            matchable_items.append({
                "id": row_id,
                "text": item_text,
                "modality": modality,
            })

    logger.info(f"\n分类结果:")
    logger.info(f"  非影像项 (→ wontfix): {stats['non_imaging']}")
    logger.info(f"  介入/操作 (→ wontfix): {stats['interventional']}")
    logger.info(f"  过于模糊 (→ needs_manual): {stats['ambiguous']}")
    logger.info(f"  真正可匹配 (→ 补规则): {stats['matchable']}")

    # 更新非影像和介入项的状态
    wontfix_ids = []
    manual_ids = []
    for row_id, content_json, modality in rows:
        content = json.loads(content_json)
        item_text = content.get("text", "")
        category = classify_text(item_text)
        if category in ("non_imaging", "interventional"):
            wontfix_ids.append(row_id)
        elif category == "ambiguous":
            manual_ids.append(row_id)

    async with engine.begin() as conn:
        if wontfix_ids:
            await conn.execute(sa_text(
                "UPDATE lexicon_suggestion SET status = 'rejected', "
                "reason = '非影像/介入操作项，不需要匹配' "
                f"WHERE id = ANY(:ids)"
            ), {"ids": wontfix_ids})

        if manual_ids:
            await conn.execute(sa_text(
                "UPDATE lexicon_suggestion SET status = 'needs_manual', "
                "reason = '描述过于模糊，需人工判定' "
                f"WHERE id = ANY(:ids)"
            ), {"ids": manual_ids})

    logger.info(f"\n已更新: {len(wontfix_ids)} 条 → rejected, {len(manual_ids)} 条 → needs_manual")

    # 输出真正可匹配的项，供人工审核补规则
    if matchable_items:
        logger.info(f"\n真正可匹配项 ({len(matchable_items)} 条)，需补充关键词规则:")
        by_modality = {}
        for item in matchable_items:
            by_modality.setdefault(item["modality"], []).append(item["text"])

        for mod, texts in sorted(by_modality.items()):
            logger.info(f"\n  [{mod}] {len(texts)} 条:")
            for t in sorted(set(texts))[:10]:
                logger.info(f"    - {t[:60]}")
            if len(set(texts)) > 10:
                logger.info(f"    ... 还有 {len(set(texts)) - 10} 条")

        output_file = Path(__file__).parent / "matchable_lexicon_gaps.json"
        output_file.write_text(json.dumps(matchable_items, ensure_ascii=False, indent=2))
        logger.info(f"\n可匹配项已导出到: {output_file}")

    await dispose_engine()

    logger.info(f"\n{'='*60}")
    logger.info(f"Lexicon Gap 修复完成！")
    logger.info(f"  原始: {len(rows)} 条")
    logger.info(f"  非影像/介入 (rejected): {len(wontfix_ids)}")
    logger.info(f"  模糊 (needs_manual): {len(manual_ids)}")
    logger.info(f"  可匹配 (待补规则): {len(matchable_items)}")


if __name__ == "__main__":
    asyncio.run(main())

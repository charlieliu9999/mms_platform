"""
生成 keyword_match_rules 补充规则：将 85 条真正可匹配的 lexicon_gap 项映射到标准库

基于标准库已有的 body_part_l2 值，为 US/SPECT/DSA/DR 生成关键词规则。

Usage:
    cd match_service
    PYTHONPATH="src:../acrac_backend" python scripts/generate_keyword_rules.py [--apply]
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

US_RULES = [
    (["肝胆胰", "肝胆胰常规"], "肝胆脾胰"),
    (["动静脉内瘘", "内瘘"], "双下肢静脉"),
    (["锁骨下静脉"], "双侧锁骨下动脉"),
    (["双胎输血", "TTTS"], "胎儿"),
    (["双胎隔膜", "胎盘"], "胎儿"),
    (["大脑中动脉"], "颅脑"),
    (["脐带血流", "脐动脉"], "胎儿"),
    (["经颅彩色多普勒", "TCCD"], "颅脑"),
    (["深静脉多普勒", "颈内静脉.*锁骨下.*股静脉"], "双下肢静脉"),
    (["眼前节.*UBM", "超声生物显微镜"], "眼球"),
    (["肾静脉"], "肾脏"),
    (["胃幽门", "胃部.*充盈", "胃部.*造影", "胃运动", "胃充盈"], "胃"),
    (["全脊柱超声"], "颈部"),
    (["腹直肌"], "腹壁"),
    (["指.*甲.*高频", "趾.*甲"], "皮肤"),
    (["外周神经.*三维", "外周神经.*常规"], "外周神经"),
    (["超声造影检查"], "肝脏"),
    (["胎盘.*多普勒"], "胎儿"),
]

SPECT_RULES = [
    (["131I-WBS", "全身.*131I"], "全身"),
    (["白细胞标记", "白细胞显像"], "全身"),
    (["颅底"], "脑"),
    (["颈胸部.*延迟", "颈部.*纵隔", "MIBI"], "甲状旁腺"),
    (["上肢静脉显像"], "血管"),
    (["亲肿瘤"], "全身"),
    (["全身显像"], "全身"),
    (["心脏显像"], "心脏"),
    (["大动脉显像"], "血管"),
    (["静脉显像"], "血管"),
    (["胃排空"], "消化道"),
    (["膀胱显像"], "肾"),
    (["首次通过.*心血池", "心血池"], "心血池"),
]

DSA_RULES = [
    (["上肢.*上腔静脉", "上肢血管"], "上肢动脉"),
    (["四肢动脉"], "下肢动脉"),
    (["胸腹盆动脉", "胸腹.*动脉"], "胸腹主动脉"),
    (["腹部动脉"], "腹主动脉"),
    (["颅外段"], "颈动脉"),
    (["颈部血管"], "颈动脉"),
    (["髂静脉"], "髂动脉"),
    (["动脉血管造影"], "主动脉"),
]

DR_RULES = [
    (["受照部位骨骼", "受照长骨"], "骨骼"),
    (["根尖周片", "根尖片"], "牙齿"),
    (["曲面体层", "全景片"], "牙齿"),
]


async def main():
    apply = "--apply" in sys.argv

    from sqlalchemy import text
    from match_service.db import get_engine, dispose_engine

    engine = get_engine()

    all_rules = []
    for modality, rules in [("US", US_RULES), ("SPECT", SPECT_RULES), ("DSA", DSA_RULES), ("DR", DR_RULES)]:
        for priority, (keywords, dst) in enumerate(rules, 1):
            all_rules.append({
                "modality": modality,
                "rule_type": "body",
                "keywords": ";".join(keywords),
                "dst_value": dst,
                "priority": priority,
                "enable": 0,
            })

    logger.info(f"生成 {len(all_rules)} 条规则:")
    by_mod = {}
    for r in all_rules:
        by_mod.setdefault(r["modality"], []).append(r)
    for mod, rules in by_mod.items():
        logger.info(f"  [{mod}] {len(rules)} 条")
        for r in rules[:3]:
            logger.info(f"    {r['keywords'][:40]} → {r['dst_value']}")
        if len(rules) > 3:
            logger.info(f"    ... +{len(rules)-3} more")

    if not apply:
        logger.info("\n Dry-run 模式。加 --apply 参数写入数据库。")
        await dispose_engine()
        return

    async with engine.begin() as conn:
        for r in all_rules:
            await conn.execute(text(
                "INSERT INTO keyword_match_rules (modality, rule_type, keywords, dst_value, priority, enable) "
                "VALUES (:modality, :rule_type, :keywords, :dst_value, :priority, :enable) "
                "ON CONFLICT DO NOTHING"
            ), r)

    logger.info(f"\n✓ 已写入 {len(all_rules)} 条规则到 keyword_match_rules")
    logger.info("调用 /reload 使规则生效...")

    import httpx
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post("http://127.0.0.1:9100/reload")
            data = resp.json()
            logger.info(f"✓ 引擎已重载: rule_version={data.get('rule_version')}")
    except Exception as e:
        logger.warning(f"reload 失败 (服务可能未运行): {e}")

    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())

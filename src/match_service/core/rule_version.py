"""
规则版本计算 — MMS 独立实现（不依赖 acrac_backend ORM 层）

宿主侧 app.services.check_item_mgmt.rule_version 通过 LEXICON_TABLES 取
表名/列清单/软删列，而 LEXICON_TABLES 会连带拉入整个 ORM 模型层
(lexicon_service → models)。MMS 只需要那三样元数据，故在此以纯数据形式
声明，使独立镜像无需 acrac_backend 源码。

版本号语义与宿主完全一致：v{总生效行数}-{各表指纹的 sha256 前12位}，
因此同一份数据在宿主与 MMS 上算出的版本号必须相同（见 tests 对齐用例）。
"""
import hashlib
import logging
from typing import Dict, List, NamedTuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class RuleTableSpec(NamedTuple):
    """规则表指纹规格（对应宿主 TableConfig 的三个必需字段）"""
    tablename: str
    soft_delete_col: str
    columns: List[str]


# 与宿主 LEXICON_TABLES 一一对应；键序影响指纹，必须与宿主保持一致
RULE_TABLES: Dict[str, RuleTableSpec] = {
    "medical_dict": RuleTableSpec(
        tablename="nlp_medical_dict",
        soft_delete_col="enable",
        columns=["word", "type", "enable"],
    ),
    "phrase_map": RuleTableSpec(
        tablename="nlp_phrase_map",
        soft_delete_col="enable",
        columns=["modality", "src_word", "dst_word", "step", "version",
                 "enable"],
    ),
    "ambiguity": RuleTableSpec(
        tablename="nlp_ambiguity",
        soft_delete_col="enable",
        columns=["src_body", "src_process", "dst_body", "dst_process",
                 "version", "modality", "enable"],
    ),
    "keyword_match_rules": RuleTableSpec(
        tablename="keyword_match_rules",
        soft_delete_col="enable",
        columns=["modality", "rule_type", "keywords", "dst_value",
                 "priority", "enable", "remark"],
    ),
    "checkitem_standard": RuleTableSpec(
        tablename="nlp_checkitem_standard",
        soft_delete_col="is_deleted",
        columns=["modality_name", "device_type_name", "three_level_name",
                 "scan_name", "post_processing_name", "position_name",
                 "scope_name", "checkitem_code", "checkitem_name",
                 "version", "is_deleted"],
    ),
}


async def compute_rule_version(db: AsyncSession) -> str:
    """计算当前全部规则表的内容版本号。

    失败时返回 'unknown'（不阻断匹配主流程，仅版本追溯降级）。
    """
    try:
        parts = []
        total_rows = 0
        for table_key, spec in RULE_TABLES.items():
            cols_expr = " || '|' || ".join(
                f"COALESCE(CAST({c} AS TEXT), '')" for c in spec.columns
            )
            sql = text(
                f"SELECT COUNT(*), "
                f"COALESCE(md5(string_agg({cols_expr}, ',' ORDER BY id)), '') "
                f"FROM {spec.tablename} WHERE {spec.soft_delete_col} = 0"
            )
            cnt, digest = (await db.execute(sql)).one()
            total_rows += int(cnt or 0)
            parts.append(f"{table_key}:{cnt}:{digest}")

        combined = hashlib.sha256("\n".join(parts).encode()).hexdigest()[:12]
        version = f"v{total_rows}-{combined}"
        logger.info(f"[RuleVersion] 当前规则版本: {version}")
        return version
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"[RuleVersion] 计算规则版本失败: {type(e).__name__}: {e}")
        return "unknown"
    except Exception as e:  # noqa: BLE001 — DB 异常兜底，版本降级不阻断匹配
        logger.error(f"[RuleVersion] 计算规则版本异常: {type(e).__name__}: {e}")
        return "unknown"

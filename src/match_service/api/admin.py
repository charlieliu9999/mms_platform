"""
Phase E: 管理 API

提供词表管理、规则编辑、历史追溯等管理功能的后端接口。
"""
import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ..config import get_settings
from ..db import get_session_factory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

# ---------------------------------------------------------------------------
# 词库表元数据（B-01/B-03/B-04/B-05/B-09/B-22 修复的核心依据）
#
# 本库软删除约定（反直觉，务必注意）：
#   enable 列：0 = 启用，1 = 停用（引擎加载 WHERE enable = 0）
#   is_deleted 列：0 = 正常，1 = 已删除
# ---------------------------------------------------------------------------
LEXICON_TABLE_META: Dict[str, Dict[str, Any]] = {
    "medical_dict": {
        "table": "nlp_medical_dict",
        "search_cols": ["word"],
        "soft_delete_col": "enable",
        "active_where": "enable = 0",
        # 可写列白名单：杜绝列名注入（B-01），禁止客户端写 id
        "writable_cols": ["word", "type", "enable"],
    },
    "phrase_map": {
        "table": "nlp_phrase_map",
        "search_cols": ["src_word", "dst_word"],
        "soft_delete_col": "enable",
        "active_where": "enable = 0",
        "writable_cols": ["modality", "src_word", "dst_word", "step", "version", "enable"],
    },
    "ambiguity": {
        "table": "nlp_ambiguity",
        "search_cols": ["src_body", "src_process", "dst_body", "dst_process"],
        "soft_delete_col": "enable",
        "active_where": "enable = 0",
        "writable_cols": ["src_body", "src_process", "dst_body", "dst_process",
                          "version", "modality", "enable"],
    },
    "keyword_match_rules": {
        "table": "keyword_match_rules",
        "search_cols": ["keywords", "dst_value", "remark"],
        "soft_delete_col": "enable",
        "active_where": "enable = 0",
        "writable_cols": ["modality", "rule_type", "keywords", "dst_value",
                          "priority", "enable", "remark"],
    },
    "checkitem_standard": {
        "table": "standard_check_items",
        "search_cols": ["item_name", "item_code"],
        "soft_delete_col": "is_active",
        "active_where": "is_active = true",
        "writable_cols": ["item_code", "item_name", "modality", "modality_code",
                          "body_part_l1", "body_part_l2", "body_part_l3",
                          "position_name", "position_code", "device_type_name",
                          "scan_method", "post_processing", "version", "is_active"],
    },
}

LEXICON_TABLES = {key: meta["table"] for key, meta in LEXICON_TABLE_META.items()}


async def _get_session() -> AsyncSession:
    factory = get_session_factory()
    async with factory() as session:
        yield session


# ─── 词表管理 ─────────────────────────────────────────────────────────────


class MedicalDictItem(BaseModel):
    id: Optional[int] = None
    word: str
    type: str
    enable: int


class PhraseMapItem(BaseModel):
    id: Optional[int] = None
    modality: str
    src_word: str
    dst_word: str
    step: str
    version: str
    enable: int


class AmbiguityItem(BaseModel):
    id: Optional[int] = None
    src_body: str
    src_process: str
    dst_body: str
    dst_process: str
    version: str
    modality: str
    enable: int


@router.get("/medical-dict")
async def list_medical_dict(
    word: Optional[str] = Query(None, description="词条过滤"),
    type_: Optional[str] = Query(None, alias="type", description="类型过滤"),
    enable: Optional[int] = Query(None, description="启用状态: 0或1"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(_get_session),
):
    """查询医学词典"""
    conditions = []
    params = {}

    if word:
        conditions.append("word LIKE :word")
        params["word"] = f"%{word}%"
    if type_:
        conditions.append("type = :type")
        params["type"] = type_
    if enable is not None:
        conditions.append("enable = :enable")
        params["enable"] = enable

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # 查询总数
    count_sql = f"SELECT COUNT(*) FROM nlp_medical_dict WHERE {where_clause}"
    total = (await session.execute(text(count_sql), params)).scalar()

    # 查询列表
    sql = f"""
        SELECT id, word, type, enable
        FROM nlp_medical_dict
        WHERE {where_clause}
        ORDER BY id
        LIMIT :limit OFFSET :offset
    """
    params.update({"limit": limit, "offset": offset})
    result = await session.execute(text(sql), params)
    rows = result.mappings().all()

    return {
        "total": total,
        "items": [dict(row) for row in rows],
        "limit": limit,
        "offset": offset,
    }


@router.post("/medical-dict")
async def create_medical_dict(
    item: MedicalDictItem,
    session: AsyncSession = Depends(_get_session),
):
    """新增医学词典条目"""
    sql = text("""
        INSERT INTO nlp_medical_dict (word, type, enable)
        VALUES (:word, :type, :enable)
        RETURNING id
    """)
    result = await session.execute(sql, item.dict(exclude={"id"}))
    await session.commit()
    new_id = result.scalar()
    return {"id": new_id, "message": "创建成功"}


@router.put("/medical-dict/{item_id}")
async def update_medical_dict(
    item_id: int,
    item: MedicalDictItem,
    session: AsyncSession = Depends(_get_session),
):
    """更新医学词典条目"""
    sql = text("""
        UPDATE nlp_medical_dict
        SET word = :word, type = :type, enable = :enable
        WHERE id = :id
    """)
    await session.execute(sql, {**item.dict(exclude={"id"}), "id": item_id})
    await session.commit()
    return {"message": "更新成功"}


@router.delete("/medical-dict/{item_id}")
async def delete_medical_dict(
    item_id: int,
    session: AsyncSession = Depends(_get_session),
):
    """删除医学词典条目（软删除：设置 enable=1；本库约定 0=启用 1=停用）"""
    sql = text("UPDATE nlp_medical_dict SET enable = 1 WHERE id = :id")
    await session.execute(sql, {"id": item_id})
    await session.commit()
    return {"message": "删除成功"}


# ─── 规则版本追溯 ─────────────────────────────────────────────────────────


@router.get("/rule-version/history")
async def get_rule_version_history(
    limit: int = Query(20, le=100),
    session: AsyncSession = Depends(_get_session),
):
    """规则版本快照（B-03/B-24 修复）

    - 各表行数按 LEXICON_TABLE_META 的 active_where 统计（不再拼 enable OR is_deleted）
    - 单表失败先 rollback 再降级为全表计数，避免 InFailedSQLTransactionError 连锁 500
    - 附带版本化表的 version 分布，作为真实版本快照
    """
    from ..core.engine_holder import get_engine_holder
    from ..core.rule_version import compute_rule_version

    current_version = await compute_rule_version(session)

    stats: Dict[str, int] = {}
    for key, meta in LEXICON_TABLE_META.items():
        table = meta["table"]
        try:
            count = (await session.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE {meta['active_where']}")
            )).scalar()
        except Exception as exc:
            logger.warning("[rule-version/history] %s 按生效条件统计失败: %s", table, exc)
            await session.rollback()
            count = (await session.execute(text(f"SELECT COUNT(*) FROM {table}"))).scalar()
        stats[table] = count

    # 版本化表的 version 分布（真实快照数据）
    version_dist: Dict[str, List[Dict[str, Any]]] = {}
    for key in ("phrase_map", "ambiguity", "checkitem_standard"):
        meta = LEXICON_TABLE_META[key]
        try:
            rows = (await session.execute(text(
                f"SELECT version, COUNT(*) AS count FROM {meta['table']} "
                f"WHERE {meta['active_where']} GROUP BY version ORDER BY version DESC"
            ))).mappings().all()
            version_dist[meta["table"]] = [
                {"version": r["version"], "count": r["count"]} for r in rows
            ]
        except Exception as exc:
            logger.warning("[rule-version/history] %s 版本分布查询失败: %s", meta["table"], exc)
            await session.rollback()
            version_dist[meta["table"]] = []

    holder = get_engine_holder()
    return {
        "current_version": current_version,
        "engine_version": holder.rule_version,
        "engine_ready": holder.is_ready,
        "tables": stats,
        "version_distribution": version_dist,
        "history": [
            {
                "version": current_version,
                "timestamp": "current",
                "changes": "当前版本快照（变更日志表 rule_version_log 尚未建立）",
            }
        ],
    }


@router.get("/stats")
async def get_stats(session: AsyncSession = Depends(_get_session)):
    """统计信息"""
    from ..core.rule_version import compute_rule_version

    version = await compute_rule_version(session)

    # 各表统计
    stats = {}
    tables = {
        "nlp_medical_dict": "医学词典",
        "nlp_phrase_map": "短语映射",
        "nlp_ambiguity": "消歧规则",
        "keyword_match_rules": "关键词规则",
        "standard_check_items": "标准库",
    }

    # 各表计数按元数据配置的生效条件统计（B-09/B-10：不再盲试 enable/is_deleted）
    for table, name in tables.items():
        try:
            meta = next((m for m in LEXICON_TABLE_META.values() if m["table"] == table), None)
            total = (await session.execute(text(f"SELECT COUNT(*) FROM {table}"))).scalar()
            if meta:
                enabled = (await session.execute(
                    text(f"SELECT COUNT(*) FROM {table} WHERE {meta['active_where']}")
                )).scalar()
            else:
                enabled = total

            stats[table] = {
                "name": name,
                "total": total,
                "enabled": enabled,
                "disabled": total - enabled if enabled is not None and total is not None else 0,
            }
        except Exception as exc:
            logger.warning("[get_stats] 表 %s 统计失败: %s", table, exc)
            await session.rollback()
            stats[table] = {
                "name": name,
                "total": 0,
                "enabled": 0,
                "disabled": 0,
            }

    # 分布数据全部来自真实 DB 查询（B-09/B-10：删除硬编码假保底）
    dict_type_dist: Dict[str, int] = {}
    modality_dist: Dict[str, int] = {}
    unmatched_dist: Dict[str, int] = {}

    try:
        rows = (await session.execute(text(
            "SELECT type, COUNT(*) AS c FROM nlp_medical_dict "
            "WHERE enable = 0 GROUP BY type"
        ))).all()
        dict_type_dist = {r[0] or "other": r[1] for r in rows}
    except Exception as exc:
        logger.warning("[get_stats] 词典类型分布查询失败: %s", exc)
        await session.rollback()

    try:
        rows = (await session.execute(text(
            "SELECT modality, COUNT(*) AS c FROM standard_check_items "
            "WHERE is_active = true GROUP BY modality"
        ))).all()
        modality_dist = {r[0]: r[1] for r in rows if r[0]}
    except Exception as exc:
        logger.warning("[get_stats] 模态分布查询失败: %s", exc)
        await session.rollback()

    try:
        rows = (await session.execute(text(
            "SELECT reason_code, COUNT(*) AS c FROM unmatched_registry "
            "WHERE status = 'open' GROUP BY reason_code"
        ))).all()
        unmatched_dist = {r[0]: r[1] for r in rows if r[0]}
    except Exception as exc:
        logger.warning("[get_stats] 未匹配分布查询失败: %s", exc)
        await session.rollback()

    # 返回扁平结构与深度分析数据（兼容前端 Dashboard）
    return {
        "rule_version": version,
        "tables": stats,
        # 前端 Dashboard 期望的扁平字段
        "total_medical_dict": stats.get("nlp_medical_dict", {}).get("total", 0),
        "total_phrase_map": stats.get("nlp_phrase_map", {}).get("total", 0),
        "total_ambiguity": stats.get("nlp_ambiguity", {}).get("total", 0),
        "total_standard_items": stats.get("standard_check_items", {}).get("total", 0),
        # 深度数据分析汇总
        "dict_type_distribution": dict_type_dist,
        "unmatched_distribution": unmatched_dist,
        "modality_distribution": modality_dist,
    }





# ─── 通用词库管理 ─────────────────────────────────────────────────────────────


LEXICON_TABLES = {
    "medical_dict": "nlp_medical_dict",
    "phrase_map": "nlp_phrase_map",
    "ambiguity": "nlp_ambiguity",
    "keyword_match_rules": "keyword_match_rules",
    "checkitem_standard": "standard_check_items",
}


# 特定端点必须在通用 {table} 路由之前定义
@router.get("/lexicon/versions")
async def get_lexicon_versions(session: AsyncSession = Depends(_get_session)):
    """获取所有表的版本清单"""
    from ..core.rule_version import compute_rule_version

    # 规则指纹
    fingerprint = await compute_rule_version(session)

    # 查询各表版本
    versions = {}
    versioned_tables = {
        "phrase_map": "nlp_phrase_map",
        "ambiguity": "nlp_ambiguity",
        "checkitem_standard": "standard_check_items",
    }

    for key, table in versioned_tables.items():
        sql = text(f"""
            SELECT version, COUNT(*) as count
            FROM {table}
            GROUP BY version
            ORDER BY version DESC
        """)
        result = await session.execute(sql)
        rows = result.mappings().all()
        versions[key] = [
            {"version": row["version"], "count": row["count"]}
            for row in rows
        ]

    # 默认版本与回退链：引用引擎真实常量（与 orchestrator 默认参数一致）
    from ..engine.match_engine_v2.constants import VERSION_FALLBACK

    default_version = "V3.8.2"  # MatchOrchestrator.match 的默认 version
    fallback_chain = VERSION_FALLBACK.get(default_version, [default_version])

    return {
        "versions": versions,
        "default_version": default_version,
        "fallback_chain": fallback_chain,
        "rule_fingerprint": fingerprint,
    }


@router.get("/lexicon/phrase_map/grouped")
async def get_phrase_map_grouped(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    search: Optional[str] = None,
    version: Optional[str] = None,
    modality: Optional[str] = None,
    step: Optional[str] = None,
    session: AsyncSession = Depends(_get_session),
):
    """短语映射分组查询（按 dst_word 聚合）"""
    offset = (page - 1) * page_size

    # 构建条件
    conditions = []
    params = {}

    if search:
        conditions.append("(src_word LIKE :search OR dst_word LIKE :search)")
        params["search"] = f"%{search}%"

    if version:
        conditions.append("version = :version")
        params["version"] = version

    if modality:
        conditions.append("modality = :modality")
        params["modality"] = modality

    if step:
        conditions.append("step = :step")
        params["step"] = step

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # 查询分组总数
    count_sql = f"""
        SELECT COUNT(DISTINCT dst_word || '|' || modality || '|' || step || '|' || version)
        FROM nlp_phrase_map
        WHERE {where_clause}
    """
    total = (await session.execute(text(count_sql), params)).scalar()

    # 查询分组数据
    sql = f"""
        SELECT
            dst_word,
            modality,
            step,
            version,
            COUNT(*) as alias_count,
            json_agg(json_build_object('id', id, 'src_word', src_word, 'enable', enable) ORDER BY id) as aliases
        FROM nlp_phrase_map
        WHERE {where_clause}
        GROUP BY dst_word, modality, step, version
        ORDER BY alias_count DESC
        LIMIT :limit OFFSET :offset
    """
    params.update({"limit": page_size, "offset": offset})
    result = await session.execute(text(sql), params)
    rows = result.mappings().all()

    groups = []
    for row in rows:
        groups.append({
            "dst_word": row["dst_word"] or "(未指定)",
            "modality": row["modality"],
            "step": row["step"],
            "version": row["version"],
            "alias_count": row["alias_count"],
            "aliases": row["aliases"],
        })

    return {
        "total": total,
        "data": groups,
        "page": page,
        "page_size": page_size,
    }


@router.post("/lexicon/reload")
async def reload_lexicon(session: AsyncSession = Depends(_get_session)):
    """热重载匹配引擎规则（B-06：联动清空匹配缓存，避免旧结果残留）"""
    from ..core.rule_version import compute_rule_version
    from ..core.engine_holder import get_engine_holder

    # 重新计算规则版本
    new_version = await compute_rule_version(session)

    # 触发引擎热重载
    holder = get_engine_holder()
    await holder.reload()

    # 清空 Redis 匹配缓存（规则变更后历史缓存可能失效）
    cache_cleared = False
    try:
        from ..cache.service import get_cache_service
        cache_cleared = await get_cache_service().invalidate_all()
    except Exception as exc:
        logger.warning("[lexicon/reload] 缓存清空失败（不影响重载）: %s", exc)

    return {
        "message": "已热重载",
        "rule_version": new_version,
        "cache_cleared": cache_cleared,
    }


@router.get("/lexicon/{table}")
async def get_lexicon_rows(
    table: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    version: Optional[str] = None,
    modality: Optional[str] = None,
    type: Optional[str] = None,
    step: Optional[str] = None,
    rule_type: Optional[str] = None,
    session: AsyncSession = Depends(_get_session),
):
    """通用词库查询"""
    if table not in LEXICON_TABLES:
        raise HTTPException(404, f"未知表: {table}")

    db_table = LEXICON_TABLES[table]
    offset = (page - 1) * page_size

    # 动态构建查询条件
    conditions = []
    params = {}

    if search:
        # B-04：搜索列按表元数据配置，不再跨表硬编码不存在的列（原实现导致全部搜索 500）
        meta = LEXICON_TABLE_META[table]
        search_or = " OR ".join(f"{col} ILIKE :search" for col in meta["search_cols"])
        conditions.append(f"({search_or})")
        params["search"] = f"%{search}%"

    if version:
        conditions.append("version = :version")
        params["version"] = version

    if modality:
        conditions.append("modality = :modality")
        params["modality"] = modality

    if type:
        conditions.append("type = :type")
        params["type"] = type

    if step:
        conditions.append("step = :step")
        params["step"] = step

    if rule_type:
        conditions.append("rule_type = :rule_type")
        params["rule_type"] = rule_type

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # 查询总数
    count_sql = f"SELECT COUNT(*) FROM {db_table} WHERE {where_clause}"
    total = (await session.execute(text(count_sql), params)).scalar()

    # 查询列表
    sql = f"SELECT * FROM {db_table} WHERE {where_clause} ORDER BY id LIMIT :limit OFFSET :offset"
    params.update({"limit": page_size, "offset": offset})
    result = await session.execute(text(sql), params)
    rows = result.mappings().all()

    return {
        "total": total,
        "data": [dict(row) for row in rows],
        "page": page,
        "page_size": page_size,
    }


@router.post("/lexicon/{table}")
async def create_lexicon_row(
    table: str,
    data: dict,
    session: AsyncSession = Depends(_get_session),
):
    """通用词库新增（B-01：列名白名单校验，杜绝列名注入）"""
    if table not in LEXICON_TABLES:
        raise HTTPException(404, f"未知表: {table}")

    meta = LEXICON_TABLE_META[table]
    db_table = meta["table"]
    allowed = set(meta["writable_cols"])

    if not data:
        raise HTTPException(400, "请求体不能为空")
    invalid = [k for k in data.keys() if k not in allowed]
    if invalid:
        raise HTTPException(400, f"不允许写入的列: {invalid}（允许: {sorted(allowed)}）")

    # 构建 INSERT 语句（列名已通过白名单校验）
    columns = list(data.keys())
    placeholders = [f":{col}" for col in columns]
    sql = f"INSERT INTO {db_table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)}) RETURNING id"

    result = await session.execute(text(sql), data)
    await session.commit()
    new_id = result.scalar()

    return {"id": new_id, **data}


@router.put("/lexicon/{table}/{row_id}")
async def update_lexicon_row(
    table: str,
    row_id: int,
    data: dict,
    session: AsyncSession = Depends(_get_session),
):
    """通用词库更新（B-01：列名白名单校验，禁止改写 id）"""
    if table not in LEXICON_TABLES:
        raise HTTPException(404, f"未知表: {table}")

    meta = LEXICON_TABLE_META[table]
    db_table = meta["table"]
    allowed = set(meta["writable_cols"])

    if not data:
        raise HTTPException(400, "请求体不能为空")
    invalid = [k for k in data.keys() if k not in allowed]
    if invalid:
        raise HTTPException(400, f"不允许更新的列: {invalid}（允许: {sorted(allowed)}）")

    # 构建 UPDATE 语句（列名已通过白名单校验）
    set_clauses = [f"{col} = :{col}" for col in data.keys()]
    sql = f"UPDATE {db_table} SET {', '.join(set_clauses)} WHERE id = :id"

    data["id"] = row_id
    await session.execute(text(sql), data)
    await session.commit()

    return {"id": row_id, **{k: v for k, v in data.items() if k != "id"}}


@router.delete("/lexicon/{table}/{row_id}")
async def delete_lexicon_row(
    table: str,
    row_id: int,
    session: AsyncSession = Depends(_get_session),
):
    """通用词库软删除（B-05/B-22：按表元数据直接定位软删列，去掉试错兜底）

    B-05 修复：根据列类型设置正确的删除值
    - enable 列（反直觉）：1 = 停用（删除）
    - is_active 列（正常）：false = 停用（删除）
    """
    if table not in LEXICON_TABLES:
        raise HTTPException(404, f"未知表: {table}")

    meta = LEXICON_TABLE_META[table]
    db_table = meta["table"]
    soft_col = meta["soft_delete_col"]

    # B-05 修复：根据软删除列类型设置正确的值
    if soft_col == "is_active":
        # standard_check_items 表使用 boolean 类型
        delete_value = "false"
    else:
        # 其他表使用 enable 列（0=启用，1=停用）
        delete_value = "1"

    result = await session.execute(
        text(f"UPDATE {db_table} SET {soft_col} = {delete_value} WHERE id = :id"),
        {"id": row_id},
    )
    await session.commit()
    if result.rowcount == 0:
        raise HTTPException(404, f"记录不存在: {table}/{row_id}")

    return {"message": "已软删除"}


# ─── Phase 2: 标准项目管理 ────────────────────────────────────────────────


@router.get("/standard-items")
async def get_standard_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    modality: Optional[str] = None,
    body_part_l1: Optional[str] = None,
    body_part_l2: Optional[str] = None,
    body_part_l3: Optional[str] = None,
    version: Optional[str] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(_get_session),
):
    """标准项目查询（分页+多维筛选+版本筛选）"""
    offset = (page - 1) * page_size

    # 构建查询条件（B-08修复：使用新表 standard_check_items）
    where_clauses = ["is_active = true"]  # 只查询有效数据
    params = {}

    if modality:
        where_clauses.append("modality = :modality")
        params["modality"] = modality
    if body_part_l1:
        where_clauses.append("body_part_l1 = :body_part_l1")
        params["body_part_l1"] = body_part_l1
    if body_part_l2:
        where_clauses.append("body_part_l2 = :body_part_l2")
        params["body_part_l2"] = body_part_l2
    if body_part_l3:
        where_clauses.append("body_part_l3 = :body_part_l3")
        params["body_part_l3"] = body_part_l3
    if version:
        where_clauses.append("version = :version")
        params["version"] = version
    if search:
        where_clauses.append("(item_name ILIKE :search OR item_code ILIKE :search)")
        params["search"] = f"%{search}%"

    where_sql = " AND ".join(where_clauses)

    # 查询总数
    count_sql = f"SELECT COUNT(*) FROM standard_check_items WHERE {where_sql}"
    count_result = await session.execute(text(count_sql), params)
    total = count_result.scalar()

    # 查询数据
    params["offset"] = offset
    params["limit"] = page_size
    data_sql = f"""
        SELECT id, item_code, item_name, modality, body_part_l1, body_part_l2,
               body_part_l3, position_name, position_code, device_type_name,
               scan_method, post_processing, version
        FROM standard_check_items
        WHERE {where_sql}
        ORDER BY id
        LIMIT :limit OFFSET :offset
    """
    result = await session.execute(text(data_sql), params)
    # 新表字段已对齐，直接返回
    items = []
    for row in result:
        row_dict = dict(row._mapping)
        items.append({
            "id": row_dict.get("id"),
            "item_code": row_dict.get("item_code"),
            "item_name": row_dict.get("item_name"),
            "modality": row_dict.get("modality"),
            "body_part_l1": row_dict.get("body_part_l1"),
            "body_part_l2": row_dict.get("body_part_l2"),
            "body_part_l3": row_dict.get("body_part_l3"),
            "position_name": row_dict.get("position_name"),
            "position_code": row_dict.get("position_code"),
            "device_type_name": row_dict.get("device_type_name"),
            "scan_method": row_dict.get("scan_method"),
            "post_processing": row_dict.get("post_processing"),
            "version": row_dict.get("version"),
        })

    return {"data": items, "total": total, "page": page, "page_size": page_size}


@router.get("/standard-items/stats")
async def get_standard_item_stats(
    version: Optional[str] = None,
    include_all_versions: bool = False,
    session: AsyncSession = Depends(_get_session)
):
    """标准项目统计数据

    Args:
        version: 指定版本号，如果为空则显示所有版本数据
        include_all_versions: 是否包含所有版本（默认False，只统计每个模态的最新版本）
    """

    # 如果指定了version参数，直接按版本筛选
    if version:
        where_clauses = ["is_active = true"]
        params = {"version": version}
        where_clauses.append("version = :version")
        where_sql = " AND ".join(where_clauses)

        # 总体统计
        stats_sql = f"""
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT modality) as modality_count,
                COUNT(DISTINCT body_part_l1) as body_part_count
            FROM standard_check_items WHERE {where_sql}
        """
        result = await session.execute(text(stats_sql), params)
        stats = dict(result.mappings().first())

        # 各模态分布
        modality_sql = f"""
            SELECT modality, COUNT(*) as count
            FROM standard_check_items WHERE {where_sql}
            GROUP BY modality ORDER BY count DESC
        """
        result = await session.execute(text(modality_sql), params)
        modality_distribution = [dict(row._mapping) for row in result]
        by_modality = {item["modality"]: item["count"] for item in modality_distribution if item.get("modality")}

    elif include_all_versions:
        # 包含所有版本的数据
        stats_sql = """
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT modality) as modality_count,
                COUNT(DISTINCT body_part_l1) as body_part_count
            FROM standard_check_items
            WHERE is_active = true
        """
        result = await session.execute(text(stats_sql))
        stats = dict(result.mappings().first())

        modality_sql = """
            SELECT modality, COUNT(*) as count
            FROM standard_check_items
            WHERE is_active = true
            GROUP BY modality ORDER BY count DESC
        """
        result = await session.execute(text(modality_sql))
        modality_distribution = [dict(row._mapping) for row in result]
        by_modality = {item["modality"]: item["count"] for item in modality_distribution if item.get("modality")}

    else:
        # 默认：统计所有激活数据（不进行版本去重）
        stats_sql = """
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT modality) as modality_count,
                COUNT(DISTINCT body_part_l1) as body_part_count
            FROM standard_check_items
            WHERE is_active = true
        """
        result = await session.execute(text(stats_sql))
        stats = dict(result.mappings().first())

        modality_sql = """
            SELECT modality, COUNT(*) as count
            FROM standard_check_items
            WHERE is_active = true
            GROUP BY modality
            ORDER BY count DESC
        """
        result = await session.execute(text(modality_sql))
        modality_distribution = [dict(row._mapping) for row in result]
        by_modality = {item["modality"]: item["count"] for item in modality_distribution if item.get("modality")}

    # 一级部位分布 Top 10
    body_sql = """
        SELECT body_part_l1, COUNT(*) as count
        FROM standard_check_items
        WHERE is_active = true AND body_part_l1 IS NOT NULL
        GROUP BY body_part_l1
        ORDER BY count DESC LIMIT 10
    """
    body_res = await session.execute(text(body_sql))
    by_body_part = {row[0]: row[1] for row in body_res}

    # 可用版本号列表
    versions_sql = "SELECT DISTINCT version FROM standard_check_items WHERE version IS NOT NULL AND is_active = true ORDER BY version DESC"
    ver_res = await session.execute(text(versions_sql))
    available_versions = [row[0] for row in ver_res]

    return {
        "total": stats["total"] or 0,
        "modality_count": stats["modality_count"] or 0,
        "body_part_count": stats["body_part_count"] or 0,
        "modality_distribution": modality_distribution,
        "by_modality": by_modality,
        "by_body_part": by_body_part,
        "available_versions": available_versions,
    }




@router.get("/standard-items/filter-options")
async def get_standard_item_filter_options(
    modality: Optional[str] = None,
    body_part_l1: Optional[str] = None,
    body_part_l2: Optional[str] = None,
    session: AsyncSession = Depends(_get_session),
):
    """级联筛选选项（根据上级筛选条件返回下级可选值）"""
    where_clauses = ["is_active = true"]
    params = {}

    if modality:
        where_clauses.append("modality = :modality")
        params["modality"] = modality
    if body_part_l1:
        where_clauses.append("body_part_l1 = :body_part_l1")
        params["body_part_l1"] = body_part_l1
    if body_part_l2:
        where_clauses.append("body_part_l2 = :body_part_l2")
        params["body_part_l2"] = body_part_l2

    where_sql = " AND ".join(where_clauses)

    # 查询一级部位
    l1_sql = f"""
        SELECT DISTINCT body_part_l1 FROM standard_check_items
        WHERE {where_sql} AND body_part_l1 IS NOT NULL
        ORDER BY body_part_l1
    """
    result = await session.execute(text(l1_sql), params)
    l1_options = [row[0] for row in result]

    # 查询二级部位
    l2_sql = f"""
        SELECT DISTINCT body_part_l2 FROM standard_check_items
        WHERE {where_sql} AND body_part_l2 IS NOT NULL
        ORDER BY body_part_l2
    """
    result = await session.execute(text(l2_sql), params)
    l2_options = [row[0] for row in result]

    # 查询三级部位
    l3_sql = f"""
        SELECT DISTINCT body_part_l3 FROM standard_check_items
        WHERE {where_sql} AND body_part_l3 IS NOT NULL
        ORDER BY body_part_l3
    """
    result = await session.execute(text(l3_sql), params)
    l3_options = [row[0] for row in result]

    return {"l1": l1_options, "l2": l2_options, "l3": l3_options}


@router.post("/standard-items/import-all")
async def import_all_standard_items(session: AsyncSession = Depends(_get_session)):
    """批量导入标准项目（占位实现，实际需要从数据源导入）"""
    # TODO: 实现从外部数据源（CSV/Excel/API）批量导入
    return {"message": "批量导入功能待实现", "imported": 0}


# ─── Phase 3: 未匹配工作台 ────────────────────────────────────────────────


@router.get("/unmatched/summary")
async def get_unmatched_summary(session: AsyncSession = Depends(_get_session)):
    """未匹配项目汇总统计（按 reason_code 分组）"""
    sql = """
        SELECT reason_code, COUNT(*) as count
        FROM unmatched_registry
        WHERE status = 'open'
        GROUP BY reason_code
        ORDER BY count DESC
    """
    result = await session.execute(text(sql))
    items = [dict(row._mapping) for row in result]

    total_sql = "SELECT COUNT(*) FROM unmatched_registry WHERE status = 'open'"
    total_result = await session.execute(text(total_sql))
    total = total_result.scalar()

    return {"total": total, "by_reason": items}


@router.get("/unmatched/list")
async def get_unmatched_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    reason_code: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(_get_session),
):
    """未匹配项目列表查询（分页+筛选）"""
    offset = (page - 1) * page_size

    where_clauses = []
    params = {}

    if reason_code:
        where_clauses.append("u.reason_code = :reason_code")
        params["reason_code"] = reason_code
    if status:
        where_clauses.append("u.status = :status")
        params["status"] = status
    else:
        where_clauses.append("u.status = 'open'")  # 默认只显示待处理

    if search:
        # 搜索覆盖：标准名 / 归因详情 / procedure_id（无字典映射的记录也能搜到）
        where_clauses.append(
            "(p.name_zh ILIKE :search OR u.detail ILIKE :search OR u.procedure_id::text ILIKE :search)"
        )
        params["search"] = f"%{search}%"

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # 查询总数
    count_sql = f"""
        SELECT COUNT(*)
        FROM unmatched_registry u
        LEFT JOIN procedure_dictionary p ON u.procedure_id = p.id
        WHERE {where_sql}
    """
    count_result = await session.execute(text(count_sql), params)
    total = count_result.scalar()

    # 查询数据
    params["offset"] = offset
    params["limit"] = page_size
    data_sql = f"""
        SELECT
            u.id, u.procedure_id, u.modality, u.reason_code, u.detail, u.status,
            u.handled_at, u.created_at, u.updated_at,
            p.name_zh as procedure_name, p.semantic_id,
            pmr.effective_modality, pmr.tier,
            pmr.standards_json AS candidate_standards
        FROM unmatched_registry u
        LEFT JOIN procedure_dictionary p ON u.procedure_id = p.id
        LEFT JOIN procedure_match_results pmr ON u.procedure_id = pmr.procedure_id
        WHERE {where_sql}
        ORDER BY u.created_at DESC
        LIMIT :limit OFFSET :offset
    """
    result = await session.execute(text(data_sql), params)
    items = [dict(row._mapping) for row in result]

    return {"data": items, "total": total, "page": page, "page_size": page_size}


@router.put("/unmatched/{unmatched_id}/status")
async def update_unmatched_status(
    unmatched_id: int,
    status: str = Query(..., pattern="^(open|resolved|wontfix)$"),
    session: AsyncSession = Depends(_get_session),
):
    """更新未匹配项目状态"""
    # 检查记录是否存在
    check_sql = "SELECT id FROM unmatched_registry WHERE id = :id"
    result = await session.execute(text(check_sql), {"id": unmatched_id})
    if not result.first():
        raise HTTPException(404, "记录不存在")

    # 更新状态
    if status != "open":
        update_sql = """
            UPDATE unmatched_registry
            SET status = :status, handled_at = NOW(), updated_at = NOW()
            WHERE id = :id
        """
    else:
        update_sql = """
            UPDATE unmatched_registry
            SET status = :status, updated_at = NOW()
            WHERE id = :id
        """

    await session.execute(text(update_sql), {"id": unmatched_id, "status": status})
    await session.commit()

    return {"message": "状态已更新", "id": unmatched_id, "status": status}


# ─── Phase 4: 检查项目匹配测试中心 ─────────────────────────────────────────
#
# 数据源：procedure_dictionary（检查项目字典，active≈4555 条），
# 通过 unmatched_registry（procedure_id 唯一）承载未匹配状态与归因。


@router.get("/procedure-items")
async def list_procedure_items(
    modality: Optional[str] = Query(None, description="模态过滤（原始值）"),
    search: Optional[str] = Query(None, description="名称搜索"),
    limit: int = Query(6000, ge=1, le=6000),
    session: AsyncSession = Depends(_get_session),
):
    """列出检查项目字典（procedure_dictionary）及其未匹配状态。

    返回全量 active 项目（含 unmatched_registry 的 open 状态与归因），
    以及按模态聚合的统计，供前端"匹配测试中心"分组/过滤/批量匹配。
    """
    where = ["pd.is_active = true"]
    params: Dict[str, Any] = {}
    if modality:
        where.append("pd.modality = :modality")
        params["modality"] = modality
    if search:
        where.append("pd.name_zh ILIKE :search")
        params["search"] = f"%{search}%"
    where_sql = " AND ".join(where)

    items_sql = text(f"""
        SELECT pd.id, pd.semantic_id, pd.name_zh,
               UPPER(pd.modality) AS modality,
               ur.status AS um_status, ur.reason_code AS um_reason,
               pmr.matched AS last_matched,
               pmr.tier AS last_tier,
               pmr.confidence AS last_confidence,
               pmr.source AS last_source,
               pmr.effective_modality AS last_effective_modality,
               pmr.standards_json AS last_standards,
               pmr.reason_code AS last_reason_code,
               pmr.detail AS last_detail,
               pmr.rule_version AS last_rule_version,
               pmr.evaluated_at AS last_evaluated_at
        FROM procedure_dictionary pd
        LEFT JOIN unmatched_registry ur ON ur.procedure_id = pd.id
        LEFT JOIN procedure_match_results pmr ON pmr.procedure_id = pd.id
        WHERE {where_sql}
        ORDER BY pd.modality, pd.id
        LIMIT :limit
    """)
    params["limit"] = limit
    rows = (await session.execute(items_sql, params)).mappings().all()

    items = [
        {
            "id": r["id"],
            "semantic_id": r["semantic_id"],
            "name_zh": r["name_zh"] or "",
            "modality": r["modality"] or "UNKNOWN",
            "um_status": r["um_status"],
            "um_reason": r["um_reason"],
            "last_matched": r["last_matched"],
            "last_tier": r["last_tier"],
            "last_confidence": r["last_confidence"],
            "last_source": r["last_source"],
            "last_effective_modality": r["last_effective_modality"],
            "last_standards": r["last_standards"] or [],
            "last_reason_code": r["last_reason_code"],
            "last_detail": r["last_detail"],
            "last_rule_version": r["last_rule_version"],
            "last_evaluated_at": r["last_evaluated_at"],
        }
        for r in rows
    ]

    # 模态统计（不受 modality 过滤影响，始终给出全貌；受 search 影响）
    stats_where = ["pd.is_active = true"]
    stats_params: Dict[str, Any] = {}
    if search:
        stats_where.append("pd.name_zh ILIKE :search")
        stats_params["search"] = f"%{search}%"
    stats_sql = text(f"""
        SELECT UPPER(pd.modality) AS modality,
               COUNT(*) AS total,
               COUNT(*) FILTER (WHERE pmr.matched = true) AS matched,
               COUNT(*) FILTER (WHERE pmr.matched = false) AS unmatched,
               COUNT(*) FILTER (WHERE pmr.procedure_id IS NULL) AS untested
        FROM procedure_dictionary pd
        LEFT JOIN procedure_match_results pmr ON pmr.procedure_id = pd.id
        WHERE {' AND '.join(stats_where)}
        GROUP BY UPPER(pd.modality)
        ORDER BY total DESC
    """)
    stats_rows = (await session.execute(stats_sql, stats_params)).mappings().all()
    modality_stats = {
        (r["modality"] or "UNKNOWN"): {
            "total": r["total"],
            "matched": r["matched"],
            "unmatched": r["unmatched"],
            "untested": r["untested"],
        }
        for r in stats_rows
    }

    settings = get_settings()
    return {
        "items": items,
        "total": len(items),
        "modality_stats": modality_stats,
        "match_config": {
            "clear_cache_before_run": settings.PROCEDURE_MATCH_CLEAR_CACHE_BEFORE_RUN,
        },
    }


class MatchProceduresRequest(BaseModel):
    """批量匹配检查项目请求"""
    procedure_ids: List[int] = Field(..., description="procedure_dictionary.id 列表")


def _classify_unmatched(result: Dict[str, Any]) -> "tuple[str, str]":
    """根据引擎匹配结果归因 reason_code（对齐 unmatched_registry 既有语义）。

    依据引擎返回的 reason/has_entity 信号：
    - tier=ambiguous → parser_ambiguity / modality_route_review / standard_data_conflict
    - reason=excluded_* → 关键词引擎结构化排除原因
    - reason=unsupported_modality → unsupported_modality
    - has_entity=None 且命中旧排除标记 → unmatchable_by_design
    - has_entity=True  → 解析出医学实体但标准库无对应 → standard_lib_gap
    - has_entity=False → 未解析出医学实体（词库未覆盖）→ lexicon_gap
    """
    tier = result.get("tier", "none")
    has_entity = result.get("has_entity")
    if tier == "error":
        return "engine_error", result.get("reason") or "引擎异常"
    if tier == "ambiguous":
        ambiguous_reason = result.get("reason") or ""
        if ambiguous_reason == "exact_name_collision":
            return "standard_data_conflict", "标准名称对应多个有效编码或模态，禁止自动选择"
        if ambiguous_reason == "routed_result_requires_review":
            return "modality_route_review", "跨模态路由结果置信度不足，需人工确认"
        if ambiguous_reason == "compound_item_incomplete":
            return "parser_ambiguity", "联合检查仅部分子项命中，不能整条自动确认"
        return "parser_ambiguity", "多候选或解析残留，需人工确认"
    reason = result.get("reason") or ""
    if reason == "unsupported_modality":
        return "unsupported_modality", "当前匹配引擎未支持该模态"
    if reason == "excluded_intervention":
        return "excluded_intervention", "治疗性介入项目不自动匹配诊断影像标准"
    if reason == "excluded_non_imaging":
        return "excluded_non_imaging", "非影像或内镜类项目不在自动匹配范围"
    if reason == "standard_lib_gap":
        return "standard_lib_gap", "已识别医学实体，但标准库无对应项"
    if reason == "lexicon_gap":
        return "lexicon_gap", "未解析出医学实体（词库未覆盖）"
    if reason == "engine_not_ready":
        return "engine_error", "关键词引擎未就绪"
    if has_entity is None:
        return "unmatchable_by_design", (f"unmatchable:{reason}" if reason else "tier=none")
    if has_entity:
        return "standard_lib_gap", "解析出医学实体，标准库无对应项"
    return "lexicon_gap", "未解析出医学实体（词库未覆盖）"


def _extract_standards(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从引擎结果 data[].standard[] 结构提取标准项（code/name）。"""
    standards: List[Dict[str, Any]] = []
    for d in result.get("data", []) or []:
        if not isinstance(d, dict):
            continue
        std_list = d.get("standard")
        if isinstance(std_list, list) and std_list:
            for s in std_list:
                if isinstance(s, dict):
                    standards.append({"code": s.get("code"), "name": s.get("name")})
        elif d.get("item_code") or d.get("item_name"):
            standards.append({"code": d.get("item_code"), "name": d.get("item_name")})
    return standards


@router.post("/match-procedures")
async def match_procedures(
    request: MatchProceduresRequest,
    session: AsyncSession = Depends(_get_session),
):
    """对指定检查项目批量执行匹配，并将未匹配结果回写 unmatched_registry。

    - 已匹配：若此前登记为 open，则置为 resolved
    - 未匹配：upsert 为 open，并按 has_entity/tier 归因 reason_code
    前端按 chunk 分批调用以控制单次耗时。
    """
    from ..core.dispatcher import MatchDispatcher
    from ..core.engine_holder import get_engine_holder

    holder = get_engine_holder()
    if not holder.is_ready:
        raise HTTPException(status_code=503, detail="引擎未就绪")
    dispatcher = MatchDispatcher(session, holder)

    ids = list(dict.fromkeys(request.procedure_ids))[:400]  # 去重 + 单次上限
    if not ids:
        return {"total_processed": 0, "matched_count": 0, "unmatched_count": 0,
                "by_modality": {}, "results": []}

    rows = (await session.execute(
        text("SELECT id, semantic_id, name_zh, modality FROM procedure_dictionary WHERE id = ANY(:ids)"),
        {"ids": ids},
    )).mappings().all()

    results: List[Dict[str, Any]] = []
    registry_ops: List[Dict[str, Any]] = []
    persisted_results: List[Dict[str, Any]] = []
    matched_count = 0
    by_modality: Dict[str, Dict[str, int]] = {}

    for r in rows:
        pid = r["id"]
        name = r["name_zh"] or ""
        mod_raw = r["modality"] or ""
        mod_upper = mod_raw.upper() or "UNKNOWN"

        result = await dispatcher.match(name, mod_raw)
        tier = result.get("tier", "none")
        standards = _extract_standards(result)
        matched = result.get("num_standard", 0) > 0 and tier in ("exact", "partial", "degraded")
        cache_hit = bool(result.get("_cache_hit"))
        source = (
            result.get("_cache_source") if cache_hit else "algorithm"
        ) or "algorithm"
        effective_modality = (
            result.get("effective_modality")
            or dispatcher._normalize_modality(mod_raw)
            or mod_upper
        )
        reason_code: Optional[str] = None
        detail: Optional[str] = None

        slot = by_modality.setdefault(mod_upper, {"total": 0, "matched": 0, "unmatched": 0})
        slot["total"] += 1

        entry: Dict[str, Any] = {
            "procedure_id": pid,
            "semantic_id": r["semantic_id"],
            "name_zh": name,
            "modality": mod_upper,
            "effective_modality": effective_modality,
            "matched": matched,
            "tier": tier,
            "confidence": result.get("confidence", 0.0),
            "engine": result.get("engine"),
            "source": source,
            "cache_hit": cache_hit,
            "rule_version": holder.rule_version,
            "standards": standards,
        }

        if matched:
            matched_count += 1
            slot["matched"] += 1
            registry_ops.append({"pid": pid, "action": "resolve"})
        else:
            slot["unmatched"] += 1
            reason_code, detail = _classify_unmatched(result)
            entry["reason_code"] = reason_code
            entry["detail"] = detail
            registry_ops.append({
                "pid": pid, "action": "upsert", "modality": mod_upper,
                "reason": reason_code, "detail": detail,
            })
        results.append(entry)
        persisted_results.append({
            "pid": pid,
            "matched": matched,
            "tier": tier,
            "confidence": float(result.get("confidence", 0.0) or 0.0),
            "source": source,
            "effective_modality": effective_modality,
            "standards_json": json.dumps(standards, ensure_ascii=False),
            "reason_code": reason_code,
            "detail": detail,
            "rule_version": holder.rule_version,
        })

    # 回写 unmatched_registry（procedure_id 唯一索引，安全 upsert）
    for op in registry_ops:
        if op["action"] == "upsert":
            await session.execute(text("""
                INSERT INTO unmatched_registry
                    (procedure_id, modality, reason_code, detail, status, created_at, updated_at)
                VALUES (:pid, :modality, :reason, :detail, 'open', NOW(), NOW())
                ON CONFLICT (procedure_id) DO UPDATE SET
                    modality = EXCLUDED.modality,
                    reason_code = EXCLUDED.reason_code,
                    detail = EXCLUDED.detail,
                    status = 'open',
                    updated_at = NOW()
            """), {"pid": op["pid"], "modality": op["modality"],
                   "reason": op["reason"], "detail": op["detail"]})
        else:
            await session.execute(text("""
                UPDATE unmatched_registry
                SET status = 'resolved', handled_at = NOW(), updated_at = NOW()
                WHERE procedure_id = :pid AND status = 'open'
            """), {"pid": op["pid"]})

    # 持久化每个项目的最近一次完整结果，使页面刷新后仍能正确展示
    # matched/tier/标准项，而不再把无 unmatched_registry 行误判为“未检测”。
    if persisted_results:
        await session.execute(text("""
            INSERT INTO procedure_match_results
                (procedure_id, matched, tier, confidence, source,
                 effective_modality, standards_json,
                 reason_code, detail, rule_version, evaluated_at)
            VALUES
                (:pid, :matched, :tier, :confidence, :source,
                 :effective_modality, CAST(:standards_json AS jsonb), :reason_code, :detail,
                 :rule_version, NOW())
            ON CONFLICT (procedure_id) DO UPDATE SET
                matched = EXCLUDED.matched,
                tier = EXCLUDED.tier,
                confidence = EXCLUDED.confidence,
                source = EXCLUDED.source,
                effective_modality = EXCLUDED.effective_modality,
                standards_json = EXCLUDED.standards_json,
                reason_code = EXCLUDED.reason_code,
                detail = EXCLUDED.detail,
                rule_version = EXCLUDED.rule_version,
                evaluated_at = NOW()
        """), persisted_results)
    await session.commit()

    return {
        "total_processed": len(results),
        "matched_count": matched_count,
        "unmatched_count": len(results) - matched_count,
        "by_modality": by_modality,
        "results": results,
    }


# ─── 技术详情补全候选与正式参数库 ─────────────────────────────────────────


TECHNICAL_LIBRARY_FIELDS = [
    "body_position", "scan_scope", "contrast_agent", "image_region",
    "image_focus", "scan_method_detail", "scan_param", "coil",
    "base_sequence", "compose_sequence", "clinical_indication",
    "clinical_significance", "organs", "anatomical_structure",
    "technical_notes", "image_grade", "image_score",
]

TECHNICAL_LIBRARY_PRESENT_SQL = " OR ".join(
    f"s.{field} IS NOT NULL" for field in TECHNICAL_LIBRARY_FIELDS[:-2]
)


class TechnicalDetailGenerateRequest(BaseModel):
    version: str = "V3.8.2"
    modality: str = Field("CT", pattern="^(CT|MR)$")
    item_code: Optional[str] = None
    limit: Optional[int] = Field(None, ge=1, le=1000)
    persist: bool = False


class TechnicalDetailReviewRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected)$")
    reviewer: str = Field("后台操作", min_length=1, max_length=100)
    notes: Optional[str] = None


class TechnicalDetailEditRequest(BaseModel):
    candidate_fields: Dict[str, Optional[str]]
    editor: str = Field("后台操作", min_length=1, max_length=100)
    notes: Optional[str] = None


class TechnicalDetailPublishRequest(BaseModel):
    publisher: str = Field("后台操作", min_length=1, max_length=100)
    notes: Optional[str] = None


class TechnicalDetailRollbackRequest(BaseModel):
    operator: str = Field("后台操作", min_length=1, max_length=100)
    reason: str = Field(..., min_length=1)


class TechnicalDetailBulkPublishRequest(BaseModel):
    candidate_ids: Optional[List[int]] = None
    select_all: bool = False
    status: Optional[str] = Field(None, pattern="^(pending_review|approved|rejected|applied|superseded)$")
    modality: Optional[str] = Field(None, pattern="^(CT|MR)$")
    search: Optional[str] = Field(None, max_length=100)
    has_conflicts: Optional[bool] = None
    operator: str = Field("后台批量操作", min_length=1, max_length=100)
    notes: Optional[str] = None


@router.get("/technical-detail-library/stats")
async def get_technical_detail_library_stats(
    session: AsyncSession = Depends(_get_session),
):
    """正式技术参数库统计及来源分布。"""
    summary = (
        await session.execute(
            text(
                f"""
                SELECT COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE s.is_active = true) AS active_total,
                       COUNT(*) FILTER (WHERE s.modality = 'CT') AS ct_total,
                       COUNT(*) FILTER (WHERE s.modality = 'MR') AS mr_total
                FROM standard_check_items s
                WHERE {TECHNICAL_LIBRARY_PRESENT_SQL}
                """
            )
        )
    ).mappings().one()
    source_rows = (
        await session.execute(
            text(
                """
                SELECT source_kind, source_table, COUNT(*) AS count
                FROM technical_detail_provenance
                WHERE is_active = true
                GROUP BY source_kind, source_table
                ORDER BY source_kind, source_table
                """
            )
        )
    ).mappings().all()
    return {
        **dict(summary),
        "sources": [dict(row) for row in source_rows],
    }


@router.get("/technical-detail-library")
async def list_technical_detail_library(
    modality: Optional[str] = Query(None, pattern="^(CT|MR)$"),
    source_kind: Optional[str] = Query(None, pattern="^(historical_import|rule_fusion|evaluation_import)$"),
    search: Optional[str] = Query(None, max_length=100),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(_get_session),
):
    """查询已经进入正式标准库的技术参数及其数据来源。"""
    conditions = [f"({TECHNICAL_LIBRARY_PRESENT_SQL})"]
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if modality:
        conditions.append("s.modality = :modality")
        params["modality"] = modality
    if search:
        conditions.append("(s.item_code ILIKE :search OR s.item_name ILIKE :search)")
        params["search"] = f"%{search}%"
    if is_active is not None:
        conditions.append("s.is_active = :is_active")
        params["is_active"] = is_active
    if source_kind:
        conditions.append(
            """
            EXISTS (
                SELECT 1 FROM technical_detail_provenance pf
                WHERE pf.target_item_id = s.id
                  AND pf.is_active = true
                  AND pf.source_kind = :source_kind
            )
            """
        )
        params["source_kind"] = source_kind
    where_sql = " AND ".join(conditions)

    total = (
        await session.execute(
            text(f"SELECT COUNT(*) FROM standard_check_items s WHERE {where_sql}"),
            params,
        )
    ).scalar_one()

    columns = ", ".join(f"s.{field}" for field in TECHNICAL_LIBRARY_FIELDS)
    rows = (
        await session.execute(
            text(
                f"""
                SELECT s.id, s.item_code, s.item_name, s.modality, s.version,
                       s.scan_method, s.post_processing, s.is_active,
                       {columns},
                       COALESCE(provenance.sources, '[]'::jsonb) AS sources
                FROM standard_check_items s
                LEFT JOIN LATERAL (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'id', p.id,
                            'source_kind', p.source_kind,
                            'source_system', p.source_system,
                            'source_table', p.source_table,
                            'source_record_key', p.source_record_key,
                            'import_batch', p.import_batch,
                            'match_method', p.match_method,
                            'field_names', p.field_names_json,
                            'source_notes', p.source_notes,
                            'publication_id', p.publication_id,
                            'created_at', p.created_at,
                            'source_label', CASE p.source_table
                                WHEN 'ai.CT_specification' THEN '生产标准库 · CT技术参数'
                                WHEN 'ai.MR_specification' THEN '生产标准库 · MR技术参数'
                                WHEN 'ai.CheckitemGrade' THEN '生产标准库 · 评价指标'
                                WHEN 'technical_detail_candidates' THEN '规则融合候选 · 审核发布'
                                ELSE p.source_table
                            END
                        ) ORDER BY p.id
                    ) AS sources
                    FROM technical_detail_provenance p
                    WHERE p.target_item_id = s.id AND p.is_active = true
                ) provenance ON true
                WHERE {where_sql}
                ORDER BY s.is_active DESC, s.modality, s.item_code, s.id
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
    ).mappings().all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [dict(row) for row in rows],
    }


@router.get("/technical-detail-library/{item_id}")
async def get_technical_detail_library_item(
    item_id: int,
    session: AsyncSession = Depends(_get_session),
):
    """查询单个正式项目的完整技术字段和来源证据。"""
    columns = ", ".join(f"s.{field}" for field in TECHNICAL_LIBRARY_FIELDS)
    row = (
        await session.execute(
            text(
                f"""
                SELECT s.id, s.item_code, s.item_name, s.modality, s.version,
                       s.scan_method, s.post_processing, s.is_active, {columns},
                       COALESCE(provenance.sources, '[]'::jsonb) AS sources
                FROM standard_check_items s
                LEFT JOIN LATERAL (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'id', p.id,
                            'source_kind', p.source_kind,
                            'source_system', p.source_system,
                            'source_table', p.source_table,
                            'source_record_key', p.source_record_key,
                            'import_batch', p.import_batch,
                            'match_method', p.match_method,
                            'field_names', p.field_names_json,
                            'source_notes', p.source_notes,
                            'publication_id', p.publication_id,
                            'created_at', p.created_at,
                            'source_label', CASE p.source_table
                                WHEN 'ai.CT_specification' THEN '生产标准库 · CT技术参数'
                                WHEN 'ai.MR_specification' THEN '生产标准库 · MR技术参数'
                                WHEN 'ai.CheckitemGrade' THEN '生产标准库 · 评价指标'
                                WHEN 'technical_detail_candidates' THEN '规则融合候选 · 审核发布'
                                ELSE p.source_table
                            END
                        ) ORDER BY p.id
                    ) AS sources
                    FROM technical_detail_provenance p
                    WHERE p.target_item_id = s.id AND p.is_active = true
                ) provenance ON true
                WHERE s.id = :id AND ({TECHNICAL_LIBRARY_PRESENT_SQL})
                """
            ),
            {"id": item_id},
        )
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="正式技术参数不存在")
    return dict(row)


@router.post("/technical-detail-candidates/generate")
async def generate_technical_detail_candidates(
    request: TechnicalDetailGenerateRequest,
    session: AsyncSession = Depends(_get_session),
):
    """生成技术详情候选。

    默认 dry-run；即使 ``persist=true`` 也只写候选审核表，不更新正式标准数据。
    """
    from ..agent.technical_detail_completion import TechnicalDetailCompletionAgent

    agent = TechnicalDetailCompletionAgent(session)
    result = await agent.generate_candidates(
        version=request.version,
        modality=request.modality,
        item_code=request.item_code,
        limit=request.limit,
        persist=request.persist,
    )
    return result


@router.get("/technical-detail-candidates")
async def list_technical_detail_candidates(
    status: Optional[str] = Query(None, pattern="^(pending_review|approved|rejected|applied|superseded)$"),
    modality: Optional[str] = Query(None, pattern="^(CT|MR)$"),
    search: Optional[str] = Query(None, max_length=100),
    has_conflicts: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(_get_session),
):
    """查询补全候选审核队列（列表不返回大段候选正文）。"""
    conditions = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if status:
        conditions.append("status = :status")
        params["status"] = status
    if modality:
        conditions.append("modality = :modality")
        params["modality"] = modality
    if search:
        conditions.append("(target_item_code ILIKE :search OR target_item_name ILIKE :search)")
        params["search"] = f"%{search}%"
    if has_conflicts is not None:
        conditions.append("conflicts_json <> '[]'::jsonb" if has_conflicts else "conflicts_json = '[]'::jsonb")
    where_sql = " AND ".join(conditions) if conditions else "1=1"

    total = (
        await session.execute(
            text(f"SELECT COUNT(*) FROM technical_detail_candidates WHERE {where_sql}"),
            params,
        )
    ).scalar()
    rows = (
        await session.execute(
            text(
                f"""
                SELECT id, target_item_id, target_item_code, target_item_name,
                       target_version, modality, generation_method, confidence,
                       conflicts_json, source_item_ids_json, algorithm_version,
                       rationale, status, reviewer, reviewed_at, has_manual_edits,
                       last_edited_by, last_edited_at, created_at, updated_at
                FROM technical_detail_candidates
                WHERE {where_sql}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
    ).mappings().all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [dict(row) for row in rows],
    }


@router.get("/technical-detail-candidates/stats")
async def get_technical_detail_candidate_stats(
    session: AsyncSession = Depends(_get_session),
):
    """候选构建、审核和发布统计。"""
    status_rows = (
        await session.execute(
            text("SELECT status, COUNT(*) AS count FROM technical_detail_candidates GROUP BY status")
        )
    ).mappings().all()
    method_rows = (
        await session.execute(
            text(
                """
                SELECT generation_method, COUNT(*) AS count
                FROM technical_detail_candidates
                GROUP BY generation_method
                """
            )
        )
    ).mappings().all()
    conflict_count = (
        await session.execute(
            text("SELECT COUNT(*) FROM technical_detail_candidates WHERE conflicts_json <> '[]'::jsonb")
        )
    ).scalar_one()
    publication_count = (
        await session.execute(
            text("SELECT COUNT(*) FROM technical_detail_publications WHERE status = 'published'")
        )
    ).scalar_one()
    return {
        "total": sum(row["count"] for row in status_rows),
        "by_status": {row["status"]: row["count"] for row in status_rows},
        "by_method": {row["generation_method"]: row["count"] for row in method_rows},
        "conflict_count": conflict_count,
        "active_publication_count": publication_count,
    }


@router.get("/technical-detail-candidates/{candidate_id}")
async def get_technical_detail_candidate(
    candidate_id: int,
    session: AsyncSession = Depends(_get_session),
):
    """获取候选正文、字段来源与冲突信息。"""
    from ..agent.technical_detail_completion import TechnicalDetailCompletionAgent

    candidate = await TechnicalDetailCompletionAgent(session).get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="补全候选不存在")
    return candidate


@router.put("/technical-detail-candidates/{candidate_id}")
async def edit_technical_detail_candidate(
    candidate_id: int,
    request: TechnicalDetailEditRequest,
    session: AsyncSession = Depends(_get_session),
):
    """人工编辑候选并保存修订快照；修改后必须重新审核。"""
    from ..agent.technical_detail_completion import TechnicalDetailCompletionAgent

    try:
        return await TechnicalDetailCompletionAgent(session).edit_candidate(
            candidate_id,
            candidate_fields=request.candidate_fields,
            editor=request.editor,
            notes=request.notes,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/technical-detail-candidates/{candidate_id}/review")
async def review_technical_detail_candidate(
    candidate_id: int,
    request: TechnicalDetailReviewRequest,
    session: AsyncSession = Depends(_get_session),
):
    """记录人工审核结论；审核通过不会自动写入正式标准表。"""
    from ..agent.technical_detail_completion import TechnicalDetailCompletionAgent

    updated = await TechnicalDetailCompletionAgent(session).review_candidate(
        candidate_id,
        decision=request.decision,
        reviewer=request.reviewer,
        notes=request.notes,
    )
    if not updated:
        raise HTTPException(status_code=409, detail="候选不存在或已完成审核")
    return {"id": candidate_id, "status": request.decision}


@router.post("/technical-detail-candidates/{candidate_id}/publish")
async def publish_technical_detail_candidate(
    candidate_id: int,
    request: TechnicalDetailPublishRequest,
    session: AsyncSession = Depends(_get_session),
):
    """将已审核候选发布到官网数据源，并创建回滚快照。"""
    from ..agent.technical_detail_completion import TechnicalDetailCompletionAgent

    try:
        return await TechnicalDetailCompletionAgent(session).publish_candidate(
            candidate_id,
            publisher=request.publisher,
            notes=request.notes,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/technical-detail-bulk/review-and-publish")
async def bulk_review_and_publish_technical_details(
    request: TechnicalDetailBulkPublishRequest,
    session: AsyncSession = Depends(_get_session),
):
    """批量确认并发布选中候选，支持跨分页选择当前筛选全部结果。

    批量任务逐条提交并返回失败明细，单条失败不会撤销其他成功发布。
    """
    from ..agent.technical_detail_completion import TechnicalDetailCompletionAgent

    candidate_ids = list(dict.fromkeys(request.candidate_ids or []))
    if request.select_all:
        conditions = []
        params: dict[str, Any] = {}
        if request.status:
            conditions.append("status = :status")
            params["status"] = request.status
        if request.modality:
            conditions.append("modality = :modality")
            params["modality"] = request.modality
        if request.search:
            conditions.append("(target_item_code ILIKE :search OR target_item_name ILIKE :search)")
            params["search"] = f"%{request.search}%"
        if request.has_conflicts is not None:
            conditions.append(
                "conflicts_json <> '[]'::jsonb"
                if request.has_conflicts
                else "conflicts_json = '[]'::jsonb"
            )
        where_sql = " AND ".join(conditions) if conditions else "1=1"
        rows = await session.execute(
            text(
                f"""
                SELECT id FROM technical_detail_candidates
                WHERE {where_sql}
                ORDER BY id
                LIMIT 1001
                """
            ),
            params,
        )
        candidate_ids = [row[0] for row in rows.fetchall()]
        if len(candidate_ids) > 1000:
            raise HTTPException(status_code=422, detail="单次批量操作最多处理1000条候选")

    if not candidate_ids:
        raise HTTPException(status_code=422, detail="请至少选择一条候选")
    if len(candidate_ids) > 1000:
        raise HTTPException(status_code=422, detail="单次批量操作最多处理1000条候选")

    agent = TechnicalDetailCompletionAgent(session)
    published: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    for candidate_id in candidate_ids:
        try:
            candidate = await agent.get_candidate(candidate_id)
            if not candidate:
                failed.append({"id": candidate_id, "reason": "候选不存在"})
                continue
            current_status = candidate["status"]
            if current_status == "applied":
                skipped.append({
                    "id": candidate_id,
                    "item_code": candidate["target_item_code"],
                    "reason": "已经发布",
                })
                continue
            if current_status == "pending_review":
                reviewed = await agent.review_candidate(
                    candidate_id,
                    decision="approved",
                    reviewer=request.operator,
                    notes=request.notes or "批量确认并发布",
                )
                if not reviewed:
                    raise RuntimeError("候选状态已变化，请刷新后重试")
            elif current_status != "approved":
                raise RuntimeError(f"当前状态 {current_status} 不允许批量发布")

            result = await agent.publish_candidate(
                candidate_id,
                publisher=request.operator,
                notes=request.notes or "批量确认并发布",
            )
            published.append(result)
            # 关键修复：每次成功发布后立即提交事务，避免后续失败时回滚已完成的发布
            await session.commit()
        except (LookupError, RuntimeError, ValueError) as exc:
            await session.rollback()
            failed.append({"id": candidate_id, "reason": str(exc)})
        except Exception as exc:
            await session.rollback()
            logger.exception("批量发布技术详情失败: candidate_id=%s", candidate_id)
            failed.append({"id": candidate_id, "reason": f"发布失败: {type(exc).__name__}"})

    return {
        "requested_count": len(candidate_ids),
        "published_count": len(published),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "published": published,
        "skipped": skipped,
        "failed": failed,
    }


@router.get("/technical-detail-publications")
async def list_technical_detail_publications(
    status: Optional[str] = Query(None, pattern="^(published|rolled_back)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(_get_session),
):
    """查询官网发布和回滚记录。"""
    where_sql = "status = :status" if status else "1=1"
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if status:
        params["status"] = status
    total = (
        await session.execute(
            text(f"SELECT COUNT(*) FROM technical_detail_publications WHERE {where_sql}"),
            params,
        )
    ).scalar_one()
    rows = (
        await session.execute(
            text(
                f"""
                SELECT id, candidate_id, target_item_id, target_item_code,
                       after_json, published_by, publish_notes, published_at,
                       status, rolled_back_by, rollback_reason, rolled_back_at
                FROM technical_detail_publications
                WHERE {where_sql}
                ORDER BY published_at DESC, id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
    ).mappings().all()
    return {"total": total, "limit": limit, "offset": offset, "items": [dict(row) for row in rows]}


@router.post("/technical-detail-publications/{publication_id}/rollback")
async def rollback_technical_detail_publication(
    publication_id: int,
    request: TechnicalDetailRollbackRequest,
    session: AsyncSession = Depends(_get_session),
):
    """回滚一次官网发布；若正式字段已被再次编辑则拒绝自动回滚。"""
    from ..agent.technical_detail_completion import TechnicalDetailCompletionAgent

    try:
        return await TechnicalDetailCompletionAgent(session).rollback_publication(
            publication_id,
            operator=request.operator,
            reason=request.reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


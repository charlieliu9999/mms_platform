"""
Phase E: 管理 API

提供词表管理、规则编辑、历史追溯等管理功能的后端接口。
"""
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

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
               body_part_l3, scan_method, post_processing, version
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
            p.name_zh as procedure_name, p.semantic_id
        FROM unmatched_registry u
        LEFT JOIN procedure_dictionary p ON u.procedure_id = p.id
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


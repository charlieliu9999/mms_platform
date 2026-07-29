"""旧服务 API 兼容层（Phase C1/C2）

平替生产 examine-standard(:50000) 的 6 个端点，使数据中台等既有调用方
无需改代码即可切到 MMS。

契约来源：设计文档 §0.2（生产实测）
- 三段包裹：{"code":0,"msg":"success","data":[...]}
- md5 是调用方行标识，必须原样回传
- debug 带编号 pipeline 轨迹（1-preprocess / 2-split / ... / op）
- 支持 9 模态：CT/MR/DR/RF/MG/US/PET-CT/PET-MR/SPECT

与新式 /match 的区别：新式返回内部结构（data[].raw / standard[].code），
legacy 返回旧结构（data[].subitem / standard[].std_check_code），
由 legacy_adapter 做双向映射。
"""
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dispatcher import MatchDispatcher
from ..core.engine_holder import get_engine_holder
from ..db import get_session_factory
from .legacy_adapter import (
    LEGACY_MODALITY_ALIASES,
    to_legacy_error,
    to_legacy_response,
    to_legacy_row,
)

logger = logging.getLogger(__name__)
legacy_router = APIRouter(prefix="/algorithm/standardCheck", tags=["legacy"])

DEFAULT_VERSION = "V3.8.2"


async def _get_session() -> AsyncSession:
    factory = get_session_factory()
    async with factory() as session:
        yield session


def _normalize_modality(raw: str) -> str:
    """旧调用方可能传 PET-CT，内部标准值是 PET/CT。"""
    m = (raw or "").strip().upper()
    return LEGACY_MODALITY_ALIASES.get(m, m)


@legacy_router.post("/match")
async def legacy_match(request: Request):
    """单/多条同步匹配 —— 旧服务主力端点。

    请求：{"request_id":"x","version":"V3.8.2",
          "data":[{"check_item":"CT头部平扫","modality":"CT","md5":"t1"}]}
    """
    try:
        payload = await request.json()
    except (ValueError, TypeError) as exc:
        logger.warning(f"[legacy/match] 请求体解析失败: {exc}")
        return to_legacy_error("invalid json body")

    holder = get_engine_holder()
    if not holder.is_ready:
        return to_legacy_error("engine not ready", code=503)

    rows = payload.get("data") or []
    if not isinstance(rows, list):
        return to_legacy_error("data must be a list")

    version = payload.get("version") or DEFAULT_VERSION

    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        check_item = str(row.get("check_item", "") or "")
        modality = _normalize_modality(row.get("modality", ""))
        md5 = row.get("md5", "")

        if not check_item:
            out.append(to_legacy_row("", modality, md5, None))
            continue

        # legacy 端点需要 debug 轨迹，绕过 L1 缓存直接走引擎
        # （缓存只存最终结果，没有中间态）
        trace: dict = {}
        engine = holder.match_engine
        try:
            result = engine.match(check_item, modality, version, trace=trace)
        except (KeyError, ValueError, AttributeError, TypeError) as exc:
            logger.error(
                f"[legacy/match] 引擎异常 {check_item!r} [{modality}]: "
                f"{type(exc).__name__}: {exc}",
                exc_info=True,
            )
            out.append(to_legacy_row(check_item, modality, md5, None))
            continue

        out.append(to_legacy_row(check_item, modality, md5, result,
                                 trace=trace, version=version))

    return to_legacy_response(out)


@legacy_router.post("/batch_match")
async def legacy_batch_match(
    request: Request, session: AsyncSession = Depends(_get_session)
):
    """批量匹配。

    ⚠️ 旧服务此端点跑完会 POST 回调数据中台的审批列表
    （见设计文档 §0.2）。回调实现属 C3，此处先同步返回结果，
    回调开关由 C3 引入，避免在未验证前向生产数据中台写入。
    """
    try:
        payload = await request.json()
    except (ValueError, TypeError) as exc:
        logger.warning(f"[legacy/batch_match] 请求体解析失败: {exc}")
        return to_legacy_error("invalid json body")

    holder = get_engine_holder()
    if not holder.is_ready:
        return to_legacy_error("engine not ready", code=503)

    rows = payload.get("data") or []
    if not isinstance(rows, list):
        return to_legacy_error("data must be a list")

    version = payload.get("version") or DEFAULT_VERSION
    dispatcher = MatchDispatcher(session, holder)

    items = []
    md5_by_key = {}
    meta_by_key = {}
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        key = str(idx)
        modality = _normalize_modality(row.get("modality", ""))
        items.append({
            "key": key,
            "name": str(row.get("check_item", "") or ""),
            "modality": modality,
        })
        md5_by_key[key] = row.get("md5", "")
        meta_by_key[key] = modality

    # 批量走三层分派（含 L1 缓存），批量场景不返回 debug 轨迹
    response = await dispatcher.batch_match(items, version)
    results = response.get("results", {})

    out = []
    for it in items:
        key = it["key"]
        out.append(to_legacy_row(
            it["name"], meta_by_key.get(key, ""), md5_by_key.get(key, ""),
            results.get(key), version=version,
        ))

    return to_legacy_response(out)


@legacy_router.post("/update_table")
async def legacy_update_table(request: Request):
    """按表名热重载规则。旧契约接受 {"table_name": "..."}。

    MMS 的规则加载是整体式的（RuleDataLoader 一次加载全部词表），
    因此无论传哪个表名都执行全量 reload，语义上是旧行为的超集。
    """
    try:
        payload = await request.json()
    except (ValueError, TypeError):
        payload = {}

    table_name = (payload or {}).get("table_name", "(all)")
    holder = get_engine_holder()
    try:
        await holder.reload()
    except (RuntimeError, OSError) as exc:
        logger.error(f"[legacy/update_table] reload 失败: {exc}", exc_info=True)
        return to_legacy_error(f"reload failed: {exc}", code=500)

    logger.info(f"[legacy/update_table] 收到 table_name={table_name}，已全量 reload")
    return to_legacy_response({
        "table_name": table_name,
        "rule_version": holder.rule_version,
    })


@legacy_router.api_route("/query_rule", methods=["GET", "POST"])
async def legacy_query_rule(request: Request):
    """按词查规则（旧服务的规则排查入口）。

    旧服务返回该词在各词表中的命中情况，供人工判断规则为何未生效。
    """
    word = request.query_params.get("word", "")
    if not word and request.method == "POST":
        try:
            payload = await request.json()
            word = (payload or {}).get("word", "")
        except (ValueError, TypeError):
            word = ""

    word = (word or "").strip()
    if not word:
        return to_legacy_error("word is required")

    holder = get_engine_holder()
    if not holder.is_ready:
        return to_legacy_error("engine not ready", code=503)

    engine = holder.match_engine
    loader = getattr(engine, "data_loader", None)
    if loader is None:
        return to_legacy_error("rule data not loaded", code=503)

    hits = {"medical_dict": None, "phrase_map": []}

    # mdict 是 {词: 词性} 字典，不是 DataFrame
    mdict = getattr(loader, "mdict", None) or {}
    if word in mdict:
        hits["medical_dict"] = {"word": word, "type": mdict[word]}

    # pre_rules 是 {模态: DataFrame}；modality=="ALL" 的通用归一化规则被
    # loader 单独拆到 common_normal，不在 pre_rules 里，须一并查询，
    # 否则 头部→颅脑 这类全局规则会漏报
    sources = dict(getattr(loader, "pre_rules", None) or {})
    common = getattr(loader, "common_normal", None)
    if common is not None and not common.empty:
        sources["ALL"] = common
    for modality, df in sources.items():
        if df is None or df.empty:
            continue
        cols = set(df.columns)
        if not {"src_word", "dst_word"} <= cols:
            continue
        mask = (df["src_word"] == word) | (df["dst_word"] == word)
        for _, r in df[mask].iterrows():
            hits["phrase_map"].append({
                "modality": modality,
                "src_word": r.get("src_word"),
                "dst_word": r.get("dst_word"),
                "step": r.get("step"),
                "version": r.get("version"),
            })

    return to_legacy_response({"word": word, "hits": hits})


@legacy_router.api_route("/modify_phrase_map", methods=["GET", "POST"])
async def legacy_modify_phrase_map():
    """同义词表增删改。

    MMS 的词表治理走 acrac 治理台（设计决策 D8：独立服务完成前
    治理能力不中断），此端点返回明确的 501 而非静默成功，
    避免调用方以为写入生效。
    """
    return to_legacy_error(
        "phrase_map 写操作请走 acrac 词表治理台（D8）；"
        "MMS 侧词表为只读副本",
        code=501,
    )


@legacy_router.api_route("/modify_rule_map", methods=["GET", "POST"])
async def legacy_modify_rule_map():
    """规则映射表增删改。同 modify_phrase_map，写操作走治理台。"""
    return to_legacy_error(
        "rule_map 写操作请走 acrac 词表治理台（D8）；"
        "MMS 侧词表为只读副本",
        code=501,
    )

"""旧服务响应格式适配器（Phase C2）

把 MMS 内部结果映射成生产 examine-standard 的响应契约。

内部结构（match_engine_v2）:
    {"check_item": str, "num_standard": int, "score": int,
     "data": [{"raw": str, "standard": [{"code": str, "name": str}]}],
     "tier": str, "confidence": float, ...}

旧契约（设计文档 §0.2 实测）:
    {"code": 0, "msg": "success", "data": [{
        "check_item": str, "num_standard": int, "score": float,
        "md5": str, "modality": str,
        "data": [{"subitem": str, "standard": [
            {"modality": str, "std_check_name": str,
             "std_check_code": str, "version": str}]}],
        "debug": {"op": [], "1-preprocess": str, ...}}]}

字段映射要点：
- standard[].code      → std_check_code
- standard[].name      → std_check_name
- data[].raw           → subitem
- score 内部是 int，旧服务返回 float
- tier/confidence 等 MMS 新增字段不出现在 legacy 响应里（保持契约一致）
"""
from copy import deepcopy

# 旧调用方的模态写法 → 内部标准值
# 生产旧服务用连字符，standard_check_items.modality 用斜杠
LEGACY_MODALITY_ALIASES = {
    "PET-CT": "PET/CT",
    "PET-MR": "PET/MR",
    "PETCT": "PET/CT",
    "PETMR": "PET/MR",
}

# 内部标准值 → 旧调用方期望的回显写法（回传时还原，避免调用方解析失败）
_MODALITY_ECHO = {
    "PET/CT": "PET-CT",
    "PET/MR": "PET-MR",
}


def to_legacy_response(data, code: int = 0, msg: str = "success") -> dict:
    """三段包裹。data 可以是 list（多行结果）或 dict（单对象）。"""
    return {"code": code, "msg": msg, "data": data}


def to_legacy_error(msg: str, code: int = 1) -> dict:
    """错误响应。旧服务用 code!=0 表示失败，HTTP 状态码始终 200。"""
    return {"code": code, "msg": msg, "data": []}


def to_legacy_row(check_item: str, modality: str, md5: str,
                  result: dict = None, trace: dict = None,
                  version: str = "V3.8.2") -> dict:
    """单行结果 → 旧格式。

    Args:
        result: 内部匹配结果；None 表示引擎异常或空输入，
                返回 num_standard=0 的空行（旧服务同样行为）
        trace:  pipeline 中间态，映射到 debug 字段
    """
    echo_modality = _MODALITY_ECHO.get(modality, modality)

    if not result:
        return {
            "check_item": check_item,
            "num_standard": 0,
            "score": 0.0,
            "md5": md5,
            "modality": echo_modality,
            "data": [],
            "debug": deepcopy(trace) if trace else {},
        }

    sub_items = []
    for block in (result.get("data") or []):
        standards = []
        for std in (block.get("standard") or []):
            standards.append({
                "modality": echo_modality,
                "std_check_name": std.get("name", ""),
                "std_check_code": std.get("code", ""),
                "version": version,
            })
        sub_items.append({
            "subitem": block.get("raw", check_item),
            "standard": standards,
        })

    return {
        "check_item": result.get("check_item", check_item),
        "num_standard": result.get("num_standard", 0),
        # 旧服务 score 是 float
        "score": float(result.get("score", 0)),
        "md5": md5,
        "modality": echo_modality,
        "data": sub_items,
        "debug": deepcopy(trace) if trace else {},
    }

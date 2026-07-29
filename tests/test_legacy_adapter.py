"""legacy 契约适配器单测（Phase C2）

锁定旧服务响应格式，防止后续重构悄悄改变契约导致数据中台解析失败。
契约基线来源：设计文档 §0.2 生产实测响应。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from match_service.api.legacy_adapter import (  # noqa: E402
    LEGACY_MODALITY_ALIASES,
    to_legacy_error,
    to_legacy_response,
    to_legacy_row,
)

INTERNAL_HIT = {
    "check_item": "CT头部平扫",
    "num_standard": 1,
    "score": 10,
    "tier": "exact",
    "confidence": 1.0,
    "data": [{
        "raw": "CT头部平扫",
        "standard": [{"code": "20010100110000", "name": "* CT颅脑(平扫)"}],
    }],
}


def test_response_envelope():
    """三段包裹：code/msg/data，且 code=0 表示成功。"""
    r = to_legacy_response([{"x": 1}])
    assert r == {"code": 0, "msg": "success", "data": [{"x": 1}]}


def test_error_uses_code_not_http_status():
    """旧服务错误也走 HTTP 200，靠 code!=0 区分。"""
    r = to_legacy_error("bad input")
    assert r["code"] == 1
    assert r["data"] == []


def test_row_field_mapping():
    """内部字段名 → 旧契约字段名。"""
    row = to_legacy_row("CT头部平扫", "CT", "md5-1", INTERNAL_HIT)

    assert row["md5"] == "md5-1"
    assert row["num_standard"] == 1
    # 旧服务 score 是 float
    assert isinstance(row["score"], float)

    block = row["data"][0]
    assert block["subitem"] == "CT头部平扫"          # raw → subitem
    std = block["standard"][0]
    assert std["std_check_code"] == "20010100110000"  # code → std_check_code
    assert std["std_check_name"] == "* CT颅脑(平扫)"   # name → std_check_name
    assert std["version"] == "V3.8.2"


def test_internal_only_fields_absent():
    """tier/confidence 是 MMS 新增字段，不能泄漏到 legacy 响应。"""
    row = to_legacy_row("CT头部平扫", "CT", "m", INTERNAL_HIT)
    assert "tier" not in row
    assert "confidence" not in row


def test_pet_modality_roundtrip():
    """入参 PET-CT → 内部 PET/CT → 回显仍是 PET-CT。"""
    assert LEGACY_MODALITY_ALIASES["PET-CT"] == "PET/CT"
    row = to_legacy_row("PET-CT全身", "PET/CT", "m", None)
    assert row["modality"] == "PET-CT"


def test_empty_result_is_zero_row_not_error():
    """未命中返回 num_standard=0 的正常行，不是错误。"""
    row = to_legacy_row("鬼东西", "CT", "m", None)
    assert row["num_standard"] == 0
    assert row["data"] == []
    assert row["md5"] == "m"


def test_debug_trace_passthrough():
    """debug 带编号 pipeline 轨迹，供规则排查。"""
    trace = {"op": [], "1-preprocess": "CT颅脑平扫"}
    row = to_legacy_row("CT头部平扫", "CT", "m", INTERNAL_HIT, trace=trace)
    assert row["debug"]["1-preprocess"] == "CT颅脑平扫"
    # 必须是副本，避免调用方改动污染引擎内部 trace
    row["debug"]["op"].append("x")
    assert trace["op"] == []

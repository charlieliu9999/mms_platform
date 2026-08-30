"""MMS 对外标准化服务契约。

这些测试固定 ``acrac_web_mgmt`` 实际消费的路径、请求结构和响应结构；
不连接数据库，也不依赖完整匹配词表。
"""

import pytest

from match_service.api import routes
from match_service.api.schemas import BatchRequest
from match_service.main import app


class _ReadyHolder:
    is_ready = True
    rule_version = "rules-contract"


@pytest.mark.asyncio
async def test_batch_match_keeps_consumer_contract(monkeypatch):
    captured = {}

    class _Dispatcher:
        def __init__(self, session, holder):
            captured["session"] = session
            captured["holder"] = holder

        async def batch_match(self, items, version):
            captured["items"] = items
            captured["version"] = version
            return {
                "results": {
                    "explicit": {
                        "data": [
                            {
                                "raw": "CT头部平扫",
                                "standard": [
                                    {"code": "20010100110000", "name": "* CT颅脑(平扫)"}
                                ],
                            }
                        ],
                        "tier": "exact",
                        "confidence": 1.0,
                        "effective_modality": "CT",
                    },
                    "inferred": {
                        "data": [
                            {
                                "raw": "CT头部平扫",
                                "standard": [
                                    {"code": "20010100110000", "name": "* CT颅脑(平扫)"}
                                ],
                            }
                        ],
                        "tier": "exact",
                        "confidence": 1.0,
                        "effective_modality": "CT",
                    },
                },
                "stats": {"total": 2, "cache_hits": 0, "engine_hits": 2, "misses": 0},
                "rule_version": "rules-contract",
            }

    monkeypatch.setattr(routes, "get_engine_holder", lambda: _ReadyHolder())
    monkeypatch.setattr(routes, "MatchDispatcher", _Dispatcher)

    request = BatchRequest.model_validate(
        {
            "items": [
                {"key": "explicit", "name": "CT头部平扫", "modality": "CT"},
                {"key": "inferred", "text": "CT头部平扫", "modality": ""},
            ],
            "version": "V3.8.2",
        }
    )
    response = await routes.batch_match(request, session=object())

    assert captured["items"] == [
        {"key": "explicit", "name": "CT头部平扫", "modality": "CT"},
        {"key": "inferred", "name": "CT头部平扫", "modality": ""},
    ]
    assert captured["version"] == "V3.8.2"
    assert response["rule_version"] == "rules-contract"
    assert response["results"]["explicit"]["data"][0]["standard"] == [
        {"code": "20010100110000", "name": "* CT颅脑(平扫)"}
    ]
    assert response["results"]["inferred"]["effective_modality"] == "CT"


def test_openapi_exposes_consumer_endpoints():
    paths = app.openapi()["paths"]

    assert "post" in paths["/api/batch-match"]
    assert "get" in paths["/api/health"]
    assert "get" in paths["/api/rules/snapshot"]
    assert "post" in paths["/api/reload"]

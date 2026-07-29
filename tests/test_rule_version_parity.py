"""
规则版本剥离对齐测试 — MMS 自有实现须与宿主算出完全相同的版本号。

这是 app.* 依赖剥离的正确性硬标准：MMS 侧 RULE_TABLES 若漏表、列序不同
或软删列写错，都会导致版本号漂移，进而使灰度期两侧版本追溯对不上账。
需要本地 PG（词表库）可连，无库时 skip。
"""
import pytest

from match_service.core.rule_version import (
    RULE_TABLES,
    compute_rule_version as mms_compute,
)


def _host_spec():
    """取宿主 LEXICON_TABLES 的等价元数据（缺 acrac_backend 时返回 None）"""
    try:
        from app.services.check_item_mgmt.lexicon_service import LEXICON_TABLES
    except ImportError:
        return None
    return {
        k: (v.model.__tablename__, v.soft_delete_col, list(v.columns))
        for k, v in LEXICON_TABLES.items()
    }


def test_table_spec_matches_host():
    """表名/软删列/列清单/键序 四项须与宿主逐一相同。"""
    host = _host_spec()
    if host is None:
        pytest.skip("acrac_backend 不在 sys.path，跳过宿主对齐校验")

    mms = {
        k: (v.tablename, v.soft_delete_col, list(v.columns))
        for k, v in RULE_TABLES.items()
    }

    assert list(mms.keys()) == list(host.keys()), (
        f"键序/表集不一致\nMMS : {list(mms.keys())}\n宿主: {list(host.keys())}"
    )
    for key in host:
        assert mms[key] == host[key], (
            f"表 {key} 规格不一致\nMMS : {mms[key]}\n宿主: {host[key]}"
        )


@pytest.mark.asyncio
async def test_version_identical_to_host():
    """同一库上，两侧算出的版本号字符串必须完全相同。"""
    host = _host_spec()
    if host is None:
        pytest.skip("acrac_backend 不在 sys.path，跳过版本号对齐校验")

    from app.services.check_item_mgmt.rule_version import (
        compute_rule_version as host_compute,
    )
    from match_service.db import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        mms_ver = await mms_compute(session)
        host_ver = await host_compute(session)

    if mms_ver == "unknown" or host_ver == "unknown":
        pytest.skip(f"库不可达 (mms={mms_ver}, host={host_ver})")

    assert mms_ver == host_ver, f"版本号漂移: MMS={mms_ver} 宿主={host_ver}"

"""Version-scoped cache behavior with an in-memory SQL session double."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from match_service.cache.models import MatchCache
from match_service.cache.service import CacheService, standard_versions
from match_service.core.dispatcher import MatchDispatcher


def result(version="v3.8.2"):
    standard = {"code": "ct-code", "name": "* CT颅脑(平扫)"}
    if version is not None:
        standard["version"] = version
    return {"tier": "exact", "confidence": 1.0, "num_standard": 1,
            "data": [{"standard": [standard]}]}


def row(source="algorithm", version="v3.8.2", **kwargs):
    return MatchCache(
        text_hash="hash", modality="CT", original_text="CT颅脑平扫",
        result_json=MatchCache.make_result_json(result(version)), confidence=1.0,
        source=source, rule_version="rules-current", hit_count=0, **kwargs,
    )


def session(*rows):
    db = AsyncMock()
    db.add = MagicMock()
    db.execute.side_effect = [SimpleNamespace(scalar_one_or_none=lambda r=r: r) for r in rows]
    return db


def test_selector_hash_isolated_but_case_insensitive():
    old = MatchCache.compute_hash("CT头部", "CT")
    new = MatchCache.compute_hash("CT头部", "CT", "V3.8.2")
    assert old != new
    assert new == MatchCache.compute_hash("CT头部", "CT", " v3.8.2 ")
    assert new != MatchCache.compute_hash("CT头部", "CT", "v4.0.0")


@pytest.mark.parametrize("bad", [None, {}, {"data": None}, {"data": {}},
    {"data": [None]}, {"data": [{"standard": {}}]},
    {"data": [{"standard": [None]}]}, result(None)])
def test_bad_or_missing_provenance_never_inferred(bad):
    assert standard_versions(bad) is None


@pytest.mark.asyncio
async def test_algorithm_lookup_uses_selector_hash_and_actual_version():
    cached_row = row(version="v1.1")
    db = session(None, cached_row)
    cached = await CacheService(db).lookup("CT头部", "CT", "rules-current", "V3.8.2")
    # Fallback actual version is preserved; selector is only a cache key.
    assert cached["data"][0]["standard"][0]["version"] == "v1.1"
    params = db.execute.call_args_list[1].args[0].compile().params
    assert MatchCache.compute_hash("CT头部", "CT", "V3.8.2") in params.values()
    assert cached_row.hit_count == 1
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_algorithm_missing_version_is_not_cached_or_returned():
    db = session(None, row(version=None))
    cache = CacheService(db)
    assert await cache.lookup("CT头部", "CT", "rules-current", "V3.8.2") is None
    await cache.store("CT头部", "CT", result(None), 1.0,
                      rule_version="rules-current", requested_version="V3.8.2")
    assert db.execute.await_count == 2
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_expired_algorithm_is_retained_without_hit():
    cached_row = row(expires_at=datetime.utcnow() - timedelta(days=1))
    db = session(None, cached_row)
    assert await CacheService(db).lookup("CT头部", "CT", "rules-current", "V3.8.2") is None
    db.delete.assert_not_awaited()
    db.commit.assert_not_awaited()
    assert cached_row.hit_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["manual", "agent_confirmed"])
async def test_default_request_keeps_unversioned_confirmation(source):
    confirmed = row(source=source, version=None, expires_at=datetime.utcnow() - timedelta(days=1))
    original = confirmed.result_json
    db = session(confirmed)
    cached = await CacheService(db).lookup("CT头部", "CT", "new-rules", "V3.8.2", False)
    assert cached["tier"] == "exact"
    assert cached["provenance_missing"] is True
    assert "version" not in cached["data"][0]["standard"][0]
    assert cached["_cache_source"] == source
    assert confirmed.result_json == original
    db.commit.assert_not_awaited()
    db.delete.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(("version", "reason"), [
    (None, "confirmed_version_missing"), ("v1.1", "confirmed_version_conflict")])
async def test_explicit_request_keeps_conflicting_confirmation_for_review(version, reason):
    confirmed = row(source="manual", version=version)
    db = session(confirmed)
    cached = await CacheService(db).lookup("CT头部", "CT", "rules-current", "V3.8.2")
    assert cached["tier"] == "ambiguous"
    assert cached["confidence"] == 0.4
    assert cached["reason"] == reason
    assert cached["data"] == result(version)["data"]
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_scoped_confirmation_survives_old_rule_and_expiry():
    confirmed = row(source="agent_confirmed", expires_at=datetime.utcnow() - timedelta(days=1))
    confirmed.rule_version = "old-rules"
    db = session(None, confirmed)
    cached = await CacheService(db).lookup("CT头部", "CT", "new-rules", "V3.8.2")
    assert cached["tier"] == "exact"
    assert cached["_cache_rule_version"] == "old-rules"
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("version,expected_tier", [("v1.1", "exact"), ("v9.9", "ambiguous"), (None, "ambiguous")])
async def test_confirmed_us_honors_allowed_modality_fallback(version, expected_tier):
    confirmed = row(source="manual", version=version)
    confirmed.modality = "US"
    db = session(confirmed)
    cached = await CacheService(db).lookup("US甲状腺", "US", "rules-current", "V3.8.2")
    assert cached["tier"] == expected_tier
    MatchDispatcher._annotate_version_selection(cached, "V3.8.2", True)
    if version == "v1.1":
        assert cached["version_fallback_reason"] == "confirmed_mapping"
    assert confirmed.get_result() == result(version)


@pytest.mark.asyncio
async def test_algorithm_never_overwrites_confirmation():
    confirmed = row(source="manual")
    original = confirmed.result_json
    db = session(confirmed)
    await CacheService(db).store("CT头部", "CT", result("v4.0.0"), 1.0,
                                 rule_version="new-rules")
    assert confirmed.result_json == original
    assert confirmed.source == "manual"
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("raw_json", ["null", "[]", "broken-json"])
async def test_corrupt_confirmation_is_retained_for_review(raw_json):
    confirmed = row(source="manual")
    confirmed.result_json = raw_json
    db = session(confirmed)
    cached = await CacheService(db).lookup("CT头部", "CT", "rules-current", "V3.8.2", False)
    assert cached["tier"] == "ambiguous"
    assert cached["reason"] == "confirmed_result_invalid"
    assert confirmed.result_json == raw_json
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_store_isolates_two_selectors_without_relabeling_actual_version():
    db = session(None, None)
    cache = CacheService(db)
    for selector in ["V3.8.2", "V4.0.0"]:
        await cache.store("CT头部", "CT", result("v1.1"), 1.0,
                          rule_version="rules-current", requested_version=selector)
    first, second = [call.args[0] for call in db.add.call_args_list]
    assert first.text_hash != second.text_hash
    assert first.get_result()["data"][0]["standard"][0]["version"] == "v1.1"
    assert second.get_result()["data"][0]["standard"][0]["version"] == "v1.1"


@pytest.mark.asyncio
@pytest.mark.parametrize("modality", [None, "CT"])
async def test_invalidation_excludes_confirmations(modality):
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(rowcount=2)
    cache = CacheService(db)
    if modality:
        assert await cache.invalidate_by_modality(modality) == 2
    else:
        assert await cache.invalidate_all() == 2
    sql = str(db.execute.call_args.args[0].compile(compile_kwargs={"literal_binds": True}))
    assert "NOT IN ('manual', 'agent_confirmed')" in sql or "NOT IN ('agent_confirmed', 'manual')" in sql


@pytest.mark.asyncio
async def test_dispatcher_preserves_review_confidence_and_does_not_overwrite_manual():
    holder = SimpleNamespace(rule_version="rules-current", match_engine=None)
    dispatcher = MatchDispatcher(AsyncMock(), holder)
    cached = result()
    cached.update(tier="ambiguous", confidence=0.4,
                  reason="confirmed_version_conflict", _cache_hit=True, _cache_confidence=1.0)
    dispatcher.cache_service.lookup = AsyncMock(return_value=cached)
    dispatcher.cache_service.store = AsyncMock()
    dispatcher._record_feedback = AsyncMock()
    output = await dispatcher.match("CT头部平扫", "CT", version_is_explicit=True)
    assert output["tier"] == "ambiguous"
    assert output["confidence"] == 0.4
    dispatcher.cache_service.store.assert_not_awaited()
    dispatcher._record_feedback.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("engine_routed", [True, False])
async def test_dispatcher_routing_matches_on_cold_and_warm_calls(engine_routed):
    from copy import deepcopy
    value = result("v1.1")
    value.update(tier="exact", confidence=1.0, num_standard=1,
                 modality_routed=engine_routed)
    engine = SimpleNamespace(is_ready=True, match=MagicMock(return_value=value))
    dispatcher = MatchDispatcher(AsyncMock(), SimpleNamespace(rule_version="rules", match_engine=engine))
    dispatcher.cache_service.lookup = AsyncMock(return_value=None)
    dispatcher.cache_service.store = AsyncMock()
    dispatcher._record_feedback = AsyncMock()
    cold = await dispatcher.match("US甲状腺常规超声检查", "CT")
    cached = deepcopy(cold)
    cached.update(_cache_hit=True, _cache_source="algorithm")
    dispatcher.cache_service.lookup.return_value = cached
    warm = await dispatcher.match("US甲状腺常规超声检查", "CT")
    assert warm["modality_routed"] == cold["modality_routed"] is True
    assert warm["engine_modality_routed"] is engine_routed
    # A different caller may have the correct source modality already.
    dispatcher.cache_service.lookup.return_value = deepcopy(cold) | {"_cache_source": "algorithm"}
    correct_source = await dispatcher.match("US甲状腺常规超声检查", "US")
    assert correct_source["modality_routed"] is engine_routed


@pytest.mark.asyncio
async def test_old_algorithm_routing_provenance_is_recomputed():
    value = result("v1.1")
    value.update(tier="exact", confidence=1.0, num_standard=1)
    engine = SimpleNamespace(is_ready=True, match=MagicMock(return_value=value))
    dispatcher = MatchDispatcher(AsyncMock(), SimpleNamespace(rule_version="rules", match_engine=engine))
    dispatcher.cache_service.lookup = AsyncMock(return_value=value | {"_cache_source": "algorithm"})
    dispatcher.cache_service.store = AsyncMock()
    dispatcher._record_feedback = AsyncMock()
    output = await dispatcher.match("US甲状腺常规超声检查", "US")
    engine.match.assert_called_once()
    assert output["engine_modality_routed"] is False

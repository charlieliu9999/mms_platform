"""Actual row-version propagation and fixed modality policy, without databases."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from match_service.core.dispatcher import MatchDispatcher
from match_service.engine.catalog_policy import CATALOG_POLICY_SQL, MODALITY_CATALOG_VERSIONS
from match_service.engine.keyword.us_spect_pet_matcher import USSpectPetMatcher
from match_service.engine.match_engine_v2.data_loader import RuleDataLoader, normalize_standard_name
from match_service.engine.match_engine_v2.match_node import MatchNode
from match_service.engine.match_engine_v2.orchestrator import MatchEngineOrchestrator
from match_service.engine.match_engine_v2.standard_lookup_service import StandardLookupService


def test_policy_selects_one_catalog_per_modality():
    assert MODALITY_CATALOG_VERSIONS["US"] == "v1.1"
    assert MODALITY_CATALOG_VERSIONS["PET/CT"] == "v1.1"
    assert MODALITY_CATALOG_VERSIONS["DSA"] == "v2.0"
    assert MODALITY_CATALOG_VERSIONS["SPECT"] == "v2.0"
    for modality in ["CT", "MR", "DR", "RF", "MG"]:
        assert MODALITY_CATALOG_VERSIONS[modality] == "v3.8.2"
    assert "V4.0.0" not in CATALOG_POLICY_SQL


@pytest.mark.asyncio
async def test_exact_loader_uses_policy_and_retains_database_version():
    conn = AsyncMock()
    conn.execute.side_effect = [
        SimpleNamespace(fetchall=lambda: [("US", "v1.1", "us-code", "* US甲状腺")]),
        SimpleNamespace(fetchall=lambda: []),
    ]
    loader = RuleDataLoader(engine=MagicMock())
    await loader._load_standard_table(conn)
    query = str(conn.execute.call_args_list[0].args[0])
    assert CATALOG_POLICY_SQL in query
    assert loader.standard_name_index[normalize_standard_name("US甲状腺")][0]["version"] == "v1.1"


@pytest.mark.asyncio
async def test_keyword_loader_keeps_actual_version_without_changing_tuple_contract():
    engine = MagicMock()
    conn = AsyncMock()
    engine.connect.return_value.__aenter__.return_value = conn
    conn.execute.return_value = SimpleNamespace(fetchall=lambda: [
        ("us-code", "* US甲状腺", "US", "头颈", "甲状腺", "甲状腺", "常规", "v1.1")
    ])
    matcher = USSpectPetMatcher(engine=engine)
    matcher._load_rules_from_db = AsyncMock()
    await matcher.initialize()
    assert CATALOG_POLICY_SQL in str(conn.execute.call_args.args[0])
    assert matcher.standard_version("us-code", "* US甲状腺", "US") == "v1.1"
    assert matcher.standard_version("us-code", "* US甲状腺", "CT") is None
    assert matcher._us_items.iloc[0]["version"] == "v1.1"


def test_exact_name_result_has_actual_version():
    engine = MatchEngineOrchestrator.__new__(MatchEngineOrchestrator)
    engine.data_loader = SimpleNamespace(standard_name_index={
        normalize_standard_name("US甲状腺"): [{"code": "us-code", "name": "* US甲状腺",
                                                "modality": "US", "version": "v1.1"}]
    })
    result = engine._match_exact_standard_name("US甲状腺", "US")
    assert result["data"][0]["standard"][0]["version"] == "v1.1"


@pytest.mark.parametrize("source", ["US", "OTHER"])
def test_us_display_prefix_alias_preserves_anatomy_and_row(source):
    candidate = {"code": "interphalangeal", "name": "US指间关节常规超声检查",
                 "modality": "US", "version": "v1.1"}
    engine = MatchEngineOrchestrator.__new__(MatchEngineOrchestrator)
    engine.data_loader = SimpleNamespace(standard_name_index={},
        us_standard_name_alias_index={normalize_standard_name("指间关节常规超声检查"): [candidate]})
    result = engine._match_exact_standard_name("指间关节常规超声检查", source)
    assert result["tier"] == "exact"
    assert result["data"][0]["standard"] == [{k: candidate[k] for k in ["code", "name", "version"]}]
    assert engine._match_exact_standard_name("指间关节常规超声检查", "CT") is None


def test_us_prefix_alias_collision_requires_review():
    engine = MatchEngineOrchestrator.__new__(MatchEngineOrchestrator)
    engine.data_loader = SimpleNamespace(standard_name_index={}, us_standard_name_alias_index={
        "甲状腺超声检查": [{"code": code, "name": "US甲状腺超声检查", "modality": "US", "version": "v1.1"}
                       for code in ["one", "two"]]})
    result = engine._match_exact_standard_name("甲状腺超声检查", "US")
    assert result["tier"] == "ambiguous"
    assert result["reason"] == "standard_name_alias_collision"


@pytest.mark.parametrize("candidate", [("us-code", "* US甲状腺"),
                                        ("us-code", "* US甲状腺", "v1.1")])
def test_keyword_wrapper_keeps_pairs_and_adds_actual_row_version(candidate):
    engine = MatchEngineOrchestrator.__new__(MatchEngineOrchestrator)
    engine._kw_matcher = SimpleNamespace(
        match=lambda name, modality: [candidate],
        standard_version=lambda code, name, modality: "v1.1",
        _last_tier="exact", _last_reason="", _last_has_entity=True,
    )
    result = engine._kw_match("US甲状腺", "US")
    assert result["data"][0]["standard"] == [{"code": "us-code", "name": "* US甲状腺", "version": "v1.1"}]


@pytest.mark.parametrize("candidate", [("us-code", "US甲状腺"),
                                        ("us-code", "US甲状腺", None)])
def test_keyword_wrapper_missing_provenance_is_not_invented(candidate):
    engine = MatchEngineOrchestrator.__new__(MatchEngineOrchestrator)
    engine._kw_matcher = SimpleNamespace(
        match=lambda name, modality: [candidate],
        _last_tier="exact", _last_reason="", _last_has_entity=True,
    )
    result = engine._kw_match("US甲状腺", "US")
    assert result["data"][0]["standard"] == [{"code": "us-code", "name": "US甲状腺"}]


def test_keyword_wrapper_reports_malformed_candidate_as_error():
    engine = MatchEngineOrchestrator.__new__(MatchEngineOrchestrator)
    engine._kw_matcher = SimpleNamespace(match=lambda *args: [("incomplete",)])
    result = engine._kw_match("US甲状腺", "US")
    assert result["tier"] == "error"
    assert result["data"] == []


@pytest.mark.parametrize("legacy_version", [None, "", "  "])
def test_formatter_accepts_unversioned_historical_result(legacy_version):
    result = {"data": [{"standard": [{"code": "old", "name": "* CT头部",
                                      "std_version": legacy_version}]}]}
    dispatcher = MatchDispatcher.__new__(MatchDispatcher)
    dispatcher._format_result(result)
    standard = result["data"][0]["standard"][0]
    assert "version" not in standard
    assert standard["name"] == "CT头部"


def test_node_sorting_keeps_each_version_with_its_code():
    node = MatchNode("mixed", "CT", "V4.0.0")
    node.standard_check_code = ["z", "a"]
    node.standard_check_name = ["Z标准", "A标准"]
    node.standard_check_version = ["v3.8.2", "v1.1"]
    assert node.standard()["standard"] == [
        {"code": "a", "name": "A标准", "version": "v1.1"},
        {"code": "z", "name": "Z标准", "version": "v3.8.2"},
    ]


def test_node_never_fills_actual_version_from_selector():
    node = MatchNode("CT头部", "CT", "V4.0.0")
    node.standard_check_code = ["code"]
    node.standard_check_name = ["CT头部"]
    assert "version" not in node.standard()["standard"][0]


def test_lookup_row_version_survives_selector_fallback():
    df = pd.DataFrame([{"checkitem_code": "code", "checkitem_name": "CT头部", "version": "v3.8.2"}])
    loader = SimpleNamespace(df_standard={"CT": {"v3.8.2": df}})
    lookup = StandardLookupService(loader, MagicMock())
    lookup._query_standard_table = lambda *args: (df, False)
    node = MatchNode("CT头部", "CT", "V3.8.2")
    lookup.lookup_standard([node], {}, "scan", "CT", "V3.8.2")
    assert node.standard()["standard"][0]["version"] == "v3.8.2"


@pytest.mark.parametrize("explicit", [True, False])
def test_fallback_annotation_separates_request_from_actual(explicit):
    result = {"data": [{"standard": [{"code": "us-code", "name": "US甲状腺", "version": "v1.1"}]}]}
    MatchDispatcher._annotate_version_selection(result, "V3.8.2", explicit)
    assert result["requested_version"] == ("V3.8.2" if explicit else None)
    assert result["version_fallback"] is True
    assert result["version_fallback_reason"] == "loaded_modality_catalog_policy"
    assert result["data"][0]["standard"][0]["version"] == "v1.1"


@pytest.mark.parametrize("modality,input_name,pairs,expected_reason", [
    ("US", "US颈部血管多普勒超声检查", [("mass", "颈部包块常规超声检查")], "standard_semantic_conflict"),
    ("US", "超声多普勒（上肢及颈部静脉）", [("mass", "颈部包块常规超声检查")], "standard_semantic_conflict"),
    ("SPECT", "SPECT心肌灌注显像", [("infarct", "SPECT急性心肌梗死显像")], "standard_semantic_conflict"),
])
def test_keyword_semantic_conflicts_are_not_auto_accepted(modality, input_name, pairs, expected_reason):
    matcher = USSpectPetMatcher(engine=MagicMock())
    matcher._initialized = True
    matcher._match_us = lambda name: pairs
    matcher._match_spect = lambda name: pairs
    assert matcher.match(input_name, modality) == []
    assert matcher._last_reason == expected_reason
    assert matcher._last_unresolved_components


def test_spect_technical_candidates_remain_for_review():
    matcher = USSpectPetMatcher(engine=MagicMock())
    matcher._initialized = True
    pairs = [("bone", "SPECT常规静态骨显像"), ("blood", "SPECT骨血池显像")]
    matcher._match_spect = lambda name: pairs
    assert matcher.match("SPECT骨显像", "SPECT") == pairs
    assert matcher._last_tier == "ambiguous"
    assert matcher._last_reason == "multiple_technical_candidates"


def test_specific_spect_name_and_vascular_us_remain_valid():
    matcher = USSpectPetMatcher(engine=MagicMock())
    matcher._initialized = True
    matcher._match_us = lambda name: [("vascular", "双侧颈动脉常规超声检查")]
    matcher._match_spect = lambda name: [("perfusion", "SPECT心肌灌注断层显像")]
    assert matcher.match("US双侧颈动脉彩色多普勒超声检查", "US")
    assert matcher.match("SPECT心肌灌注断层显像", "SPECT")
    assert matcher._last_tier == "exact"


def test_explicit_mass_doppler_is_not_rejected_as_vascular():
    matcher = USSpectPetMatcher(engine=MagicMock())
    matcher._initialized = True
    pairs = [("mass", "颈部包块常规超声检查")]
    matcher._match_us = lambda name: pairs
    assert matcher.match("颈部包块彩色多普勒超声", "US") == pairs
    assert matcher._last_reason == ""


def test_hybrid_ct_exact_cannot_hide_spect_review():
    engine = MatchEngineOrchestrator.__new__(MatchEngineOrchestrator)
    engine._initialized = True
    engine._check_unmatchable = lambda *args: (False, "")
    engine._match_exact_standard_name = lambda *args: None
    engine._kw_match = lambda *args: {
        "data": [{"standard": [{"code": "bone", "name": "SPECT骨显像", "version": "v2.0"}]}],
        "tier": "ambiguous", "score": 4,
    }
    engine._inner_match = lambda *args: {
        "data": [{"standard": [{"code": "ct", "name": "CT骨盆平扫", "version": "v3.8.2"}]}],
        "tier": "exact", "score": 10,
    }
    result = engine.match("SPECT/CT胸部(骨显像+CT平扫)", "SPECT")
    assert result["tier"] == "ambiguous"
    assert result["num_standard"] == 2
    assert result["reason"] == "multiple_technical_candidates"


def spect_policy_engine(standards=True):
    engine = MatchEngineOrchestrator.__new__(MatchEngineOrchestrator)
    engine._initialized = True
    engine.data_loader = SimpleNamespace(standard_name_index={
        normalize_standard_name("SPECT常规静态骨显像"): [
            {"code": "database-bone-code", "name": "SPECT常规静态骨显像",
             "modality": "SPECT", "version": "v2.0"},
        ] if standards else [],
    })
    return engine


@pytest.mark.parametrize("name", ["SPECT/CT骨盆(骨显像+CT平扫)",
                                  " spect / ct 骨盆（骨显像 ＋ CT平扫） "])
@pytest.mark.parametrize("modality", ["SPECT", "SPECT/CT", ""])
def test_approved_pelvis_returns_only_loaded_static_spect(name, modality):
    result = spect_policy_engine().match(name, modality)
    assert result["tier"] == "exact"
    assert result["num_standard"] == 1
    assert result["data"] == [{"raw": name, "standard": [
        {"code": "database-bone-code", "name": "SPECT常规静态骨显像", "version": "v2.0"},
    ]}]
    assert result["excluded_components"][0]["modality"] == "CT"
    MatchDispatcher._apply_result_review_policy(result, name, "SPECT", modality != "SPECT", modality)
    assert result["tier"] == "exact"


def test_approved_pelvis_missing_standard_does_not_return_ct():
    result = spect_policy_engine(standards=False).match("SPECT/CT骨盆(骨显像+CT平扫)", "SPECT")
    assert result["tier"] == "none"
    assert result["data"] == []
    assert result["reason"] == "standard_lib_gap"


@pytest.mark.parametrize("name", ["SPECT/CT胸部(骨显像+CT平扫)",
                                  "SPECT/CT骨盆(骨显像+CT诊断平扫)",
                                  "SPECT/CT骨盆(骨血池显像+CT平扫)"])
def test_other_hybrids_cannot_skip_ct_review_with_policy_metadata(name):
    result = {"tier": "exact", "confidence": 1.0, "num_standard": 1,
              "business_policy": "spect_pelvis_bone_only",
              "excluded_components": [{"modality": "CT"}],
              "data": [{"standard": [{"code": "bone", "name": "SPECT常规静态骨显像", "version": "v2.0"}]}]}
    MatchDispatcher._apply_result_review_policy(result, name, "SPECT", False, "SPECT")
    assert result["tier"] == "ambiguous"
    assert result["reason"] == "compound_item_incomplete"


@pytest.mark.asyncio
@pytest.mark.parametrize("explicit", [True, False])
async def test_approved_pelvis_bypasses_old_ct_cache_without_mutating_it(explicit):
    holder = SimpleNamespace(match_engine=spect_policy_engine(), rule_version="rules")
    dispatcher = MatchDispatcher(AsyncMock(), holder)
    dispatcher.cache_service.lookup = AsyncMock(return_value={"tier": "exact", "data": [
        {"standard": [{"code": "ct", "name": "CT骨盆平扫", "version": "v3.8.2"}]}]})
    dispatcher.cache_service.store = AsyncMock()
    dispatcher._record_feedback = AsyncMock()
    result = await dispatcher.match("SPECT/CT骨盆(骨显像+CT平扫)", "SPECT/CT",
                                    version_is_explicit=explicit)
    assert result["tier"] == "exact"
    assert result["data"][0]["standard"][0]["version"] == "v2.0"
    assert result["requested_version"] == ("V3.8.2" if explicit else None)
    dispatcher.cache_service.lookup.assert_not_awaited()
    dispatcher.cache_service.store.assert_not_awaited()
    dispatcher._record_feedback.assert_not_awaited()


def test_remaining_safe_candidate_does_not_hide_semantic_conflict():
    matcher = USSpectPetMatcher(engine=MagicMock())
    matcher._initialized = True
    matcher._match_us = lambda name: [("good", "颈动脉超声检查"), ("bad", "颈部包块超声检查")]
    assert matcher.match("颈部血管超声检查", "US") == [("good", "颈动脉超声检查")]
    assert matcher._last_tier == "ambiguous"
    assert matcher._last_reason == "standard_semantic_conflict"


def test_combined_us_keeps_unresolved_component_and_requires_review():
    engine = MatchEngineOrchestrator.__new__(MatchEngineOrchestrator)
    engine._initialized = True
    engine._check_unmatchable = lambda *args: (False, "")
    engine._match_exact_standard_name = lambda *args: None
    def keyword(name, modality):
        if "静脉" in name:
            return {"tier": "none", "data": [], "score": 0,
                    "reason": "standard_semantic_conflict", "unresolved_components": ["颈部静脉"]}
        return {"tier": "exact", "score": 10,
                "data": [{"standard": [{"code": "abdomen", "name": "US腹部", "version": "v1.1"}]}]}
    engine._kw_match = keyword
    result = engine.match("US腹部常规超声,US颈部静脉超声", "US")
    assert result["tier"] == "ambiguous"
    assert result["unresolved_components"] == ["颈部静脉"]


@pytest.mark.parametrize("phase", ["负荷", "静息"])
def test_explicit_cardiac_perfusion_technique_remains_positive(phase):
    matcher = USSpectPetMatcher(engine=MagicMock())
    matcher._initialized = True
    matcher._match_spect = lambda name: [("perfusion", f"SPECT{phase}心肌灌注断层显像")]
    assert matcher.match(f"SPECT{phase}心肌灌注断层显像", "SPECT")
    assert matcher._last_tier == "exact"


@pytest.mark.parametrize("with_version", [False, True])
def test_generic_perfusion_cannot_choose_a_technical_qualifier(with_version):
    matcher = USSpectPetMatcher(engine=MagicMock())
    matcher._initialized = True
    candidate = ("perfusion", "SPECT负荷心肌灌注断层显像")
    if with_version:
        candidate += ("v3.8.2",)
    matcher._match_spect = lambda name: [candidate]
    assert matcher.match("SPECT心肌灌注显像", "SPECT")
    assert matcher._last_tier == "ambiguous"
    assert matcher._last_reason == "unspecified_technical_qualifier"


@pytest.mark.parametrize("with_version", [False, True])
def test_supplemented_base_scan_uses_row_version(with_version):
    df = pd.DataFrame([
        {"checkitem_code": "post", "checkitem_name": "CT头部三维重建", "version": "v3.8.2"},
        {"checkitem_code": "base", "checkitem_name": "CT头部平扫", "version": "v3.8.2"},
    ])
    loader = SimpleNamespace(df_standard={"CT": {"v3.8.2": df}})
    lookup = StandardLookupService(loader, MagicMock())
    lookup._query_standard_table = lambda *args: (df.iloc[:1], False)
    candidate = ("CT头部平扫", "base")
    if with_version:
        candidate += ("v3.8.2",)
    lookup._supplement_base_scans = lambda *args: [candidate]
    node = MatchNode("CT头部三维重建", "CT", "V3.8.2")
    node.add_entity("头部", "body", "头部")
    node.add_entity("三维重建", "post", "三维重建")
    lookup.lookup_standard([node], {}, "scan", "CT", "V3.8.2")
    assert {s["code"]: s["version"] for s in node.standard()["standard"]} == {
        "post": "v3.8.2", "base": "v3.8.2",
    }

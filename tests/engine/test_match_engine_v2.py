"""
匹配引擎 V2 vs V1 对比测试

需要数据库连接才能运行（从 nlp_* 表加载规则数据）。
用法：
    cd acrac_backend
    poetry run pytest tests/test_match_engine_v2.py -v
"""
import asyncio
import pytest

from match_service.db import get_engine
async_engine = get_engine()


# ─── Fixtures ──────────────────────────────────────────────────────────────

# @pytest.fixture(scope="module")
@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    # 全局 async_engine 的连接池可能持有绑定在其他模块 event loop 上的连接，
    # 先清空连接池，避免跨模块混跑时报 "attached to a different loop"
    loop.run_until_complete(async_engine.dispose())
    yield loop
    loop.run_until_complete(async_engine.dispose())
    loop.close()


@pytest.fixture(scope="module")
def v1_engine(event_loop):
# Phase A: V1 引擎已移除
    eng = ExamineMatchEngine()
    event_loop.run_until_complete(eng.initialize())
    return eng  # Phase A: V1 引擎不再可用，对比测试已禁用


@pytest.fixture(scope="module")
def v2_engine(event_loop):
    from match_service.engine.match_engine_v2 import MatchEngineOrchestrator
    orch = MatchEngineOrchestrator(async_engine)
    event_loop.run_until_complete(orch.initialize())
    return orch


# ─── 测试用例 ──────────────────────────────────────────────────────────────

CT_CASES = [
    ("CT头部平扫", "CT"),
    ("CT头部平扫+增强", "CT"),
    ("CT胸部平扫", "CT"),
    ("CT腹部平扫+增强", "CT"),
    ("CT颈部增强", "CT"),
    ("冠状动脉CTA", "CT"),
    # ("头颈部CTA", "CT"),  # 移至 VASCULAR_FIX_CASES（V2 修复子串贪婪，比 V1 更正确）
    ("下肢动脉CTA", "CT"),
    ("CT腰椎平扫", "CT"),
    ("CT全腹部平扫+增强", "CT"),
    ("CT胸部高分辨平扫", "CT"),
    # ("CT膝关节平扫", "CT"),  # 移至 BILATERAL_FIX_CASES
]

MR_CASES = [
    ("MR头部平扫", "MR"),
    ("MR头部平扫+增强", "MR"),
    ("MR腰椎平扫", "MR"),
    # ("MR膝关节平扫", "MR"),  # 移至 BILATERAL_FIX_CASES
    ("MR乳腺平扫+增强", "MR"),
    ("MR颈椎平扫", "MR"),
    ("颅脑MRA", "MR"),
]

DR_CASES = [
    ("胸部正位", "DR"),
    # ("膝关节正、侧位", "DR"),  # 移至 BILATERAL_FIX_CASES
    ("腰椎正、侧位", "DR"),
    ("颈椎正、侧位", "DR"),
    # ("手正位", "DR"),  # 移至 BILATERAL_FIX_CASES
    ("骨盆正位", "DR"),
    # ("踝关节正、侧位", "DR"),  # 移至 BILATERAL_FIX_CASES
]

RF_MG_CASES = [
    ("上消化道钡餐造影", "RF"),
    # ("乳腺钼靶", "MG"),  # 移至 BILATERAL_FIX_CASES
]

# V2 双侧匹配修复后的正确行为（与 V1 不同，V2 更正确）
# 这些 case V1 错误地匹配到单侧，V2 修复后正确匹配双侧
BILATERAL_FIX_CASES = [
    ("CT膝关节平扫", "CT", "双膝关节"),
    ("MR膝关节平扫", "MR", "双膝关节"),
    ("膝关节正、侧位", "DR", "双膝关节"),
    ("手正位", "DR", "双手"),
    ("踝关节正、侧位", "DR", "双踝关节"),
    ("乳腺钼靶", "MG", "双侧乳腺"),
]

# V2 血管成像复合部位修复后的正确行为（与 V1 不同，V2 更正确）
# 根因：_normalize_vascular_body 子串贪婪匹配，V1 把"头颈部动脉"截断成"颈部动脉"，
# V2 修复后按复合部位优先匹配。详见 tests/test_vascular_body_matching.py
VASCULAR_FIX_CASES = [
    ("头颈部CTA", "CT", "头颈部动脉"),
]


def _extract_standards(result: dict) -> set:
    """提取标准项名称集合"""
    names = set()
    for data_item in result.get('data', []):
        for std in data_item.get('standard', []):
            names.add(std['name'])
    return names


# @pytest.mark.parametrize("record,modality", CT_CASES + MR_CASES + DR_CASES + RF_MG_CASES)
# Phase A: 以下测试依赖 V1 引擎对比，已禁用
# def test_v2_matches_v1(v1_engine, v2_engine, record, modality):
#     """V2 引擎的标准项输出应与 V1 一致"""
#     r1 = v1_engine.match(record, modality, "V3.8.2")
#     r2 = v2_engine.match(record, modality, "V3.8.2")

#     s1 = _extract_standards(r1)
#     s2 = _extract_standards(r2)

#     assert s1 == s2, (
#         f"\n输入: {record} ({modality})"
#         f"\nV1: {sorted(s1)}"
#         f"\nV2: {sorted(s2)}"
#         f"\nV1多: {sorted(s1 - s2)}"
#         f"\nV2多: {sorted(s2 - s1)}"
#     )


@pytest.mark.parametrize("record,modality,expected_keyword", BILATERAL_FIX_CASES)
def test_v2_bilateral_fix(v2_engine, record, modality, expected_keyword):
    """
    V2 双侧匹配修复验证（与 V1 行为不同，V2 更正确）

    修复前（V1 和旧 V2）：未指定左右的部位错误匹配到单侧
    修复后（新 V2）：未指定左右时正确匹配双侧（医学默认行为）

    详见: docs/reports/2026-06-30-bilateral-body-fix-summary.md
    """
    result = v2_engine.match(record, modality, "V3.8.2")
    standards = _extract_standards(result)

    assert len(standards) > 0, f"V2 应能匹配到结果: {record} ({modality})"

    # 核心断言：匹配结果中应包含期望的双侧关键词
    matched_names = ' '.join(standards)
    assert expected_keyword in matched_names, (
        f"\n输入: {record} ({modality})"
        f"\n期望包含: {expected_keyword}"
        f"\n实际匹配: {sorted(standards)}"
    )


@pytest.mark.parametrize("record,modality,expected_keyword", VASCULAR_FIX_CASES)
def test_v2_vascular_fix(v2_engine, record, modality, expected_keyword):
    """
    V2 血管成像复合部位修复验证（与 V1 行为不同，V2 更正确）

    修复前（V1 和旧 V2）："头颈部动脉"被子串贪婪规则"颈部"截断成"颈部动脉"
    修复后（新 V2）：复合部位"头颈部"优先匹配，正确命中头颈部动脉标准项

    详见: tests/test_vascular_body_matching.py
    """
    result = v2_engine.match(record, modality, "V3.8.2")
    standards = _extract_standards(result)

    assert len(standards) > 0, f"V2 应能匹配到结果: {record} ({modality})"

    matched_names = ' '.join(standards)
    assert expected_keyword in matched_names, (
        f"\n输入: {record} ({modality})"
        f"\n期望包含: {expected_keyword}"
        f"\n实际匹配: {sorted(standards)}"
    )


@pytest.mark.parametrize("record,modality", CT_CASES[:5])
def test_v2_has_results(v2_engine, record, modality):
    """V2 引擎应能产出非空匹配"""
    result = v2_engine.match(record, modality, "V3.8.2")
    standards = _extract_standards(result)
    assert len(standards) > 0, f"V2 无匹配结果: {record} ({modality})"


def test_v2_batch_match(v2_engine):
    """批量匹配应返回正确结构（CT/MR/DR 走 NLP，US 走关键词引擎）"""
    items = [
        {"key": "1", "modality": "CT", "name": "CT胸部平扫"},
        {"key": "2", "modality": "MR", "name": "MR头部平扫"},
        {"key": "3", "modality": "DR", "name": "膝关节正、侧位"},
        {"key": "4", "modality": "US", "name": "超声心动"},
    ]
    results = v2_engine.batch_match(items, version="V3.8.2")

    assert "1" in results
    assert "2" in results
    assert "3" in results
    assert "4" in results
    # US 现在通过统一入口策略分派到关键词引擎，应能匹配到结果
    assert len(results["4"]) > 0, f"US 应能匹配到结果: 超声心动"


def test_v2_unmatchable_markers(v2_engine):
    """包含特殊标识的医嘱不应自动匹配"""
    items = [
        {"key": "a", "modality": "CT", "name": "CT引导下穿刺定位"},
        {"key": "b", "modality": "CT", "name": "CT介入治疗"},
        {"key": "c", "modality": "CT", "name": "CT放疗定位"},
    ]
    results = v2_engine.batch_match(items, version="V3.8.2")
    for key in ("a", "b", "c"):
        assert results[key] == [], f"特殊医嘱不应匹配: {items[ord(key) - ord('a')]['name']}"


def test_v2_empty_input(v2_engine):
    """空输入应返回空结果"""
    result = v2_engine.match("", "CT", "V3.8.2")
    assert result['num_standard'] == 0


def test_v2_invalid_modality(v2_engine):
    """无效模态应返回空结果"""
    result = v2_engine.match("CT头部平扫", "INVALID", "V3.8.2")
    assert result['num_standard'] == 0
    assert result['score'] == 0


# ─── US/PET/SPECT 统一入口强断言（策略分派到关键词引擎）──────────────────────

US_STRONG_CASES = [
    ("超声心动", "US"),
    ("腹部超声", "US"),
    ("甲状腺超声", "US"),
    ("颈动脉彩超", "US"),
    ("乳腺超声", "US"),
]

PET_STRONG_CASES = [
    ("PET/CT全身显像", "PET/CT"),
    ("PET/CT脑代谢", "PET/CT"),
    ("PET/MR全身", "PET/MR"),
]

SPECT_STRONG_CASES = [
    ("SPECT心肌灌注", "SPECT"),
    ("SPECT骨显像", "SPECT"),
    ("SPECT甲状腺显像", "SPECT"),
]


@pytest.mark.parametrize("record,modality", US_STRONG_CASES)
def test_v2_us_match_has_results(v2_engine, record, modality):
    """US 通过统一入口应匹配到非空结果（委托关键词引擎）"""
    result = v2_engine.match(record, modality, "V3.8.2")
    assert result['check_item'] == record
    assert result['num_standard'] > 0, f"US 无匹配结果: {record}"
    # 验证返回结构一致（与 NLP 格式相同）
    assert isinstance(result['data'], list)
    assert len(result['data']) > 0
    std = result['data'][0].get('standard', [])
    assert len(std) > 0
    # 每个标准项应有 code 和 name
    assert 'code' in std[0] and 'name' in std[0]


@pytest.mark.parametrize("record,modality", PET_STRONG_CASES)
def test_v2_pet_match_has_results(v2_engine, record, modality):
    """PET 通过统一入口应匹配到非空结果（委托关键词引擎）"""
    result = v2_engine.match(record, modality, "V3.8.2")
    assert result['check_item'] == record
    assert result['num_standard'] > 0, f"PET 无匹配结果: {record}"


@pytest.mark.parametrize("record,modality", SPECT_STRONG_CASES)
def test_v2_spect_match_has_results(v2_engine, record, modality):
    """SPECT 通过统一入口应匹配到非空结果（委托关键词引擎）"""
    result = v2_engine.match(record, modality, "V3.8.2")
    assert result['check_item'] == record
    assert result['num_standard'] > 0, f"SPECT 无匹配结果: {record}"


def test_v2_batch_match_all_modalities(v2_engine):
    """批量匹配应统一支持所有模态（NLP + 关键词引擎自动分派）"""
    items = [
        {"key": "ct1", "modality": "CT", "name": "CT胸部平扫"},
        {"key": "us1", "modality": "US", "name": "腹部超声"},
        {"key": "pet1", "modality": "PET/CT", "name": "PET/CT全身显像"},
        {"key": "spect1", "modality": "SPECT", "name": "SPECT骨显像"},
        {"key": "bad1", "modality": "INVALID", "name": "无效模态"},
    ]
    results = v2_engine.batch_match(items, version="V3.8.2")

    for key in ("ct1", "us1", "pet1", "spect1", "bad1"):
        assert key in results
    # 无效模态返回空
    assert results["bad1"] == []
    # 各有效模态都应匹配到结果
    assert len(results["ct1"]) > 0, "CT 应匹配到结果"
    assert len(results["us1"]) > 0, "US 应匹配到结果"
    assert len(results["pet1"]) > 0, "PET/CT 应匹配到结果"
    assert len(results["spect1"]) > 0, "SPECT 应匹配到结果"


def test_v2_cross_modality_split(v2_engine):
    """跨模态拆分：CT+US 混合输入，两部分都应匹配到结果"""
    result = v2_engine.match("CT胸部平扫;超声心动", "CT", "V3.8.2")
    assert result['check_item'] == "CT胸部平扫;超声心动"
    # CT 部分 + US 部分都应有匹配
    assert result['num_standard'] >= 2, (
        f"组合医嘱应同时匹配 CT 和 US: num_standard={result['num_standard']}"
    )
    # 验证 data 中包含两种模态的结果
    all_standards = []
    for d in result['data']:
        all_standards.extend(d.get('standard', []))
    all_names = ' '.join(s['name'] for s in all_standards)
    # CT 胸部相关 + US 心脏相关都应在结果中
    assert any('胸' in n for n in all_names), f"缺少 CT 胸部匹配: {all_names}"
    assert any('心' in n for n in all_names), f"缺少 US 心脏匹配: {all_names}"


def test_v2_us_unmatchable(v2_engine):
    """US 特殊用途医嘱不应匹配（关键词引擎内部的 US_UNMATCHABLE）"""
    items = [
        {"key": "u1", "modality": "US", "name": "超声临床操作"},
        {"key": "u2", "modality": "US", "name": "超声内镜检查"},
    ]
    results = v2_engine.batch_match(items, version="V3.8.2")
    for key in ("u1", "u2"):
        assert results[key] == [], f"US 特殊医嘱不应匹配: {items[ord(key[1]) - ord('1')]['name']}"


# ─── 置信度四档（tier）───────────────────────────────────────────────────────

def test_v2_tier_exact(v2_engine):
    """显式部位+扫描方式 → exact 档，confidence=1.0"""
    result = v2_engine.match("CT头部平扫", "CT", "V3.8.2")
    assert result['num_standard'] > 0
    assert result['tier'] == 'exact'
    assert result['confidence'] == 1.0


def test_v2_tier_partial_default_process(v2_engine):
    """只给部位不给扫描方式 → 默认推断处理方式 → partial 档"""
    result = v2_engine.match("CT头部", "CT", "V3.8.2")
    assert result['num_standard'] > 0
    assert result['tier'] == 'partial'
    assert result['confidence'] == 0.8


def test_v2_tier_none(v2_engine):
    """无效模态 → none 档，confidence=0"""
    result = v2_engine.match("CT头部平扫", "INVALID", "V3.8.2")
    assert result['tier'] == 'none'
    assert result['confidence'] == 0.0


def test_v2_batch_match_detailed_contains_confidence(v2_engine):
    """batch_match_detailed 每条结果都带 pairs/score/tier/confidence"""
    items = [
        {"key": "1", "modality": "CT", "name": "CT头部平扫"},
        {"key": "2", "modality": "INVALID", "name": "未知检查"},
    ]
    results = v2_engine.batch_match_detailed(items, version="V3.8.2")
    assert set(results.keys()) == {"1", "2"}
    for info in results.values():
        assert {'pairs', 'score', 'tier', 'confidence'} <= set(info.keys())
    assert results["1"]['tier'] == 'exact'
    assert results["1"]['confidence'] == 1.0
    assert results["2"]['tier'] == 'none'
    assert results["2"]['pairs'] == []

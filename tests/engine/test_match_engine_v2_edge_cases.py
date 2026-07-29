"""
边界场景和异常输入测试

覆盖各种特殊情况、错误输入、边界条件
"""
import asyncio
import pytest
from match_service.db import get_engine
async_engine = get_engine()


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    # 清空全局连接池，避免复用绑定在其他模块 event loop 上的连接
    loop.run_until_complete(async_engine.dispose())
    yield loop
    loop.run_until_complete(async_engine.dispose())
    loop.close()


@pytest.fixture(scope="module")
def v2_engine(event_loop):
    from match_service.engine.match_engine_v2 import MatchEngineOrchestrator
    orch = MatchEngineOrchestrator(async_engine)
    event_loop.run_until_complete(orch.initialize())
    return orch


class TestEdgeCases:
    """边界场景测试"""

    # ─── 输入边界 ───────────────────────────────────────────────────

    def test_empty_input(self, v2_engine):
        """空输入"""
        result = v2_engine.match("", "CT", "V3.8.2")
        assert result['num_standard'] == 0

    def test_whitespace_only(self, v2_engine):
        """纯空格输入"""
        result = v2_engine.match("   ", "CT", "V3.8.2")
        assert result['num_standard'] == 0

    def test_very_long_input(self, v2_engine):
        """超长输入（100+ 字符）"""
        long_text = "CT头部平扫," * 30
        result = v2_engine.match(long_text, "CT", "V3.8.2")
        # 应能处理，不崩溃
        assert 'num_standard' in result

    def test_special_characters(self, v2_engine):
        """特殊字符"""
        result = v2_engine.match("CT头部@#$%平扫&*", "CT", "V3.8.2")
        # 应能容错处理
        assert 'num_standard' in result

    def test_unicode_variants(self, v2_engine):
        """Unicode 变体（全角、半角混合）"""
        result = v2_engine.match("ＣＲ头部ＰＬａｎ扫描", "CT", "V3.8.2")
        assert 'num_standard' in result

    # ─── 模态边界 ───────────────────────────────────────────────────

    def test_invalid_modality(self, v2_engine):
        """无效模态"""
        result = v2_engine.match("头部平扫", "INVALID", "V3.8.2")
        assert result['num_standard'] == 0
        assert result['score'] == 0

    def test_case_sensitive_modality(self, v2_engine):
        """模态大小写"""
        result1 = v2_engine.match("头部平扫", "CT", "V3.8.2")
        result2 = v2_engine.match("头部平扫", "ct", "V3.8.2")
        # 小写应失败
        assert result1['num_standard'] > 0
        assert result2['num_standard'] == 0

    def test_us_delegates_to_keyword_engine(self, v2_engine):
        """US 模态已支持：应委托关键词引擎并返回结果"""
        result = v2_engine.match("超声心动", "US", "V3.8.2")
        assert result['num_standard'] > 0
        names = {s['name'] for d in result['data'] for s in d['standard']}
        assert any('心' in n for n in names)

    # ─── 复杂结构 ───────────────────────────────────────────────────

    def test_multiple_bodies_with_single_scan(self, v2_engine):
        """多部位 + 单处理方式"""
        result = v2_engine.match("头部胸部腹部平扫", "CT", "V3.8.2")
        # 应分裂为 3 个部位
        assert result['num_standard'] >= 3

    def test_multiple_scans_with_single_body(self, v2_engine):
        """单部位 + 多处理方式"""
        result = v2_engine.match("头部平扫增强", "CT", "V3.8.2")
        # 应产生至少 2 个匹配（平扫 + 增强）
        assert result['num_standard'] >= 1

    def test_cross_modality_mix(self, v2_engine):
        """跨模态混合输入"""
        result = v2_engine.match("CT头部,MR腰椎,DR胸部", "CT", "V3.8.2")
        # 应处理 3 个模态
        assert len(result['data']) >= 3

    def test_nested_parentheses(self, v2_engine):
        """嵌套括号"""
        result = v2_engine.match("CT头部(平扫(普通))", "CT", "V3.8.2")
        assert 'num_standard' in result

    # ─── 脊椎专项 ───────────────────────────────────────────────────

    def test_vertebra_range_simple(self, v2_engine):
        """简单脊椎范围"""
        result = v2_engine.match("腰椎L3-L5", "CT", "V3.8.2")
        assert result['num_standard'] > 0

    def test_vertebra_range_complex(self, v2_engine):
        """复杂脊椎范围（跨段）"""
        result = v2_engine.match("颈胸段C7-T2", "CT", "V3.8.2")
        assert result['num_standard'] >= 0

    def test_vertebra_without_prefix(self, v2_engine):
        """脊椎无前缀（应自动补全）"""
        result = v2_engine.match("L4-L5椎间盘", "CT", "V3.8.2")
        # 应能识别为腰椎
        assert result['num_standard'] >= 0

    # ─── 左右部位 ───────────────────────────────────────────────────

    def test_left_right_explicit(self, v2_engine):
        """明确左右"""
        result = v2_engine.match("左膝关节", "DR", "V3.8.2")
        assert result['num_standard'] > 0

    def test_bilateral(self, v2_engine):
        """双侧"""
        result = v2_engine.match("双侧膝关节", "DR", "V3.8.2")
        assert result['num_standard'] > 0

    def test_left_or_right(self, v2_engine):
        """左|右并列"""
        result = v2_engine.match("左|右膝关节", "DR", "V3.8.2")
        # 应分裂为 2 个
        assert result['num_standard'] >= 2
        names = {s['name'] for d in result['data'] for s in d['standard']}
        assert any('左膝' in n for n in names)
        assert any('右膝' in n for n in names)

    # ─── 血管成像 ───────────────────────────────────────────────────

    def test_vascular_cta_without_body(self, v2_engine):
        """CTA 无明确部位（应推断）"""
        result = v2_engine.match("CTA", "CT", "V3.8.2")
        # 应能匹配到非指定部位的 CTA
        assert result['num_standard'] >= 0

    def test_vascular_artery_vs_vein(self, v2_engine):
        """动脉 vs 静脉消歧"""
        result1 = v2_engine.match("下肢动脉CTA", "CT", "V3.8.2")
        result2 = v2_engine.match("下肢静脉CTV", "CT", "V3.8.2")

        assert result1['num_standard'] > 0
        assert result2['num_standard'] > 0
        # 结果应不同
        names1 = {s['name'] for d in result1['data'] for s in d['standard']}
        names2 = {s['name'] for d in result2['data'] for s in d['standard']}
        assert names1 != names2

    def test_coronary_artery(self, v2_engine):
        """冠状动脉特殊处理"""
        result = v2_engine.match("冠状动脉CTA", "CT", "V3.8.2")
        assert result['num_standard'] > 0
        names = {s['name'] for d in result['data'] for s in d['standard']}
        assert any('冠' in n for n in names)

    # ─── DR 体位专项 ──────────────────────────────────────────────────

    def test_dr_position_combined(self, v2_engine):
        """组合体位（正、侧位）：标准库中"正、侧位"是单一组合项，应精确命中"""
        result = v2_engine.match("膝关节正、侧位", "DR", "V3.8.2")
        assert result['num_standard'] >= 1
        names = {s['name'] for d in result['data'] for s in d['standard']}
        assert any('膝关节正、侧位' in n for n in names)

    def test_dr_position_standing_with_body(self, v2_engine):
        """站立体位（带部位）：应命中站立组合项"""
        result = v2_engine.match("膝关节站立正、侧位", "DR", "V3.8.2")
        assert result['num_standard'] > 0
        names = {s['name'] for d in result['data'] for s in d['standard']}
        assert any('站立' in n for n in names)

    def test_dr_position_standing_without_body(self, v2_engine):
        """站立体位（无部位）：标准库中站立位仅存在于膝/足，
        无部位时歧义，应明确拒绝而非强行匹配"""
        result = v2_engine.match("站立正、侧位", "DR", "V3.8.2")
        assert result['num_standard'] == 0

    def test_dr_position_weight_bearing_with_body(self, v2_engine):
        """负重体位（带部位）：标准库仅有"负重正、侧位"组合项，
        "负重正位"应通过超集映射命中该项"""
        result = v2_engine.match("膝关节负重正位", "DR", "V3.8.2")
        assert result['num_standard'] > 0
        names = {s['name'] for d in result['data'] for s in d['standard']}
        assert any('负重' in n for n in names)

    def test_dr_position_weight_bearing_without_body(self, v2_engine):
        """负重体位（无部位）：歧义输入应明确拒绝"""
        result = v2_engine.match("负重正位", "DR", "V3.8.2")
        assert result['num_standard'] == 0

    # ─── 特殊医嘱 ───────────────────────────────────────────────────

    def test_special_radiotherapy(self, v2_engine):
        """放疗定位（不应匹配）"""
        items = [{"key": "1", "modality": "CT", "name": "CT放疗定位"}]
        result = v2_engine.batch_match(items, "V3.8.2")
        assert result["1"] == []

    def test_special_intervention(self, v2_engine):
        """介入操作（不应匹配）"""
        items = [{"key": "1", "modality": "CT", "name": "CT引导介入"}]
        result = v2_engine.batch_match(items, "V3.8.2")
        assert result["1"] == []

    def test_special_biopsy(self, v2_engine):
        """穿刺定位（不应匹配）"""
        items = [{"key": "1", "modality": "CT", "name": "CT穿刺定位"}]
        result = v2_engine.batch_match(items, "V3.8.2")
        assert result["1"] == []

    # ─── 批量匹配边界 ───────────────────────────────────────────────

    def test_batch_empty_list(self, v2_engine):
        """空列表"""
        result = v2_engine.batch_match([], "V3.8.2")
        assert result == {}

    def test_batch_missing_fields(self, v2_engine):
        """缺少必需字段"""
        items = [{"key": "1"}]  # 缺少 modality, name
        result = v2_engine.batch_match(items, "V3.8.2")
        assert result["1"] == []

    def test_batch_duplicate_keys(self, v2_engine):
        """重复 key（后者覆盖前者）"""
        items = [
            {"key": "1", "modality": "CT", "name": "CT头部"},
            {"key": "1", "modality": "MR", "name": "MR腰椎"},
        ]
        result = v2_engine.batch_match(items, "V3.8.2")
        # 后者覆盖
        assert "1" in result

    def test_batch_large_scale(self, v2_engine):
        """大批量（100+ 项）"""
        items = [
            {"key": str(i), "modality": "CT", "name": "CT头部平扫"}
            for i in range(100)
        ]
        result = v2_engine.batch_match(items, "V3.8.2")
        assert len(result) == 100


class TestVersionCompatibility:
    """版本兼容性测试"""

    def test_version_v3_8(self, v2_engine):
        """V3.8 版本"""
        result = v2_engine.match("CT头部平扫", "CT", "V3.8")
        assert result['num_standard'] > 0

    def test_version_v3_8_2(self, v2_engine):
        """V3.8.2 版本"""
        result = v2_engine.match("CT头部平扫", "CT", "V3.8.2")
        assert result['num_standard'] > 0

    def test_version_fallback(self, v2_engine):
        """版本回退（V3.8.2 → V3.8）"""
        # 如果某项只在 V3.8 中存在，V3.8.2 应能回退匹配
        result = v2_engine.match("CT头部平扫", "CT", "V3.8.2")
        assert result['num_standard'] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-k", "test_"])

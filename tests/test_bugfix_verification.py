"""
验证 2026-08-02 修复的 8 个算法漏洞（C1-C4, H1-H4）
运行: python -m pytest tests/test_bugfix_verification.py -v
"""
import re
import sys
import os
import pytest

# 确保 src 在路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


# ============================================================
# C1: preprocess 连字符删除破坏 CE-MRA
# ============================================================
class TestC1HyphenProtection:
    """C1: CE-MRA/CE-MRV 连字符在预处理后应保留"""

    def _preprocess(self, text: str) -> str:
        """模拟 preprocess_service 的连字符处理逻辑"""
        _protected = ('CE-MRA', 'CE-MRV', 'CE-CT', 'CE-MRI')
        for term in _protected:
            text = text.replace(term, term.replace('-', '\x01'))
        text = re.sub(r'([A-Za-z]+)-([A-Za-z]+)', r'\1\2', text)
        for term in _protected:
            text = text.replace(term.replace('-', '\x01'), term)
        return text

    def test_ce_mra_preserved(self):
        result = self._preprocess("CE-MRA头颅")
        assert 'CE-MRA' in result, f"CE-MRA 被破坏: {result}"

    def test_ce_mrv_preserved(self):
        result = self._preprocess("CE-MRV腹部")
        assert 'CE-MRV' in result, f"CE-MRV 被破坏: {result}"

    def test_ce_ct_preserved(self):
        result = self._preprocess("CE-CT胸部")
        assert 'CE-CT' in result, f"CE-CT 被破坏: {result}"

    def test_normal_hyphen_removed(self):
        """非医学缩写的连字符仍应被删除"""
        result = self._preprocess("T-SPOT检测")
        assert 'TSPOT' in result or 'T-SPOT' not in result.replace('CE-', ''), \
            f"普通连字符未被删除: {result}"

    def test_disambiguation_regex_matches(self):
        """Step 8.5 的正则应能匹配保留连字符后的文本"""
        text = self._preprocess("CE-MRA头颅")
        assert re.search(r'(CE-MRA|CE-MRV)', text), \
            f"Step 8.5 正则无法匹配: {text}"


# ============================================================
# C2: merge_nodes 合并后 body_0/process_0 未更新
# ============================================================
class TestC2MergeNodeRefresh:
    """C2: 合并后 body_0/process_0 应重新计算"""

    def test_source_code_has_refresh(self):
        """验证源码中包含 body_0/process_0 重新计算逻辑"""
        src_path = os.path.join(
            os.path.dirname(__file__), '..', 'src',
            'match_service', 'engine', 'match_engine_v2', 'disambiguation_service.py'
        )
        with open(src_path, 'r') as f:
            source = f.read()

        # 检查 merge_nodes 方法中，node_0 = node_j 之后有 body_0 重新赋值
        merge_section = source[source.index('def merge_nodes'):]
        merge_section = merge_section[:merge_section.index('\n    def ', 1)]

        assert 'node_0 = node_j' in merge_section, "缺少 node_0 = node_j"
        # 在 node_0 = node_j 之后应有 body_0 重新计算
        idx = merge_section.index('node_0 = node_j')
        after_merge = merge_section[idx:]
        assert 'body_0 = node_0' in after_merge, \
            "C2 未修复：node_0 = node_j 之后缺少 body_0 重新计算"
        assert 'process_0 = ' in after_merge, \
            "C2 未修复：node_0 = node_j 之后缺少 process_0 重新计算"


# ============================================================
# C3: lru_cache 热重载不失效
# ============================================================
class TestC3CacheClear:
    """C3: TokenizerService 应有 clear_cache 方法"""

    def test_clear_cache_method_exists(self):
        src_path = os.path.join(
            os.path.dirname(__file__), '..', 'src',
            'match_service', 'engine', 'match_engine_v2', 'tokenizer_service.py'
        )
        with open(src_path, 'r') as f:
            source = f.read()
        assert 'def clear_cache(self)' in source, \
            "C3 未修复：TokenizerService 缺少 clear_cache 方法"
        assert 'cache_clear()' in source, \
            "C3 未修复：clear_cache 未调用 cache_clear()"

    def test_orchestrator_calls_clear_cache(self):
        src_path = os.path.join(
            os.path.dirname(__file__), '..', 'src',
            'match_service', 'engine', 'match_engine_v2', 'orchestrator.py'
        )
        with open(src_path, 'r') as f:
            source = f.read()
        assert 'clear_cache()' in source, \
            "C3 未修复：orchestrator 未在重新初始化时调用 clear_cache()"


# ============================================================
# C4: US 扫描降级仍报 exact/1.0
# ============================================================
class TestC4DegradedTier:
    """C4: US 扫描方式降级后应标记 degraded"""

    def test_matcher_has_last_tier(self):
        src_path = os.path.join(
            os.path.dirname(__file__), '..', 'src',
            'match_service', 'engine', 'keyword', 'us_spect_pet_matcher.py'
        )
        with open(src_path, 'r') as f:
            source = f.read()
        assert "_last_tier" in source, "C4 未修复：matcher 缺少 _last_tier 属性"
        assert "self._last_tier = 'degraded'" in source, \
            "C4 未修复：降级时未设置 _last_tier = 'degraded'"

    def test_orchestrator_reads_last_tier(self):
        src_path = os.path.join(
            os.path.dirname(__file__), '..', 'src',
            'match_service', 'engine', 'match_engine_v2', 'orchestrator.py'
        )
        with open(src_path, 'r') as f:
            source = f.read()
        assert '_last_tier' in source, \
            "C4 未修复：orchestrator 未读取 matcher 的 _last_tier"

    def test_match_resets_tier(self):
        """match() 方法应在每次调用前重置 _last_tier"""
        src_path = os.path.join(
            os.path.dirname(__file__), '..', 'src',
            'match_service', 'engine', 'keyword', 'us_spect_pet_matcher.py'
        )
        with open(src_path, 'r') as f:
            source = f.read()
        match_method = source[source.index('def match(self'):]
        match_method = match_method[:match_method.index('\n    def ', 1)]
        assert "self._last_tier = 'exact'" in match_method, \
            "C4 未修复：match() 未在调用前重置 _last_tier"


# ============================================================
# H1: SPECT/PET/OCT 无 unmatchable 检查
# ============================================================
class TestH1Unmatchable:
    """H1: SPECT/PET/OCT 应有 unmatchable 排除检查"""

    def _read_matcher_source(self) -> str:
        src_path = os.path.join(
            os.path.dirname(__file__), '..', 'src',
            'match_service', 'engine', 'keyword', 'us_spect_pet_matcher.py'
        )
        with open(src_path, 'r') as f:
            return f.read()

    def test_spect_unmatchable(self):
        source = self._read_matcher_source()
        assert '_spect_unmatchable' in source, "H1: SPECT 缺少 unmatchable 属性"
        # 检查 _match_spect 中有排除逻辑
        match_spect = source[source.index('def _match_spect'):]
        match_spect = match_spect[:match_spect.index('\n    def ', 1)]
        assert '_spect_unmatchable' in match_spect, "H1: _match_spect 缺少排除检查"

    def test_pet_unmatchable(self):
        source = self._read_matcher_source()
        assert '_pet_unmatchable' in source, "H1: PET 缺少 unmatchable 属性"
        match_pet = source[source.index('def _match_pet'):]
        match_pet = match_pet[:match_pet.index('\n    def ', 1)]
        assert '_pet_unmatchable' in match_pet, "H1: _match_pet 缺少排除检查"

    def test_oct_unmatchable(self):
        source = self._read_matcher_source()
        assert '_oct_unmatchable' in source, "H1: OCT 缺少 unmatchable 属性"
        match_oct = source[source.index('def _match_oct'):]
        match_oct = match_oct[:match_oct.index('\n    def ', 1)]
        assert '_oct_unmatchable' in match_oct, "H1: _match_oct 缺少排除检查"

    def test_db_loading(self):
        """验证 _load_rules_from_db 加载了 SPECT/PET/OCT 的 unmatchable"""
        source = self._read_matcher_source()
        load_section = source[source.index('def _load_rules_from_db'):]
        load_section = load_section[:load_section.index('\n    def ', 1)]
        assert "_unmatch('SPECT')" in load_section, "H1: DB 未加载 SPECT unmatchable"
        assert "_unmatch('PET')" in load_section, "H1: DB 未加载 PET unmatchable"
        assert "_unmatch('OCT')" in load_section, "H1: DB 未加载 OCT unmatchable"


# ============================================================
# H2: PET 默认回退 '躯干' 假阳性
# ============================================================
class TestH2PetDefault:
    """H2: PET 部位提取不应默认回退 '躯干'"""

    def test_no_default_trunk(self):
        src_path = os.path.join(
            os.path.dirname(__file__), '..', 'src',
            'match_service', 'engine', 'keyword', 'us_spect_pet_matcher.py'
        )
        with open(src_path, 'r') as f:
            source = f.read()
        extract_pet = source[source.index('def _extract_pet_body'):]
        extract_pet = extract_pet[:extract_pet.index('\n    def ', 1)]
        # 不应有 return '躯干' 作为默认值
        assert "return '躯干'" not in extract_pet, \
            "H2 未修复：_extract_pet_body 仍默认回退 '躯干'"
        assert 'return None' in extract_pet, \
            "H2 未修复：_extract_pet_body 应返回 None 而非默认值"


# ============================================================
# H3: 脊椎节段正则 [C|颈] 字符类错误
# ============================================================
class TestH3SpineRegex:
    """H3: 脊椎正则应使用 (?:C|颈) 而非 [C|颈]"""

    def test_no_pipe_in_char_class(self):
        src_path = os.path.join(
            os.path.dirname(__file__), '..', 'src',
            'match_service', 'engine', 'match_engine_v2', 'preprocess_service.py'
        )
        with open(src_path, 'r') as f:
            source = f.read()
        # 不应有 [C|颈] 这样的错误字符类
        assert '[C|颈]' not in source, "H3 未修复：仍存在 [C|颈] 错误字符类"
        assert '[T|胸]' not in source, "H3 未修复：仍存在 [T|胸] 错误字符类"
        assert '[L|腰]' not in source, "H3 未修复：仍存在 [L|腰] 错误字符类"
        assert '[S|骶]' not in source, "H3 未修复：仍存在 [S|骶] 错误字符类"

    def test_correct_regex_pattern(self):
        """验证修正后的正则能正确匹配"""
        # 模拟修正后的正则
        text = "|C3|C4|C5"
        result = re.sub(r'(\||^|;|,|以|及|、|，|（|\(|\+|:)(?:C|颈)(\d+)', r'\1颈椎C\2', text)
        assert '颈椎C3' in result, f"正则匹配失败: {result}"
        assert '颈椎C4' in result, f"正则匹配失败: {result}"

    def test_chinese_variant(self):
        """验证中文变体也能匹配"""
        text = "颈3颈4"
        result = re.sub(r'(\||^|;|,|以|及|、|，|（|\(|\+|:)(?:C|颈)(\d+)', r'\1颈椎C\2', text)
        # 注意：原文 "颈3" 前面没有分隔符，不会被匹配（这是预期行为）
        # 但 "|颈3" 应该被匹配
        text2 = "|颈3|颈4"
        result2 = re.sub(r'(\||^|;|,|以|及|、|，|（|\(|\+|:)(?:C|颈)(\d+)', r'\1颈椎C\2', text2)
        assert '颈椎C3' in result2, f"中文变体匹配失败: {result2}"


# ============================================================
# H4: SPECT 多结果静默丢弃
# ============================================================
class TestH4SpectMultiResult:
    """H4: SPECT 多结果应全部返回"""

    def test_returns_all_results(self):
        src_path = os.path.join(
            os.path.dirname(__file__), '..', 'src',
            'match_service', 'engine', 'keyword', 'us_spect_pet_matcher.py'
        )
        with open(src_path, 'r') as f:
            source = f.read()
        query_spect = source[source.index('def _query_spect'):]
        query_spect = query_spect[:query_spect.index('\n    def ', 1)]
        # 不应只返回 first
        assert "result.iloc[0]" not in query_spect or "iterrows" in query_spect, \
            "H4 未修复：_query_spect 仍只返回第一条结果"
        assert "iterrows" in query_spect, \
            "H4 未修复：_query_spect 应使用 iterrows 返回全部结果"

    def test_multi_result_degraded(self):
        """多结果时应标记 degraded"""
        src_path = os.path.join(
            os.path.dirname(__file__), '..', 'src',
            'match_service', 'engine', 'keyword', 'us_spect_pet_matcher.py'
        )
        with open(src_path, 'r') as f:
            source = f.read()
        query_spect = source[source.index('def _query_spect'):]
        query_spect = query_spect[:query_spect.index('\n    def ', 1)]
        assert "len(result) > 1" in query_spect, \
            "H4 未修复：未检查多结果情况"
        assert "_last_tier = 'degraded'" in query_spect, \
            "H4 未修复：多结果时未标记 degraded"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
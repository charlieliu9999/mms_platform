"""
全量匹配与 L1 导入的共享工具

被以下脚本复用：
- bulk_match_and_import.py  (Phase 1 全量匹配)
- analyze_benchmark_results.py (Phase 2 分析)
- import_to_l1_cache.py     (Phase 3 L1 导入)
- verify_l1_import.py       (Phase 4 验证)
"""
import logging
import re
import sys
from pathlib import Path

# 让脚本能 import match_service
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

logger = logging.getLogger(__name__)

# tier → confidence 映射，与 engine/match_engine_v2/orchestrator.py 保持一致
TIER_CONFIDENCE = {
    'exact': 1.0,
    'partial': 0.8,
    'degraded': 0.6,
    'ambiguous': 0.4,
    'none': 0.0,
    'error': 0.0,
}

# L1 导入的置信度门槛，与 core/dispatcher.py 的 AUTO_CACHE_MIN_CONFIDENCE 对齐
MIN_CONFIDENCE = 0.8

DEFAULT_DATASET = "tests/benchmark/16zzy_combined_246k.csv"
OUTPUT_DIR = Path("data/bulk_match")


def setup_logging(verbose: bool = False) -> None:
    """统一日志配置"""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # 抑制 SQLAlchemy 的 INFO 噪声
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def normalize_code(raw) -> str:
    """
    标准编码归一化：剥离 pandas 读取产生的 .0 浮点后缀

    源数据中 expected_standard_code 形如 '20041100010000.0'
    """
    code = str(raw).strip()
    if code.endswith('.0'):
        code = code[:-2]
    return code


def extract_confidence(match_result: dict) -> float:
    """
    从引擎结果中提取置信度

    优先取 confidence 字段（0.0-1.0）；缺失时按 tier 映射兜底。
    注意：不能用 score 字段，那是 0-10 的匹配得分，不是置信度。
    """
    confidence = match_result.get('confidence')
    if confidence is None:
        confidence = TIER_CONFIDENCE.get(match_result.get('tier', 'none'), 0.0)
    try:
        return float(confidence)
    except (TypeError, ValueError):
        logger.warning(f"置信度无法解析为 float: {confidence!r}, 归零处理")
        return 0.0


def fuzzy_match(expected: str, actual: str) -> bool:
    """
    模糊匹配：移除标点和空格后比较

    处理名称的表述差异，例如：
    - CTA vs CTPA
    - 三维重建 vs 三维成像
    - 中下腹部 vs 下腹部

    与 evaluation/runner.py 的 _fuzzy_match 保持同一口径。
    """
    if not expected or not actual:
        return False

    clean_expected = re.sub(r'[*\(\)\s+\-、，。]', '', expected)
    clean_actual = re.sub(r'[*\(\)\s+\-、，。]', '', actual)

    # 双向包含
    if clean_expected in clean_actual or clean_actual in clean_expected:
        return True

    # 去掉模态前缀后再比
    clean_expected = re.sub(r'^CT', '', clean_expected)
    clean_actual = re.sub(r'^CT', '', clean_actual)

    if len(clean_expected) > 0 and len(clean_actual) > 0:
        shorter = min(len(clean_expected), len(clean_actual))
        longer = max(len(clean_expected), len(clean_actual))

        if shorter / longer >= 0.8:
            common_chars = sum(1 for c in clean_expected if c in clean_actual)
            return common_chars / longer >= 0.7

    return False


def judge_correctness(match_result: dict, expected_name: str) -> tuple[bool, str, str, str]:
    """
    在全部候选中判定正确性，完全匹配优先于模糊匹配

    Returns:
        (is_correct, match_method, actual_code, actual_name)
        match_method ∈ {'exact', 'fuzzy', 'wrong'}
    """
    candidates = match_result.get('data') or []

    # 默认取第一个候选作为"实际结果"
    actual_code = ''
    actual_name = ''
    for cand in candidates:
        for std in cand.get('standard', []):
            actual_code = normalize_code(std.get('code', ''))
            actual_name = std.get('name', '')
            break
        if actual_name:
            break

    fuzzy_hit = None

    for cand in candidates:
        for std in cand.get('standard', []):
            std_name = std.get('name', '')

            if std_name == expected_name:
                return True, 'exact', normalize_code(std.get('code', '')), std_name

            if fuzzy_hit is None and fuzzy_match(expected_name, std_name):
                fuzzy_hit = (normalize_code(std.get('code', '')), std_name)

    if fuzzy_hit is not None:
        return True, 'fuzzy', fuzzy_hit[0], fuzzy_hit[1]

    return False, 'wrong', actual_code, actual_name


def classify_failure(check_item: str) -> str:
    """
    未匹配项的失败原因启发式分类

    返回: complex | missing_word
    与 evaluation/runner.py 的 _classify_failure 保持一致。
    """
    if len(check_item) > 100:
        return 'complex'
    if check_item.count('(') > 3:
        return 'complex'
    if ',' in check_item or '、' in check_item:
        return 'complex'
    return 'missing_word'


def build_result_json(check_item: str, code: str, name: str,
                      confidence: float, tier: str) -> dict:
    """
    构造写入 match_cache.result_json 的结构

    必须与引擎直出结果同构，这样 CacheService.lookup 的返回值
    和 L2 直出结果对调用方无差别。
    """
    has_standard = bool(code)
    return {
        "check_item": check_item,
        "num_standard": 1 if has_standard else 0,
        "data": [{
            "raw": check_item,
            "standard": [{"code": code, "name": name}],
        }] if has_standard else [],
        "score": 10,
        "tier": tier if tier in ('exact', 'partial') else 'exact',
        "confidence": confidence,
        "reason": "",
        "has_entity": True,
    }


def percentile(sorted_values: list[float], pct: float) -> float:
    """从已排序列表中取百分位数（线性插值）"""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]

    idx = (len(sorted_values) - 1) * pct
    lower = int(idx)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = idx - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight

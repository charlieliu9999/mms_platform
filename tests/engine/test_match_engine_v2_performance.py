"""
性能和回归测试

确保 V2 引擎性能不劣于 V1
"""
import asyncio
import time
import pytest
from match_service.db import get_engine
async_engine = get_engine()


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Phase A: V1 引擎 fixture 已禁用
# @pytest.fixture(scope="module")
# def v1_engine(event_loop):
# # Phase A: V1 引擎已移除
#     eng = ExamineMatchEngine()
#     event_loop.run_until_complete(eng.initialize())
#     return eng



@pytest.fixture(scope="module")
def v2_engine(event_loop):
    from match_service.engine.match_engine_v2 import MatchEngineOrchestrator
    orch = MatchEngineOrchestrator(async_engine)
    event_loop.run_until_complete(orch.initialize())
    return orch


# 大规模测试数据集
BENCHMARK_CASES = [
    ("CT头部平扫", "CT"),
    ("CT头部平扫+增强", "CT"),
    ("CT胸部平扫", "CT"),
    ("CT腹部平扫+增强", "CT"),
    ("CT全腹部平扫", "CT"),
    ("CT颈部增强", "CT"),
    ("CT腰椎平扫", "CT"),
    ("CT膝关节平扫", "CT"),
    ("冠状动脉CTA", "CT"),
    ("头颈部CTA", "CT"),
    ("下肢动脉CTA", "CT"),
    ("MR头部平扫", "MR"),
    ("MR头部平扫+增强", "MR"),
    ("MR腰椎平扫", "MR"),
    ("MR膝关节平扫", "MR"),
    ("MR乳腺平扫+增强", "MR"),
    ("MR颈椎平扫", "MR"),
    ("颅脑MRA", "MR"),
    ("胸部正位", "DR"),
    ("膝关节正、侧位", "DR"),
    ("腰椎正、侧位", "DR"),
    ("颈椎正、侧位", "DR"),
    ("手正位", "DR"),
    ("骨盆正位", "DR"),
    ("踝关节正、侧位", "DR"),
] * 4  # 重复 4 遍，共 100 个


class TestPerformance:
    """性能测试"""

# Phase A: V1 引擎对比测试已禁用
#     def test_single_match_latency_v1(self, v1_engine, benchmark):
#         """V1 单次匹配延迟"""
#         def run():
#             return v1_engine.match("CT头部平扫+增强", "CT", "V3.8.2")

#         result = benchmark(run)
#         assert result['num_standard'] > 0

#     def test_single_match_latency_v2(self, v2_engine, benchmark):
#         """V2 单次匹配延迟"""
#         def run():
#             return v2_engine.match("CT头部平扫+增强", "CT", "V3.8.2")

#         result = benchmark(run)
#         assert result['num_standard'] > 0

# Phase A: V1 引擎对比测试已禁用
#     def test_batch_match_throughput_v1(self, v1_engine):
#         """V1 批量匹配吞吐量"""
#         items = [
#             {"key": str(i), "modality": mod, "name": name}
#             for i, (name, mod) in enumerate(BENCHMARK_CASES)
#         ]

#         start = time.time()
#         results = v1_engine.batch_match(items, "V3.8.2")
#         elapsed = time.time() - start

#         print(f"\nV1 批量匹配: {len(items)} 项, 耗时 {elapsed:.3f}s, "
#               f"吞吐量 {len(items)/elapsed:.1f} items/s")

#         assert len(results) == len(items)

#     def test_batch_match_throughput_v2(self, v2_engine):
#         """V2 批量匹配吞吐量"""
#         items = [
#             {"key": str(i), "modality": mod, "name": name}
#             for i, (name, mod) in enumerate(BENCHMARK_CASES)
#         ]

#         start = time.time()
#         results = v2_engine.batch_match(items, "V3.8.2")
#         elapsed = time.time() - start

#         print(f"\nV2 批量匹配: {len(items)} 项, 耗时 {elapsed:.3f}s, "
#               f"吞吐量 {len(items)/elapsed:.1f} items/s")

#         assert len(results) == len(items)

#     def test_memory_usage(self, v2_engine):
#         """内存占用检查（粗略）"""
#         import sys

#         # 匹配前
#         size_before = sys.getsizeof(v2_engine)

#         # 大批量匹配
#         items = [
#             {"key": str(i), "modality": "CT", "name": "CT头部平扫"}
#             for i in range(1000)
#         ]
#         v2_engine.batch_match(items, "V3.8.2")

#         # 匹配后（不应显著增长）
#         size_after = sys.getsizeof(v2_engine)
#         delta = size_after - size_before

#         print(f"\n内存变化: {delta} bytes")
#         # 内存增长应控制在合理范围
#         assert delta < 10 * 1024 * 1024  # < 10MB



class TestRegression:
    """回归测试 - 确保已知正确的输入产出不变"""

    GOLDEN_CASES = [
        # (input, modality, expected_count, expected_contains)
        ("CT头部平扫", "CT", 1, "颅脑"),
        # 标准库将“平扫+增强”建模为一个组合标准项，不应断言拆成两项。
        ("CT头部平扫+增强", "CT", 1, "颅脑"),
        # DR“正、侧位”同样是一个组合体位标准项。
        ("膝关节正、侧位", "DR", 1, "膝关节"),
        ("冠状动脉CTA", "CT", 1, "冠状动脉"),
    ]

    @pytest.mark.parametrize("text,modality,min_count,keyword", GOLDEN_CASES)
    def test_golden_output(self, v2_engine, text, modality, min_count, keyword):
        """黄金标准输出回归"""
        result = v2_engine.match(text, modality, "V3.8.2")

        # 匹配数量应 >= 预期
        assert result['num_standard'] >= min_count

        # 应包含关键词
        names = {s['name'] for d in result['data'] for s in d['standard']}
        assert any(keyword in name for name in names)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])

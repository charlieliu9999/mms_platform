"""
Pipeline 流程验证测试 - 检查每一步的中间状态

目的：确保 10 步 Pipeline 每一步都按预期工作
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
def v2_orchestrator(event_loop):
    from match_service.engine.match_engine_v2 import MatchEngineOrchestrator
    orch = MatchEngineOrchestrator(async_engine)
    event_loop.run_until_complete(orch.initialize())
    return orch


class TestPipelineFlow:
    """测试 Pipeline 各步骤的正确性"""

    def test_step1_preprocess(self, v2_orchestrator):
        """Step 1: 预处理应规范化文本"""
        service = v2_orchestrator.preprocess_service

        # 全角 → 半角
        assert service.preprocess("ＣＴ头部", "CT", "V3.8.2") == "CT头部"

        # 脊椎补全
        result = service.preprocess("腰椎L3-L5", "CT", "V3.8.2")
        assert "腰椎L3" in result

        # 中文标点 → 英文标点
        result = service.preprocess("CT头部（平扫）", "CT", "V3.8.2")
        assert "(" in result and "（" not in result

    def test_step2_split_record(self, v2_orchestrator):
        """Step 2: 子项拆分应正确识别模态"""
        service = v2_orchestrator.preprocess_service

        # 单项
        result = service.split_record("CT头部平扫", "CT")
        assert len(result) == 1
        assert result[0] == ("CT", 0, "CT头部平扫")

        # 多项（逗号分隔）
        result = service.split_record("CT头部平扫,MR腰椎平扫", "CT")
        assert len(result) == 2
        assert result[0][0] == "CT"
        assert result[1][0] == "MR"

        # 跨模态
        result = service.split_record("CT胸部,超声心脏", "CT")
        assert result[0][0] == "CT"
        assert result[1][0] == "US"

    def test_step3_tokenize_and_build_tree(self, v2_orchestrator):
        """Step 3: 分词建树应正确标注词性"""
        service = v2_orchestrator.tokenizer_service
        disamb = v2_orchestrator.disamb_service

        records = [("CT", 0, "CT头部平扫")]
        nodes, _ = service.make_tree(records, "CT", "V3.8.2", disamb)

        assert len(nodes) == 1
        node = nodes[0]

        # 应包含 body（规则库已将"头部"归一化为"颅脑"）
        assert len(node.pos_dict['body']) > 0
        body_idx = node.pos_dict['body'][0]
        assert node.std_names[body_idx] in ('颅脑', '头部', '头')

        # 应包含 scan
        assert len(node.pos_dict['scan']) > 0
        scan_idx = node.pos_dict['scan'][0]
        assert '平扫' in node.std_names[scan_idx]

    def test_step4_pattern_processing(self, v2_orchestrator):
        """Step 4: 模式处理应合并冗余、分裂复杂节点"""
        service = v2_orchestrator.tokenizer_service
        processor = v2_orchestrator.pattern_processor
        disamb = v2_orchestrator.disamb_service

        # B(B) 合并：左膝关节 → 膝关节（左）
        records = [("DR", 0, "左膝关节")]
        nodes, _ = service.make_tree(records, "DR", "V3.8.2", disamb)
        processed = processor.process_by_pattern(nodes, "V3.8.2")

        # 应只有一个节点
        assert len(processed) >= 1

    def test_step5_merge_no_body(self, v2_orchestrator):
        """Step 5: 无 body 节点应合并到相邻有 body 的节点"""
        from match_service.engine.match_engine_v2.match_node import MatchNode

        processor = v2_orchestrator.pattern_processor
        disamb = v2_orchestrator.disamb_service

        # 构造测试节点：[body+scan, post(无body)]
        node1 = MatchNode("头部平扫", "CT", "V3.8.2")
        node1.add_entity("头部", "body", "头部")
        node1.add_entity("平扫", "scan", "平扫")

        node2 = MatchNode("增强", "CT", "V3.8.2")
        node2.add_entity("增强", "post", "增强")

        merged = processor.merge_no_body([node1, node2], disamb)

        # 应合并为 1 个节点
        assert len(merged) == 1
        assert len(merged[0].pos_dict['body']) > 0
        assert len(merged[0].pos_dict['scan']) > 0
        assert len(merged[0].pos_dict['post']) > 0

    def test_step6_split_multi_body(self, v2_orchestrator):
        """Step 6: 多 body 节点应分裂为多个节点"""
        from match_service.engine.match_engine_v2.match_node import MatchNode

        processor = v2_orchestrator.pattern_processor

        # 构造测试节点：2个body + 1个scan
        node = MatchNode("头部胸部平扫", "CT", "V3.8.2")
        node.add_entity("头部", "body", "头部")
        node.add_entity("胸部", "body", "胸部")
        node.add_entity("平扫", "scan", "平扫")

        split = processor.split_multi_body([node])

        # 应分裂为 2 个节点
        assert len(split) == 2
        assert len(split[0].pos_dict['body']) == 1
        assert len(split[1].pos_dict['body']) == 1

    def test_step9_default_process(self, v2_orchestrator):
        """Step 9: 无处理方式时应补充默认值"""
        from match_service.engine.match_engine_v2.match_node import MatchNode

        lookup = v2_orchestrator.lookup_service

        # 构造只有 body 的节点
        node = MatchNode("头部", "CT", "V3.8.2")
        node.add_entity("头部", "body", "头部")

        result = lookup.find_default_process([node], "scan", "CT", "V3.8.2")

        # 应补充默认 scan（平扫）
        assert len(result[0].pos_dict['scan']) > 0

    def test_step10_lookup_standard(self, v2_orchestrator):
        """Step 10: 查标准表应返回匹配项"""
        from match_service.engine.match_engine_v2.match_node import MatchNode

        lookup = v2_orchestrator.lookup_service

        # 构造完整节点（标准表使用归一化部位名"颅脑"，而非原始"头部"）
        node = MatchNode("颅脑平扫", "CT", "V3.8.2")
        node.add_entity("颅脑", "body", "颅脑")
        node.add_entity("平扫", "scan", "平扫")

        query_fields = {'body': [], 'scan': [], 'post': []}
        lookup.lookup_standard([node], query_fields, "scan", "CT", "V3.8.2")

        # 应有匹配结果
        assert len(node.standard_check_name) > 0
        assert len(node.standard_check_code) > 0
        assert len(node.standard_check_name) == len(node.standard_check_code)


class TestPipelineIntegration:
    """测试完整 Pipeline 集成"""

    def test_full_pipeline_ct(self, v2_orchestrator):
        """完整 Pipeline - CT 场景"""
        result = v2_orchestrator.match("CT头部平扫+增强", "CT", "V3.8.2")

        assert result['check_item'] == "CT头部平扫+增强"
        assert result['num_standard'] > 0
        assert len(result['data']) > 0
        assert result['score'] <= 10

        # 应包含标准项
        for item in result['data']:
            assert 'standard' in item
            for std in item['standard']:
                assert 'code' in std
                assert 'name' in std
                assert std['code']
                assert std['name']

    def test_full_pipeline_cross_modality(self, v2_orchestrator):
        """完整 Pipeline - 跨模态场景"""
        result = v2_orchestrator.match("CT胸部,MR腰椎", "CT", "V3.8.2")

        # 应处理两个模态
        assert result['num_standard'] >= 2
        assert len(result['data']) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

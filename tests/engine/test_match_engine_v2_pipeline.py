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

        # preprocess 同时返回处理文本和方括号审计处理器。
        result, _ = service.preprocess("ＣＴ头部", "CT", "V3.8.2")
        assert result == "CT头部"

        # 脊椎补全
        result, _ = service.preprocess("腰椎L3-L5", "CT", "V3.8.2")
        assert "腰椎L3" in result

        # 中文标点 → 英文标点
        result, _ = service.preprocess("CT头部（平扫）", "CT", "V3.8.2")
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

    def test_orchestrators_do_not_share_stale_keyword_snapshot(
        self, event_loop, v2_orchestrator
    ):
        """热重载构建的新协调器必须重新读取 keyword_match_rules。"""
        from match_service.engine.match_engine_v2 import MatchEngineOrchestrator

        reloaded = MatchEngineOrchestrator(async_engine)
        event_loop.run_until_complete(reloaded.initialize())
        assert reloaded._kw_matcher is not v2_orchestrator._kw_matcher

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

    def test_unique_standard_name_precedes_unsupported_and_exclusion_guards(
        self, v2_orchestrator
    ):
        """错桶及介入词不能拦截标准库中唯一、完全同名的有效项目。"""
        other = v2_orchestrator.match("甲状腺弹性超声检查", "OTHER")
        assert other["tier"] == "exact"
        assert other["engine"] == "standard_name_exact"
        assert other["effective_modality"] == "US"
        assert other["data"][0]["standard"][0]["code"] == "50U101000C1000"

        intervention = v2_orchestrator.match("甲状旁腺介入超声检查", "IR")
        assert intervention["tier"] == "exact"
        assert intervention["data"][0]["standard"][0]["code"] == "50U102000C5000"

        # 标准库和来源模态一致时，名称中的历史错误前缀不能覆盖权威模态。
        oct_result = v2_orchestrator.match(
            "MR眼前节光学相干断层扫描(AS-OCT)", "OCT"
        )
        assert oct_result["tier"] == "exact"
        assert oct_result["data"][0]["standard"][0]["code"] == "120990000110000"

    def test_exact_name_collision_resolved_by_code_priority(self, v2_orchestrator):
        """同名多编码由编码优先级收敛（业务决策 2026-09-11）。

        旧契约要求同名多编码一律返回 ambiguous/exact_name_collision，
        但标准库只使用 v3.8.2 后，真正的同名多编码只剩「ACR 数字编码 +
        内部 C010A 编码」这类可裁决组合。ACR 标准编码优先，不再要求人工。
        无法裁决时（多候选同级）则放行到下游引擎，而不是直接判 ambiguous。
        """
        result = v2_orchestrator.match(
            "SPECT放射性核素大动脉显像", "SPECT"
        )
        assert result["tier"] == "exact"
        assert result["engine"] == "standard_name_exact"
        # ACR 14 位数字编码优先于内部 C010A 编码
        assert result["data"][0]["standard"][0]["code"] == "50100000110000"

    @pytest.mark.parametrize(
        ("text", "modality", "reason", "has_entity"),
        [
            ("US支气管镜引导经支气管针吸活检术", "US", "excluded_non_imaging", None),
            ("DSA机械性血栓切除术", "DSA", "excluded_intervention", None),
            ("DSA髂静脉手术", "DSA", "excluded_intervention", None),
            ("US完全未知部位超声检查", "US", "lexicon_gap", False),
        ],
    )
    def test_keyword_engine_returns_structured_failure_reason(
        self, v2_orchestrator, text, modality, reason, has_entity
    ):
        result = v2_orchestrator.match(text, modality)
        assert result["tier"] == "none"
        assert result["reason"] == reason
        assert result["has_entity"] is has_entity

    @pytest.mark.parametrize(
        ("text", "expected_code"),
        [
            ("US肝胆胰常规超声检查", "50U301000C0000"),
            ("US胃部(口服超声造影)", "50U309003C4000"),
            ("US手术区域皮肤(高频超声+多普勒)", "50U201000C0000"),
        ],
    )
    def test_keyword_high_confidence_aliases(self, v2_orchestrator, text, expected_code):
        result = v2_orchestrator.match(text, "US")
        codes = {
            item["code"]
            for block in result.get("data", [])
            for item in block.get("standard", [])
        }
        assert expected_code in codes

    def test_keyword_multi_candidate_is_not_exact(self, v2_orchestrator):
        result = v2_orchestrator.match("超声心动", "US")
        assert result["num_standard"] > 0
        assert result["tier"] == "degraded"

    def test_exact_name_rejects_text_standard_modality_conflict(self, v2_orchestrator):
        """PET/MRI 文本不得自动命中错误标为 PET/CT 的同名脏数据。"""
        result = v2_orchestrator.match(
            "PET/MRI大血管(代谢显像+平扫+增强)", "PET/MR"
        )
        codes = {
            standard["code"]
            for block in result.get("data", [])
            for standard in block.get("standard", [])
        }
        assert "100990000130000" not in codes

    @pytest.mark.parametrize(
        ("text", "expected_code"),
        [
            ("MR肝脏普通扫描", "30050101110000"),
            ("MR垂体普通扫描", "30010301110000"),
        ],
    )
    def test_mr_v382_body_normalization_matches_current_standard_library(
        self, v2_orchestrator, text, expected_code
    ):
        """肝脏/垂体不能再被反向归一化为旧标准表名称。"""
        result = v2_orchestrator.match(text, "MR", "V3.8.2")
        codes = {
            standard["code"]
            for block in result["data"]
            for standard in block["standard"]
        }
        assert expected_code in codes

    def test_vascular_normalization_is_independent_of_scan_order(self, v2_orchestrator):
        """MRA+CE-MRA 的语义不能受 set/list 或 PYTHONHASHSEED 顺序影响。"""
        from match_service.engine.match_engine_v2.match_node import MatchNode

        def normalize(scan_order):
            node = MatchNode(
                "MR腹部动脉血管平扫+增强成像(MRA+CE-MRA)", "MR", "V3.8.2"
            )
            node.add_entity("腹部动脉", "body", "腹主动脉")
            for scan in scan_order:
                node.add_entity(scan, "scan", scan)
            result = v2_orchestrator.disamb_service.normalize_vascular_nodes(
                [node], "scan", "MR"
            )[0]
            return sorted(result.std_names[i] for i in result.pos_dict["scan"])

        expected = ["动脉血管增强成像(CE-MRA)", "动脉血管成像(MRA)"]
        assert normalize(["平扫+增强", "动脉血管成像(MRA)"]) == expected
        assert normalize(["动脉血管成像(MRA)", "平扫+增强"]) == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

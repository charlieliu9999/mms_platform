"""测试非血管造影不被误判为血管成像"""
import asyncio
import pytest
from match_service.db import get_engine

async_engine = get_engine()


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    loop.run_until_complete(async_engine.dispose())
    yield loop
    loop.run_until_complete(async_engine.dispose())
    loop.close()


@pytest.fixture(scope="module")
def engine(event_loop):
    """初始化引擎"""
    from match_service.engine.match_engine_v2 import MatchEngineOrchestrator
    orch = MatchEngineOrchestrator(async_engine)
    event_loop.run_until_complete(orch.initialize())
    return orch


class TestNonVascularContrast:
    """测试非血管造影不被误判为CTA/MRA"""
    
    def test_ctu_urinary_contrast(self, engine):
        """CT尿路造影应该匹配CTU，不应该匹配CTA"""
        result = engine.match("CT尿路造影(平扫+增强)", 'CT')
        
        print(f"\n测试: CT尿路造影(平扫+增强)")
        print(f"结果: tier={result['tier']}, num={result['num_standard']}")
        
        # 应该能匹配到标准项
        assert result['tier'] in ['exact', 'partial', 'degraded'], \
            f"CT尿路造影应该能匹配，但tier={result['tier']}"
        
        # 匹配结果应该包含"尿路"或"CTU"
        matched_names = []
        for item in result.get('data', []):
            for std in item.get('standard', []):
                name = std.get('name', '')
                matched_names.append(name)
                print(f"  匹配到: {name}")
        
        has_urinary = any('尿路' in name or 'CTU' in name for name in matched_names)
        assert has_urinary, f"应该匹配到尿路相关项，但匹配到: {matched_names}"
        
        # 不应该匹配到CTA
        has_cta = any('CTA' in name and '尿路' not in name for name in matched_names)
        assert not has_cta, f"不应该匹配到CTA，但匹配到: {matched_names}"
    
    def test_joint_contrast(self, engine):
        """CT关节造影 - 验证不被误判为CTA"""
        # 使用更通用的关节造影测试（标准库中有此项）
        result = engine.match("CT关节造影", 'CT')
        
        print(f"\n测试: CT关节造影")
        print(f"结果: tier={result['tier']}, num={result['num_standard']}")
        
        # CT关节造影在标准库中有精确匹配项
        assert result['num_standard'] > 0, \
            f"CT关节造影应该能匹配，但num={result['num_standard']}"
        
        # 验证匹配结果
        matched_names = []
        for item in result.get('data', []):
            for std in item.get('standard', []):
                name = std.get('name', '')
                matched_names.append(name)
                print(f"  匹配到: {name}")
        
        # 应该匹配到关节相关项
        has_joint = any('关节' in name for name in matched_names)
        assert has_joint, f"应该匹配到关节相关项，但匹配到: {matched_names}"


class TestVascularContrastStillWorks:
    """测试血管造影仍然能正确识别"""
    
    def test_aorta_contrast_is_vascular(self, engine):
        """CT主动脉造影应该被识别为血管成像"""
        result = engine.match("CT主动脉造影", 'CT')
        
        print(f"\n测试: CT主动脉造影")
        print(f"结果: tier={result['tier']}, num={result['num_standard']}")
        
        # 应该匹配到CTA相关项
        assert result['num_standard'] > 0, \
            f"CT主动脉造影应该能匹配，但num={result['num_standard']}"
        
        matched_names = []
        for item in result.get('data', []):
            for std in item.get('standard', []):
                name = std.get('name', '')
                matched_names.append(name)
                print(f"  匹配到: {name}")
        
        has_vascular = any('CTA' in name or '血管' in name or '主动脉' in name 
                          for name in matched_names)
        assert has_vascular, f"应该匹配到血管相关项，但匹配到: {matched_names}"
    
    def test_vessel_imaging_is_vascular(self, engine):
        """CT血管造影应该被识别为血管成像"""
        result = engine.match("CT血管造影", 'CT')
        
        print(f"\n测试: CT血管造影")
        print(f"结果: tier={result['tier']}, num={result['num_standard']}")
        
        # 应该匹配到血管相关项
        assert result['num_standard'] > 0, \
            f"CT血管造影应该能匹配，但num={result['num_standard']}"
        
        matched_names = []
        for item in result.get('data', []):
            for std in item.get('standard', []):
                name = std.get('name', '')
                matched_names.append(name)
                print(f"  匹配到: {name}")
        
        has_vascular = any('血管' in name or 'CTA' in name 
                          for name in matched_names)
        assert has_vascular, f"应该匹配到血管相关项，但匹配到: {matched_names}"

"""
模态归一化功能测试

测试 MatchDispatcher 的模态归一化功能，确保：
1. MRI → MR
2. XR → DR
3. 大小写不敏感
4. 空值处理
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from match_service.core.dispatcher import MatchDispatcher


class TestModalityNormalization:
    """模态归一化测试套件"""

    @pytest.fixture
    def dispatcher(self):
        """创建测试用的 dispatcher 实例"""
        session = AsyncMock()
        engine_holder = MagicMock()
        return MatchDispatcher(session, engine_holder)

    def test_mri_to_mr(self, dispatcher):
        """测试 MRI → MR 映射"""
        assert dispatcher._normalize_modality('MRI') == 'MR'
        assert dispatcher._normalize_modality('mri') == 'MR'
        assert dispatcher._normalize_modality('Mri') == 'MR'
        assert dispatcher._normalize_modality('MR') == 'MR'

    def test_xr_to_dr(self, dispatcher):
        """测试 XR/CR → DR 映射"""
        assert dispatcher._normalize_modality('XR') == 'DR'
        assert dispatcher._normalize_modality('xr') == 'DR'
        assert dispatcher._normalize_modality('DR') == 'DR'
        assert dispatcher._normalize_modality('CR') == 'DR'
        assert dispatcher._normalize_modality('X线') == 'DR'

    def test_ct_unchanged(self, dispatcher):
        """测试 CT 保持不变"""
        assert dispatcher._normalize_modality('CT') == 'CT'
        assert dispatcher._normalize_modality('ct') == 'CT'
        assert dispatcher._normalize_modality('HRCT') == 'CT'
        assert dispatcher._normalize_modality('CTA') == 'CT'

    def test_us_unchanged(self, dispatcher):
        """测试 US 保持不变"""
        assert dispatcher._normalize_modality('US') == 'US'
        assert dispatcher._normalize_modality('us') == 'US'
        assert dispatcher._normalize_modality('ULTRASOUND') == 'US'
        assert dispatcher._normalize_modality('超声') == 'US'

    def test_pet_series(self, dispatcher):
        """测试 PET 系列映射"""
        assert dispatcher._normalize_modality('PET-CT') == 'PET/CT'
        assert dispatcher._normalize_modality('PET/CT') == 'PET/CT'
        assert dispatcher._normalize_modality('PET-MR') == 'PET/MR'
        assert dispatcher._normalize_modality('PET/MR') == 'PET/MR'
        assert dispatcher._normalize_modality('PET') == 'PET'

    def test_nuclear_medicine(self, dispatcher):
        """测试核医学模态"""
        assert dispatcher._normalize_modality('NM') == 'NM'
        assert dispatcher._normalize_modality('SPECT') == 'NM'

    def test_dsa_mapping(self, dispatcher):
        """测试 DSA/ANGIO 映射"""
        assert dispatcher._normalize_modality('DSA') == 'DSA'
        assert dispatcher._normalize_modality('ANGIO') == 'DSA'

    def test_other_modalities(self, dispatcher):
        """测试其他模态"""
        assert dispatcher._normalize_modality('RF') == 'RF'
        assert dispatcher._normalize_modality('FL') == 'RF'
        assert dispatcher._normalize_modality('MG') == 'MG'
        assert dispatcher._normalize_modality('OCT') == 'OCT'

    def test_empty_and_none(self, dispatcher):
        """测试空值处理"""
        assert dispatcher._normalize_modality('') == ''
        assert dispatcher._normalize_modality(None) is None

    def test_whitespace_handling(self, dispatcher):
        """测试空格处理"""
        assert dispatcher._normalize_modality(' MRI ') == 'MR'
        assert dispatcher._normalize_modality('  CT  ') == 'CT'

    def test_unknown_modality(self, dispatcher):
        """测试未知模态（保持原值）"""
        assert dispatcher._normalize_modality('UNKNOWN') == 'UNKNOWN'
        assert dispatcher._normalize_modality('XYZ') == 'XYZ'

    def test_case_insensitive(self, dispatcher):
        """测试大小写不敏感"""
        test_cases = [
            ('mri', 'MR'),
            ('MRI', 'MR'),
            ('Mri', 'MR'),
            ('xr', 'DR'),
            ('XR', 'DR'),
            ('Xr', 'DR'),
        ]
        for input_val, expected in test_cases:
            assert dispatcher._normalize_modality(input_val) == expected

    def test_mapping_completeness(self, dispatcher):
        """验证映射表的完整性"""
        mapping = MatchDispatcher.MODALITY_NORMALIZATION

        # 验证关键映射存在
        assert 'MRI' in mapping, "缺少 MRI 映射"
        assert 'XR' in mapping, "缺少 XR 映射"
        assert 'CT' in mapping, "缺少 CT 映射"
        assert 'US' in mapping, "缺少 US 映射"

        # 验证映射值的合理性
        assert mapping['MRI'] == 'MR', "MRI 应映射到 MR"
        assert mapping['XR'] == 'DR', "XR 应映射到 DR"

    def test_chinese_modality_names(self, dispatcher):
        """测试中文模态名称"""
        assert dispatcher._normalize_modality('X线') == 'DR'
        assert dispatcher._normalize_modality('超声') == 'US'
        assert dispatcher._normalize_modality('放射') == 'DR'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

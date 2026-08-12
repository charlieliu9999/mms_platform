"""
文本预处理服务
"""
import re
from typing import List, Tuple

import pandas as pd

from .bracket_modifier_handler import BracketModifierHandler
from .constants import (
    CHN_PUNCT,
    ENG_PUNCT,
    FULL_ANGLE,
    HALF_ANGLE,
    VERSION_FALLBACK,
)

# 全角半角转换表
_full2half = str.maketrans(FULL_ANGLE, HALF_ANGLE)
_chn2eng = str.maketrans(CHN_PUNCT, ENG_PUNCT)


class PreprocessService:
    """文本预处理服务"""

    def __init__(self, pre_rules: dict):
        """
        Args:
            pre_rules: {modality: pd.DataFrame} 预处理规则
        """
        self.pre_rules = pre_rules
        self.bracket_handler = BracketModifierHandler()

    def preprocess(self, text: str, modality: str, version: str) -> Tuple[str, BracketModifierHandler]:
        """
        预处理文本

        步骤：
        0. 剥离方括号修饰语（CT头部平扫[薄层] -> CT头部平扫）
        1. 全角→半角
        2. 中文标点→英文标点
        3. 特殊字符替换
        4. 脊椎节段补全
        5. 数据库规则替换

        Returns:
            (处理后的文本, 方括号处理器) - 处理器用于审计被剥离的内容
        """
        # 0. 剥离方括号修饰语（在所有其他处理之前）
        text = self.bracket_handler.protect_brackets(text)

        text = self._convert_full2half(text)
        text = self._convert_chn2eng(text)
        text = self._normalize_special_chars(text)
        text = self._expand_left_right(text)
        text = self._complete_vertebra_segments(text)
        text = self._apply_db_rules(text, modality, version)
        return text, self.bracket_handler

    @staticmethod
    def _convert_full2half(text: str) -> str:
        """全角转半角"""
        return text.translate(_full2half)

    @staticmethod
    def _convert_chn2eng(text: str) -> str:
        """中文标点转英文"""
        return text.translate(_chn2eng)

    @staticmethod
    def _normalize_special_chars(text: str) -> str:
        """特殊字符归一化"""
        text = (text.replace('—', '-').replace('\\', '/')
                .replace('上、中、下', '上中下')
                .replace('中、下', '中下').replace('上、中', '上中')
                .replace('中、上', '中上').replace('上、下', '上下')
                .upper().replace('T1WI', '').replace('T2WI', '')
                .replace('DWI', '').replace('STIR', '')
                .replace('弥散加权成像', '').replace('扩散加权成像', '')
                .replace('弥散', '').replace('扩散', ''))

        # 去除连字符（保护医学缩写 CE-MRA/CE-MRV/CE-CT 等，Step 8.5 依赖原文判断增强）
        _protected = ('CE-MRA', 'CE-MRV', 'CE-CT', 'CE-MRI')
        for term in _protected:
            text = text.replace(term, term.replace('-', '\x01'))
        text = re.sub(r'([A-Za-z]+)-([A-Za-z]+)', r'\1\2', text)
        for term in _protected:
            text = text.replace(term.replace('-', '\x01'), term)

        # 脊椎节段字母标准化
        text = re.sub(r'-颈(\d)', r'-C\1', text)
        text = re.sub(r'-胸(\d)', r'-T\1', text)
        text = re.sub(r'-腰(\d)', r'-L\1', text)
        text = re.sub(r'-骶(\d)', r'-S\1', text)

        # 去除括号中扫描范围
        text = re.sub(r'[(|（][一-龥]+至[一-龥]+[)|）]', '', text)

        # 低剂量扫描归一化为平扫（标准表中无单独低剂量项目）
        text = text.replace('(低剂量扫描)', '(平扫)')
        text = text.replace('（低剂量扫描）', '(平扫)')
        text = re.sub(r'低剂量(扫描|平扫)', '平扫', text)

        # 部位别名归一化
        text = text.replace('鼻窦', '副鼻窦')

        # === 技术描述规范化（算法资产：减少解析残留）===
        # 多期增强+血管成像 → CTA
        text = re.sub(r'[(（]?双?低?剂量?多期(动态)?增强[+及与]血管成像[)）]?', '(CTA)', text)
        text = re.sub(r'[(（]?多期(动态)?增强[+及与]血管成像[)）]?', '(CTA)', text)
        text = re.sub(r'[(（]?增强[+及与]血管成像[)）]?', '(CTA)', text)
        text = re.sub(r'[(（]?血管成像[+及与]多期增强[)）]?', '(CTA)', text)
        
        # 心电门控 → 移除（技术参数，不影响匹配）
        text = re.sub(r'心电门控(增强)?多排螺旋CT', '增强', text)
        text = re.sub(r'[(（]?心电门控[)）]?', '', text)
        text = re.sub(r'[(（]?前瞻性门控[)）]?', '', text)
        text = re.sub(r'[(（]?回顾性门控[)）]?', '', text)
        
        # 多排螺旋CT → 移除
        text = re.sub(r'多排螺旋CT', '', text)
        text = re.sub(r'MSCT', '', text)
        
        # 重建方式规范化
        text = re.sub(r'[(（]?多平面重组[)）]?', '(MPR)', text)
        text = re.sub(r'[(（]?多平面重建[)）]?', '(MPR)', text)
        text = re.sub(r'[(（]?容积再现[)）]?', '(VR)', text)
        text = re.sub(r'[(（]?容积重建[)）]?', '(VR)', text)
        text = re.sub(r'MPR[+及与]VR', 'MPR,VR', text)  # 联合重建拆成子项
        
        # 分辨率描述 → 移除
        text = re.sub(r'[(（]?超?高分辨率?[)）]?', '', text)
        text = re.sub(r'[(（]?UHR模式[)）]?', '', text)
        
        # 增强期别规范化（动静脉双期、动脉期、静脉期 → 增强）
        text = re.sub(r'(动静脉)?双期增强', '增强', text)
        text = re.sub(r'动脉期增强', '增强', text)
        text = re.sub(r'静脉期增强', '增强', text)

        # 泛指部位清理（让引擎走"非指定部位"降级分支）
        # 这些词汇无法对应具体解剖部位，删除后保留扫描方式，匹配"无部位"标准项
        generic_body_patterns = [
            r'受累关节',
            r'受累部位',
            r'病变部位',
            r'可疑部位',
            r'目标部位',
            r'指定部位',
            r'相关部位',
        ]
        for pattern in generic_body_patterns:
            text = re.sub(pattern, '', text)

        return text

    @staticmethod
    def _expand_left_right(text: str) -> str:
        """左右并列展开："左|右膝关节" → "左膝关节,右膝关节"

        分词器会把孤立的"左"标为 other 丢弃，导致并列表达只剩单侧。
        展开成逗号分隔后由 split_record 拆成两个子项分别匹配。
        """
        text = re.sub(r'左[|/]右([一-龥]+)', r'左\1,右\1', text)
        text = re.sub(r'右[|/]左([一-龥]+)', r'右\1,左\1', text)
        return text

    @staticmethod
    def _complete_vertebra_segments(text: str) -> str:
        """脊椎节段补全"""
        # 颈椎（H3 修复：字符类中 | 是字面量，改用非捕获组）
        if '颈椎' not in text:
            text = re.sub(r'(\||^|;|,|以|及|、|，|（|\(|\+|:)(?:C|颈)(\d+)', r'\1颈椎C\2', text)
        # 胸椎
        if '胸椎' not in text:
            text = re.sub(r'(\||^|;|,|以|及|、|，|（|\(|\+|:)(?:T|胸)(\d+)', r'\1胸椎T\2', text)
        # 腰椎
        if '腰椎' not in text:
            text = re.sub(r'(\||^|;|,|以|及|、|，|（|\(|\+|:)(?:L|腰)(\d+)', r'\1腰椎L\2', text)
        # 骶椎
        if '骶椎' not in text:
            text = re.sub(r'(\||^|;|,|以|及|、|，|（|\(|\+|:)(?:S|骶)(\d+)', r'\1骶椎S\2', text)

        # 段合并
        text = re.sub(r'(T\d+[-~]L\d)', r'胸腰段\1', text)
        text = re.sub(r'(L\d+[-~]S\d)', r'腰骶段\1', text)
        text = re.sub(r'(C\d+[-~]T\d)', r'颈胸段\1', text)

        return text

    def _apply_db_rules(self, text: str, modality: str, version: str) -> str:
        """应用数据库预处理规则"""
        if modality not in self.pre_rules:
            return text

        rules = self.pre_rules[modality]
        if rules.empty:
            return text

        # 版本回退
        version_rules = pd.DataFrame()
        for ver in VERSION_FALLBACK.get(version, [version]):
            version_rules = rules[rules['version'] == ver]
            if not version_rules.empty:
                break

        # 应用替换规则
        for _, row in version_rules.iterrows():
            text = text.replace(row['src_word'], row['dst_word'])

        return text

    def split_record(self, record: str, default_modality: str) -> List[Tuple[str, int, str]]:
        """
        拆分记录为子项

        Returns:
            [(modality, index, item), ...]
        """
        parts = re.split(r'[,;，。；\n]', record)
        result = []
        for idx, item in enumerate(parts):
            item = item.strip()
            if not item:
                continue
            detected = self._detect_modality(item, default_modality)
            result.append((detected, idx, item))
        return result

    @staticmethod
    def _detect_modality(item: str, default: str) -> str:
        """
        从文本推断模态

        检测顺序：复合模态（PET/CT 等）→ 超声 → MR → 钼靶 → DR → CT → RF
        """
        upper = item.upper()

        # 超声
        if '彩超' in item or '超声' in item or 'B超' in item:
            return 'US'

        # 复合模态（优先排除）
        if 'PET/CT' in upper or 'PET/MR' in upper or 'SPECT' in upper:
            return default

        # MR
        if 'MR' in upper or '磁共振' in item:
            return 'MR'

        # 钼靶
        if '钼靶' in item:
            return 'MG'
        if any(k in item for k in ('乳腺', '双乳', '左乳', '右乳', '乳房')):
            return 'MG'

        # DR
        if 'DR' in upper:
            return 'DR'

        # CT
        if 'CT' in upper:
            return 'CT'

        # RF (造影)
        if default not in ('CT', 'MR') and ('钡餐' in item or '造影' in item):
            return 'RF'

        return default

"""
方括号修饰语处理器

处理 `面神经[颅外段]` 等方括号修饰语，防止被分词器拆分成独立实体。
"""
import re
from typing import Dict, Tuple


class BracketModifierHandler:
    """方括号修饰语处理器"""

    # 占位符标记（使用不常见字符，避免与正常文本冲突）
    PLACEHOLDER_PREFIX = '\x02BRACKET_'
    PLACEHOLDER_SUFFIX = '\x03'

    def __init__(self):
        self._protected_map: Dict[str, str] = {}
        self._counter = 0

    def protect_brackets(self, text: str) -> str:
        """
        保护方括号修饰语，替换为占位符

        示例：
            'MR面神经[颅外段](平扫)' -> 'MR面神经__BRACKET_0__(平扫)'

        Args:
            text: 原始文本

        Returns:
            处理后的文本（方括号被占位符替换）
        """
        self._protected_map.clear()
        self._counter = 0

        # 匹配模式：部位名称 + [修饰语]
        # 确保方括号前有实际内容（至少一个汉字或字母）
        pattern = r'([一-龥A-Za-z]+)\[([^\]]+)\]'

        def replacer(match):
            base = match.group(1)  # 主体部位
            modifier = match.group(2)  # 方括号内修饰语

            # 生成占位符
            placeholder = f'{self.PLACEHOLDER_PREFIX}{self._counter}{self.PLACEHOLDER_SUFFIX}'

            # 保存原始组合（包含方括号，用于恢复）
            original_with_bracket = f'{base}[{modifier}]'
            self._protected_map[placeholder] = original_with_bracket

            self._counter += 1

            # 返回：主体 + 占位符（不包含方括号，避免被再次匹配）
            return placeholder

        result = re.sub(pattern, replacer, text)
        return result

    def restore_brackets(self, text: str) -> str:
        """
        恢复方括号修饰语

        Args:
            text: 包含占位符的文本

        Returns:
            恢复后的文本
        """
        result = text
        for placeholder, original in self._protected_map.items():
            result = result.replace(placeholder, original)
        return result

    def get_protected_terms(self) -> Dict[str, str]:
        """
        获取所有被保护的方括号术语

        Returns:
            {占位符: 原始术语} 映射
        """
        return self._protected_map.copy()

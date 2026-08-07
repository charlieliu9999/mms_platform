"""
方括号修饰语处理器

剥离 `CT头部平扫[薄层]`、`MR腰椎平扫[抑脂]` 等方括号修饰语，防止干扰标准项匹配。
修饰语被直接移除，不参与后续匹配逻辑。
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
        剥离方括号修饰语（直接移除）

        示例：
            'MR面神经[颅外段](平扫)' -> 'MR面神经(平扫)'
            'CT头部平扫[薄层]' -> 'CT头部平扫'

        Args:
            text: 原始文本

        Returns:
            处理后的文本（方括号及其内容已移除）
        """
        self._protected_map.clear()
        self._counter = 0

        # 匹配模式：部位名称 + [修饰语]
        # 确保方括号前有实际内容（至少一个汉字或字母）
        pattern = r'([一-龥A-Za-z]+)\[([^\]]+)\]'

        def replacer(match):
            base = match.group(1)  # 主体部位
            modifier = match.group(2)  # 方括号内修饰语

            # 保存被移除的修饰语（用于审计/调试）
            original_with_bracket = f'{base}[{modifier}]'
            stripped_key = f'STRIPPED_{self._counter}'
            self._protected_map[stripped_key] = original_with_bracket

            self._counter += 1

            # 直接返回主体部位，修饰语被剥离
            return base

        result = re.sub(pattern, replacer, text)
        return result

    def restore_brackets(self, text: str) -> str:
        """
        恢复方括号修饰语（已改为剥离策略，此方法保持向后兼容）

        Args:
            text: 处理后的文本

        Returns:
            文本（方括号已被剥离，不再恢复）
        """
        # 方括号已在 protect_brackets 中被剥离，不需要恢复
        return text

    def get_protected_terms(self) -> Dict[str, str]:
        """
        获取所有被剥离的方括号术语（用于审计/调试）

        Returns:
            {STRIPPED_N: 原始术语} 映射
        """
        return self._protected_map.copy()

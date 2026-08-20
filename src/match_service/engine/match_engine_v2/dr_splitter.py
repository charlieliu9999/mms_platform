"""
DR 复合项目拆分器

处理医院收费系统中常见的组合套餐格式：
  输入: "(DR)右手掌正侧位数字化摄影,(DR)右前臂正侧位数字化摄影"
  输出: ["右手掌正侧位", "右前臂正侧位"]
"""
import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class DRSplitter:
    """DR 复合项目拆分器"""

    # 需要过滤的耗材和操作关键词
    MATERIAL_KEYWORDS = {
        '静脉穿刺置管术',
        '密闭式静脉留置针',
        '透明敷料',
        '复杂模拟定位',
        '专用X线机复杂模拟定位',
        '影像中心',
    }

    # DR 检查项目常见前缀（需要剥离）
    DR_PREFIXES = [
        r'\(DR\)',
        r'DR',
        r'\[DR\]',
    ]

    # DR 检查项目常见后缀（需要剥离）
    DR_SUFFIXES = [
        r'数字化摄影',
        r'DR摄影',
        r'摄影',
    ]

    def __init__(self):
        """初始化拆分器"""
        # 编译正则表达式以提高性能
        self._prefix_pattern = re.compile(
            '|'.join(self.DR_PREFIXES),
            re.IGNORECASE
        )
        self._suffix_pattern = re.compile(
            '|'.join(self.DR_SUFFIXES) + r'$',
            re.IGNORECASE
        )

    def is_complex_item(self, text: str) -> bool:
        """
        判断是否为复合项目

        Args:
            text: 原始检查项目文本

        Returns:
            True 如果包含逗号分隔的多个子项
        """
        # 简单判断：包含逗号或顿号
        return ',' in text or '，' in text or '、' in text

    def split(self, text: str) -> List[str]:
        """
        拆分复合项目为独立子项

        Args:
            text: 原始复合项目文本

        Returns:
            拆分后的子项列表（已过滤耗材/操作，已清理前后缀）
        """
        # 1. 按逗号/顿号分割
        # 统一转换为英文逗号
        text = text.replace('，', ',').replace('、', ',')
        items = text.split(',')

        # 2. 清理每个子项
        cleaned_items = []
        for item in items:
            item = item.strip()
            if not item:
                continue

            # 过滤耗材和操作项
            if self._is_material_or_operation(item):
                logger.debug(f"DR拆分：过滤耗材/操作项: {item}")
                continue

            # 清理前后缀
            cleaned = self._clean_item(item)
            if cleaned:
                cleaned_items.append(cleaned)

        logger.info(
            f"DR拆分: {len(items)}项 → {len(cleaned_items)}项有效检查项 "
            f"(原始: {text[:50]}...)"
        )

        return cleaned_items

    def _is_material_or_operation(self, item: str) -> bool:
        """
        判断是否为耗材或操作项

        Args:
            item: 单个子项

        Returns:
            True 如果是耗材/操作项
        """
        return any(keyword in item for keyword in self.MATERIAL_KEYWORDS)

    def _clean_item(self, item: str) -> str:
        """
        清理单个子项，去除前后缀

        Args:
            item: 单个子项

        Returns:
            清理后的核心检查名称
        """
        # 去除前缀 (DR)、DR、[DR]
        cleaned = self._prefix_pattern.sub('', item)

        # 去除后缀：数字化摄影、DR摄影、摄影
        cleaned = self._suffix_pattern.sub('', cleaned)

        # 去除首尾空格
        cleaned = cleaned.strip()

        return cleaned

    def split_and_match(self, text: str, match_func, modality: str = 'DR') -> dict:
        """
        拆分复合项目并对每个子项进行匹配

        Args:
            text: 原始复合项目文本
            match_func: 匹配函数，签名为 func(text, modality) -> dict
            modality: 模态（默认 DR）

        Returns:
            匹配结果字典，格式：
            {
                'check_item': 原始文本,
                'is_complex': True,
                'sub_items': [
                    {'text': '子项1', 'result': {...}},
                    {'text': '子项2', 'result': {...}},
                ],
                'num_standard': 所有子项匹配到的标准项总数,
                'data': 合并的匹配数据,
                'tier': 综合层级,
                'confidence': 平均置信度,
            }
        """
        sub_items = self.split(text)

        if not sub_items:
            # 拆分后无有效项（全是耗材），返回空结果
            return {
                'check_item': text,
                'is_complex': True,
                'sub_items': [],
                'num_standard': 0,
                'data': [],
                'tier': 'none',
                'confidence': 0.0,
                'reason': 'complex_all_materials',
            }

        # 对每个子项执行匹配
        matched_results = []
        for sub_text in sub_items:
            result = match_func(sub_text, modality)
            matched_results.append({
                'text': sub_text,
                'result': result,
            })

        # 合并结果
        return self._merge_results(text, matched_results)

    def _merge_results(self, original_text: str, matched_results: List[dict]) -> dict:
        """
        合并多个子项的匹配结果

        Args:
            original_text: 原始复合项目文本
            matched_results: 每个子项的匹配结果列表

        Returns:
            合并后的匹配结果
        """
        # 统计所有匹配到的标准项
        total_standards = 0
        all_data = []
        confidences = []

        for item in matched_results:
            result = item['result']
            num = result.get('num_standard', 0)
            total_standards += num

            if num > 0 and result.get('data'):
                # 添加子项信息到 data 中
                for data_item in result['data']:
                    data_with_sub = data_item.copy()
                    data_with_sub['sub_item'] = item['text']
                    all_data.append(data_with_sub)

                # 收集置信度
                conf = result.get('confidence', 0.0)
                if conf > 0:
                    confidences.append(conf)

        # 计算平均置信度
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # 确定综合层级
        if total_standards == 0:
            tier = 'none'
        elif avg_confidence >= 0.8:
            tier = 'exact'
        elif avg_confidence >= 0.6:
            tier = 'partial'
        else:
            tier = 'degraded'

        return {
            'check_item': original_text,
            'is_complex': True,
            'sub_items': matched_results,
            'num_standard': total_standards,
            'data': all_data,
            'tier': tier,
            'confidence': avg_confidence,
            'score': int(avg_confidence * 10),  # 兼容旧格式
        }

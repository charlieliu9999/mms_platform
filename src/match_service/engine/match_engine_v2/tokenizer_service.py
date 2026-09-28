"""
分词和建树服务
"""
import re
from functools import lru_cache
from typing import Dict, List, Tuple, TYPE_CHECKING

import jieba.posseg as psg
import pandas as pd

from .constants import VERSION_FALLBACK
from .match_node import MatchNode

if TYPE_CHECKING:
    from .disambiguation_service import DisambiguationService


class TokenizerService:
    """分词和建树服务"""

    def __init__(self, mdict: Dict[str, str], common_normal: pd.DataFrame,
                 normal_rules: Dict[str, pd.DataFrame]):
        self.mdict = mdict
        self.common_normal = common_normal
        self.normal_rules = normal_rules

    def make_tree(self, records: List[Tuple[str, int, str]],
                  modality: str, version: str,
                  disamb_service: 'DisambiguationService' = None
                  ) -> Tuple[List[MatchNode], Dict]:
        """
        分词并构建 MatchNode 树

        Returns:
            (childrens, other_record)
        """
        childrens = []
        other_record: Dict[str, List] = {}

        for mode, index, record in records:
            if mode != modality:
                other_record.setdefault(mode, []).append((mode, index, record))
                continue

            node = self._build_node(record, modality, version)
            node.remove_by_pattern()
            if disamb_service is not None:
                node.determine_left_or_right(disamb_service)

            if node and node.entitys:
                childrens.append(node)

        return childrens, other_record

    def _build_node(self, record: str, modality: str,
                    version: str) -> MatchNode:
        node = MatchNode(record, modality, version)

        clean_record = re.sub(r'\d-\d椎体', '椎体', record)
        clean_record = re.sub(r'\d-\d椎间盘', '椎间盘', clean_record)

        for pair in psg.cut(clean_record):
            word = pair.word
            flag = pair.flag
            std_name, std_type = self.get_standard_name(
                word, flag, modality, version)
            if std_type in ('rfscan', 'mgscan'):
                std_type = 'scan'
            node.add_entity(word, std_type, std_name)

        return node

    @lru_cache(maxsize=2048)
    def get_standard_name(self, entity: str, pos: str,
                          modality: str,
                          version: str) -> Tuple[str, str]:
        dst = entity
        versions = VERSION_FALLBACK.get(version, [version])

        if not self.common_normal.empty:
            for ver in versions:
                match = self.common_normal[
                    (self.common_normal['src_word'] == entity) &
                    (self.common_normal['version'] == ver)
                ]
                if len(match) >= 1:
                    dst = str(match['dst_word'].iloc[0])
                    break

        if modality in self.normal_rules:
            mod_rules = self.normal_rules[modality]
            if not mod_rules.empty:
                for ver in versions:
                    mod_match = mod_rules[
                        (mod_rules['src_word'] == dst) &
                        (mod_rules['version'] == ver)
                    ]
                    if len(mod_match) >= 1:
                        dst = str(mod_match['dst_word'].iloc[0])
                        break

        if dst != entity:
            entity_type = self.mdict.get(dst, pos)
            return dst, entity_type

        return entity, self.mdict.get(entity, pos)

    def clear_cache(self):
        """C3 修复：清除 lru_cache，热重载规则数据后必须调用。
        @lru_cache 装饰实例方法时，缓存绑定在函数对象上，
        数据更新后旧缓存不会自动失效，需手动清除。"""
        self.get_standard_name.cache_clear()

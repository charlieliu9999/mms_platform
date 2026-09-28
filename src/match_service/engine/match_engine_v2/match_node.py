"""
MatchNode 数据类 - 匹配树节点，行为与原引擎 MatchNode 完全对齐
"""
import re
from typing import Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .disambiguation_service import DisambiguationService


class MatchNode:
    """匹配树节点，存储一个检查子项的结构化信息"""

    POS_MAP = {'body': 'B', 'scan': 'S', 'position': 'O', 'post': 'P'}
    POS_SET = {'body', 'scan', 'post', 'position', 'scope', 'special'}

    def __init__(self, raw: str, modality: str, version: str):
        self.raw_str = raw
        self.modality = modality
        self.version = version

        self.entitys: List[str] = []
        self.std_names: List[str] = []
        self.pos_types: List[str] = []
        self.patterns: List[str] = []
        self.pattern_str = ''

        self.pos_dict: Dict[str, List[int]] = {k: [] for k in self.POS_SET}
        self.extra: List[dict] = []
        self.standard_check_name: List[str] = []
        self.standard_check_code: List[str] = []
        self.standard_check_version: List[str] = []

        # 置信度信号（由 pipeline 各步骤设置，orchestrator 汇总为四档 tier）
        self.fill_default = False   # Step 9 补充了默认处理方式（部位命中、处理方式为推断）
        self.degraded = False       # Step 10 走了降级查询分支（模糊/回退命中）

    def add_entity(self, entity: str, pos: str, std: str = ''):
        self.entitys.append(entity)
        self.pos_types.append(pos)
        if pos not in self.pos_dict:
            self.pos_dict[pos] = []
        self.pos_dict[pos].append(len(self.entitys) - 1)
        self.std_names.append(std)

        if pos in self.POS_MAP:
            self.patterns.append(self.POS_MAP[pos])
        elif len(entity) == 1:
            self.patterns.append(entity)
        else:
            self.patterns.append('U')
        self.pattern_str = ''.join(self.patterns)

    def remove_entity(self, indices: List[int]):
        if not indices:
            return
        new_std, new_ent, new_pos, patterns = [], [], [], []
        for i in range(len(self.std_names)):
            if i in indices:
                continue
            new_std.append(self.std_names[i])
            new_ent.append(self.entitys[i])
            new_pos.append(self.pos_types[i])
            if self.pos_types[i] in self.POS_MAP:
                patterns.append(self.POS_MAP[self.pos_types[i]])
            elif len(self.entitys[i]) == 1:
                patterns.append(self.entitys[i])
            else:
                patterns.append('U')

        self.std_names = new_std
        self.entitys = new_ent
        self.pos_types = new_pos
        self.patterns = patterns
        self.pattern_str = ''.join(patterns)
        for k in self.pos_dict:
            self.pos_dict[k] = []
        for idx, pos in enumerate(self.pos_types):
            if pos not in self.pos_dict:
                self.pos_dict[pos] = []
            self.pos_dict[pos].append(idx)

    def add_extra(self, entity: str, type_: str):
        self.extra.append({type_: entity})

    def remove_by_pattern(self):
        """根据模式处理节点，BB/B(BS)/BUS(B)/BU/B/[B]...B 等冗余清理"""
        tag = ''
        tgt = self.pattern_str.find('BB')
        if tgt >= 0:
            body_pre = self.std_names[tgt]
            body_post = self.std_names[tgt + 1]
            if body_pre in ('胎儿', '胎儿及胎盘') or body_post == '四肢及关节':
                self.remove_entity([tgt + 1])
                tag = '从属'
            if body_pre == '主动脉全长':
                self.remove_entity([tgt])
                tag = '从属'
            if '椎' in body_pre and '段' in body_post:
                self.remove_entity([tgt])
                tag = '从属'

        tgt = self.pattern_str.find('B/B')
        if tgt >= 0:
            body_pre = self.std_names[tgt]
            if body_pre in ('胎儿', '胎儿及胎盘'):
                self.remove_entity([tgt + 1, tgt + 2])
            else:
                self.remove_entity([tgt, tgt + 1])
            tag = '从属'

        tgt = self.pattern_str.find('B(BS)')
        if tgt >= 0:
            self.remove_entity([tgt, tgt + 1])
            tag = '从属'

        tgt = self.pattern_str.find('BUS(B)')
        if tgt >= 0:
            self.remove_entity([tgt + 4, tgt + 5])
            tag = '从属'

        tgt = self.pattern_str.find('BU/B')
        if tgt >= 0:
            self.remove_entity([tgt, tgt + 2])
            tag = '从属'

        ret = re.match(r'.*\[B\].*B', self.pattern_str)
        if ret is not None:
            tgt = self.pattern_str.find('[B]')
            if tgt >= 0:
                self.remove_entity([tgt, tgt + 1])
                tag = '从属'

        return tag

    def determine_left_or_right(self, disamb_service: 'DisambiguationService'):
        """确定左、右部位"""
        select_body = {}
        for idx in range(len(self.entitys)):
            word = self.std_names[idx]
            if word not in ('左', '右'):
                continue

            is_merge = False
            for idy in range(0, idx):
                word_body = re.split('[|&]', self.std_names[idy])
                if self.pos_types[idy] != 'body':
                    continue
                for body in word_body:
                    if word not in body:
                        continue
                    if idy not in select_body:
                        select_body[idy] = []
                    _, std_name, _ = disamb_service.db_get_standard_name(
                        body, 'body', self.modality, self.version)
                    select_body[idy].append(std_name)
                    is_merge = True
                    break

            if is_merge:
                continue
            for idy in range(idx, len(self.std_names)):
                word_body = re.split('[|&]', self.std_names[idy])
                if self.pos_types[idy] != 'body':
                    continue
                for body in word_body:
                    if word not in body:
                        continue
                    if idy not in select_body:
                        select_body[idy] = []
                    _, std_name, _ = disamb_service.db_get_standard_name(
                        body, 'body', self.modality, self.version)
                    select_body[idy].append(std_name)
                    is_merge = True
                    break

        for idx, bodys in select_body.items():
            self.std_names[idx] = '|'.join(bodys)

    def determine_artery_or_vein(self, disamb_service: 'DisambiguationService'):
        """确定静脉/动脉部位"""
        select_body = {}
        for idx in range(len(self.entitys)):
            word = self.std_names[idx]
            if word not in ('动脉', '静脉'):
                continue

            is_merge = False
            for idy in range(0, idx):
                word_body = re.split('[|&]', self.std_names[idy])
                if self.pos_types[idy] != 'scan':
                    continue
                for body in word_body:
                    if word not in body:
                        continue
                    if idy not in select_body:
                        select_body[idy] = []
                    _, std_name, _ = disamb_service.db_get_standard_name(
                        body, 'scan', self.modality, self.version)
                    select_body[idy].append(std_name)
                    is_merge = True
                    break

            if is_merge:
                continue
            for idy in range(idx, len(self.std_names)):
                word_body = re.split('[|&]', self.std_names[idy])
                if self.pos_types[idy] != 'scan':
                    continue
                for body in word_body:
                    if word not in body:
                        continue
                    if idy not in select_body:
                        select_body[idy] = []
                    _, std_name, _ = disamb_service.db_get_standard_name(
                        body, 'scan', self.modality, self.version)
                    select_body[idy].append(std_name)
                    is_merge = True
                    break

        for idx, bodys in select_body.items():
            self.std_names[idx] = '|'.join(bodys)

    def merge(self, other: 'MatchNode', disamb_service: 'DisambiguationService' = None,
              pos_types=None):
        """合并另一个节点到自身"""
        if pos_types is None:
            pos_types = ['body', 'scan', 'post', 'position', 'scope', 'other', 'special']

        if self.raw_str != other.raw_str:
            self.raw_str = self.raw_str + '|' + other.raw_str
        self.patterns += other.patterns
        self.pattern_str = ''.join(self.patterns)

        for i in range(len(other.entitys)):
            if other.pos_types[i] not in pos_types:
                continue
            if other.std_names[i] in self.std_names:
                continue
            self.add_entity(other.entitys[i], other.pos_types[i], other.std_names[i])

        if disamb_service is not None:
            self.determine_left_or_right(disamb_service)
            self.determine_artery_or_vein(disamb_service)

    def split(self) -> List['MatchNode']:
        """根据序列类型转换分裂节点（BSPB → BS + PB）"""
        node_list = []
        hasBody, hasProcess, hasPost, curBody = False, False, False, False
        new_node = MatchNode(self.raw_str, self.modality, self.version)

        for idx, ptn in enumerate(self.patterns):
            if ptn == 'B':
                hasBody = True
                curBody = True
            elif ptn in ('S', 'P', 'O'):
                hasProcess = True
                curBody = False

            if all([hasBody, curBody]) and any([hasProcess, hasPost]):
                node_list.append(new_node)
                hasBody, hasProcess, hasPost, curBody = False, False, False, False
                new_node = MatchNode(self.raw_str, self.modality, self.version)
                new_node.add_entity(self.entitys[idx], self.pos_types[idx], self.std_names[idx])
            else:
                new_node.add_entity(self.entitys[idx], self.pos_types[idx], self.std_names[idx])

        node_list.append(new_node)
        return node_list

    def standard(self, usage_stats: dict = None) -> dict:
        """
        返回标准化结果

        Args:
            usage_stats: 使用频率统计 {code: usage_count}，用于智能排序

        Returns:
            包含原始文本和标准项列表的字典

        Phase 7: 智能排序优化
        - 如果提供 usage_stats，按使用频率降序 → 字母序排序
        - 否则按字母序排序（保持向后兼容）
        """
        # 组合 code, name 和 version（健壮处理可能的长度不匹配）
        results = [
            (code, name, self.standard_check_version[i]
             if i < len(self.standard_check_version) else None)
            for i, (code, name) in enumerate(zip(self.standard_check_code, self.standard_check_name))
        ]

        # Phase 7: 智能排序
        if usage_stats:
            # 使用频率降序 → 字母序（稳定性）
            results.sort(key=lambda x: (-usage_stats.get(x[0], 0), x[1]))
        else:
            # 默认按名称字母序（向后兼容）
            results.sort(key=lambda x: x[1])

        return {
            'raw': self.raw_str,
            'standard': [
                {'code': c, 'name': n, **({'version': v} if v else {})}
                for c, n, v in results
            ],
        }

    def get_body(self) -> List[str]:
        return [self.entitys[i] for i in self.pos_dict.get('body', [])]

    def get_scan(self) -> List[str]:
        return [self.entitys[i] for i in self.pos_dict.get('scan', [])]

    def get_post(self) -> List[str]:
        return [self.entitys[i] for i in self.pos_dict.get('post', [])]

    def get_position(self) -> List[str]:
        return [self.entitys[i] for i in self.pos_dict.get('position', [])]

    def __repr__(self):
        parts = [f"{self.std_names[i]}({self.pos_types[i]})" for i in range(len(self.entitys))]
        return f"Node[{self.raw_str}] → {' | '.join(parts)}"

"""
模式处理服务 — Pipeline Step 4/5/6
"""
import re
from copy import deepcopy
from typing import TYPE_CHECKING, List, Set, Tuple

from .match_node import MatchNode

if TYPE_CHECKING:
    from .data_loader import RuleDataLoader
    from .disambiguation_service import DisambiguationService


class PatternProcessor:
    """
    Step 4: B(B)合并 + BSPB分裂
    Step 5: 合并无body节点
    Step 6: 并列部位分裂
    """

    def __init__(self, data_loader: 'RuleDataLoader'):
        self.data_loader = data_loader

    def process_by_pattern(self, childrens: List[MatchNode],
                           version: str) -> List[MatchNode]:
        """Step 4: B(B)合并 + BSPB分裂"""
        # B(B) 合并
        for idx, node in enumerate(childrens):
            ret = re.match(r'.*B\(B.*\).*', node.pattern_str)
            if ret is None:
                continue
            tgt = node.pattern_str.find('B(B')
            if tgt < 0:
                continue
            body_out = node.std_names[tgt]
            body_index = node.pos_dict['body']
            if (tgt + 2) not in body_index:
                continue
            body_in_start = body_index.index(tgt + 2)
            body_in_end = node.pattern_str.find(')', tgt)
            body_in = ''
            body_in_list = []
            for idy in body_index[body_in_start:]:
                if idy >= body_in_end:
                    break
                body_in = body_in + '|' + node.std_names[idy]
                body_in_list.append(idy)
            dst_body, msg = self._db_find_body(
                f'{body_out}{body_in}', version, 'local_map')
            if msg == 'found':
                node.remove_entity(body_in_list)
                node.std_names[tgt] = dst_body
                childrens[idx] = node
                continue
            if '左' in body_out or '右' in body_out or '双' in body_out or '脉' in body_out:
                node.remove_entity([tgt + 2])
            else:
                node.remove_entity([tgt])
            childrens[idx] = node

        # BSPB 分裂
        for node_index in range(len(childrens) - 1, -1, -1):
            cur_node = childrens[node_index]
            tgt1 = re.match(r'.*B.*[SPO].*B.*[SPO]', cur_node.pattern_str)
            tgt2 = re.match(r'.*B.*[SPO].*[SPO].*B', cur_node.pattern_str)
            tgt3 = re.match(r'.*[SPO].*B.*B.*[SPO]', cur_node.pattern_str)
            tgt4 = re.match(r'.*[SPO].*B.*[SPO].*B', cur_node.pattern_str)
            if tgt1 is None and tgt2 is None and tgt3 is None and tgt4 is None:
                continue
            new_node_list = cur_node.split()
            for i, node in enumerate(new_node_list):
                childrens.insert(node_index + i, node)
            childrens.remove(cur_node)
        return childrens

    def merge_no_body(self, childrens: List[MatchNode],
                      disamb_service: 'DisambiguationService') -> List[MatchNode]:
        """Step 5: 无body节点向左/向右合并"""
        if len(childrens) <= 1:
            return childrens

        to_remove = set()
        for i, node in enumerate(childrens):
            if node.pos_dict['body']:
                continue
            merged = False
            for l in range(i - 1, -1, -1):
                if l in to_remove:
                    continue
                if childrens[l].pos_dict['body']:
                    childrens[l].merge(node, disamb_service)
                    merged = True
                    break
            if not merged:
                for r in range(i + 1, len(childrens)):
                    if r in to_remove:
                        continue
                    if childrens[r].pos_dict['body']:
                        childrens[r].merge(node, disamb_service)
                        merged = True
                        break
            if merged:
                to_remove.add(i)

        return [n for i, n in enumerate(childrens) if i not in to_remove]

    def split_multi_body(self, childrens: List[MatchNode]) -> List[MatchNode]:
        """Step 6: 并列部位分裂"""
        childrens, msg = self._split_body(childrens)
        if msg == 'split':
            return childrens

        new_node_list = []
        node_to_del = []
        for node_index in range(len(childrens) - 1, -1, -1):
            cur_node = childrens[node_index]
            if len(cur_node.pos_dict['body']) <= 1:
                continue
            insert_index = node_index
            for idx, pos in enumerate(cur_node.pos_types):
                if pos != 'body':
                    continue
                new_node = MatchNode(cur_node.raw_str, cur_node.modality, cur_node.version)
                new_node.add_entity(cur_node.entitys[idx], pos, cur_node.std_names[idx])
                for idy in range(0, len(cur_node.pos_types)):
                    if cur_node.pos_types[idy] == 'body':
                        continue
                    new_node.add_entity(
                        cur_node.entitys[idy], cur_node.pos_types[idy], cur_node.std_names[idy])
                new_node_list.append((insert_index, new_node))
                insert_index += 1
            if insert_index > node_index:
                node_to_del.append(cur_node)

        if new_node_list:
            for insert_index, node in new_node_list:
                childrens.insert(insert_index, node)
            for node in node_to_del:
                childrens.remove(node)
        return childrens

    def _split_body(self, childrens: List[MatchNode]) -> Tuple[List[MatchNode], str]:
        """拆分含 '|' 的单body节点"""
        new_node_list = []
        node_to_del = []
        for node_index in range(len(childrens) - 1, -1, -1):
            cur_node = childrens[node_index]
            if len(cur_node.pos_dict['body']) != 1:
                continue
            bodies = cur_node.std_names[cur_node.pos_dict['body'][0]]
            if '&' in bodies or '|' not in bodies:
                continue
            insert_index = node_index
            for body in bodies.split('|'):
                new_node = deepcopy(cur_node)
                new_node.std_names[new_node.pos_dict['body'][0]] = body
                new_node_list.append((insert_index, new_node))
                insert_index += 1
            node_to_del.append(cur_node)

        if new_node_list:
            for insert_index, node in new_node_list:
                childrens.insert(insert_index, node)
            for node in node_to_del:
                childrens.remove(node)
            return childrens, 'split'
        return childrens, 'nop'

    def _db_find_body(self, inbody: str, version: str,
                      step: str) -> Tuple[str, str]:
        """查找body映射 global_map/local_map"""
        in_process_set = set(inbody.split('|'))
        body_map = self.data_loader.body_map
        df_body = body_map.query(f'version=="{version}" and step=="{step}"')
        ret_set: Set[str] = set()
        dst_body = ''
        for _, row in df_body.iterrows():
            process_set = set(row['src_word'].split('|'))
            union_set = process_set & in_process_set
            if union_set == process_set and len(ret_set) < len(union_set):
                ret_set = union_set
                dst_body = row['dst_word']
        if dst_body != '':
            return dst_body, 'found'
        return inbody, 'not found'

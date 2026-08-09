"""
消歧服务 — Pipeline Step 7/8
包含：节点间合并、3步级联消歧映射、血管成像归一化
"""
import re
from typing import Dict, List, Optional, Set, Tuple, TYPE_CHECKING

import pandas as pd

from .constants import VERSION_FALLBACK
from .match_node import MatchNode

if TYPE_CHECKING:
    from .data_loader import RuleDataLoader


class DisambiguationService:
    """
    Step 7: 节点间合并（上下位关系）
    Step 8: 消歧映射（3步级联 + 血管归一化）
    """

    _VASCULAR_BODY_RULES: List[Tuple[str, str, Optional[str]]] = [
        (r'冠状动脉|冠脉|心脏',         '冠状动脉',     None),
        # 复合部位「头颈部」必须排在「头部」「颈部」之前：
        # re.search 子串贪婪匹配，否则「头颈部动脉」会被「颈部」规则截断成「颈部动脉」。
        (r'头颈部|头颈',                 '头颈部动脉',   '头颈部静脉'),
        (r'头部|头颅|颅内|脑',           '颅内动脉',     '颅内静脉'),
        (r'颈部|颈动脉|颈静脉',          '颈部动脉',     '颈部静脉'),
        (r'上腔静脉',                    '上腔静脉',     '上腔静脉'),
        # 复合部位「左心房肺静脉」必须排在「肺静脉」之前，避免被子串截断成「肺静脉」。
        (r'左心房肺静脉|左心房',           '左心房肺静脉', '左心房肺静脉'),
        (r'肺静脉',                      '肺静脉',       '肺静脉'),
        (r'肺动脉',                      '肺动脉',       None),
        (r'支气管动脉|支气管.*血管',       '支气管动脉',   None),
        (r'胸腹主动脉',                   '胸腹主动脉',   None),
        (r'胸主动脉',                    '胸主动脉',     None),
        (r'腹主动脉|夹层动脉瘤|主动脉瘤', '腹主动脉',     None),
        (r'肠道|肠系膜',                  '肠系膜上动脉', None),
        (r'肾',                          '肾动脉',       '肾静脉'),
        (r'髂',                          '髂动脉',       '髂静脉'),
        (r'锁骨下静脉',                   '锁骨下静脉',   '锁骨下静脉'),
        (r'锁骨下动脉|上肢|前臂|上臂|手部', '上肢动脉',   '上肢静脉'),
        (r'下肢|大腿|小腿|足部',           '下肢动脉',   '下肢静脉'),
    ]

    def __init__(self, data_loader: 'RuleDataLoader'):
        self.data_loader = data_loader

    # ─── Step 7: 节点间合并 ─────────────────────────────────────────────────

    def merge_nodes(self, childrens: List[MatchNode], process_type: str,
                    modality: str, version: str) -> List[MatchNode]:
        new_childrens = []
        while len(childrens) > 0:
            node_0 = childrens.pop(0)
            if len(node_0.pos_dict['body']) == 0:
                self._merge_process(node_0, 'special', modality, version)
                self._merge_process(node_0, process_type, modality, version)
                self._merge_process(node_0, 'post', modality, version)
                new_childrens.append(node_0)
                continue

            body_0 = node_0.std_names[node_0.pos_dict['body'][0]]
            process_0 = [node_0.std_names[i] for i in node_0.pos_dict[process_type]]
            node_to_del = []

            for j in range(len(childrens)):
                node_j = childrens[j]
                if len(node_j.pos_dict['body']) == 0:
                    continue
                body_j = node_j.std_names[node_j.pos_dict['body'][0]]
                process_j = [node_j.std_names[i] for i in node_j.pos_dict[process_type]]

                body_rel = self._is_merge_fn(body_0, body_j, process_0, process_j, version)
                if len(body_rel) > 1:
                    continue

                if body_rel[0] == body_0:
                    node_0.merge(node_j, self, pos_types=['scan', 'post', 'position', 'scope'])
                else:
                    node_j.merge(node_0, self, pos_types=['scan', 'post', 'position', 'scope'])
                    node_j.std_names[node_j.pos_dict['body'][0]] = body_rel[0]
                    node_0 = node_j
                    # C2 修复：合并后 node_0 已变更，必须重新计算 body_0/process_0
                    # 否则后续循环使用过期值，导致 3+ 节点链式合并错误
                    body_0 = node_0.std_names[node_0.pos_dict['body'][0]]
                    process_0 = [node_0.std_names[i] for i in node_0.pos_dict[process_type]]
                node_to_del.append(node_j)

            self._merge_process(node_0, process_type, modality, version)
            self._merge_process(node_0, 'post', modality, version)
            new_childrens.append(node_0)

            for node in node_to_del:
                childrens.remove(node)

        return new_childrens

    def _merge_process(self, node: MatchNode, process_type: str,
                       modality: str, version: str):
        """合并处理方式 平扫|增强→平扫+增强"""
        process = [node.std_names[i] for i in node.pos_dict.get(process_type, [])]
        if not process:
            return
        ret, process_std_list = self.db_get_process_normal(process, modality, version)
        if ret == 'unfound':
            return
        node.remove_entity([i for i in node.pos_dict[process_type]])
        process_str = '|'.join(process)
        for process_std in process_std_list:
            node.add_entity(process_str, process_type, process_std)

    def _is_merge_fn(self, bodypart1: str, bodypart2: str,
                     scan1: list, scan2: list, version: str) -> list:
        if bodypart1 != bodypart2:
            bodypart1_ = re.split('[|&]', bodypart1)
            bodypart2_ = re.split('[|&]', bodypart2)
            if len(bodypart1_) > 1 or len(bodypart2_) > 1:
                body_ = set(bodypart1_) & set(bodypart2_)
                if body_:
                    return sorted(body_)
            for ver in VERSION_FALLBACK.get(version, [version]):
                dst_body, msg = self._db_find_body(
                    f'{bodypart1}|{bodypart2}', ver, 'global_map')
                if msg == 'found':
                    return [dst_body]
            return [bodypart1, bodypart2]
        return [bodypart1]

    # ─── Step 8: 消歧映射 ──────────────────────────────────────────────────

    def body_2process_remap(self, childrens: List[MatchNode], process_type: str,
                            modality: str, version: str) -> List[MatchNode]:
        if modality in ('CT', 'MR'):
            result = self._body_2process_remap_ct_mr(
                childrens, 'scan', 'post', modality, version)
        elif modality == 'DR':
            result = self._body_2process_remap_dr(
                childrens, 'position', 'scan', modality, version)
        else:
            return childrens
        return self._dedup_identical_nodes(result)

    @staticmethod
    def _dedup_identical_nodes(childrens: List[MatchNode]) -> List[MatchNode]:
        """去除 remap 产生的完全相同节点（同 raw + 同 body/process 组合）。

        括号缩写（如 "(CTPA)"）与主扫描词解析到同一实体时会产生重复节点；
        lookup_standard 的 dup_set 使第二个重复节点拿不到标准项，
        进而被 orchestrator 误判为"有实体未匹配"导致 ambiguous 降级。
        """
        seen = set()
        result = []
        for node in childrens:
            key_parts = []
            for pos in sorted(node.pos_dict.keys()):
                # 添加索引边界检查，防止 pos_dict 中的过期索引
                valid_indices = [j for j in node.pos_dict[pos] if j < len(node.std_names)]
                if len(valid_indices) != len(node.pos_dict[pos]):
                    logger.warning(
                        f"Node '{node.raw_str}' has invalid indices for pos '{pos}': "
                        f"expected {len(node.pos_dict[pos])}, valid {len(valid_indices)}"
                    )
                vals = tuple(sorted(node.std_names[j] for j in valid_indices))
                key_parts.append((pos, vals))
            key = (node.raw_str, tuple(key_parts))
            if key in seen:
                continue
            seen.add(key)
            result.append(node)
        return result

    def _body_2process_remap_ct_mr(self, childrens: List[MatchNode],
                                    process1: str, process2: str,
                                    modality: str, version: str) -> List[MatchNode]:
        node_to_add, node_to_del = [], []

        for idx in range(len(childrens)):
            node = childrens[idx]
            body = node.std_names[node.pos_dict['body'][0]] \
                if len(node.pos_dict['body']) == 1 else ""
            ret = [False] * 3

            _add, _del, ret[0] = self._scan_post_map(
                body, process1, process2, node, idx, modality, version)
            node_to_add += _add
            node_to_del += _del
            if ret[0]:
                continue

            _add, _del, ret[1] = self._scan_map(
                body, process1, node, idx, modality, version)
            node_to_add += _add
            node_to_del += _del

            _add, _del, ret[2] = self._post_map(
                body, process2, node, idx, modality, version)
            node_to_add += _add
            node_to_del += _del

        # 逆序插入避免索引失效：每次插入会移动后续元素，
        # 从右向左插入可确保左侧索引保持有效
        for i, node in sorted(node_to_add, key=lambda x: x[0], reverse=True):
            childrens.insert(i, node)
        for node in node_to_del:
            if node in childrens:
                childrens.remove(node)
        return childrens

    def _body_2process_remap_dr(self, childrens: List[MatchNode],
                                 process1: str, process2: str,
                                 modality: str, version: str) -> List[MatchNode]:
        node_to_add, node_to_del = [], []

        for idx in range(len(childrens)):
            node = childrens[idx]
            body = node.std_names[node.pos_dict['body'][0]] \
                if len(node.pos_dict['body']) == 1 else ""
            _add, _del, ret = self._scan_map(
                body, process1, node, idx, modality, version)
            node_to_add += _add
            node_to_del += _del

        # 逆序插入避免索引失效：每次插入会移动后续元素，
        # 从右向左插入可确保左侧索引保持有效
        for i, node in sorted(node_to_add, key=lambda x: x[0], reverse=True):
            childrens.insert(i, node)
        for node in node_to_del:
            if node in childrens:
                childrens.remove(node)
        return childrens

    def _scan_post_map(self, body: str, process1: str, process2: str,
                       node: MatchNode, idx: int, modality: str,
                       version: str) -> Tuple[list, list, bool]:
        entity_to_remove = []
        node_to_add, node_to_del = [], []
        is_disambiguity = False

        if not node.pos_dict.get(process1) and not node.pos_dict.get(process2):
            return [], [], False

        for j1 in node.pos_dict.get(process1, []):
            scan = node.std_names[j1]
            for j2 in node.pos_dict.get(process2, []):
                post = node.std_names[j2]
                msg, ret = self._db_disambiguity(
                    body, scan + '_' + post, modality, version)
                if msg == 'unfound':
                    continue

                is_disambiguity = True
                if ret is not None and len(ret) > 1:
                    continue

                dst_body = ret['dst_body'].iloc[0]
                dst_process = ret['dst_process'].iloc[0]
                if '_' in dst_process:
                    new_scan, new_post = dst_process.split('_')
                else:
                    new_scan = dst_process
                    new_post = post

                if node.pos_dict.get('body'):
                    if (dst_body == node.std_names[node.pos_dict['body'][0]]
                            and new_scan == scan and new_post == post):
                        continue
                    new_node = MatchNode(node.raw_str, node.modality, node.version)
                    new_node.add_entity(body, 'body', dst_body)
                    new_node.add_entity(scan, process1, new_scan)
                    new_node.add_entity(post, process2, new_post)
                    node_to_add.append((idx, new_node))
                    entity_to_remove.append(j1)
                    entity_to_remove.append(j2)

        if not is_disambiguity:
            return node_to_add, node_to_del, False

        node.remove_entity(entity_to_remove)
        if not node.pos_dict.get(process1) and not node.pos_dict.get(process2):
            node_to_del.append(node)

        return node_to_add, node_to_del, is_disambiguity

    def _scan_map(self, body: str, process1: str, in_node: MatchNode,
                  idx: int, modality: str,
                  version: str) -> Tuple[list, list, bool]:
        entity_to_remove = []
        node_to_add, node_to_del = [], []
        is_disambiguity = False

        if not in_node.pos_dict.get(process1):
            return [], [], False

        for j in in_node.pos_dict.get(process1, []):
            scan = in_node.std_names[j]
            msg, ret = self._db_disambiguity(body, scan, modality, version)
            if msg == 'unfound':
                continue

            is_disambiguity = True

            if ret is not None and len(ret) > 1:
                for _, row in ret.iterrows():
                    sub_body = row['dst_body']
                    sub_process = row['dst_process']
                    new_node = MatchNode(
                        in_node.raw_str, in_node.modality, in_node.version)
                    new_node.add_entity(body, 'body', sub_body)
                    new_node.add_entity(scan, process1, sub_process)
                    node_to_add.append((idx, new_node))
                entity_to_remove.append(j)
                continue

            if ret is None or ret.empty:
                continue

            dst_body = ret['dst_body'].iloc[0]
            dst_process = ret['dst_process'].iloc[0]

            if in_node.pos_dict.get('body'):
                if (dst_body == in_node.std_names[in_node.pos_dict['body'][0]]
                        and dst_process == scan):
                    continue
                new_node = MatchNode(
                    in_node.raw_str, in_node.modality, in_node.version)
                new_node.add_entity(body, 'body', dst_body)
                new_node.add_entity(scan, process1, dst_process)
                node_to_add.append((idx, new_node))
                entity_to_remove.append(j)
            else:
                in_node.add_entity(" ", 'body', dst_body)
                in_node.std_names[j] = dst_process

        if not is_disambiguity:
            return node_to_add, node_to_del, False

        in_node.remove_entity(entity_to_remove)
        if not in_node.pos_dict.get(process1) and not in_node.pos_dict.get('post'):
            node_to_del.append(in_node)

        return node_to_add, node_to_del, is_disambiguity

    def _post_map(self, body: str, process2: str, node: MatchNode,
                  idx: int, modality: str,
                  version: str) -> Tuple[list, list, bool]:
        entity_to_remove = []
        node_to_add, node_to_del = [], []
        is_disambiguity = False

        if not node.pos_dict.get(process2):
            return [], [], False

        for j in node.pos_dict.get(process2, []):
            post = node.std_names[j]
            msg, ret = self._db_disambiguity(body, post, modality, version)
            if msg == 'unfound':
                continue

            is_disambiguity = True

            if ret is not None and len(ret) > 1:
                for _, row in ret.iterrows():
                    sub_body = row['dst_body']
                    sub_process = row['dst_process']
                    new_node = MatchNode(node.raw_str, node.modality, node.version)
                    new_node.add_entity(body, 'body', sub_body)
                    new_node.add_entity(post, process2, sub_process)
                    node_to_add.append((idx, new_node))
                entity_to_remove.append(j)
                continue

            if ret is None or ret.empty:
                continue

            dst_body = ret['dst_body'].iloc[0]
            dst_process = ret['dst_process'].iloc[0]

            if node.pos_dict.get('body'):
                if (dst_body == node.std_names[node.pos_dict['body'][0]]
                        and dst_process == post):
                    continue
                new_node = MatchNode(node.raw_str, node.modality, node.version)
                new_node.add_entity(body, 'body', dst_body)
                if '_' in dst_process:
                    new_process = dst_process.split('_')
                    if not node.pos_dict.get('scan'):
                        new_node.add_entity('-', 'scan', new_process[0])
                    new_node.add_entity(post, 'post', new_process[1])
                else:
                    if not node.pos_dict.get('scan'):
                        new_node.add_entity('-', 'scan', '')
                    new_node.add_entity(post, 'post', dst_process)
                node_to_add.append((idx, new_node))
                entity_to_remove.append(j)
            else:
                node.add_entity(' ', 'scan', '-')
                node.add_entity(" ", 'body', dst_body)

        if not is_disambiguity:
            return node_to_add, node_to_del, False

        node.remove_entity(entity_to_remove)
        if not node.pos_dict.get(process2):
            node_to_del.append(node)

        return node_to_add, node_to_del, is_disambiguity

    # ─── Step 8.5: 血管成像归一化 ──────────────────────────────────────────

    def normalize_vascular_nodes(self, childrens: List[MatchNode],
                                 process_type: str,
                                 modality: str) -> List[MatchNode]:
        if modality not in ('CT', 'MR') or process_type != 'scan':
            return childrens

        for node in childrens:
            raw = node.raw_str.upper()
            if not node.pos_dict.get('body'):
                inferred_body = self._infer_vascular_body_from_raw(raw)
                if inferred_body:
                    node.add_entity(inferred_body, 'body', inferred_body)
                else:
                    continue

            scan_text = ''.join(
                node.std_names[i] for i in node.pos_dict.get('scan', [])
            ).upper()
            body_idx = node.pos_dict['body'][0]
            body = node.std_names[body_idx]

            # 非血管造影关键词白名单（排除）
            # 这些造影类型不应该被识别为血管成像
            NON_VASCULAR_CONTRAST = {
                '尿路', 'CTU', 'T管', '关节', '排粪', 
                '插管', '引流管', '碘水', '碘油', '淋巴管',
                '胆道', 'ERCP', 'PTC', '胰胆管', '穿刺',
                '口服', '钡餐', '灌肠', '逆行', '泌尿系',
                '经内镜', '经皮经肝', 'MRCP', 'MRU',
            }

            is_vascular = (
                any(k in raw for k in (
                    '血管', 'CTA', 'CTV', 'MRA', 'MRV',
                    '动脉', '静脉', '冠脉', '冠状动脉'))
                or any(k in scan_text for k in (
                    '血管', 'CTA', 'CTV', 'MRA', 'MRV'))
                or (
                    '造影' in raw 
                    and modality == 'CT'
                    and not any(k in raw for k in NON_VASCULAR_CONTRAST)
                )
            )
            if not is_vascular:
                continue

            vessel_type = self._detect_vascular_type(raw, scan_text, body)
            enhanced = bool(re.search(r'增强|CE-MRA|CE-MRV', raw + scan_text))

            body = self._normalize_vascular_body(body, raw, vessel_type)
            node.std_names[body_idx] = body

            # Phase 2 改进：支持动静脉组合扫描方式
            if modality == 'CT':
                if vessel_type == 'both':
                    scan = '动静脉血管成像(CTA+CTV)'
                elif vessel_type == 'vein':
                    scan = '静脉血管成像(CTV)'
                else:
                    scan = '动脉血管成像(CTA)'
            else:
                if vessel_type == 'both':
                    scan = ('动静脉血管增强成像(CE-MRA+CE-MRV)' if enhanced
                            else '动静脉血管成像(MRA+MRV)')
                elif vessel_type == 'vein':
                    scan = ('静脉血管增强成像(CE-MRV)' if enhanced
                            else '静脉血管成像(MRV)')
                else:
                    scan = ('动脉血管增强成像(CE-MRA)' if enhanced
                            else '动脉血管成像(MRA)')

            scan_indices = list(node.pos_dict.get('scan', []))
            if scan_indices:
                # 不能依赖 scan_indices[0]：处理方式归一化曾经由 set 生成列表，
                # 不同 PYTHONHASHSEED 会把“平扫+增强”或“MRA”随机放在首位。
                vascular_indices = [
                    idx for idx in scan_indices
                    if re.search(r'血管|CTA|CTV|MRA|MRV', node.std_names[idx], re.I)
                ]
                target_idx = vascular_indices[0] if vascular_indices else scan_indices[0]

                explicit_base_enhanced = (
                    modality == 'MR' and (
                        vessel_type == 'artery' and bool(re.search(
                            r'(?:MRA\s*\+\s*CE-MRA|CE-MRA\s*\+\s*MRA)', raw
                        ))
                        or vessel_type == 'vein' and bool(re.search(
                            r'(?:MRV\s*\+\s*CE-MRV|CE-MRV\s*\+\s*MRV)', raw
                        ))
                    )
                )
                if explicit_base_enhanced:
                    base_scan = (
                        '动脉血管成像(MRA)'
                        if vessel_type == 'artery'
                        else '静脉血管成像(MRV)'
                    )
                    node.std_names[target_idx] = base_scan
                    if scan not in node.std_names:
                        node.add_entity('增强血管成像', 'scan', scan)
                else:
                    node.std_names[target_idx] = scan

                # 血管语义已由上面的 scan 表达，普通平扫/增强组合不能继续作为
                # 独立扫描方式参与查表，否则可能误命中“全腹部平扫+增强”。
                plain_scans = {
                    '增强', '平扫', '平扫+增强', '普通扫描', '普通',
                }
                for extra_idx in scan_indices:
                    if extra_idx != target_idx and node.std_names[extra_idx] in plain_scans:
                        node.pos_types[extra_idx] = 'other'
                # pos_types 改动后重建索引，避免后续仍读取已降级 scan。
                for pos in node.pos_dict:
                    node.pos_dict[pos] = []
                for idx, pos in enumerate(node.pos_types):
                    node.pos_dict.setdefault(pos, []).append(idx)
            else:
                node.add_entity('血管成像', 'scan', scan)

        return childrens

    def _infer_vascular_body_from_raw(self, raw: str) -> Optional[str]:
        if re.search(r'胸腹主动脉', raw):
            return '胸腹主动脉'
        if re.search(r'腹主动脉|夹层动脉瘤|主动脉瘤', raw):
            return '腹主动脉'
        return None

    def _detect_vascular_type(self, raw: str, scan_text: str,
                              body: str = '') -> str:
        """检测血管类型：artery（动脉）、vein（静脉）、both（动静脉双期）"""
        # Phase 2 改进：支持动静脉组合检测
        has_artery_raw = bool(re.search(r'动脉|CTA|MRA|冠脉|冠状动脉', raw))
        has_vein_raw = bool(re.search(r'静脉|CTV|MRV', raw))

        # 检测动静脉组合的关键词
        if re.search(r'动静脉|CTA\+CTV|CTV\+CTA|MRA\+MRV|MRV\+MRA|双期', raw):
            return 'both'

        # 如果同时包含动脉和静脉关键词，判定为组合
        if has_artery_raw and has_vein_raw:
            return 'both'

        # 单一类型检测（保留原逻辑）
        if has_vein_raw:
            return 'vein'
        if has_artery_raw:
            return 'artery'

        # 从部位名称判断
        has_vein_body = '静脉' in body
        has_artery_body = '动脉' in body
        if has_vein_body and not has_artery_body:
            return 'vein'
        if has_artery_body:
            return 'artery'

        # 从扫描方式判断
        has_vein_scan = bool(re.search(r'静脉|CTV|MRV', scan_text))
        has_artery_scan = bool(re.search(r'动脉|CTA|MRA', scan_text))
        if has_vein_scan and not has_artery_scan:
            return 'vein'

        return 'artery'

    def _normalize_vascular_body(self, body: str, raw: str,
                                 vessel_type: str) -> str:
        """归一化血管部位名称

        Phase 2 改进：vessel_type='both' 时保留原部位名称（通常是通用部位）
        """
        # 动静脉组合时，保留原部位名（如"腹部血管"而非"腹部动脉/静脉"）
        if vessel_type == 'both':
            return body

        for pattern, artery, vein in self._VASCULAR_BODY_RULES:
            if re.search(pattern, raw):
                if vessel_type == 'vein' and vein is not None:
                    return vein
                return artery
        return body

    # ─── DB 工具方法 ───────────────────────────────────────────────────────

    def db_get_standard_name(self, entity: str, pos: str,
                             modality: str,
                             version: str) -> Tuple[str, str, str]:
        """3值返回：(msg, std_name, std_type)"""
        dst = entity
        versions = VERSION_FALLBACK.get(version, [version])

        df = self.data_loader.common_normal
        if not df.empty:
            for ver in versions:
                match = df[(df['src_word'] == entity) & (df['version'] == ver)]
                if len(match) >= 1:
                    dst = str(match['dst_word'].iloc[0])
                    break

        if modality in self.data_loader.normal_rules:
            mod_rules = self.data_loader.normal_rules[modality]
            if not mod_rules.empty:
                for ver in versions:
                    mod_match = mod_rules[
                        (mod_rules['src_word'] == dst) & (mod_rules['version'] == ver)]
                    if len(mod_match) >= 1:
                        dst = str(mod_match['dst_word'].iloc[0])
                        break

        if dst != entity:
            entity_type = self.data_loader.mdict.get(dst, pos)
            return 'found', dst, entity_type
        return 'unfound', entity, pos

    def _db_find_body(self, inbody: str, version: str,
                      step: str) -> Tuple[str, str]:
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

    def _db_disambiguity(self, body: str, process: str,
                         modality: str,
                         version: str) -> Tuple[str, Optional[pd.DataFrame]]:
        """完整消歧 — 5步级联"""
        msg, new_body, new_process = self._db_determin_process_by_body(process, body)
        if msg == 'found':
            m, ret = self._db_body_disambiguity(new_body, new_process, modality, version)
            if m == 'found':
                return m, ret
            return 'found', pd.DataFrame(
                [(new_body, new_process)], columns=['dst_body', 'dst_process'])

        msg, new_body, new_process = self._db_determin_body_by_process(process, body)
        if msg == 'found':
            m, ret = self._db_body_disambiguity(new_body, new_process, modality, version)
            if m == 'found':
                return m, ret
            return 'found', pd.DataFrame(
                [(new_body, new_process)], columns=['dst_body', 'dst_process'])

        msg, new_body, new_process = self._db_add_process_for_vessel(
            body, process, modality, version)
        if msg == 'found':
            m, ret = self._db_body_disambiguity(new_body, new_process, modality, version)
            if m == 'found':
                return m, ret
            return 'found', pd.DataFrame(
                [(new_body, new_process)], columns=['dst_body', 'dst_process'])

        msg, ret = self._db_supplement_process_for_vessel(
            body, process, modality, version)
        if msg == 'found':
            return msg, ret

        return self._db_body_disambiguity(body, process, modality, version)

    def _db_body_disambiguity(self, body: str, process: str,
                              modality: str,
                              version: str) -> Tuple[str, Optional[pd.DataFrame]]:
        versions = VERSION_FALLBACK.get(version, [version])
        df_0 = pd.DataFrame()
        for ver in versions:
            df_0 = self.data_loader.df_body_disamb.query(
                f'src_process=="{process}" and modality=="{modality}" and version=="{ver}"')
            if not df_0.empty:
                break

        if df_0.empty:
            return 'unfound', df_0
        if len(df_0) == 1:
            if df_0['src_body'].iloc[0] in ('any', body):
                df_0 = df_0.copy()
                for idx, row in df_0.iterrows():
                    if row['dst_body'] == 'any':
                        df_0.loc[idx, 'dst_body'] = body
                return 'found', df_0
            return 'unfound', None
        df_1 = df_0.query(f'src_body=="{body}"')
        if df_1.empty:
            df_2 = df_0.query('src_body=="any"')
            if df_2.empty:
                return 'unfound', None
            df_2 = df_2.copy()
            for idx, row in df_2.iterrows():
                if row['dst_body'] == 'any':
                    df_2.loc[idx, 'dst_body'] = body
            return 'found', df_2
        return 'found', df_1

    def _db_determin_process_by_body(self, process: str,
                                     body: str) -> Tuple[str, Optional[str], Optional[str]]:
        if body == '肝动静脉':
            return 'found', body, '动静脉血管成像(CTA+CTV)'
        process_list = sorted(set(re.split('[|&]', process)))
        if len(process_list) < 2:
            return 'unfound', None, None
        if '静脉' in body and '|' not in body:
            for item in process_list:
                if 'CTV' in item or 'MRV' in item:
                    return 'found', body, item
        if '动脉' in body and '|' not in body:
            for item in process_list:
                if 'CTA' in item or 'MRA' in item:
                    return 'found', body, item
        return 'unfound', None, None

    def _db_determin_body_by_process(self, process: str,
                                     body: str) -> Tuple[str, Optional[str], Optional[str]]:
        body_list = sorted(set(re.split('[|&]', body)))
        if len(body_list) < 2:
            return 'unfound', None, None
        bodies = []
        if ('CTV' in process or 'MRV' in process) and '|' not in process:
            for item in body_list:
                if '静脉' in item:
                    bodies.append(item)
        if ('CTA' in process or 'MRA' in process) and '|' not in process:
            for item in body_list:
                if '动脉' in item:
                    bodies.append(item)
        if bodies:
            return 'found', '|'.join(bodies), process
        return 'unfound', None, None

    def _db_add_process_for_vessel(self, body: str, process: str,
                                   modality: str,
                                   version: str) -> Tuple[str, Optional[str], Optional[str]]:
        if (len(process) > 0 or body in ('动脉', '静脉')
                or ('动脉' not in body and '静脉' not in body)):
            return 'unfound', None, None
        body_list = sorted(set(re.split('[|&]', body)))
        versions = VERSION_FALLBACK.get(version, [version])
        df_0 = pd.DataFrame()
        for ver in versions:
            if len(body_list) > 1:
                df_0 = self.data_loader.df_body_disamb.query(
                    f'src_process=="" and modality=="{modality}" '
                    f'and version=="{ver}" and src_body=="动脉|静脉"')
            elif '动脉' in body:
                df_0 = self.data_loader.df_body_disamb.query(
                    f'src_process=="" and modality=="{modality}" '
                    f'and version=="{ver}" and src_body=="动脉"')
            elif '静脉' in body:
                df_0 = self.data_loader.df_body_disamb.query(
                    f'src_process=="" and modality=="{modality}" '
                    f'and version=="{ver}" and src_body=="静脉"')
            if not df_0.empty:
                break
        if df_0.empty:
            return 'unfound', None, None
        if len(df_0) == 1:
            df_0 = df_0.copy()
            for idx, row in df_0.iterrows():
                df_0.loc[idx, 'dst_body'] = body
            return 'found', body, df_0['dst_process'].iloc[0]
        return 'unfound', None, None

    def _db_supplement_process_for_vessel(self, body: str, process: str,
                                          modality: str,
                                          version: str) -> Tuple[str, Optional[pd.DataFrame]]:
        if (process not in ('平扫', '增强', '平扫+增强')
                or ('动脉' not in body and '静脉' not in body)):
            return 'unfound', None
        versions = VERSION_FALLBACK.get(version, [version])
        body_remap = pd.DataFrame()
        for ver in versions:
            body_remap = self.data_loader.vessel_map.query(
                f'src_word=="{body}" and version=="{ver}"')
            if not body_remap.empty:
                break
        if len(body_remap) == 1:
            result = []
            dst_body_arr = body_remap['dst_word'].iloc[0].split('_')
            for sub_body in dst_body_arr:
                if '脉' in sub_body:
                    msg, _, new_process = self._db_add_process_for_vessel(
                        body, '', modality, version)
                    if msg == 'found':
                        result.append((body, new_process))
                else:
                    result.append((sub_body, process))
            if not result:
                return 'unfound', None
            df_ret = pd.DataFrame(result, columns=['dst_body', 'dst_process'])
            return 'found', df_ret
        return 'unfound', None

    def db_get_process_normal(self, in_process: list, modality: str,
                              version: str) -> Tuple[str, list]:
        """处理方式归一化"""
        ambiguous_process = []
        normal_process = []
        process = []
        for p in in_process:
            if '&' in p:
                sub_process = re.split('[|&]', p)
                ambiguous_process.append((p, set(sub_process)))
            else:
                normal_process.append(p)
                process += p.split('|')

        has_amb = False
        normal_process_set = set(normal_process) if normal_process else {''}
        for raw_p, amb_set in ambiguous_process:
            inter_process = amb_set & normal_process_set
            if len(inter_process) > 0:
                has_amb = True
                continue
            process.append(raw_p)

        in_process_set = set(process) if process else {''}
        versions = VERSION_FALLBACK.get(version, [version])
        df_normal = pd.DataFrame()
        for ver in versions:
            df_normal = self.data_loader.process_normal.query(
                f'modality=="{modality}" and version=="{ver}"')
            if not df_normal.empty:
                break

        ret_set: Set[str] = set()
        dst_set: Set[str] = set()
        for _, row in df_normal.iterrows():
            process_set = set(row['src_word'].split('|'))
            union_set = process_set & in_process_set
            if union_set == process_set and len(ret_set) < len(union_set):
                ret_set = union_set
                dst_set = in_process_set - ret_set
                dst_set.add(row['dst_word'])

        if dst_set:
            return 'found', sorted(dst_set)
        elif has_amb:
            return 'found', sorted(in_process_set)
        return 'unfound', sorted(in_process_set)

    def lookup_disambiguity(self, body: str, process: str,
                            modality: str, version: str) -> Optional[Tuple[str, str]]:
        df = self.data_loader.df_body_disamb
        for ver in VERSION_FALLBACK.get(version, [version]):
            match = df[
                (df['src_body'] == body) &
                (df['src_process'] == process) &
                (df['modality'] == modality) &
                (df['version'] == ver)
            ]
            if len(match) >= 1:
                return (match['dst_body'].iloc[0], match['dst_process'].iloc[0])
        return None

    def db_get_body_by_process(self, modality: str, version: str,
                               process: list) -> Set[str]:
        """根据处理方式查询匹配的部位"""
        mod_versions = self.data_loader.df_standard.get(modality, {})
        df_std = None
        for ver in VERSION_FALLBACK.get(version, [version]):
            if ver in mod_versions:
                df_std = mod_versions[ver]
                break
        standard_body = set()
        if df_std is not None and process:
            if modality in ('CT', 'MR'):
                mask = (df_std['scan_name'].isin(process)
                        | df_std['post_processing_name'].isin(process))
            elif modality == 'DR':
                mask = df_std['position_name'].isin(process)
            else:
                mask = pd.Series([False] * len(df_std))
            matched = df_std[mask]
            standard_body = set(matched['three_level_name'].tolist())
        versions = VERSION_FALLBACK.get(version, [version])
        for ver in versions:
            df_1 = self.data_loader.df_body_disamb.query(
                f'modality=="{modality}" and version=="{ver}"')
            if not df_1.empty:
                for _, row in df_1.iterrows():
                    if row['src_process'] in process:
                        standard_body.add(row['src_body'])
                break
        standard_body.discard('非指定部位')
        return standard_body

    def db_get_default_process(self, modality: str, version: str,
                               body: list) -> list:
        """根据部位查询默认摆位"""
        versions = VERSION_FALLBACK.get(version, [version])
        df_1 = pd.DataFrame()
        for ver in versions:
            df_1 = self.data_loader.df_body_disamb.query(
                f'src_process=="" and modality=="{modality}" and version=="{ver}"')
            if not df_1.empty:
                break
        for _, row in df_1.iterrows():
            if row['dst_body'] in body:
                return [row['dst_process']]
        return ['正、侧位']

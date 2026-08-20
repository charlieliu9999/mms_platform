"""
标准查表服务 — Pipeline Step 9/10
"""
import re
from typing import Dict, List, Optional, Set, Tuple, TYPE_CHECKING

import pandas as pd

from .constants import (
    POSITION_CONTAINS,
    POSITION_DECOMPOSE,
    POSITION_FALLBACK,
    VERSION_FALLBACK,
)
from .match_node import MatchNode

if TYPE_CHECKING:
    from .data_loader import RuleDataLoader
    from .disambiguation_service import DisambiguationService


# 部位等价映射表 (P2修复：统一引擎归一化与标准库命名差异)
BODY_PART_EQUIVALENTS = {
    "盆腔及盆底结构": ["盆腔及盆底结构", "盆腔"],
    "盆腔": ["盆腔", "盆腔及盆底结构"],
    "四肢及关节": ["四肢及关节", "四肢", "关节"],
    "四肢": ["四肢", "四肢及关节"],
    "关节": ["关节", "四肢及关节"],
    "颅脑": ["颅脑", "脑", "头颅"],
    "脑": ["脑", "颅脑"],
    "全腹部": ["全腹部", "腹部"],
    "腹部": ["腹部", "全腹部"],
}

# Phase 2: 部位层级映射表（子部位→父部位）
BODY_HIERARCHY_MAP = {
    # 消化系统
    "小肠": "全腹部",
    "十二指肠": "全腹部",
    "空肠": "全腹部",
    "回肠": "全腹部",
    "结肠": "全腹部",
    "乙状结肠": "全腹部",
    "直肠": "盆腔",
    # 泌尿系统
    "膀胱": "盆腔",
    "前列腺": "盆腔",
    "子宫": "盆腔",
    "卵巢": "盆腔",
    # 头颈部
    "眼部": "头颅",
    "眼眶": "头颅",
    "鼻": "头颅",
    "鼻腔": "头颅",
    "鼻窦": "头颅",
    "喉": "颈部",
    "咽": "颈部",
    # 关节细分
    "双肩关节": "四肢及关节",
    "双肘关节": "四肢及关节",
    "双腕关节": "四肢及关节",
    "双髋关节": "四肢及关节",
    "双膝关节": "四肢及关节",
    "双踝关节": "四肢及关节",
    # 脊髓 → 全脊柱（"脊柱脊髓"/"脑部及脊髓"等输入，脊髓无独立标准项，
    # 回退到全脊柱项；MR全脊柱(平扫/增强/平扫+增强) 均存在）
    "脊髓": "全脊柱",
}

# Phase 2: 扫描方式模糊映射（特殊序列→基础扫描）
SCAN_FUZZY_MAP = {
    # MR特殊序列→基础扫描
    "体素内非相干运动弥散成像(IVIM)": "平扫",
    "液体衰减反转恢复序列(FLAIR)": "平扫",
    "短时反转恢复序列(STIR)": "平扫",
    "双反转恢复序列(DIR)": "平扫",
    "Haste序列": "平扫",
    "Trufi序列": "平扫",
    "3D-FLAIR序列": "平扫",
    "T2WI": "平扫",
    "T1WI": "平扫",
    # CT/MR动态扫描→增强
    "动态增强": "增强",
    "动态对比增强(DCE-MRI)": "增强",
    "多期增强": "增强",
    # 造影类型→关节造影/平扫
    "直接造影": "关节造影",
}

# Phase 4: 泛指词汇模糊匹配表（泛指→匹配模式）
# 用户使用泛指词汇（"关节"、"骨骼"），标准库存储具体部位
# 通过LIKE模糊匹配返回常见项，tier=degraded
GENERIC_TERM_PATTERNS = {
    # 关节类泛指
    "关节": "%关节%",
    "四肢及关节": "%关节%",  # "关节"被消歧为"四肢及关节"
    "肩关节": "%肩关节%",
    "肘关节": "%肘关节%",
    "腕关节": "%腕关节%",
    "髋关节": "%髋关节%",
    "膝关节": "%膝关节%",
    "踝关节": "%踝关节%",

    # 骨骼类泛指
    "骨骼": "%骨%",
    "骨": "%骨%",

    # 血管类泛指（节段性）
    "脊髓动脉": "%脊髓动脉%",
    "脊髓静脉": "%脊髓静脉%",

    # 脊柱节段泛指
    "脊柱": "%脊柱%",
    "椎体": "%椎%",
}

# Phase P: 血管部位 → 标准库部位映射（"部位+血管"输入命中具体动脉/静脉标准项）
VESSEL_BODY_MAP = {
    "小肠血管": "肠系膜上动脉",
    "肝脏血管": "上腹部动脉",
    "肝血管": "上腹部动脉",
    "大血管": "主动脉",
}

# Phase P: 血管部位通用回退集合（无独立标准项时回退到通用动脉/静脉项，degraded）
VESSEL_GENERIC_FALLBACK = frozenset({
    "上腔静脉", "全腹部动脉", "脊髓血管", "脊髓动脉", "胸腰段脊髓动脉",
    "颈段脊髓动脉", "胸段脊髓动脉", "腰段脊髓动脉",
    "全脑血管", "头部血管", "颅内血管", "动静脉", "血管",
})

# Phase P: 区域部位 + 血管扫描 → 通用血管项回退（如 盆腔+CTA → CT动脉血管成像(CTA)）
VESSEL_REGION_FALLBACK = frozenset({
    "盆腔", "腹部", "全腹部", "腹盆", "胸部", "四肢", "外周",
    "头颈部", "颈部", "全身", "下肢", "上肢",
})

# Phase P: 动静脉合并扫描分解（组合扫描 → 动脉+静脉两路查询）
VESSEL_COMBINED_SCAN = {
    "动静脉血管成像(CTA+CTV)": ["动脉血管成像(CTA)", "静脉血管成像(CTV)"],
    "动静脉血管成像(MRA+MRV)": ["动脉血管成像(MRA)", "静脉血管成像(MRV)"],
    "动静脉血管增强成像(CE-MRA+CE-MRV)": [
        "动脉血管增强成像(CE-MRA)", "静脉血管增强成像(CE-MRV)"],
}

# Phase P: 部位无关扫描（标准项部位为"非指定部位"，任意部位输入均命中，degraded）
BODY_AGNOSTIC_SCANS = frozenset({
    "磁共振弹性成像(MRE)",
})


class StandardLookupService:
    """
    Step 9: 补充默认处理方式
    Step 10: 查标准表输出标准编码
    """

    def __init__(self, data_loader: 'RuleDataLoader',
                 disamb_service: 'DisambiguationService'):
        self.data_loader = data_loader
        self.disamb_service = disamb_service

    @staticmethod
    def _expand_body_equivalents(bodies: List[str]) -> List[str]:
        """
        扩展部位列表，包含所有等价名称 (P2修复)

        Args:
            bodies: 原始部位列表

        Returns:
            扩展后的部位列表（去重）
        """
        expanded = set(bodies)  # 保留原始名称
        for body in bodies:
            if body in BODY_PART_EQUIVALENTS:
                expanded.update(BODY_PART_EQUIVALENTS[body])
        return list(expanded)

    @staticmethod
    def _resolve_default_branch(value: str) -> List[str]:
        """
        解析 '|' 和 '&' 语义：
        - '|' 分隔候选项
        - '&' 后是默认分支（未指定时的首选）

        例如：
        - "左上肢|右上肢&双上肢" → ["双上肢"]（取&后默认）
        - "左膝关节|右膝关节" → ["左膝关节", "右膝关节"]（无&，全取）
        - "双侧膝关节" → ["双侧膝关节"]（无特殊符号）

        医学语义：未明确指定左/右时，默认双侧是正确的（避免漏诊）
        """
        if '&' in value:
            # 有默认分支标记，只取 & 后的值
            return [value.split('&')[-1]]
        else:
            # 无默认标记，按 | 拆分所有候选
            return value.split('|')

    @staticmethod
    def _expand_scan_abbreviation(scan: str) -> str:
        """
        展开扫描方式缩写为标准全称
        用于扫描组合降级匹配（P1优化）
        """
        # 扫描方式缩写映射表
        abbreviation_map = {
            'DWI': '弥散加权成像(DWI)',
            'DCE': '动态对比增强(DCE-MRI)',
            'CTU': '尿路造影成像(CTU)',
            'MRS': '磁共振波谱(MRS)',
            'PWI': '灌注加权成像(PWI)',
            'SWI': '磁敏感加权成像(SWI)',
            'FLAIR': '液体衰减反转恢复序列(FLAIR)',
            'MRA': '磁共振血管成像(MRA)',
            'MRV': '磁共振静脉成像(MRV)',
            'CTA': 'CT血管成像(CTA)',
            'CTV': 'CT静脉成像(CTV)',
        }
        return abbreviation_map.get(scan, scan)

    def _supplement_base_scans(self, df_std: pd.DataFrame, 
                               bodies: List[str], 
                               scans: List[str],
                               post_processing: List[str],
                               dup_set: Set[str]) -> List[Tuple[str, str]]:
        """
        修复4: 为后处理项补充基础扫描项
        
        当匹配结果中包含后处理项（三维重建/MPR等）时，自动补充对应的
        基础扫描项（平扫/增强）。例如：
        - CT胸部+腹部+盆腔三维重建 → 补充 CT胸部平扫 + CT腹部平扫 + CT盆腔平扫
        - CT全腹部(平扫)+CT三维重建 → 补充 CT全腹部平扫
        
        Args:
            df_std: 标准表DataFrame
            bodies: 部位列表
            scans: 扫描方式列表（平扫/增强等）
            post_processing: 后处理方式列表（三维重建/MPR等）
            dup_set: 已匹配项集合（用于去重）
        
        Returns:
            [(标准项名称, 标准项编码), ...]
        """
        results = []
        
        # 只有在有后处理项时才补充
        if not post_processing:
            return results
        
        # 如果没有明确的扫描方式，默认使用平扫
        # 这是因为后处理（三维重建等）通常是基于平扫图像的
        scan_list = scans if scans else ['平扫']
        
        # 展开部位等价名称
        bodies_expanded = self._expand_body_equivalents(bodies) if bodies else []
        
        # 查询对应的基础扫描项（无后处理）
        for scan in scan_list:
            mask = (
                df_std['three_level_name'].isin(bodies_expanded) &
                df_std['scan_name'].isin([scan]) &
                ((df_std['post_processing_name'] == '') | df_std['post_processing_name'].isna())
            )
            matches = df_std[mask]
            
            for _, row in matches.iterrows():
                name = row['checkitem_name']
                code = row['checkitem_code']
                
                # 跳过已存在的项
                if name not in dup_set:
                    results.append((name, code))
        
        return results

    # ─── Step 9: 补充默认处理方式 ──────────────────────────────────────────

    def find_default_process(self, childrens: List[MatchNode],
                             process_type: str, modality: str,
                             version: str) -> List[MatchNode]:
        for node in childrens:
            if node.pos_dict.get(process_type) or not node.pos_dict.get('body'):
                continue
            if modality != 'DR' and node.pos_dict.get('post'):
                continue

            body = node.std_names[node.pos_dict['body'][0]]
            dst = self.disamb_service.lookup_disambiguity(
                body, "", modality, version)
            if dst:
                node.std_names[node.pos_dict['body'][0]] = dst[0]
                node.add_entity(" ", process_type, dst[1])
            else:
                default = '平扫' if modality in ('CT', 'MR') else '正位'
                node.add_entity(" ", process_type, default)
            # 处理方式为推断补充（非原文显式指定）→ 部位命中档
            node.fill_default = True

        return childrens

    # ─── Step 10: 查标准表 ─────────────────────────────────────────────────

    def lookup_standard(self, childrens: List[MatchNode],
                        query_fields: dict, process_type: str,
                        modality: str, version: str):
        df_std = None
        mod_versions = self.data_loader.df_standard.get(modality, {})

        # 版本查找：忽略大小写
        for ver in VERSION_FALLBACK.get(version, [version]):
            # 尝试原始版本
            if ver in mod_versions:
                df_std = mod_versions[ver]
                break
            # 尝试小写版本（兼容 v3.8.2 vs V3.8.2）
            ver_lower = ver.lower()
            if ver_lower in mod_versions:
                df_std = mod_versions[ver_lower]
                break

        if df_std is None:
            return
        dup_set: Set[str] = set()

        for node in childrens:
            bodies = []
            for i in node.pos_dict.get('body', []):
                bodies += self._resolve_default_branch(node.std_names[i])
            bodies = sorted(set(bodies))

            # Phase 4: 泛指词汇检测
            # 场景1: bodies为空，检查原始文本是否包含泛指关键词
            # 场景2: bodies包含"四肢及关节"等泛指部位，也触发模糊匹配
            generic_bodies_to_add = []

            # 检查已有bodies中是否有泛指词汇
            for body in bodies:
                if body in GENERIC_TERM_PATTERNS:
                    generic_bodies_to_add.append(body)

            # 如果bodies为空，从原始文本中查找
            if not bodies and node.raw_str:
                raw_text = node.raw_str
                for generic_term in GENERIC_TERM_PATTERNS.keys():
                    if generic_term in raw_text:
                        generic_bodies_to_add.append(generic_term)
                        break  # 只添加第一个匹配的泛指词汇

            # 将泛指词汇添加到bodies（如果还没有的话）
            for generic_body in generic_bodies_to_add:
                if generic_body not in bodies:
                    bodies.append(generic_body)

            process_vals = []
            for i in node.pos_dict.get(process_type, []):
                val = node.std_names[i]
                if '&' in val:
                    process_vals.append(val.split('&')[-1])
                else:
                    process_vals += val.split('|')
            process_vals = sorted(set(process_vals))

            post_vals = []
            if process_type != 'post':
                for i in node.pos_dict.get('post', []):
                    post_vals += node.std_names[i].split('|')
            post_vals = sorted(set(post_vals))

            position_vals = []
            if modality in ('MG', 'DR'):  # DR 也需要使用 position
                for i in node.pos_dict.get('position', []):
                    position_vals += node.std_names[i].split('|')
                position_vals = sorted(set(position_vals))

            # DR 扫描方式值（无体位标准项回退用，如 DR骨密度测定）
            scan_vals = []
            if modality == 'DR':
                for i in node.pos_dict.get('scan', []):
                    scan_vals += node.std_names[i].split('|')
                scan_vals = sorted(set(scan_vals))

            candidates, degraded = self._query_standard_table(
                df_std, modality, bodies, process_type,
                process_vals, post_vals, position_vals, scan_vals)
            if degraded:
                node.degraded = True

            candidate_hits = 0
            for _, row in candidates.iterrows():
                name = row['checkitem_name']
                code = row['checkitem_code']
                
                # 修复1: 过滤跨模态标准项（数据质量问题防御）
                # 检查标准项名称前缀是否与查询模态一致
                # 例如：MR查询不应返回"CT全脊柱"这样的项目
                name_upper = name.upper().replace('*', '').strip()
                
                # 提取标准项名称的模态前缀
                item_modality_prefix = None
                for mod_prefix in ['CT', 'MR', 'DR', 'DSA', 'MG', 'RF', 'US', 'SPECT', 'PET']:
                    if name_upper.startswith(mod_prefix):
                        item_modality_prefix = mod_prefix
                        break
                
                # 如果标准项有明确的模态前缀，且与查询模态不匹配，则跳过
                if item_modality_prefix and item_modality_prefix != modality.upper():
                    continue
                
                if name in dup_set:
                    candidate_hits += 1
                    continue
                dup_set.add(name)
                candidate_hits += 1
                node.standard_check_name.append(name)
                node.standard_check_code.append(code)
            # 该节点所有候选均被其他节点去重覆盖（如"颞骨及头颈部血管"的
            # 头颈部动脉+三维重建影子节点）：语义已由组合结果覆盖，不算未匹配。
            if not node.standard_check_name and candidate_hits:
                node.dup_only = True
            
            # 修复4: CT/MR后处理项补充基础扫描
            # 当匹配到后处理项（三维重建/MPR等）且有明确部位时，
            # 自动补充对应的基础扫描项（平扫/增强）
            # 如果没有明确扫描方式，默认补充平扫
            if modality in ('CT', 'MR') and post_vals and bodies:
                base_scans = self._supplement_base_scans(
                    df_std, bodies, process_vals, post_vals, dup_set)
                for name, code in base_scans:
                    if name not in dup_set:
                        dup_set.add(name)
                        node.standard_check_name.append(name)
                        node.standard_check_code.append(code)

    def _query_standard_table(self, df: pd.DataFrame, modality: str,
                              bodies: List[str], process_type: str,
                              process_vals: List[str],
                              post_vals: List[str],
                              position_vals: List[str] = None,
                              scan_vals: List[str] = None
                              ) -> Tuple[pd.DataFrame, bool]:
        """返回 (候选 DataFrame, 是否走了降级查询分支)"""
        scan_vals = scan_vals or []
        if not bodies:
            if modality in ('CT', 'MR') and (process_vals or post_vals):
                return self._query_ct_mr(df, bodies, process_vals, post_vals)
            # DR 无部位输入：按扫描方式回退（覆盖无体位标准项，如 DR骨密度测定）
            if modality == 'DR' and scan_vals:
                return self._query_dr_scan(df, scan_vals)
            return pd.DataFrame(), False

        if modality in ('CT', 'MR'):
            return self._query_ct_mr(df, bodies, process_vals, post_vals)
        elif modality in ('RF', 'MG'):
            return self._query_rf_mg(
                df, bodies, process_vals, modality, position_vals)
        elif modality == 'DR':
            # DR 使用 position_vals，不是 process_vals；scan_vals 作无体位回退
            return self._query_dr(df, bodies, position_vals or [], scan_vals)
        else:
            return pd.DataFrame(), False

    def _query_ct_mr(self, df: pd.DataFrame, bodies: List[str],
                     scan: List[str], post: List[str]
                     ) -> Tuple[pd.DataFrame, bool]:
        results = []
        degraded = False

        # P2修复：扩展部位等价名称（盆腔 ↔ 盆腔及盆底结构）
        bodies_expanded = self._expand_body_equivalents(bodies) if bodies else []

        # Phase P: 血管部位映射（小肠血管→肠系膜上动脉、肝脏血管→上腹部动脉等）
        mapped_bodies = []
        for b in bodies_expanded:
            mapped_bodies.append(VESSEL_BODY_MAP.get(b, b))
        bodies_expanded = list(dict.fromkeys(mapped_bodies)) or bodies_expanded

        # Phase P: 动静脉合并扫描分解（动静脉血管成像(CTA+CTV) → 动脉/静脉两路）
        decomposed_scan = []
        for s in scan:
            decomposed_scan.extend(VESSEL_COMBINED_SCAN.get(s, [s]))
        scan = list(dict.fromkeys(decomposed_scan))

        # Phase P: 部位无关扫描（磁共振弹性成像(MRE) 等 → 非指定部位降级命中）
        agnostic_scan = [s for s in scan if s in BODY_AGNOSTIC_SCANS]
        if agnostic_scan:
            mask = (
                df['three_level_name'].isin(['非指定部位', '无部位']) &
                df['scan_name'].isin(agnostic_scan) &
                ((df['post_processing_name'] == '') | df['post_processing_name'].isna())
            )
            hit = df[mask]
            if not hit.empty:
                degraded = True
                results.append(hit)
            # 部位无关扫描不再参与常规部位查询，避免 body 不匹配残留
            scan = [s for s in scan if s not in BODY_AGNOSTIC_SCANS]

        if post:
            mask = (
                df['three_level_name'].isin(bodies_expanded) &
                df['scan_name'].isin(scan) &
                df['post_processing_name'].isin(post)
            )
            results.append(df[mask])

        if scan:
            mask = (
                df['three_level_name'].isin(bodies_expanded) &
                df['scan_name'].isin(scan) &
                ((df['post_processing_name'] == '') | df['post_processing_name'].isna())
            )
            results.append(df[mask])

        # 以下为无部位/非指定部位的降级分支
        if post:
            mask = (
                df['three_level_name'].isin(['非指定部位', '无部位']) &
                (df['scan_name'] == '') &
                df['post_processing_name'].isin(post)
            )
            hit = df[mask]
            if not hit.empty:
                degraded = True
            results.append(hit)

        if not bodies and scan:
            mask = (
                df['three_level_name'].isin(['非指定部位', '无部位']) &
                df['scan_name'].isin(scan) &
                ((df['post_processing_name'] == '') | df['post_processing_name'].isna())
            )
            hit = df[mask]
            if not hit.empty:
                degraded = True
            results.append(hit)

        # P1优化：扫描组合降级（平扫+DWI → 平扫 + DWI）
        # 当精确匹配为空且 scan 包含组合值（含'+'）时，拆分降级匹配
        # 注意：results 可能包含空 DataFrame，需要检查是否有实际命中
        has_match = any(not r.empty for r in results)
        if not has_match and scan and bodies:
            for scan_str in scan:
                if '+' in scan_str:
                    # 拆分组合：'平扫+DWI' → ['平扫', 'DWI']
                    components = [c.strip() for c in scan_str.split('+')]
                    # 展开缩写
                    expanded_components = []
                    for comp in components:
                        expanded = self._expand_scan_abbreviation(comp)
                        expanded_components.append(expanded)

                    # 降级查询：用分量匹配
                    mask = (
                        df['three_level_name'].isin(bodies) &
                        df['scan_name'].isin(expanded_components) &
                        ((df['post_processing_name'] == '') | df['post_processing_name'].isna())
                    )
                    hit = df[mask]
                    if not hit.empty:
                        degraded = True
                        results.append(hit)
                        has_match = True

        # Phase 2 Level 2: 部位层级映射（小肠→全腹部）
        if not has_match and scan and bodies:
            bodies_with_hierarchy = set(bodies_expanded)
            for body in bodies:
                if body in BODY_HIERARCHY_MAP:
                    parent_body = BODY_HIERARCHY_MAP[body]
                    bodies_with_hierarchy.update(self._expand_body_equivalents([parent_body]))
            
            if len(bodies_with_hierarchy) > len(bodies_expanded):
                mask = (
                    df['three_level_name'].isin(list(bodies_with_hierarchy)) &
                    df['scan_name'].isin(scan) &
                    ((df['post_processing_name'] == '') | df['post_processing_name'].isna())
                )
                hit = df[mask]
                if not hit.empty:
                    degraded = True
                    results.append(hit)
                    has_match = True
        
        # Phase 2 Level 3: 扫描方式模糊匹配（特殊序列→基础扫描）
        if not has_match and scan and bodies:
            fuzzy_scans = set(scan)
            for s in scan:
                if s in SCAN_FUZZY_MAP:
                    fuzzy_scans.add(SCAN_FUZZY_MAP[s])

            if len(fuzzy_scans) > len(scan):
                # 同时使用部位层级映射
                bodies_with_hierarchy = set(bodies_expanded)
                for body in bodies:
                    if body in BODY_HIERARCHY_MAP:
                        parent_body = BODY_HIERARCHY_MAP[body]
                        bodies_with_hierarchy.update(self._expand_body_equivalents([parent_body]))

                mask = (
                    df['three_level_name'].isin(list(bodies_with_hierarchy)) &
                    df['scan_name'].isin(list(fuzzy_scans)) &
                    ((df['post_processing_name'] == '') | df['post_processing_name'].isna())
                )
                hit = df[mask]
                if not hit.empty:
                    degraded = True
                    results.append(hit)

        # Phase 4: 泛指词汇模糊匹配（泛指→具体部位）
        # 场景1: bodies列表包含泛指词汇（如分词器识别出"关节"）
        # 场景2: bodies列表为空，但原始文本包含泛指关键词
        if not has_match and scan:
            # 收集所有泛指词汇（来自bodies或原始文本）
            generic_terms_found = []

            # 从bodies中查找
            for body in bodies:
                if body in GENERIC_TERM_PATTERNS:
                    generic_terms_found.append(body)

            # 如果bodies为空或没找到泛指词，检查原始文本
            # 注意：这里需要从调用者传入原始文本，暂时先处理bodies不为空的情况
            # TODO: 考虑将raw_text作为参数传入

            # 对每个泛指词汇进行模糊匹配
            for generic_term in generic_terms_found:
                pattern = GENERIC_TERM_PATTERNS[generic_term]
                # 使用str.contains进行模糊匹配
                # 移除pattern中的%通配符，使用pandas的contains
                search_term = pattern.replace('%', '')
                mask = (
                    df['three_level_name'].str.contains(search_term, na=False, regex=False) &
                    df['scan_name'].isin(scan) &
                    ((df['post_processing_name'] == '') | df['post_processing_name'].isna())
                )
                hit = df[mask]
                if not hit.empty:
                    degraded = True
                    results.append(hit)
                    has_match = True

        # Phase P: 血管部位通用回退（具体血管部位/区域无标准项时回退通用动脉/静脉项）。
        # 条件：扫描方式是血管成像，且当前结果中没有命中任何血管扫描标准项
        # （即使已命中后处理项如"三维重建"，仍补充通用血管项，避免组合项目缺血管件）。
        vessel_scan = [
            s for s in scan
            if any(k in s for k in ('血管成像', '血管增强'))
        ]
        is_vessel_body = any(
            b in VESSEL_GENERIC_FALLBACK
            or b.endswith(('动脉', '静脉', '血管'))
            or b in VESSEL_REGION_FALLBACK
            for b in bodies_expanded
        )
        if is_vessel_body and vessel_scan:
            has_vessel_match = any(
                not r.empty and r['scan_name'].isin(vessel_scan).any()
                for r in results
            )
            if not has_vessel_match:
                mask = (
                    df['three_level_name'].isin(['非指定部位', '无部位']) &
                    df['scan_name'].isin(vessel_scan) &
                    ((df['post_processing_name'] == '') | df['post_processing_name'].isna())
                )
                hit = df[mask]
                if not hit.empty:
                    degraded = True
                    results.append(hit)

        if results:
            combined = pd.concat(results).drop_duplicates(subset=['checkitem_name'])
            return combined, degraded
        return pd.DataFrame(), False

    def _query_rf_mg(self, df: pd.DataFrame, bodies: List[str],
                     scan: List[str], modality: str = '',
                     position: List[str] = None) -> Tuple[pd.DataFrame, bool]:
        results = []
        degraded = False
        position = position or []

        # P2修复：先应用部位等价映射
        bodies_with_equiv = self._expand_body_equivalents(bodies) if bodies else bodies

        # 再扩展左右侧
        expanded_bodies = list(bodies_with_equiv)
        for b in bodies_with_equiv:
            for prefix in ('双侧', '左侧', '右侧'):
                expanded_bodies.append(prefix + b)
        expanded_bodies = list(set(expanded_bodies))

        body_mask = df['three_level_name'].isin(expanded_bodies)

        if modality == 'MG' and position:
            mask = body_mask & df['position_name'].isin(position)
            matched = df[mask]
            if not matched.empty:
                return matched.drop_duplicates(subset=['checkitem_name']), False

        # MG 落到 scan 分支说明精确体位匹配（L207）未命中：
        # 要么输入未指定体位，要么指定的体位在标准表中不存在。
        # 两种情况都只应返回无体位的基础项，绝不返回所有体位变体
        # （正侧位/内外侧位…scan 同为"钼靶"仅 position 不同，否则会全部命中）。
        mg_basic_only = modality == 'MG'

        if scan:
            mask = body_mask & df['scan_name'].isin(scan)
            if mg_basic_only:
                mask = mask & (
                    df['position_name'].isna() | (df['position_name'] == ''))
            matched = df[mask]
            if not matched.empty:
                results.append(matched)

        if not results and scan:
            # 模糊包含匹配 → 降级
            for s in scan:
                mask = body_mask & (
                    df['scan_name'].str.contains(s, na=False) |
                    df['scan_name'].apply(lambda x: x in s if x else False))
                if mg_basic_only:
                    mask = mask & (
                        df['position_name'].isna() | (df['position_name'] == ''))
                matched = df[mask]
                if not matched.empty:
                    degraded = True
                    results.append(matched)

        if not results:
            # 仅按部位兜底 → 降级
            matched = df[body_mask]
            if not matched.empty:
                degraded = True
                basic = matched[
                    matched['position_name'].isna() | (matched['position_name'] == '')]
                if not basic.empty:
                    results = [basic]
                else:
                    results = [matched]

        if results:
            combined = pd.concat(results).drop_duplicates(subset=['checkitem_name'])
            return combined, degraded
        return pd.DataFrame(), False

    def _query_dr_scan(self, df: pd.DataFrame,
                       scan: List[str]) -> Tuple[pd.DataFrame, bool]:
        """DR 无体位/无部位输入：按扫描方式回退到无体位标准项。

        覆盖 DR骨密度测定 这类没有 position_name 的标准项（否则永远不可达）。
        """
        if not scan:
            return pd.DataFrame(), False
        mask = (
            (df['position_name'].isna() | (df['position_name'] == '')) &
            df['scan_name'].isin(scan)
        )
        result = df[mask]
        return result.drop_duplicates(subset=['checkitem_name']), True

    def _query_dr(self, df: pd.DataFrame, bodies: List[str],
                  positions: List[str],
                  scan: List[str] = None) -> Tuple[pd.DataFrame, bool]:
        scan = scan or []
        # 设备类型不作为体位参与匹配（如 "移动DR胸部" 的 移动DR 是设备）
        positions = [p for p in positions if p not in ('移动DR', 'DR')]
        # P2修复：扩展部位等价名称
        bodies_expanded = self._expand_body_equivalents(bodies) if bodies else []

        if not positions:
            # 无体位 + 有部位 → 匹配无体位标准项（degraded，如 移动DR胸部）
            if bodies:
                mask = (
                    df['three_level_name'].isin(bodies_expanded) &
                    (df['position_name'].isna() | (df['position_name'] == ''))
                )
                result = df[mask]
                if not result.empty:
                    return result.drop_duplicates(subset=['checkitem_name']), True
            # 无体位 + 无部位 → 按扫描方式回退（如 DR骨密度测定）
            if scan:
                return self._query_dr_scan(df, scan)
            return pd.DataFrame(), False

        all_positions = set(positions)
        for pos in positions:
            if pos in POSITION_FALLBACK:
                all_positions.update(POSITION_FALLBACK[pos])
        all_positions_list = list(all_positions)

        mask = (
            df['three_level_name'].isin(bodies_expanded) &
            df['position_name'].isin(all_positions_list) &
            (df['device_type_name'] == 'DR')
        )
        result = df[mask]
        degraded = False

        if result.empty and bodies:
            # 放开设备类型约束 → 降级
            mask = (
                df['three_level_name'].isin(bodies) &
                df['position_name'].isin(all_positions_list)
            )
            result = df[mask]
            if not result.empty:
                degraded = True

        if result.empty and bodies:
            # 体位分解回退 → 降级
            decomposed = set()
            for pos in positions:
                if pos in POSITION_DECOMPOSE:
                    decomposed.update(POSITION_DECOMPOSE[pos])
                else:
                    decomposed.add(pos)
            if decomposed != set(positions):
                mask = (
                    df['three_level_name'].isin(bodies) &
                    df['position_name'].isin(list(decomposed)) &
                    (df['device_type_name'] == 'DR')
                )
                result = df[mask]
                if result.empty:
                    mask = (
                        df['three_level_name'].isin(bodies) &
                        df['position_name'].isin(list(decomposed))
                    )
                    result = df[mask]
                if not result.empty:
                    degraded = True

        if result.empty and bodies:
            # 体位超集扩展 → 降级
            expanded = set()
            for pos in positions:
                if pos in POSITION_CONTAINS:
                    expanded.update(POSITION_CONTAINS[pos])
            if expanded:
                mask = (
                    df['three_level_name'].isin(bodies) &
                    df['position_name'].isin(list(expanded))
                )
                result = df[mask]
                if not result.empty:
                    degraded = True

        if result.empty and bodies:
            # 左右侧扩展回退 → 降级
            # 输入无左右侧（或默认双侧）时，标准库只有单侧项（如 DR左/右腕关节[骨龄]）
            laterality_bodies = []
            for b in bodies_expanded:
                if b.startswith('双') and len(b) > 1:
                    laterality_bodies.append('左' + b[1:])  # 双腕部 → 左腕部
                    laterality_bodies.append('右' + b[1:])  # 双腕部 → 右腕部
                elif not b.startswith(('左', '右')):
                    laterality_bodies.append(b)
            if laterality_bodies:
                mask = (
                    df['three_level_name'].isin(laterality_bodies) &
                    df['position_name'].isin(all_positions_list)
                )
                result = df[mask]
                if not result.empty:
                    degraded = True

        if result.empty and scan:
            # 无体位标准项按扫描方式回退（degraded）
            return self._query_dr_scan(df, scan)

        return result.drop_duplicates(subset=['checkitem_name']), degraded

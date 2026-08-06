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
        for ver in VERSION_FALLBACK.get(version, [version]):
            if ver in mod_versions:
                df_std = mod_versions[ver]
                break
        if df_std is None:
            return
        dup_set: Set[str] = set()

        for node in childrens:
            bodies = []
            for i in node.pos_dict.get('body', []):
                bodies += self._resolve_default_branch(node.std_names[i])
            bodies = sorted(set(bodies))

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
            if modality == 'MG':
                for i in node.pos_dict.get('position', []):
                    position_vals += node.std_names[i].split('|')
                position_vals = sorted(set(position_vals))

            candidates, degraded = self._query_standard_table(
                df_std, modality, bodies, process_type,
                process_vals, post_vals, position_vals)
            if degraded:
                node.degraded = True

            for _, row in candidates.iterrows():
                name = row['checkitem_name']
                code = row['checkitem_code']
                if name in dup_set:
                    continue
                dup_set.add(name)
                node.standard_check_name.append(name)
                node.standard_check_code.append(code)

    def _query_standard_table(self, df: pd.DataFrame, modality: str,
                              bodies: List[str], process_type: str,
                              process_vals: List[str],
                              post_vals: List[str],
                              position_vals: List[str] = None
                              ) -> Tuple[pd.DataFrame, bool]:
        """返回 (候选 DataFrame, 是否走了降级查询分支)"""
        if not bodies:
            if modality in ('CT', 'MR') and (process_vals or post_vals):
                return self._query_ct_mr(df, bodies, process_vals, post_vals)
            return pd.DataFrame(), False

        if modality in ('CT', 'MR'):
            return self._query_ct_mr(df, bodies, process_vals, post_vals)
        elif modality in ('RF', 'MG'):
            return self._query_rf_mg(
                df, bodies, process_vals, modality, position_vals)
        elif modality == 'DR':
            return self._query_dr(df, bodies, process_vals)
        else:
            return pd.DataFrame(), False

    def _query_ct_mr(self, df: pd.DataFrame, bodies: List[str],
                     scan: List[str], post: List[str]
                     ) -> Tuple[pd.DataFrame, bool]:
        results = []
        degraded = False

        if post:
            mask = (
                df['three_level_name'].isin(bodies) &
                df['scan_name'].isin(scan) &
                df['post_processing_name'].isin(post)
            )
            results.append(df[mask])

        if scan:
            mask = (
                df['three_level_name'].isin(bodies) &
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

        expanded_bodies = list(bodies)
        for b in bodies:
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

    def _query_dr(self, df: pd.DataFrame, bodies: List[str],
                  positions: List[str]) -> Tuple[pd.DataFrame, bool]:
        if not positions:
            return pd.DataFrame(), False

        all_positions = set(positions)
        for pos in positions:
            if pos in POSITION_FALLBACK:
                all_positions.update(POSITION_FALLBACK[pos])
        all_positions_list = list(all_positions)

        mask = (
            df['three_level_name'].isin(bodies) &
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

        return result.drop_duplicates(subset=['checkitem_name']), degraded

"""
匹配引擎协调器 — 统一入口（策略模式）

对外提供统一的 match() / batch_match() 接口，内部按模态自动分派：
- CT/MR/DR/RF/MG → 10 步 NLP Pipeline（结构化分词+消歧+查表）
- US/SPECT/PET/CT/PET/MR → 关键词引擎（专用规则匹配，委托 us_spect_pet_matcher）

两套底层引擎各司其职：NLP pipeline 为 CT/MR 的"部位+扫描+后处理"维度设计，
关键词引擎为 US/PET/SPECT 的"器官+扫描方式/显像方式"维度设计，字段语义不同故不可合并。
"""
import asyncio
import logging
import re
from typing import Dict, List, Tuple

from sqlalchemy.ext.asyncio import AsyncEngine

from .constants import SPECIAL_ITEM_MARKERS
from ..modality_resolver import infer_text_modality
from ..catalog_policy import (
    SPECT_PELVIS_POLICY, SPECT_PELVIS_STANDARD_NAME, spect_pelvis_bone_only,
)
from .data_loader import RuleDataLoader, normalize_standard_name
from .disambiguation_service import DisambiguationService
from .dr_splitter import DRSplitter
from .pattern_processor import PatternProcessor
from .preprocess_service import PreprocessService
from .standard_lookup_service import StandardLookupService
from .tokenizer_service import TokenizerService

logger = logging.getLogger(__name__)


def _empty_result(record: str, tier: str = 'none', reason: str = '',
                  has_entity=None) -> dict:
    return {'check_item': record, 'num_standard': 0, 'data': [],
            'score': 0, 'tier': tier, 'confidence': 0.0, 'reason': reason,
            'has_entity': has_entity}


# 置信度四档 → 数值（0.0-1.0），供 ACRStandardLink.confidence 持久化
# exact: 部位+处理方式均显式命中；partial: 处理方式为默认推断（部位命中）；
# degraded: 查表走了模糊/回退分支；ambiguous: 输入含无法解析的剩余内容
# error: 引擎异常（区别于 none 的"真未命中"，供未匹配原因分类）
TIER_CONFIDENCE = {
    'exact': 1.0,
    'partial': 0.8,
    'degraded': 0.6,
    'ambiguous': 0.4,
    'none': 0.0,
    'error': 0.0,
}

# 医学维度词性：实体归入其一才算"解析出有效医学实体"。
# 分词器对任意 token（含噪声）都会建 entitys 节点（pattern='U'），
# 因此判"是否解析出实体"须看是否落入这些维度，而非 entitys 是否非空。
_MEDICAL_POS = ('body', 'scan', 'post', 'position')


class MatchEngineOrchestrator:
    """
    匹配引擎协调器（统一入口）

    组装各个服务，提供统一的 match() 和 batch_match() 接口。
    内部按模态策略分派到 NLP pipeline 或关键词引擎。
    """

    # NLP pipeline 处理的模态（CT/MR 的"部位+扫描+后处理"维度）
    NLP_MODALITIES = frozenset({'CT', 'MR', 'DR', 'RF', 'MG'})
    # 关键词引擎处理的模态（US/PET/SPECT/OCT/DSA 的"器官+扫描方式/显像方式"维度）
    KW_MODALITIES = frozenset({'US', 'SPECT', 'PET/CT', 'PET/MR', 'OCT', 'DSA'})
    SUPPORTED_MODALITIES = NLP_MODALITIES | KW_MODALITIES

    UNMATCHABLE_MARKERS = tuple(SPECIAL_ITEM_MARKERS.keys())

    def __init__(self, engine: AsyncEngine, kw_matcher_factory=None):
        """
        Args:
            engine: 异步数据库引擎，透传给数据层与关键词引擎
            kw_matcher_factory: 可选的关键词引擎工厂，签名为
                ``async (engine) -> matcher``。缺省时回退到宿主
                ``app.services.check_item_mgmt.us_spect_pet_matcher``。
                独立部署（MMS）时由外部注入，使本包不依赖 app.* 包路径。
        """
        self.engine = engine
        self._kw_matcher_factory = kw_matcher_factory
        self.data_loader: RuleDataLoader = RuleDataLoader(engine)
        self.preprocess_service: PreprocessService = None
        self.tokenizer_service: TokenizerService = None
        self.pattern_processor: PatternProcessor = None
        self.disamb_service: DisambiguationService = None
        self.lookup_service: StandardLookupService = None
        # DR 复合项目拆分器
        self.dr_splitter: DRSplitter = DRSplitter()
        # 关键词引擎（US/SPECT/PET），懒加载避免循环导入
        self._kw_matcher = None
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def initialize(self):
        """初始化所有服务（支持热重载：重复调用时加锁并原子替换）"""
        async with self._init_lock:
            # C3 修复：热重载时清除旧 tokenizer 缓存，避免返回过期映射
            if self.tokenizer_service is not None:
                self.tokenizer_service.clear_cache()

            await self.data_loader.initialize()

            self.preprocess_service = PreprocessService(self.data_loader.pre_rules)
            self.tokenizer_service = TokenizerService(
                self.data_loader.mdict,
                self.data_loader.common_normal,
                self.data_loader.normal_rules
            )
            self.pattern_processor = PatternProcessor(self.data_loader)
            self.disamb_service = DisambiguationService(self.data_loader)
            self.lookup_service = StandardLookupService(
                self.data_loader, self.disamb_service)

            # Phase 7: 预加载使用统计（用于智能排序）
            self.usage_stats_cache = await self._load_all_usage_stats()

            # 关键词引擎（US/SPECT/PET/OCT/DSA），透传本引擎的 DB engine
            factory = self._kw_matcher_factory
            if factory is None:
                from match_service.engine.keyword.us_spect_pet_matcher import (
                    USSpectPetMatcher,
                )
                self._kw_matcher = USSpectPetMatcher(engine=self.engine)
                await self._kw_matcher.initialize()
            else:
                self._kw_matcher = await factory(engine=self.engine)

            self._initialized = True
            logger.info("[MatchEngineV2] 初始化完成 (NLP + 关键词引擎)")

    @property
    def is_ready(self) -> bool:
        return self._initialized

    def _check_unmatchable(self, record: str, modality: str):
        """统一 unmatchable 守卫（收敛原分散在 match/batch 两处的检查）。

        Returns:
            (is_unmatchable, reason_code)
            - reason_code 命中时为 SPECIAL_ITEM_MARKERS 的标识（如 biopsy/intervention），
              供未匹配原因分类（Phase 1）使用；未命中为 ''。

        注：
        - Phase 1 改进：所有模态都检查 unmatchable 标记
        - NLP 模态（CT/MR/DR/RF/MG）：检查所有标记
        - 关键词引擎模态（US/SPECT/PET/OCT/DSA）：仅检查非影像、口腔、内镜标记
        - 不支持模态（XR/CBCT/ES/SURG等）：检查所有标记
        """
        # 非影像检查标记（适用于所有模态）
        NON_IMAGING_MARKERS = {
            'non_imaging', 'dental', 'endoscopy', 'surgery'
        }

        # 检查所有标记
        for marker in self.UNMATCHABLE_MARKERS:
            if marker in record:
                reason = SPECIAL_ITEM_MARKERS[marker]

                # NLP 模态：所有标记都拦截
                if modality in self.NLP_MODALITIES:
                    return True, reason

                # 关键词引擎模态：仅拦截非影像类标记 + DSA的介入标记
                if modality in self.KW_MODALITIES:
                    if modality == 'DSA' and reason in {'intervention', 'surgery'}:
                        return True, 'excluded_intervention'
                    # "手术区域皮肤超声"描述的是检查部位，并非手术操作；US 的
                    # surgery 宽词交给关键词引擎按实际部位继续判断。
                    if modality == 'US' and reason == 'surgery':
                        continue
                    if reason in NON_IMAGING_MARKERS:
                        return True, 'excluded_non_imaging'
                    # 其他标记（如 biopsy, radiotherapy）跳过，让引擎处理
                    continue

                # 不支持模态（XR/CBCT/ES/SURG等）：所有标记都拦截
                # 这样可以识别出这些模态中的非影像检查
                if modality not in self.SUPPORTED_MODALITIES:
                    return True, reason

        return False, ''

    @staticmethod
    def _normalize_unmatchable_reason(reason: str) -> str:
        """把 NLP 标记名归一为评估侧统一的排除原因码。

        ``_check_unmatchable`` 对 NLP 模态返回的是 ``SPECIAL_ITEM_MARKERS``
        里的标记值（intervention/non_imaging/biopsy/...），而关键词引擎与评估
        侧用的是 ``excluded_intervention`` / ``excluded_non_imaging``。
        不归一会导致治疗性介入项目被误报为 ``unmatchable_by_design``，
        影响排除清单的业务核对（两者虽同在范围外，但语义不同）。
        """
        return {
            'intervention': 'excluded_intervention',
            'non_imaging': 'excluded_non_imaging',
        }.get(reason, reason)

    def match(self, record: str, modality: str, version: str = "V3.8.2",
              trace: dict = None) -> dict:
        """
        匹配单条检查记录（统一入口，内部按模态策略分派）

        Args:
            trace: 传入 dict 时收集 pipeline 各步中间态（legacy debug 字段用）

        Returns:
            {
                'check_item': 原始文本,
                'num_standard': 匹配到的标准项数量,
                'data': [{'raw': ..., 'standard': [{'code': ..., 'name': ...}]}],
                'score': 匹配置信度 0-10
            }
        """
        if not self._initialized:
            return _empty_result(record)

        # This exact procedure is approved to retain only static SPECT bone
        # imaging. Resolve code/version from loaded active standards, never CT.
        if spect_pelvis_bone_only(record):
            result = self._match_exact_standard_name(SPECT_PELVIS_STANDARD_NAME, "SPECT")
            if result is None or not all(
                standard.get("version")
                for block in result.get("data", [])
                for standard in block.get("standard", [])
            ):
                result = _empty_result(record, reason="standard_lib_gap")
            result.update({
                "check_item": record, "engine": "procedure_business_policy",
                "business_policy": SPECT_PELVIS_POLICY,
                "excluded_components": [{"modality": "CT", "name": "CT平扫",
                                         "reason": "user_approved_spect_only"}],
                "source_modality": modality, "effective_modality": "SPECT",
                "modality_routed": modality != "SPECT",
            })
            for block in result.get("data", []):
                block["raw"] = record
            if trace is not None:
                trace["op"] = [SPECT_PELVIS_POLICY]
            return result

        # Phase 3A: DR→MG强制路由检查（修复乳腺检查路由）
        # 必须在所有匹配逻辑之前执行，确保所有路径都使用正确的模态
        # 当用户明确指定DR模态，但文本包含乳腺关键词时，强制路由到MG
        original_modality = modality
        modality_routed = False
        if modality == 'DR':
            if any(k in record for k in ('乳腺', '双乳', '左乳', '右乳', '乳房', '钼靶')):
                logger.info("DR->MG routing: breast keyword detected, routing DR to MG: %s", record)
                modality = 'MG'
                modality_routed = True

        # L0：唯一标准名称精确命中。标准库中的有效精确项优先于历史排除词，
        # 解决 OTHER/IR 错桶以及"标准项存在却被归为缺库/不可匹配"的问题。
        exact_result = self._match_exact_standard_name(record, modality)
        if exact_result is not None:
            if trace is not None:
                trace['op'] = ['standard_name_exact']
            logger.info(
                "DR->MG routing: exact match returned, setting routing info: "
                "original=%s, current=%s, routed=%s",
                original_modality, modality, modality_routed
            )
            exact_result['source_modality'] = original_modality
            if not exact_result.get('effective_modality'):
                exact_result['effective_modality'] = modality
            exact_result['modality_routed'] = modality_routed
            return exact_result

        # NLP 模态的不可匹配标识检查（统一守卫，在预处理前拦截）
        is_unmatchable, reason = self._check_unmatchable(record, modality)
        if is_unmatchable:
            reason = self._normalize_unmatchable_reason(reason)
            if trace is not None:
                trace['op'] = [f'unmatchable:{reason}']
            return _empty_result(record, tier='none', reason=reason)

        # 策略分派：US/SPECT/PET → 关键词引擎
        if modality in self.KW_MODALITIES:
            if trace is not None:
                trace['op'] = ['keyword_engine']
            # Bug #4 修复：关键词引擎模态的复合项目拆分
            # DR 分词器专为 DR 设计（DR_PREFIXES/DR_SUFFIXES），不应用于其他模态
            # 关键词引擎模态如需拆分，应该使用通用分隔符拆分，不走 DR 专用逻辑
            hybrid = self._split_hybrid_spect_ct(record, modality)
            if hybrid:
                # SPECT/CT 混合显像且括号内显式列出 CT 成分：拆成 SPECT 子项
                # 与 CT 子项分别匹配后合并（业务决策 2026-09-11）。
                # 例 "SPECT/CT骨盆(骨显像+CT平扫)" →
                #   SPECT骨盆(骨显像)  +  CT骨盆(平扫)
                all_data = []
                total_score = 0
                best_tier = 'none'
                requires_review = False
                unresolved_components = []
                for sub_text, sub_mod in hybrid:
                    sub_result = self._match_exact_standard_name(sub_text, sub_mod)
                    if sub_result is None:
                        if sub_mod in self.KW_MODALITIES:
                            sub_result = self._kw_match(sub_text, sub_mod)
                        elif sub_mod in self.NLP_MODALITIES:
                            sub_result = self._inner_match(
                                sub_text, 'scan',
                                {'body': [], 'scan': [], 'post': []},
                                sub_mod, version)
                        else:
                            sub_result = _empty_result(sub_text)
                    if sub_result.get('data'):
                        all_data.extend(sub_result['data'])
                    total_score += sub_result.get('score', 0)
                    sub_tier = sub_result.get('tier', 'none')
                    unresolved_components.extend(sub_result.get('unresolved_components', []))
                    requires_review = requires_review or sub_tier == 'ambiguous' or bool(unresolved_components)
                    if sub_tier in ('exact', 'partial', 'degraded') \
                            and (best_tier == 'none'
                                 or TIER_CONFIDENCE[sub_tier]
                                 < TIER_CONFIDENCE[best_tier]):
                        best_tier = sub_tier

                num_standard = sum(len(d.get('standard', [])) for d in all_data)
                if requires_review:
                    best_tier = 'ambiguous'
                result = {
                    'check_item': record,
                    'num_standard': num_standard,
                    'data': all_data,
                    'score': total_score,
                    'tier': best_tier if num_standard > 0 else 'none',
                    'confidence': TIER_CONFIDENCE.get(best_tier, 0.0),
                    'reason': ('multiple_technical_candidates' if requires_review
                               else '' if num_standard > 0 else 'standard_lib_gap'),
                    'unresolved_components': sorted(set(unresolved_components)),
                }
                if modality_routed:
                    result['source_modality'] = original_modality
                    result['effective_modality'] = modality
                    result['modality_routed'] = True
                return result

            if re.search(r'[,，;；|。]', record):
                # 简单分割处理，不使用 DR 分词器
                parts = re.split(r'[,，;；|。]+', record)
                parts = [p.strip() for p in parts if p.strip()]
                if len(parts) > 1:
                    # 多个子项：分别匹配后合并
                    all_data = []
                    total_score = 0
                    best_tier = 'none'
                    requires_review = False
                    unresolved_components = []
                    for part in parts:
                        part_result = (
                            self._match_exact_standard_name(part, modality)
                            or self._kw_match(part, modality)
                        )
                        if part_result.get('data'):
                            all_data.extend(part_result['data'])
                        total_score += part_result.get('score', 0)
                        unresolved_components.extend(part_result.get('unresolved_components', []))
                        requires_review = requires_review or part_result.get('tier') == 'ambiguous' or bool(unresolved_components)
                        if part_result.get('tier') in ('exact', 'partial', 'degraded'):
                            best_tier = part_result['tier']

                    num_standard = sum(len(d.get('standard', [])) for d in all_data)
                    if requires_review:
                        best_tier = 'ambiguous'
                    result = {
                        'check_item': record,
                        'num_standard': num_standard,
                        'data': all_data,
                        'score': total_score,
                        'tier': best_tier if num_standard > 0 else 'none',
                        'confidence': TIER_CONFIDENCE.get(best_tier, 0.0),
                        'reason': ('multiple_technical_candidates' if requires_review
                                   else '' if num_standard > 0 else 'standard_lib_gap'),
                        'unresolved_components': sorted(set(unresolved_components)),
                    }
                else:
                    result = self._kw_match(record, modality)
            else:
                result = self._kw_match(record, modality)
            if modality_routed:
                result['source_modality'] = original_modality
                result['effective_modality'] = modality
                result['modality_routed'] = True
            return result

        # CT/MR/DR/RF/MG → NLP pipeline。未支持模态必须返回结构化原因，
        # 不能与已明确命中的"设计上不可匹配"规则混为一类。
        if modality not in self.NLP_MODALITIES:
            return _empty_result(record, reason='unsupported_modality')

        # DR 复合项目检测和拆分（在进入 NLP pipeline 之前）
        if modality == 'DR' and self.dr_splitter.is_complex_item(record):
            logger.info(f"DR复合项目检测: {record}")
            # Bug #12 修复：避免 lambda 闭包捕获循环变量
            # 使用默认参数捕获当前值，而非闭包引用
            def dr_match_func(text, mod, v=version, t=trace):
                return self._match_single_dr_item(text, mod, v, t)

            # 使用拆分器处理复合项目
            result = self.dr_splitter.split_and_match(
                record,
                match_func=dr_match_func,
                modality=modality
            )
            # 添加路由信息
            if modality_routed:
                result['source_modality'] = original_modality
                result['effective_modality'] = modality
                result['modality_routed'] = True
            return result

        if modality == 'DR':
            process_type = 'position'
            query_fields = {'body': [], 'position': [], 'scan': []}
        else:
            process_type = 'scan'
            query_fields = {'body': [], 'scan': [], 'post': []}

        if trace is not None:
            trace['op'] = []
        logger.info(
            "DR->MG routing: calling _inner_match, modality_routed=%s",
            modality_routed
        )
        result = self._inner_match(record, process_type, query_fields, modality,
                                   version, trace=trace)

        # 添加路由信息到结果中
        if modality_routed:
            logger.info(
                "DR->MG routing: adding routing info to result, routed=%s",
                modality_routed
            )
            result['source_modality'] = original_modality
            result['effective_modality'] = modality
            result['modality_routed'] = True

        logger.info(
            "DR->MG routing: final result modality_routed=%s",
            result.get('modality_routed', 'NOT_SET')
        )

        return result

    def _match_single_dr_item(self, record: str, modality: str,
                              version: str = "V3.8.2", trace: dict = None) -> dict:
        """
        匹配单个 DR 检查项（不进行复合拆分，直接匹配）

        这是拆分后的子项匹配入口，避免递归调用复合拆分逻辑。

        Args:
            record: 单个 DR 检查项文本
            modality: 模态（应该是 DR）
            version: 标准库版本
            trace: 调试信息收集器

        Returns:
            匹配结果字典
        """
        if modality == 'DR':
            process_type = 'position'
            query_fields = {'body': [], 'position': [], 'scan': []}
        else:
            process_type = 'scan'
            query_fields = {'body': [], 'scan': [], 'post': []}

        if trace is not None:
            trace['op'] = []

        return self._inner_match(record, process_type, query_fields, modality,
                                version, trace=trace)

    def _match_exact_standard_name(self, record: str,
                                   source_modality: str) -> dict | None:
        """按规范化名称命中唯一有效标准项。

        索引由 data_loader 按固定模态目录政策加载，一个模态一个版本。
        返回版本来自索引标准记录，不能从请求选择器推断。

        候选收敛顺序：
          1. 按模态过滤
          2. 唯一候选 → exact
          3. 多候选 → ``_select_by_code_priority`` 按编码优先级选唯一
             （旧实现定义了该函数却从未调用，是缺陷①的核心）
          4. 仍多候选 → **返回 None 放行到下游引擎**，而不是直接判 ambiguous
             下游 NLP/关键词引擎可通过部位同义词（眼眶→眼部、鞍区→垂体）
             给出正确结果；实测 13/17 条可回收。
             若下游也无结果，由下游按标准路径给出 standard_lib_gap。
        """
        key = normalize_standard_name(record)
        candidates = self.data_loader.standard_name_index.get(key, [])
        used_us_alias = not candidates
        if used_us_alias:
            # US is a display modality prefix, not an anatomical term. Alias
            # only loaded active US rows; preserve their actual name/version.
            alias = key[2:] if key.startswith("US") else key
            candidates = getattr(self.data_loader, "us_standard_name_alias_index", {}).get(alias, [])
        if not candidates:
            return None

        # 多候选时，先按模态过滤
        normalized_source = str(source_modality or "").upper()
        if normalized_source:
            modality_filtered = [
                c for c in candidates if c["modality"] == normalized_source
            ]
            if not modality_filtered:
                # OTHER/IR/CBBCT 等非引擎模态常来自上游错桶。只有完整标准
                # 名称命中时才允许跨桶恢复；受支持模态仍严格禁止跨模态。
                if normalized_source in self.SUPPORTED_MODALITIES:
                    return None
                modality_filtered = candidates
        else:
            modality_filtered = candidates

        if not modality_filtered:
            return None

        if used_us_alias and len(modality_filtered) > 1:
            return _empty_result(record, tier="ambiguous", reason="standard_name_alias_collision")

        if len(modality_filtered) > 1:
            # 缺陷①修复：调用已存在但从未被调用的编码优先级消歧。
            # ACR 标准编码（14 位，2-9 开头）优先于历史/内部编码。
            selected = self._select_by_code_priority(modality_filtered)
            if selected is None:
                # 同版本内仍有多个同级候选：不再直接判 ambiguous，
                # 放行到下游语义匹配（部位同义词可解），避免把可解项拦死。
                logger.info(
                    "exact-name 同名多编码未收敛，放行下游: name=%s modality=%s "
                    "candidates=%s",
                    key, normalized_source,
                    [c["code"] for c in modality_filtered],
                )
                return None
            candidate = selected
        else:
            candidate = modality_filtered[0]

        # 检查文本模态与候选模态是否冲突
        candidate_modality = candidate["modality"]
        text_modality = infer_text_modality(record)
        if (
            text_modality
            and text_modality != candidate_modality
            and normalized_source != candidate_modality
        ):
            return None

        standard = {"code": candidate["code"], "name": candidate["name"]}
        if candidate.get("version"):
            standard["version"] = candidate["version"]
        return {
            "check_item": str(record),
            "num_standard": 1,
            "data": [{"raw": str(record), "standard": [standard]}],
            "score": 10,
            "tier": "exact",
            "confidence": TIER_CONFIDENCE["exact"],
            "reason": "",
            "has_entity": True,
            "engine": "standard_name_exact",
            "source_modality": normalized_source,
            "effective_modality": candidate_modality,
        }

    @staticmethod
    def _select_by_code_priority(candidates: list) -> dict | None:
        """按编码优先级选择唯一候选。
        
        优先级：
        1. ACR标准编码（14位数字，2-9开头）
        2. 其他编码
        
        返回唯一最高优先级候选，或 None（仍有多个同等优先级）。
        """
        import re
        
        # 优先级顺序：ACR标准 > 其他
        CODE_PRIORITY = [
            r'^[2-9]\d{13}$',  # ACR标准编码（14位数字，2-9开头）
        ]
        
        for pattern in CODE_PRIORITY:
            matches = [c for c in candidates if re.match(pattern, c['code'])]
            if len(matches) == 1:
                return matches[0]
            elif len(matches) > 1:
                # 同优先级多个，无法选择
                return None
        
        # 没有ACR标准，但只有一个其他编码
        if len(candidates) == 1:
            return candidates[0]
        
        # 多个非ACR编码，无法选择
        return None

    def _kw_match(self, record: str, modality: str) -> dict:
        """
        委托关键词引擎匹配 US/SPECT/PET，结果包装为统一 dict 格式。

        关键词引擎返回 List[Tuple[item_code, item_name]]，
        这里转换成与 NLP pipeline 一致的 {'data', 'num_standard', 'score'} 结构。
        """
        record = str(record)
        try:
            pairs = self._kw_matcher.match(record, modality)
        except (KeyError, ValueError, AttributeError, TypeError) as e:
            logger.error(
                f"关键词引擎异常 [{modality}] {record!r}: "
                f"{type(e).__name__}: {e}",
                exc_info=True,
            )
            return _empty_result(record, tier='error')

        standard = []
        for code, name in pairs:
            item = {'code': code, 'name': name}
            lookup_version = getattr(self._kw_matcher, 'standard_version', None)
            actual_version = lookup_version(code, name, modality) if lookup_version else None
            if isinstance(actual_version, str) and actual_version.strip():
                item['version'] = actual_version
            standard.append(item)
        # matcher 在保持旧 List 返回协议的同时，通过 _last_* 区分"未识别实体"、
        # "实体存在但标准缺失"和"明确排除"，不能再把所有 [] 都归为词库缺失。
        if standard:
            tier = getattr(self._kw_matcher, '_last_tier', 'exact')
        else:
            tier = 'none'
        reason = getattr(self._kw_matcher, '_last_reason', '')
        has_entity = getattr(
            self._kw_matcher, '_last_has_entity', bool(standard)
        )
        return {
            'check_item': record,
            'num_standard': len(standard),
            'data': [{'raw': record, 'standard': standard}] if standard else [],
            'score': 10 if standard else 0,
            'tier': tier,
            'confidence': TIER_CONFIDENCE[tier],
            'reason': reason,
            'has_entity': has_entity,
            'engine': 'keyword',
            'unresolved_components': getattr(self._kw_matcher, '_last_unresolved_components', []),
        }

    def _inner_match(self, records: str, process_type: str,
                     query_fields: dict, modality: str,
                     version: str, trace: dict = None) -> dict:
        """完整 10 步匹配 pipeline

        Args:
            trace: 传入 dict 时按旧服务编号键收集各步中间态
                （legacy 兼容层的 debug 字段用；None 时零开销）
        """
        records = str(records)
        match_info = {
            'data': [], 'check_item': records, 'num_standard': 0, 'score': 10}

        # Step 1: 预处理（包含方括号保护）
        records, bracket_handler = self.preprocess_service.preprocess(records, modality, version)
        if trace is not None:
            trace['1-preprocess'] = records
            if bracket_handler.get_protected_terms():
                trace['1-bracket_protected'] = bracket_handler.get_protected_terms()

        # Step 2: 拆分子项
        record_split = self.preprocess_service.split_record(records, modality)
        if trace is not None:
            trace['2-split'] = list(record_split)

        # Step 3: 分词 + 建树
        childrens, other_record = self.tokenizer_service.make_tree(
            record_split, modality, version, self.disamb_service)
        factor_composite = 1 if other_record else 0
        if trace is not None:
            trace['3-make_tree'] = [str(n) for n in childrens]

        # Step 4: 模式处理（B(B)合并 + BSPB分裂）
        childrens = self.pattern_processor.process_by_pattern(childrens, version)
        if trace is not None:
            trace['4-process_by_pattern'] = [str(n) for n in childrens]

        # Step 5: 合并无body节点
        childrens = self.pattern_processor.merge_no_body(
            childrens, self.disamb_service)
        if trace is not None:
            trace['5-merge_no_body'] = [str(n) for n in childrens]

        # Step 6: 并列部位分裂
        childrens = self.pattern_processor.split_multi_body(childrens)
        if trace is not None:
            trace['6-split_multi_body'] = [str(n) for n in childrens]

        # Step 7: 节点间合并（上下位关系）
        childrens = self.disamb_service.merge_nodes(
            childrens, process_type, modality, version)
        if trace is not None:
            trace['7-merge_nodes'] = [str(n) for n in childrens]

        # Step 8: 消歧映射 — 完整3步级联
        childrens = self.disamb_service.body_2process_remap(
            childrens, process_type, modality, version)
        if trace is not None:
            trace['8-body_2process_remap'] = [str(n) for n in childrens]

        # Step 8.5: 血管成像归一化
        childrens = self.disamb_service.normalize_vascular_nodes(
            childrens, process_type, modality)
        if trace is not None:
            trace['8.5-normalize_vascular'] = [str(n) for n in childrens]

        # Step 8.6: 去除查询语义重复节点（括号缩写影子节点、平扫+增强冗余节点等），
        # 避免 lookup 的 dup_set 拦截重复节点产生空块、误判 ambiguous
        childrens = self._dedup_query_equivalent_nodes(childrens)
        if trace is not None:
            trace['8.6-dedup_query_equivalent'] = [str(n) for n in childrens]

        # Step 9: 补充默认处理方式
        childrens = self.lookup_service.find_default_process(
            childrens, process_type, modality, version)
        if trace is not None:
            trace['9-find_default_process'] = [str(n) for n in childrens]

        # Step 10: 查标准表
        self.lookup_service.lookup_standard(
            childrens, query_fields, process_type, modality, version)
        if trace is not None:
            trace['10-lookup_standard'] = [str(n) for n in childrens]

        # Step 11: 恢复方括号修饰语（在结果输出前）
        if bracket_handler.get_protected_terms():
            for node in childrens:
                # 恢复 raw_str
                node.raw_str = bracket_handler.restore_brackets(node.raw_str)
                # 恢复 standard_check_name 中的占位符
                node.standard_check_name = [
                    bracket_handler.restore_brackets(name)
                    for name in node.standard_check_name
                ]
            if trace is not None:
                trace['11-bracket_restored'] = [str(n) for n in childrens]

        # Phase 7: 获取使用统计（用于智能排序）
        usage_stats = self.usage_stats_cache.get(modality, {})

        # 汇总
        for node in childrens:
            match_info['data'].append(node.standard(usage_stats))
            match_info['num_standard'] += len(node.standard_check_name)

        score = factor_composite * 1
        match_info['score'] = 10 - score

        # 置信度四档汇总（取所有子项中最差档）：
        # - none: 无任何匹配结果
        # - ambiguous: 有结果但存在解析出实体却查不到标准项的子项（部分失配）
        # - degraded: 任一子项查表走了模糊/回退分支
        # - partial: 任一子项的处理方式为默认推断（部位命中）
        # - exact: 全部子项部位+处理方式显式精确命中
        has_result = match_info['num_standard'] > 0
        # dup_only 节点：候选全部被其他节点去重覆盖（组合项目中语义已覆盖的
        # 影子节点），不计入"有实体但未匹配"，避免组合项目被误判 ambiguous。
        has_unmatched_node = any(
            node.entitys and not node.standard_check_name
            and not getattr(node, 'dup_only', False)
            for node in childrens
        )
        # 是否解析出有效医学实体（落入 body/scan/post/position 维度）：
        # 供 backend 区分 lexicon_gap（无医学实体，词库未覆盖）与
        # standard_lib_gap（有医学实体但查不到标准项）。
        has_entity = any(
            node.pos_dict.get(k) for node in childrens for k in _MEDICAL_POS
        )
        # 组合项目：输入被拆分为多个子项（如 "MR胸主动脉MRA,MR髂动脉MRA"）。
        # 组合语义 = 各子项分别命中自己的标准项（结果含多个标准），
        # 而不是在多个候选里"选一个"——因此部分子项真缺标准时，
        # 整条应按降级组合处理，而不是歧义失败。
        is_compound = len(record_split) > 1
        if not has_result:
            tier = 'none'
            compound_reason = ''
        elif has_unmatched_node:
            # 单候选+唯一子项时，优先返回exact/degraded（技术描述规范化后无残留）
            if (match_info['num_standard'] == 1 and len(childrens) == 1 
                and not any(node.degraded for node in childrens)):
                tier = 'exact'
                compound_reason = ''
            elif (match_info['num_standard'] == 1
                  and self._unmatched_body_covered(childrens, match_info)):
                # 并列部位分裂（Step 6）会把「笼统描述 + 括号内的更具体部位」拆成
                # 两个节点。例如 "X线消化道造影(上消化道)" 会同时产生 body=消化道
                # 与 body=上消化道 两个节点；前者查不到标准项（RF 无“消化道造影”
                # 泛项），后者命中 "RF上消化道造影"。此时唯一标准项已由更具体节点
                # 给出，未被命中的节点只是其上位/同义表述，不应整条判为 ambiguous。
                # 判定条件很窄：未命中节点的部位词必须字面出现在已命中标准名中。
                tier = 'degraded'
                compound_reason = ''
            elif is_compound:
                tier = 'degraded'
                compound_reason = 'compound_item_incomplete'
            else:
                tier = 'ambiguous'
                compound_reason = ''
        elif any(node.degraded for node in childrens):
            tier = 'degraded'
            compound_reason = ''
        elif any(node.fill_default for node in childrens):
            tier = 'partial'
            compound_reason = ''
        else:
            tier = 'exact'
            compound_reason = ''

        # 处理跨模态子项（组合医嘱拆分出的其他模态子项，递归到 match() 策略分派）
        # 例如 "CT头部平扫;超声心动" 会把 US 子项递归到关键词引擎
        for other_mod, items in other_record.items():
            if other_mod not in self.SUPPORTED_MODALITIES:
                continue
            sub_record = ';'.join([item for _, _, item in items])
            sub_result = self.match(sub_record, other_mod, version)
            match_info['data'] += sub_result.get('data', [])
            match_info['num_standard'] += sub_result.get('num_standard', 0)
            has_entity = has_entity or bool(sub_result.get('has_entity'))
            # 跨模态子项取更差档
            sub_tier = sub_result.get('tier', 'none')
            if match_info['num_standard'] > 0 and sub_tier != 'none':
                if TIER_CONFIDENCE[sub_tier] < TIER_CONFIDENCE[tier]:
                    tier = sub_tier
                elif tier == 'none':
                    # 主模态无命中但跨模态子项命中（如 MR经食管超声心动图 → US 匹配）
                    tier = sub_tier
            elif sub_tier == 'none' and tier != 'none':
                # 跨模态子项完全失配 → 整体降为 ambiguous（部分失配）
                tier = 'ambiguous' if match_info['num_standard'] > 0 else 'none'

        match_info['tier'] = tier
        match_info['confidence'] = TIER_CONFIDENCE[tier]
        # NLP 正常路径无 unmatchable 标记；has_entity 供未匹配原因分类。
        # 组合项目部分子项失配时标记 compound_item_incomplete（组合语义，
        # 区别于单项目的多候选歧义）。
        match_info['reason'] = compound_reason
        match_info['has_entity'] = has_entity
        return match_info

    @staticmethod
    def _split_hybrid_spect_ct(record: str, modality: str):
        """拆分 SPECT/CT（PET/CT）混合显像中括号内显式的 CT 成分。

        背景：``SPECT/CT骨盆(骨显像+CT平扫)`` 的 ``/CT`` 属于混合模态名，
        而括号内的 ``+CT平扫`` 是真正并列的第二个检查成分。旧逻辑整条丢给
        SPECT 关键词引擎，只能拿到骨显像候选，无法给出 CT 骨盆标准。

        Args:
            record: 原始检查名
            modality: 已解析的源模态

        Returns:
            [(子项文本, 子项模态), ...]；不命中返回 None
        """
        if modality not in ('SPECT', 'PET/CT'):
            return None
        m = re.match(
            r'^\s*(SPECT|PET)\s*/\s*CT\s*([^()（）]*)\('
            r'([^()（）]*?)\+\s*CT\s*([^()+（）]*)\)\s*$',
            record,
        )
        if not m:
            return None
        hybrid_mod, body, element, ct_method = m.groups()
        body = body.strip()
        element = element.strip()
        ct_method = ct_method.strip() or '平扫'
        if not body:  # 无部位时无法定位，交回原逻辑
            return None
        spect_part = f'{hybrid_mod}{body}({element})'
        ct_part = f'CT{body}({ct_method})'
        logger.info(
            "SPECT/CT 混合显像拆分: %s → %s | %s",
            record, spect_part, ct_part,
        )
        return [(spect_part, hybrid_mod), (ct_part, 'CT')]

    @staticmethod
    def _unmatched_body_covered(childrens: List, match_info: dict) -> bool:
        """未命中的部位节点是否已被唯一标准项完全覆盖（下位/同义表述）。

        用途：Step 6 并列部位分裂会把「笼统描述 + 括号内的更具体部位」拆成两个
        平行节点，笼统节点查不到标准项时会把整条误判为 ambiguous。
        例："X线消化道造影(上消化道)" → 节点 body=消化道（RF 无泛项，查不到）
        与 body=上消化道（命中 "RF上消化道造影"）。

        判定（保守，四条同时成立）：
          1. 已命中标准项恰为 1 条；
          2. 未命中节点均非 dup_only；
          3. 未命中节点的每一个**医学维度**实体（body/scan/post/position）
             都**字面出现**在已命中标准名中；
          4. 至少有一个这样的实体（避免空节点误放行）。

        条件 3 是关键安全阀：只有「标准项名称确实包含该输入的全部医学词」时才
        放行，因此真实缺项（标准库没这个部位/方法）不会被误当作已覆盖。
        """
        standards = [
            str(std.get('name') or '')
            for block in (match_info.get('data') or [])
            for std in (block.get('standard') or [])
        ]
        if len(standards) != 1 or not standards[0]:
            return False
        std_name = standards[0]

        terms: List[str] = []
        for node in childrens:
            if not node.entitys or node.standard_check_name:
                continue
            if getattr(node, 'dup_only', False):
                continue
            for pos in ('body', 'scan', 'post', 'position'):
                for idx in node.pos_dict.get(pos, []):
                    term = str(node.entitys[idx] or '').strip()
                    if term:
                        terms.append(term)

        if not terms:
            return False
        return all(term in std_name for term in terms)

    @staticmethod
    def _node_query_signature(node) -> Tuple[frozenset, frozenset, frozenset]:
        """提取节点的查询语义签名：(body集合, scan集合, post集合)。"""
        def vals(pos):
            return frozenset(node.std_names[j] for j in node.pos_dict.get(pos, []))
        return vals('body'), vals('scan'), vals('post')

    @classmethod
    def _dedup_query_equivalent_nodes(cls, childrens: List) -> List:
        """去除查询语义重复的节点。

        典型来源：
        1) 括号缩写影子节点 —— "(CE-MRA)" 中的 MRA 被单独映射为 scan 实体，
           归一化后与主节点形成相同 (body, scan) 查询；
        2) 平扫+增强冗余节点 —— 已存在 CTA/MRA 等具体技术节点时，
           血管归一化把残留的"平扫+增强"节点转成相同查询。
        这类重复节点在 lookup 阶段会被 dup_set 拦截为空块，
        进而被误判为"有实体未匹配"导致 ambiguous 降级。

        body 兼容规则：两节点 body 均为单值且互为子串（如 全腹部 / 全腹部动脉）
        视为同一部位，保留 body 更具体（更长）的节点。

        性能优化：缓存已保留节点的签名，避免重复计算（O(n²) → O(n×m)，m为保留节点数）
        """
        result = []
        result_sigs = []  # 缓存签名避免重复计算

        for node in childrens:
            body_sig, scan_sig, post_sig = cls._node_query_signature(node)
            placed = False

            for idx, (kept, (k_body, k_scan, k_post)) in enumerate(zip(result, result_sigs)):
                if scan_sig != k_scan or post_sig != k_post:
                    continue
                if body_sig == k_body:
                    body_ok = True
                elif len(body_sig) == 1 and len(k_body) == 1 and body_sig and k_body:
                    # 仅允许相差血管后缀（如 全腹部 / 全腹部动脉），避免误并不同部位
                    # 防御性检查：确保集合非空且提取的字符串非空
                    b, kb = next(iter(body_sig)), next(iter(k_body))
                    # 验证后缀必须是完整的"动脉"或"静脉"，且基础部分非空
                    # 避免"主"和"主动脉"这种子串巧合被错误匹配
                    # 显式检查空字符串，防止 "".startswith("") 恒为 True 的边界情况
                    body_ok = False
                    if b and kb and len(b) > 0 and len(kb) > 0:
                        if kb.startswith(b) and kb[len(b):] in ('动脉', '静脉'):
                            body_ok = True
                        elif b.startswith(kb) and b[len(kb):] in ('动脉', '静脉'):
                            body_ok = True
                else:
                    body_ok = False
                if not body_ok:
                    continue
                # 重复：保留 body 更具体（总长度更长）的节点
                kept_len = sum(len(s) for s in k_body)
                node_len = sum(len(s) for s in body_sig)
                if node_len > kept_len:
                    result[idx] = node
                    result_sigs[idx] = (body_sig, scan_sig, post_sig)
                placed = True
                break
            if not placed:
                result.append(node)
                result_sigs.append((body_sig, scan_sig, post_sig))
        return result

    def batch_match(self, items: List[Dict[str, str]],
                    version: str = "V3.8.2") -> Dict[str, List[Tuple[str, str]]]:
        """
        批量匹配（统一入口，内部按模态策略分派）

        Args:
            items: [{"key": 唯一ID, "modality": "CT", "name": "CT头部平扫"}, ...]
            version: 标准版本（仅 NLP 模态使用，关键词引擎忽略）

        Returns:
            {key: [(std_code, std_name), ...]}
        """
        detailed = self.batch_match_detailed(items, version)
        return {key: info['pairs'] for key, info in detailed.items()}

    def batch_match_detailed(self, items: List[Dict[str, str]],
                             version: str = "V3.8.2") -> Dict[str, Dict]:
        """
        批量匹配（含记录级置信度）

        Args:
            items: [{"key": 唯一ID, "modality": "CT", "name": "CT头部平扫"}, ...]
            version: 标准版本（仅 NLP 模态使用，关键词引擎忽略）

        Returns:
            {key: {'pairs': [(std_code, std_name), ...],
                   'score': 0-10,
                   'tier': exact/partial/degraded/ambiguous/none,
                   'confidence': 0.0-1.0}}
        """
        result: Dict[str, Dict] = {}

        for item in items:
            key = item['key']
            modality = item.get('modality', '')
            name = item.get('name', '')

            # Phase 1 改进：优先检查 unmatchable 标记（所有模态，包括不支持的）
            # 这样可以正确识别 XR/CBCT/ES/SURG 等模态中的非影像检查
            if name:
                is_unmatchable, reason = self._check_unmatchable(name, modality)
                if is_unmatchable:
                    result[key] = {'pairs': [], 'score': 0, 'tier': 'none',
                                   'confidence': 0.0,
                                   'reason': self._normalize_unmatchable_reason(reason),
                                   'has_entity': None}
                    continue

            # 不支持模态（无 unmatchable 标记）：无引擎实体信号，reason 留空
            if not name or modality not in self.SUPPORTED_MODALITIES:
                result[key] = {'pairs': [], 'score': 0, 'tier': 'none',
                               'confidence': 0.0, 'reason': '', 'has_entity': None}
                continue

            try:
                match_result = self.match(name, modality, version)
                pairs = []
                for d in match_result.get('data', []):
                    for std in d.get('standard', []):
                        pairs.append((std['code'], std['name']))
                tier = match_result.get('tier', 'none')
                result[key] = {
                    'pairs': pairs,
                    'score': match_result.get('score', 0),
                    'tier': tier,
                    'confidence': match_result.get(
                        'confidence', TIER_CONFIDENCE.get(tier, 0.0)),
                    'reason': match_result.get('reason', ''),
                    'has_entity': match_result.get('has_entity'),
                }
            except (KeyError, ValueError, AttributeError, TypeError) as e:
                # 引擎内部数据异常：标 error（区别于 none 的"真未命中"），
                # 供未匹配原因分类识别为 engine_error 而非误判为标准库缺项。
                logger.error(
                    f"匹配引擎异常 [{key}] modality={modality} name={name!r}: "
                    f"{type(e).__name__}: {e}",
                    exc_info=True,
                )
                result[key] = {'pairs': [], 'score': 0, 'tier': 'error',
                               'confidence': 0.0, 'reason': '', 'has_entity': None}

        return result

    async def _load_all_usage_stats(self) -> dict:
        """
        Phase 7: 加载所有模态的标准项使用统计（初始化时调用）

        从 match_cache 表聚合各标准项的使用频率
        解析 result_json 提取标准项 code

        Returns:
            {modality: {checkitem_code: usage_count}} 嵌套字典
        """
        from sqlalchemy import text
        import json

        try:
            async with self.engine.begin() as conn:
                # 从缓存表读取所有记录（result_json 包含匹配结果）
                result = await conn.execute(
                    text("""
                        SELECT modality, result_json, hit_count
                        FROM match_cache
                        WHERE result_json IS NOT NULL
                          AND hit_count > 0
                        ORDER BY hit_count DESC
                        LIMIT 100000
                    """)
                )

                all_stats = {}
                for row in result:
                    modality = row[0]
                    result_json = row[1]
                    hit_count = row[2]

                    if modality not in all_stats:
                        all_stats[modality] = {}

                    # 解析 result_json 提取标准项 code
                    try:
                        result_data = json.loads(result_json)
                        # result_json 格式: {"data": [{"standard": [{"code": "...", "name": "..."}]}]}
                        for item in result_data.get('data', []):
                            for std in item.get('standard', []):
                                code = std.get('code')
                                if code:
                                    all_stats[modality][code] = all_stats[modality].get(code, 0) + hit_count
                    except (json.JSONDecodeError, KeyError, TypeError):
                        continue

                logger.info(
                    f"Phase 7: 加载使用统计完成 - "
                    f"{len(all_stats)} 个模态, "
                    f"总计 {sum(len(v) for v in all_stats.values())} 个标准项"
                )
                return all_stats

        except Exception as e:
            # 统计加载失败不影响匹配功能，降级为字母序
            logger.warning(f"Phase 7: 加载使用统计失败: {e}")
            return {}

        return result

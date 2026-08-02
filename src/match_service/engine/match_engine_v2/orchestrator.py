"""
匹配引擎协调器 — 统一入口（策略模式）

对外提供统一的 match() / batch_match() 接口，内部按模态自动分派：
- CT/MR/DR/RF/MG → 10 步 NLP Pipeline（结构化分词+消歧+查表）
- US/SPECT/PET/CT/PET/MR → 关键词引擎（专用规则匹配，委托 us_spect_pet_matcher）

两套底层引擎各司其职：NLP pipeline 为 CT/MR 的"部位+扫描+后处理"维度设计，
关键词引擎为 US/PET/SPECT 的"器官+扫描方式/显像方式"维度设计，字段语义不同故不可合并。
"""
import logging
from typing import Dict, List, Tuple

from sqlalchemy.ext.asyncio import AsyncEngine

from .constants import SPECIAL_ITEM_MARKERS
from .data_loader import RuleDataLoader
from .disambiguation_service import DisambiguationService
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
        # 关键词引擎（US/SPECT/PET），懒加载避免循环导入
        self._kw_matcher = None
        self._initialized = False

    async def initialize(self):
        """初始化所有服务（支持热重载：重复调用时清除旧缓存）"""
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

        # 关键词引擎（US/SPECT/PET/OCT/DSA），透传本引擎的 DB engine
        # 使独立 match-service 的自建 engine 一路贯通到关键词引擎
        factory = self._kw_matcher_factory
        if factory is None:
            # Phase A: 改用本地引擎路径
            from match_service.engine.keyword.us_spect_pet_matcher import (
                get_us_spect_pet_matcher,
            )
            factory = get_us_spect_pet_matcher
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

        注：仅 NLP 模态在此拦截；关键词引擎（US/SPECT/PET/OCT/DSA）有各自的
        unmatchable 词表，在引擎内部处理。
        """
        if modality not in self.NLP_MODALITIES:
            return False, ''
        for marker in self.UNMATCHABLE_MARKERS:
            if marker in record:
                return True, SPECIAL_ITEM_MARKERS[marker]
        return False, ''

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

        # NLP 模态的不可匹配标识检查（统一守卫，在预处理前拦截）
        is_unmatchable, reason = self._check_unmatchable(record, modality)
        if is_unmatchable:
            if trace is not None:
                trace['op'] = [f'unmatchable:{reason}']
            return _empty_result(record, tier='none', reason=reason)

        # 策略分派：US/SPECT/PET → 关键词引擎
        if modality in self.KW_MODALITIES:
            if trace is not None:
                trace['op'] = ['keyword_engine']
            return self._kw_match(record, modality)

        # CT/MR/DR/RF/MG → NLP pipeline
        if modality not in self.NLP_MODALITIES:
            return _empty_result(record)

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

        standard = [{'code': code, 'name': name} for code, name in pairs]
        # C4 修复：读取 matcher 的 _last_tier（降级匹配时为 'degraded'）
        # 不再一律标记 exact，避免降级结果以 1.0 置信度写入缓存
        if standard:
            tier = getattr(self._kw_matcher, '_last_tier', 'exact')
        else:
            tier = 'none'
        return {
            'check_item': record,
            'num_standard': len(standard),
            'data': [{'raw': record, 'standard': standard}] if standard else [],
            'score': 10 if standard else 0,
            'tier': tier,
            'confidence': TIER_CONFIDENCE[tier],
            'reason': '',
            # 关键词引擎为整词匹配：有命中=True，无命中=False（词库未覆盖）
            'has_entity': bool(standard),
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

        # Step 1: 预处理
        records = self.preprocess_service.preprocess(records, modality, version)
        if trace is not None:
            trace['1-preprocess'] = records

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

        # 汇总
        for node in childrens:
            match_info['data'].append(node.standard())
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
        has_unmatched_node = any(
            node.entitys and not node.standard_check_name for node in childrens
        )
        # 是否解析出有效医学实体（落入 body/scan/post/position 维度）：
        # 供 backend 区分 lexicon_gap（无医学实体，词库未覆盖）与
        # standard_lib_gap（有医学实体但查不到标准项）。
        has_entity = any(
            node.pos_dict.get(k) for node in childrens for k in _MEDICAL_POS
        )
        if not has_result:
            tier = 'none'
        elif has_unmatched_node:
            tier = 'ambiguous'
        elif any(node.degraded for node in childrens):
            tier = 'degraded'
        elif any(node.fill_default for node in childrens):
            tier = 'partial'
        else:
            tier = 'exact'

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
            elif sub_tier == 'none' and tier != 'none':
                # 跨模态子项完全失配 → 整体降为 ambiguous（部分失配）
                tier = 'ambiguous' if match_info['num_standard'] > 0 else 'none'

        match_info['tier'] = tier
        match_info['confidence'] = TIER_CONFIDENCE[tier]
        # NLP 正常路径无 unmatchable 标记；has_entity 供未匹配原因分类
        match_info['reason'] = ''
        match_info['has_entity'] = has_entity
        return match_info

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

            # 不支持模态（含特殊 CT/非影像）：无引擎实体信号，reason 留空，
            # 由 backend 按模态推导（特殊 CT→standard_lib_gap，非影像→unmatchable）。
            if not name or modality not in self.SUPPORTED_MODALITIES:
                result[key] = {'pairs': [], 'score': 0, 'tier': 'none',
                               'confidence': 0.0, 'reason': '', 'has_entity': None}
                continue

            # 特殊医嘱标识检查（统一守卫；关键词引擎有自己的 unmatchable 词表）
            # 保留 reason（穿刺/介入/放疗等标识），供 backend 判 unmatchable_by_design。
            is_unmatchable, reason = self._check_unmatchable(name, modality)
            if is_unmatchable:
                result[key] = {'pairs': [], 'score': 0, 'tier': 'none',
                               'confidence': 0.0, 'reason': reason,
                               'has_entity': None}
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

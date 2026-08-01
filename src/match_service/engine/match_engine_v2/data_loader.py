"""
规则数据加载器 - 从 PostgreSQL 加载规则表到内存
"""
import logging
from typing import Dict

import jieba
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from .constants import VERSION_FALLBACK

logger = logging.getLogger(__name__)


class RuleDataLoader:
    """规则数据加载器，负责从数据库加载所有规则表"""

    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self._initialized = False

        # 内存数据
        self.mdict: Dict[str, str] = {}
        self.alias2std: pd.DataFrame = pd.DataFrame()
        self.pre_rules: Dict[str, pd.DataFrame] = {}
        self.common_normal: pd.DataFrame = pd.DataFrame()
        self.normal_rules: Dict[str, pd.DataFrame] = {}
        self.process_normal: pd.DataFrame = pd.DataFrame()
        self.body_map: pd.DataFrame = pd.DataFrame()
        self.vessel_map: pd.DataFrame = pd.DataFrame()
        self.df_body_disamb: pd.DataFrame = pd.DataFrame()
        self.df_standard: Dict[str, Dict[str, pd.DataFrame]] = {}

    async def initialize(self):
        """从数据库加载所有规则表"""
        async with self.engine.connect() as conn:
            await self._load_medical_dict(conn)
            await self._load_phrase_map(conn)
            await self._load_ambiguity(conn)
            await self._load_standard_table(conn)

        self._initialized = True
        logger.info("[RuleDataLoader] 规则数据加载完成")

    async def _load_medical_dict(self, conn):
        """加载医学词典"""
        result = await conn.execute(text(
            "SELECT word, type FROM nlp_medical_dict WHERE enable = 0"
        ))
        rows = result.fetchall()
        self.mdict = {r[0]: r[1] for r in rows}
        logger.info(f"[RuleDataLoader] 加载医学词典: {len(self.mdict)} 词条")

        # 注册到 jieba（组合词汇使用更高词频，确保不被拆分）
        for word, wtype in self.mdict.items():
            # 多字组合词（如"双侧乳腺"）需要更高词频以避免被拆分
            if len(word) >= 3 and any(prefix in word for prefix in ['双侧', '左侧', '右侧', '单侧']):
                freq = 999999
            else:
                freq = 883635
            jieba.add_word(word, tag=wtype, freq=freq)

    async def _load_phrase_map(self, conn):
        """加载同义词/别名映射"""
        result = await conn.execute(text(
            "SELECT id, modality, src_word, dst_word, step, version "
            "FROM nlp_phrase_map WHERE enable = 0"
        ))
        rows = result.fetchall()
        self.alias2std = pd.DataFrame(
            rows, columns=['id', 'modality', 'src_word', 'dst_word', 'step', 'version']
        )
        self.alias2std.fillna("", inplace=True)

        # 优化：创建多级索引
        if not self.alias2std.empty:
            self.alias2std.set_index(['modality', 'step', 'version'], inplace=True)

        logger.info(f"[RuleDataLoader] 加载别名映射: {len(self.alias2std)} 条")

        # 分类索引（保留兼容性）
        self._build_phrase_map_indexes()

    def _build_phrase_map_indexes(self):
        """构建别名映射索引"""
        if self.alias2std.empty:
            return

        # 重置索引用于 query
        df = self.alias2std.reset_index()

        # 预处理规则 (pre step)
        for mod in ['CT', 'MR', 'DR', 'RF', 'MG']:
            self.pre_rules[mod] = df.query(
                f'modality in ["{mod}","ALL"] and step=="pre"'
            )

        # 归一化规则 (normalize step)
        self.common_normal = df.query('modality=="ALL" and step=="normalize"')
        for mod in ['CT', 'MR', 'DR', 'RF', 'MG']:
            self.normal_rules[mod] = df.query(
                f'modality=="{mod}" and step=="normalize"'
            )

        # 处理方式归一化 (process step)
        self.process_normal = df.query('step=="process"')

        # 部位映射 (global_map, local_map)
        self.body_map = df.query('step in ["global_map","local_map"]')

        # 血管映射 (vessel step)
        self.vessel_map = df.query('step=="vessel"')

    async def _load_ambiguity(self, conn):
        """加载消歧规则"""
        result = await conn.execute(text(
            "SELECT id, modality, src_body, src_process, dst_body, dst_process, version "
            "FROM nlp_ambiguity WHERE enable = 0"
        ))
        rows = result.fetchall()
        self.df_body_disamb = pd.DataFrame(
            rows, columns=['id', 'modality', 'src_body', 'src_process',
                           'dst_body', 'dst_process', 'version']
        )
        self.df_body_disamb.fillna("", inplace=True)
        logger.info(f"[RuleDataLoader] 加载消歧规则: {len(self.df_body_disamb)} 条")

    async def _load_standard_table(self, conn):
        """加载标准项目表"""
        result = await conn.execute(text(
            "SELECT modality_name, scope_name, version, three_level_name, "
            "scan_name, post_processing_name, position_name, device_type_name, "
            "checkitem_code, checkitem_name "
            "FROM nlp_checkitem_standard WHERE is_deleted = 0"
        ))
        rows = result.fetchall()
        df_all = pd.DataFrame(rows, columns=[
            'modality_name', 'scope_name', 'version', 'three_level_name',
            'scan_name', 'post_processing_name', 'position_name', 'device_type_name',
            'checkitem_code', 'checkitem_name'
        ])
        df_all.fillna("", inplace=True)
        logger.info(f"[RuleDataLoader] 加载标准项目: {len(df_all)} 条")

        # 按模态+版本分组
        self._build_standard_indexes(df_all)

    def _build_standard_indexes(self, df_all: pd.DataFrame):
        """构建标准表索引"""
        # CT/MR/DSA/MG 直接分组（MG作为独立模态）
        for modality in ['CT', 'MR', 'DSA', 'MG']:
            df_mod = df_all[df_all['modality_name'] == modality]
            self.df_standard[modality] = {}
            for ver in df_mod['version'].unique():
                self.df_standard[modality][ver] = df_mod[df_mod['version'] == ver].copy()

        # X线 按 device_type_name 拆分为 DR/RF（表驱动，替代脆弱的 checkitem_name 前缀判断）
        # device_type_name 取值：DR/移动DR/床旁机/多功能X线机 → DR，RF → RF
        df_xray = df_all[df_all['modality_name'] == 'X线']
        dev = df_xray['device_type_name'].fillna('')

        sub_masks = {
            'RF': dev == 'RF',
            # DR 及其设备变体（移动DR/床旁机/多功能X线机），并兜底空值/未知设备类型
            'DR': ~dev.isin(['RF']),
        }
        for sub, mask in sub_masks.items():
            df_sub = df_xray[mask]
            self.df_standard[sub] = {}
            for ver in df_sub['version'].unique():
                self.df_standard[sub][ver] = df_sub[df_sub['version'] == ver].copy()

    @property
    def is_ready(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

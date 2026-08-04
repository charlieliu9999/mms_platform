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

# B-18修复：进程全局追踪已注册到 jieba 的词条（跨 reload 实例持久化）
_jieba_registered_words: set = set()


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
        global _jieba_registered_words

        result = await conn.execute(text(
            "SELECT word, type FROM nlp_medical_dict WHERE enable = 0"
        ))
        rows = result.fetchall()
        self.mdict = {r[0]: r[1] for r in rows}
        current_words = set(self.mdict.keys())
        logger.info(f"[RuleDataLoader] 加载医学词典: {len(self.mdict)} 词条")

        # B-18修复：热重载时，将已删除的词条从 jieba 全局词典中移除
        removed = _jieba_registered_words - current_words
        if removed:
            for word in removed:
                jieba.del_word(word)
            logger.info(f"[RuleDataLoader] 热重载移除词条: {len(removed)} 个")

        # 注册到 jieba（组合词汇使用更高词频，确保不被拆分）
        for word, wtype in self.mdict.items():
            # 多字组合词（如"双侧乳腺"）需要更高词频以避免被拆分
            if len(word) >= 3 and any(prefix in word for prefix in ['双侧', '左侧', '右侧', '单侧']):
                freq = 999999
            else:
                freq = 883635
            jieba.add_word(word, tag=wtype, freq=freq)

        # 更新全局注册表
        _jieba_registered_words.clear()
        _jieba_registered_words.update(current_words)
        logger.info(
            f"[RuleDataLoader] 更新全局注册表: {len(_jieba_registered_words)} 词条 "
            f"(对象id={id(_jieba_registered_words)})"
        )

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
        """加载标准项目表（B-08修复：统一从 standard_check_items 加载）"""
        result = await conn.execute(text(
            "SELECT modality, body_part_l3, scan_method, post_processing, "
            "body_part_l2, version, item_code, item_name "
            "FROM standard_check_items WHERE is_active = true"
        ))
        rows = result.fetchall()

        # 字段映射：新表 → 旧表字段名（保持引擎内部逻辑不变）
        df_all = pd.DataFrame(rows, columns=[
            'modality', 'body_part_l3', 'scan_method', 'post_processing',
            'body_part_l2', 'version', 'item_code', 'item_name'
        ])

        # 重命名为引擎期望的字段名
        df_all.rename(columns={
            'modality': 'modality_name',
            'body_part_l3': 'three_level_name',
            'body_part_l2': 'position_name',
            'scan_method': 'scan_name',
            'post_processing': 'post_processing_name',
            'item_code': 'checkitem_code',
            'item_name': 'checkitem_name'
        }, inplace=True)

        # 补充引擎需要但新表没有的字段
        df_all['scope_name'] = ''
        df_all['device_type_name'] = ''

        df_all.fillna("", inplace=True)

        # ACR 导入数据用 "-" 表示"无值"（post_processing 947 行、scan_method 244 行），
        # 统一归一化为空串；否则 _query_ct_mr 的 scan 分支要求 post 为空串/NaN，
        # 会漏掉 post='-' 的行（如 MR颅内动脉血管成像(MRA) 无法命中）
        for col in ('three_level_name', 'position_name', 'scan_name', 'post_processing_name'):
            df_all[col] = df_all[col].replace('-', '')

        logger.info(f"[RuleDataLoader] 加载标准项目（从 standard_check_items）: {len(df_all)} 条")

        # 按模态+版本分组
        self._build_standard_indexes(df_all)

    def _build_standard_indexes(self, df_all: pd.DataFrame):
        """构建标准表索引（B-08修复：兼容新表字段）"""
        # 独立模态：直接按 modality_name 分组
        # 注意：RF、PET/CT、PET/MR、SPECT 都是独立模态（modality_name直接等于模态名）
        for modality in ['CT', 'MR', 'DR', 'DSA', 'MG', 'RF', 'SPECT', 'PET/CT', 'PET/MR']:
            df_mod = df_all[df_all['modality_name'] == modality].copy()
            if not df_mod.empty:
                self.df_standard[modality] = {}
                versions = df_mod['version'].fillna('').unique()
                for ver in versions:
                    if ver:  # 跳过空版本
                        self.df_standard[modality][ver] = df_mod[df_mod['version'] == ver].copy()
                logger.info(f"[RuleDataLoader] 加载 {modality} 标准: {len(df_mod)} 条")

        # 注意：新表中 DR 是独立模态，不再需要从 X线 拆分
        # device_type_name 在新表中为空，此逻辑已废弃

    @property
    def is_ready(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

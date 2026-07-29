"""
检查项目匹配引擎 V2 - 重构版本

职责分离架构：
- RuleDataLoader: 规则数据加载
- PreprocessService: 文本预处理
- TokenizerService: 分词和建树
- PatternProcessor: 模式处理
- DisambiguationService: 消歧映射
- StandardLookupService: 标准表查询
- MatchEngineOrchestrator: Pipeline 协调器
"""

from .orchestrator import MatchEngineOrchestrator

__all__ = ['MatchEngineOrchestrator']

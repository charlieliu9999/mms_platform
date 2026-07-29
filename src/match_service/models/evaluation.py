"""
评测系统数据模型
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DECIMAL,
    TIMESTAMP, ARRAY, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from ..cache.models import Base


class EvalTask(Base):
    """评测任务表"""
    __tablename__ = 'mms_eval_tasks'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    test_file_path = Column(String(500))
    sample_size = Column(Integer)
    modality = Column(String(10))  # NULL = 全部

    # 执行状态
    status = Column(String(20), default='pending')  # pending/running/completed/failed
    progress = Column(Integer, default=0)  # 0-100

    # 结果统计
    total_count = Column(Integer, default=0)
    matched_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    wrong_count = Column(Integer, default=0)
    no_match_count = Column(Integer, default=0)

    # 指标
    match_rate = Column(DECIMAL(5, 2))
    accuracy = Column(DECIMAL(5, 2))
    precision_score = Column(DECIMAL(5, 2))
    recall_score = Column(DECIMAL(5, 2))
    f1_score = Column(DECIMAL(5, 2))
    avg_confidence = Column(DECIMAL(5, 3))
    avg_response_time = Column(DECIMAL(10, 2))  # ms

    # 词表版本快照
    dict_version = Column(String(50))
    dict_count = Column(Integer)
    phrase_count = Column(Integer)

    # 时间戳
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    started_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)

    # 元数据
    created_by = Column(String(100))
    tags = Column(ARRAY(String(200)))

    # 关系
    details = relationship("EvalDetail", back_populates="task", cascade="all, delete-orphan")
    suggestions = relationship("OptimizationSuggestion", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_eval_tasks_status', 'status'),
        Index('idx_eval_tasks_created_at', 'created_at'),
    )


class EvalDetail(Base):
    """评测详情表"""
    __tablename__ = 'mms_eval_details'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('mms_eval_tasks.id', ondelete='CASCADE'), nullable=False)

    # 输入
    check_item = Column(Text, nullable=False)
    modality = Column(String(10))
    expected_code = Column(String(50))
    expected_name = Column(String(200))

    # 输出
    actual_code = Column(String(50))
    actual_name = Column(String(200))
    confidence = Column(DECIMAL(5, 3))
    response_time = Column(DECIMAL(10, 2))  # ms

    # 结果分类
    is_matched = Column(Boolean)
    is_correct = Column(Boolean)
    match_type = Column(String(20))  # exact/fuzzy/wrong/none

    # 失败原因分类
    failure_reason = Column(String(50))  # missing_word/ambiguity/complex/algorithm
    failure_detail = Column(Text)

    # 人工审核
    reviewed = Column(Boolean, default=False)
    reviewer = Column(String(100))
    review_note = Column(Text)
    review_time = Column(TIMESTAMP)

    # 优化建议
    suggested_action = Column(String(50))  # add_word/add_phrase/add_rule/algorithm_fix
    suggestion_data = Column(JSONB)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # 关系
    task = relationship("EvalTask", back_populates="details")

    __table_args__ = (
        Index('idx_eval_details_task_id', 'task_id'),
        Index('idx_eval_details_is_correct', 'is_correct'),
        Index('idx_eval_details_failure_reason', 'failure_reason'),
        Index('idx_eval_details_reviewed', 'reviewed'),
    )


class OptimizationSuggestion(Base):
    """优化建议表"""
    __tablename__ = 'mms_optimization_suggestions'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('mms_eval_tasks.id'), nullable=False)

    # 建议类型
    suggestion_type = Column(String(50), nullable=False)  # add_medical_dict/add_phrase_map/add_ambiguity_rule
    priority = Column(Integer, default=5)  # 1-10

    # 建议内容
    word = Column(String(200))
    type = Column(String(50))
    source_phrase = Column(String(200))
    target_phrase = Column(String(200))
    step = Column(String(50))

    # 影响范围
    affected_count = Column(Integer)
    example_cases = Column(ARRAY(Text))

    # 状态
    status = Column(String(20), default='pending')  # pending/approved/rejected/applied
    applied_at = Column(TIMESTAMP)

    # 人工审核
    reviewed_by = Column(String(100))
    review_note = Column(Text)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # 关系
    task = relationship("EvalTask", back_populates="suggestions")

    __table_args__ = (
        Index('idx_optimization_suggestions_task_id', 'task_id'),
        Index('idx_optimization_suggestions_status', 'status'),
        Index('idx_optimization_suggestions_priority', 'priority'),
    )


class LexiconVersion(Base):
    """词表版本表"""
    __tablename__ = 'mms_lexicon_versions'

    id = Column(Integer, primary_key=True)
    version = Column(String(50), unique=True, nullable=False)
    description = Column(Text)

    # 词表统计
    medical_dict_count = Column(Integer)
    phrase_map_count = Column(Integer)
    ambiguity_rule_count = Column(Integer)

    # 变更内容
    changelog = Column(Text)
    added_words = Column(Integer, default=0)
    updated_words = Column(Integer, default=0)
    deleted_words = Column(Integer, default=0)

    # 性能指标
    match_rate = Column(DECIMAL(5, 2))
    accuracy = Column(DECIMAL(5, 2))
    f1_score = Column(DECIMAL(5, 2))

    # 状态
    is_active = Column(Boolean, default=False)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    created_by = Column(String(100))

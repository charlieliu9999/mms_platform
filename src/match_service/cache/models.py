import hashlib
import json
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class MatchCache(Base):
    """L1 映射库：已确认的 procedure → standard 映射缓存"""

    __tablename__ = "match_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text_hash = Column(String(64), nullable=False, index=True)
    modality = Column(String(20), nullable=False)
    original_text = Column(Text, nullable=False)
    result_json = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    source = Column(String(30), nullable=False, default="algorithm")
    hit_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())
    confirmed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_match_cache_lookup", "text_hash", "modality", unique=True),
        Index("ix_match_cache_confidence", "confidence"),
    )

    @staticmethod
    def compute_hash(text: str, modality: str) -> str:
        normalized = text.strip().lower().replace(" ", "")
        raw = f"{normalized}|{modality.upper()}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get_result(self) -> dict:
        return json.loads(self.result_json)

    @staticmethod
    def make_result_json(result: dict) -> str:
        return json.dumps(result, ensure_ascii=False)


class MatchFeedback(Base):
    """匹配反馈记录：用于 Agent 学习和算法进化"""

    __tablename__ = "match_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text_hash = Column(String(64), nullable=False, index=True)
    modality = Column(String(20), nullable=False)
    original_text = Column(Text, nullable=False)
    engine_result_json = Column(Text, nullable=True)
    engine_tier = Column(String(20), nullable=True)
    feedback_type = Column(String(30), nullable=False)
    suggested_fix = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_match_feedback_status", "status", "feedback_type"),
    )


class LexiconSuggestion(Base):
    """Agent 生成的词典/规则补充建议"""

    __tablename__ = "lexicon_suggestion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    suggestion_type = Column(String(30), nullable=False)
    modality = Column(String(20), nullable=True)
    content_json = Column(Text, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    applied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

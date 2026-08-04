from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class MatchRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="检查项目原始文本")
    text: Optional[str] = Field(default=None, description="检查项目原始文本（name 的别名，兼容历史调用方）")
    modality: str = Field(..., description="影像模态 (CT/MR/DR/US/SPECT/PET/CT 等)")
    version: str = Field(default="V3.8.2", description="规则版本")

    @model_validator(mode="after")
    def _check_name_or_text(self):
        if not (self.name or self.text):
            raise ValueError("name 或 text 至少提供一个")
        if not self.name:
            self.name = self.text
        return self


class BatchItem(BaseModel):
    key: Optional[str] = Field(default=None, description="业务唯一标识（缺省时用 name 填充）")
    name: Optional[str] = Field(default=None, description="检查项目原始文本")
    text: Optional[str] = Field(default=None, description="检查项目原始文本（name 的别名）")
    modality: str = Field(..., description="影像模态")

    @model_validator(mode="after")
    def _check_name_or_text(self):
        if not (self.name or self.text):
            raise ValueError("name 或 text 至少提供一个")
        if not self.name:
            self.name = self.text
        if not self.key:
            self.key = self.name
        return self


class BatchRequest(BaseModel):
    items: List[BatchItem] = Field(..., description="批量匹配项")
    version: str = Field(default="V3.8.2", description="规则版本")


class MatchResult(BaseModel):
    check_item: str
    num_standard: int
    data: list
    score: float
    tier: str
    confidence: float
    reason: Optional[str] = ""
    has_entity: Optional[bool] = None
    cache_hit: bool = False
    cache_source: Optional[str] = None


class BatchResponse(BaseModel):
    results: dict
    stats: dict
    rule_version: str


class CacheStoreRequest(BaseModel):
    text: str
    modality: str
    result: dict
    confidence: float = 1.0
    source: str = "manual"


class CacheInvalidateRequest(BaseModel):
    modality: Optional[str] = None


class FeedbackItem(BaseModel):
    text: str
    modality: str
    correct_result: Optional[dict] = None
    comment: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    rule_version: str
    engine_ready: bool
    cache_stats: Optional[dict] = None

"""
L3 Agent 审核器 — 对算法匹配结果进行审核和进化

工作模式：
  A. 审核确认：对 tier=exact/partial 的结果抽样验证，确认后入 L1
  B. 进化修复：对 lexicon_gap 项分析文本，生成词典补充建议
  C. 语义兜底：对 standard_lib_gap 项用 LLM 语义匹配

当前为 P2 阶段骨架，核心逻辑后续迭代填充。
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..cache.models import LexiconSuggestion, MatchFeedback

logger = logging.getLogger(__name__)


class MatchReviewer:
    """Agent 审核器"""

    def __init__(self, session: AsyncSession, llm_client=None):
        self.session = session
        self.llm_client = llm_client

    async def review_batch(self, limit: int = 50) -> dict:
        """审核待处理的 feedback 记录"""
        from sqlalchemy import select

        stmt = (
            select(MatchFeedback)
            .where(MatchFeedback.status == "pending")
            .order_by(MatchFeedback.created_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        pending = result.scalars().all()

        reviewed = 0
        suggestions = 0
        for fb in pending:
            action = await self._analyze_feedback(fb)
            fb.status = action
            if action == "suggestion_created":
                suggestions += 1
            reviewed += 1

        await self.session.commit()
        return {"reviewed": reviewed, "suggestions": suggestions}

    async def _analyze_feedback(self, fb: MatchFeedback) -> str:
        """分析单条 feedback，决定处理路径

        分类优先级：
        1. feedback_type 直接携带 reason_code（迁移数据）→ 按类型分派
        2. 引擎实时结果 → 按 has_entity 判断
        3. 无法判断 → needs_manual
        """
        if fb.feedback_type == "manual_correction":
            return "resolved"

        if fb.feedback_type == "unmatchable_by_design":
            return "wontfix"

        if fb.feedback_type == "standard_lib_gap":
            await self._suggest_standard_entry(fb)
            return "suggestion_created"

        if fb.feedback_type == "lexicon_gap":
            await self._suggest_lexicon_entry(fb)
            return "suggestion_created"

        if fb.engine_tier == "none":
            has_entity = self._check_has_entity(fb)
            if not has_entity:
                await self._suggest_lexicon_entry(fb)
            else:
                await self._suggest_standard_entry(fb)
            return "suggestion_created"

        return "needs_manual"

    def _check_has_entity(self, fb: MatchFeedback) -> bool:
        """从引擎结果判断是否解析出了医学实体"""
        import json

        if not fb.engine_result_json:
            return False
        try:
            result = json.loads(fb.engine_result_json)
            return result.get("has_entity", False)
        except (json.JSONDecodeError, TypeError):
            return False

    async def _suggest_lexicon_entry(self, fb: MatchFeedback):
        """生成词典补充建议（lexicon_gap）"""
        import json

        suggestion = LexiconSuggestion(
            suggestion_type="lexicon_gap",
            modality=fb.modality,
            content_json=json.dumps(
                {"text": fb.original_text, "action": "add_to_medical_dict"},
                ensure_ascii=False,
            ),
            reason=f"引擎未解析出医学实体: {fb.original_text[:100]}",
            status="pending",
        )
        self.session.add(suggestion)

    async def _suggest_standard_entry(self, fb: MatchFeedback):
        """生成标准库补项建议（standard_lib_gap）"""
        import json

        suggestion = LexiconSuggestion(
            suggestion_type="standard_lib_gap",
            modality=fb.modality,
            content_json=json.dumps(
                {"text": fb.original_text, "action": "add_to_standard_table"},
                ensure_ascii=False,
            ),
            reason=f"解析出实体但标准库无对应: {fb.original_text[:100]}",
            status="pending",
        )
        self.session.add(suggestion)

    async def get_pending_suggestions(self, limit: int = 100) -> list:
        """获取待审批的词典/规则建议"""
        from sqlalchemy import select

        stmt = (
            select(LexiconSuggestion)
            .where(LexiconSuggestion.status == "pending")
            .order_by(LexiconSuggestion.created_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def approve_suggestion(self, suggestion_id: int) -> dict:
        """审批通过一条建议（后续对接 lexicon_api /reload）"""
        from sqlalchemy import select

        stmt = select(LexiconSuggestion).where(LexiconSuggestion.id == suggestion_id)
        result = await self.session.execute(stmt)
        suggestion = result.scalar_one_or_none()
        if not suggestion:
            return {"status": "not_found"}

        suggestion.status = "approved"
        from datetime import datetime
        suggestion.applied_at = datetime.utcnow()
        await self.session.commit()
        return {"status": "approved", "id": suggestion_id}

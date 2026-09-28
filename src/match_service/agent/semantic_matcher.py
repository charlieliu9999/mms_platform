"""
L3 LLM 语义匹配器 — 对算法引擎无法解决的 standard_lib_gap 项进行语义兜底

工作流程：
1. 从 standard_check_items 表按 modality 加载候选标准项
2. 用文本相似度（关键词重叠 + 编辑距离）预筛 Top-K 候选
3. 调 LLM 判断语义等价性，输出结构化 JSON
4. 高置信（≥0.85）→ 写入 L1 映射库
5. 低置信 → 推人工审核

支持 OpenAI / DashScope / 任意 OpenAI-compatible API。
"""
import json
import logging
from typing import Optional

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..cache.models import MatchCache
from ..cache.service import CacheService
from ..config import get_settings

logger = logging.getLogger(__name__)

SEMANTIC_MATCH_PROMPT = """你是医学影像检查项目标准化专家。

任务：判断「待匹配项」与「候选标准项」是否语义等价（即临床上指同一检查）。

判断标准：
- 检查部位相同或等价（如"头部"="颅脑"，"腰椎"="腰段脊柱"）
- 检查方式/序列相同（如"平扫"="常规扫描"，"增强"="增强扫描"）
- 模态一致（CT对CT，MR对MR）
- 允许名称表述差异，但临床含义必须一致

输出严格 JSON（不要其他文字）：
{{"match": true/false, "confidence": 0.0-1.0, "standard_code": "匹配的标准项code或空", "standard_name": "匹配的标准项名称或空", "reason": "简要理由"}}

待匹配项：
- 原文：{query_text}
- 模态：{modality}

候选标准项（按相似度排序）：
{candidates}

请判断待匹配项是否与某个候选标准项语义等价。如果都不匹配，返回 match=false。"""


class LLMSemanticMatcher:
    """LLM 语义匹配器"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._settings = get_settings()
        self._standard_cache: dict[str, list[dict]] = {}

    async def initialize(self):
        """预加载标准项到内存（按 modality 分组）"""
        result = await self.session.execute(text(
            "SELECT item_code, item_name, modality, body_part_l2, scan_method "
            "FROM standard_check_items WHERE is_active = true "
            "ORDER BY modality, item_code"
        ))
        rows = result.fetchall()
        for code, name, modality, body, scan in rows:
            self._standard_cache.setdefault(modality, []).append({
                "code": code,
                "name": name,
                "body": body or "",
                "scan": scan or "",
            })
        total = sum(len(v) for v in self._standard_cache.values())
        logger.info(f"[LLMSemanticMatcher] 加载 {total} 条标准项, {len(self._standard_cache)} 个模态")

    async def match_one(self, query_text: str, modality: str) -> Optional[dict]:
        """对单条未匹配项进行 LLM 语义匹配

        Returns:
            匹配结果 dict（含 confidence）或 None（无法匹配）
        """
        candidates = self._retrieve_candidates(query_text, modality, top_k=8)
        if not candidates:
            logger.debug(f"[LLMSemantic] 无候选: {query_text[:30]} ({modality})")
            return None

        prompt = self._build_prompt(query_text, modality, candidates)
        llm_response = await self._call_llm(prompt)
        if not llm_response:
            return None

        parsed = self._parse_response(llm_response)
        if not parsed or not parsed.get("match"):
            return None

        confidence = parsed.get("confidence", 0.0)
        return {
            "check_item": query_text,
            "num_standard": 1,
            "data": [{
                "raw": query_text,
                "standard": [{
                    "code": parsed.get("standard_code", ""),
                    "name": parsed.get("standard_name", ""),
                }],
            }],
            "score": int(confidence * 10),
            "tier": "exact" if confidence >= 0.9 else "partial",
            "confidence": confidence,
            "reason": parsed.get("reason", ""),
            "has_entity": True,
            "_source": "llm_semantic",
        }

    async def batch_semantic_match(
        self, items: list[dict], auto_cache_threshold: float = 0.85
    ) -> dict:
        """批量语义匹配 + 自动入缓存

        Args:
            items: [{"text": "...", "modality": "CT"}, ...]
            auto_cache_threshold: 置信度阈值，超过则自动写入 L1

        Returns:
            {"matched": n, "cached": n, "failed": n, "results": [...]}
        """
        if not self._standard_cache:
            await self.initialize()

        cache_service = CacheService(self.session)
        from ..core.engine_holder import get_engine_holder
        rule_version = get_engine_holder().rule_version
        matched = 0
        cached = 0
        failed = 0
        results = []

        for item in items:
            text_val = item.get("text", "")
            modality = item.get("modality", "")

            result = await self.match_one(text_val, modality)
            if result and result["confidence"] >= auto_cache_threshold:
                await cache_service.store(
                    text_val,
                    modality,
                    result,
                    result["confidence"],
                    "llm_semantic",
                    rule_version,
                )
                cached += 1
                matched += 1
            elif result:
                matched += 1
            else:
                failed += 1

            results.append({
                "text": text_val,
                "modality": modality,
                "result": result,
            })

        await self.session.commit()
        return {
            "matched": matched,
            "cached": cached,
            "failed": failed,
            "total": len(items),
            "results": results,
        }

    def _retrieve_candidates(
        self, query_text: str, modality: str, top_k: int = 8
    ) -> list[dict]:
        """基于关键词重叠的候选预筛"""
        pool = self._standard_cache.get(modality, [])
        if not pool:
            for m, items in self._standard_cache.items():
                if m.upper() == modality.upper():
                    pool = items
                    break
        if not pool:
            return []

        query_chars = set(query_text.replace(" ", ""))
        query_lower = query_text.lower()

        scored = []
        for item in pool:
            name = item["name"]
            name_chars = set(name.replace(" ", ""))
            overlap = len(query_chars & name_chars)
            union = len(query_chars | name_chars)
            char_sim = overlap / union if union > 0 else 0

            bonus = 0
            body = item.get("body", "")
            scan = item.get("scan", "")
            if body and body in query_text:
                bonus += 0.3
            if scan and scan in query_text:
                bonus += 0.2
            if name in query_text or query_text in name:
                bonus += 0.5

            scored.append((char_sim + bonus, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def _build_prompt(
        self, query_text: str, modality: str, candidates: list[dict]
    ) -> str:
        cand_lines = []
        for i, c in enumerate(candidates, 1):
            cand_lines.append(
                f"{i}. [{c['code']}] {c['name']} "
                f"(部位: {c.get('body', '-')}, 方式: {c.get('scan', '-')})"
            )
        return SEMANTIC_MATCH_PROMPT.format(
            query_text=query_text,
            modality=modality,
            candidates="\n".join(cand_lines),
        )

    async def _call_llm(self, prompt: str) -> Optional[str]:
        """调用 LLM API（OpenAI-compatible）"""
        settings = self._settings
        api_base = settings.LLM_API_BASE
        api_key = settings.LLM_API_KEY
        model = settings.LLM_MODEL

        if not api_base or not api_key:
            import os
            api_base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            api_key = os.getenv("OPENAI_API_KEY", "")
            model = model or "gpt-4o-mini"

        if not api_key:
            logger.warning("[LLMSemantic] 无 LLM API Key，跳过语义匹配")
            return None

        url = f"{api_base.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是医学影像标准化专家，输出严格JSON。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 4000,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                message = data["choices"][0]["message"]
                content = message.get("content") or ""
                if not content.strip():
                    reasoning = message.get("reasoning") or message.get("reasoning_content") or ""
                    json_start = reasoning.rfind("{")
                    if json_start >= 0:
                        content = reasoning[json_start:]
                return content if content.strip() else None
        except Exception as e:
            logger.error(f"[LLMSemantic] LLM 调用失败: {type(e).__name__}: {e}")
            return None

    @staticmethod
    def _parse_response(response: str) -> Optional[dict]:
        """解析 LLM 返回的 JSON（兼容 thinking 模型在 JSON 前后输出推理文本）"""
        import re

        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            result = json.loads(text)
            if isinstance(result, dict) and "match" in result:
                return result
        except json.JSONDecodeError:
            pass

        candidates = []
        for m in re.finditer(r'\{[^{}]*\}', text):
            try:
                obj = json.loads(m.group())
                if isinstance(obj, dict) and "match" in obj:
                    candidates.append(obj)
            except json.JSONDecodeError:
                continue

        if candidates:
            return candidates[-1]

        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                result = json.loads(text[start:end])
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass

        repaired = LLMSemanticMatcher._repair_truncated_json(text)
        if repaired:
            return repaired

        logger.warning(f"[LLMSemantic] 无法解析 LLM 响应: {text[:100]}")
        return None

    @staticmethod
    def _repair_truncated_json(text: str) -> Optional[dict]:
        """修复被截断的 JSON（thinking 模型 token 耗尽时 content 被切断）"""
        start = text.find('{"match"')
        if start < 0:
            start = text.find("{")
        if start < 0:
            return None

        fragment = text[start:]
        for suffix in ['"}', '"}', "}", '"]}', "]}"]:
            try:
                obj = json.loads(fragment + suffix)
                if isinstance(obj, dict) and "match" in obj:
                    return obj
            except json.JSONDecodeError:
                continue

        import re
        keys_found = re.findall(r'"(\w+)"\s*:', fragment)
        if "match" in keys_found:
            match_val = re.search(r'"match"\s*:\s*(true|false)', fragment)
            conf_val = re.search(r'"confidence"\s*:\s*([\d.]+)', fragment)
            code_val = re.search(r'"standard_code"\s*:\s*"([^"]*)"', fragment)
            name_val = re.search(r'"standard_name"\s*:\s*"([^"]*)"', fragment)
            if match_val:
                return {
                    "match": match_val.group(1) == "true",
                    "confidence": float(conf_val.group(1)) if conf_val else 0.5,
                    "standard_code": code_val.group(1) if code_val else "",
                    "standard_name": name_val.group(1) if name_val else "",
                    "reason": "repaired_from_truncated",
                }
        return None

"""基于检查项目文本解析实际执行模态。

procedure_dictionary.modality 是上游来源字段，历史数据中存在 OTHER/IR/XR 等
混合桶。这里仅实现高确定性规则；联合检查保留原模态，交给子项拆分处理，
避免把整条联合项目错误路由到其中一个模态。
"""
from __future__ import annotations

import re
from typing import Optional


_XR_PREFIX = re.compile(r"^\s*X\s*线", re.IGNORECASE)


def mentioned_modalities(text: str) -> set[str]:
    """提取文本中显式出现的模态，用于阻止联合/混合项目整条改路由。"""
    upper = str(text or "").upper()
    mentions: set[str] = set()

    composite_patterns = [
        (r"PET\s*[-/]?\s*(?:MRI|MR)(?![A-Z])", "PET/MR"),
        (r"PET\s*[-/]?\s*CT(?![A-Z])", "PET/CT"),
        (r"SPECT\s*/\s*CT", "SPECT"),
    ]
    remaining = upper
    for pattern, modality in composite_patterns:
        if re.search(pattern, remaining):
            mentions.add(modality)
            remaining = re.sub(pattern, " ", remaining)

    token_patterns = [
        (r"(?:^|[,，+;/]|联合)\s*(?:MRI|MRA|MRV|MR)(?![A-Z])", "MR"),
        (r"(?:^|[,，+;/]|联合)\s*(?:CTA|CT)(?![A-Z])", "CT"),
        (r"(?:^|[,，+;/]|联合)\s*(?:US|ULTRASOUND)(?![A-Z])", "US"),
        (r"(?:^|[,，+;/]|联合)\s*(?:DSA|ANGIO)(?![A-Z])", "DSA"),
        (r"(?:^|[,，+;/]|联合)\s*(?:SPECT|ECT)(?![A-Z])", "SPECT"),
        (r"(?:^|[,，+;/]|联合)\s*(?:DR|CR)(?![A-Z])", "DR"),
        (r"(?:^|[,，+;/]|联合)\s*RF(?![A-Z])", "RF"),
        (r"(?:^|[,，+;/]|联合)\s*MG(?![A-Z])", "MG"),
    ]
    for pattern, modality in token_patterns:
        if re.search(pattern, remaining):
            mentions.add(modality)
    if re.search(r"(?:^|[,，+;/]|联合)\s*X\s*线", str(text or ""), re.I):
        mentions.add("DR")
    if re.search(r"超声|彩超", str(text or ""), re.I):
        mentions.add("US")
    if re.search(r"(?:AS-)?OCT", upper):
        mentions.add("OCT")
    return mentions


def infer_text_modality(text: str) -> Optional[str]:
    """从文本中推断高确定性的标准模态；无法确定时返回 ``None``。"""
    raw = str(text or "").strip()
    upper = raw.upper()
    if not raw:
        return None

    # 组合模态必须优先识别，避免 PET/MRI 被普通 MR 规则截断。
    if re.search(r"PET\s*[-/]?\s*(MRI|MR)(?![A-Z])", upper):
        return "PET/MR"
    if re.search(r"PET\s*[-/]?\s*CT(?![A-Z])", upper):
        return "PET/CT"
    if re.match(r"^\s*(SPECT|ECT)(?![A-Z])", upper):
        return "SPECT"
    if re.match(r"^\s*(DSA|ANGIO)(?![A-Z])", upper):
        return "DSA"
    if re.match(r"^\s*(移动\s*)?(DR|CR)(?![A-Z])", upper):
        return "DR"
    if re.match(r"^\s*(MRI|MRA|MRV|MR)(?![A-Z])", upper):
        return "MR"
    if re.match(r"^\s*(CTA|CT)(?![A-Z])", upper):
        return "CT"
    if re.match(r"^\s*(US|ULTRASOUND)(?![A-Z])", upper):
        return "US"
    if re.match(r"^\s*RF(?![A-Z])", upper):
        return "RF"
    if re.match(r"^\s*MG(?![A-Z])", upper):
        return "MG"
    if re.match(r"^\s*(?:AS-)?OCT(?![A-Z])", upper):
        return "OCT"
    if re.match(r"^\s*ES(?![A-Z])", upper):
        return "ES"

    if _XR_PREFIX.match(raw):
        if re.search(r"乳腺|乳房|钼靶|CEM|TOMO", raw, re.IGNORECASE):
            if re.search(r"VABB|穿刺|活检|定位", upper):
                return None
            return "MG"
        if re.search(r"DSA|冠状动脉|肾动脉|血管造影", raw, re.IGNORECASE):
            # QFR/FFR 等是复合功能评估；仅命中“冠状动脉造影”不能代表
            # 整条项目已完整匹配，因此不做整条自动路由。
            if re.search(r"QFR|FFR|取栓|溶栓|栓塞|支架|成形", upper):
                return None
            return "DSA"
        if "造影" in raw:
            return "RF"
        return "DR"

    # 无模态前缀但检查方式足够明确的历史数据。
    if re.search(r"超声|彩超|(?<![A-Z])IVUS(?![A-Z])|(?<![A-Z])TCD(?![A-Z])", raw, re.IGNORECASE):
        return "US"
    if re.search(r"冠状动脉造影|侵入性.*血管造影|有创.*血管造影", raw):
        if re.search(r"QFR|FFR|取栓|溶栓|栓塞|支架|成形", upper):
            return None
        return "DSA"
    if re.search(r"MRA|MRV", upper):
        return "MR"
    if re.match(r"^\s*核素", raw):
        return "SPECT"

    return None


def resolve_effective_modality(text: str, source_modality: str) -> str:
    """返回实际送入引擎的模态。

    联合检查不能整体改路由；唯一标准名称层仍可在引擎内处理标准库中已明确
    建模的组合项目。
    """
    source = str(source_modality or "").upper().strip()
    raw = str(text or "")
    if "联合" in raw or len(mentioned_modalities(raw)) > 1:
        return source

    inferred = infer_text_modality(raw)
    return inferred or source

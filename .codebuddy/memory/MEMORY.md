# 项目长期记忆

## 算法架构核心事实（2026-08-02 确认）

### 三层调度
- L0 模态归一化 → L1 SHA256 缓存 → L2 算法引擎 → L3 LLM 兜底
- L2 有两个子引擎：NLP Pipeline (CT/MR/DR/RF/MG) + Keyword Engine (US/SPECT/PET/CT/PET/MR/OCT/DSA)

### NLP Pipeline 是 10 步（非 6 步）
1. preprocess（5步文本清洗）
2. split_record（分割+子项模态检测 _detect_modality）
3. make_tree（jieba分词+MatchNode构建）
4. process_by_pattern（B(B)合并 + BSPB分裂）
5. merge_no_body（无部位节点合并）
6. split_multi_body（多部位节点分裂）
7. merge_nodes（节点间上下位合并）
8. body_2process_remap（3步级联×5步_db_disambiguity）
8.5. normalize_vascular_nodes（CTA/CTV/MRA/MRV归一化）
9. find_default_process（默认处理方式填充）
10. lookup_standard（标准项查询，DR有3级降级）

### 模态识别是三级机制
1. 入口：_normalize_modality()（20+别名映射）
2. 分发：NLP_MODALITIES vs KW_MODALITIES 集合判定
3. 子项：_detect_modality()（split_record中，处理跨模态混合医嘱）

### 置信度是 tier-based（非100分制）
exact(1.0) / partial(0.8) / degraded(0.6) / ambiguous(0.4) / none(0.0) / error(0.0)

### DR 特殊性
- 用 position（正位/侧位）作为 process_type，非 scan
- 查询有3级降级：POSITION_FALLBACK → POSITION_DECOMPOSE → POSITION_CONTAINS

### 数据表
- nlp_medical_dict(2,435) / nlp_phrase_map(7,839) / nlp_ambiguity(1,229) / nlp_checkitem_standard
- keyword_match_rules（关键词引擎单一真相源）
- DR 标准项从 X线模态按 device_type_name 过滤派生

## 算法漏洞修复状态（2026-08-02）

### 已修复（8 个 Critical+High，21 个验证测试通过）
- ✅ C1: preprocess 保护 CE-MRA/CE-MRV/CE-CT 连字符（占位符替换法）
- ✅ C2: merge_nodes 合并后重新计算 body_0/process_0
- ✅ C3: TokenizerService.clear_cache() + orchestrator 热重载时调用
- ✅ C4: matcher._last_tier 属性 + orchestrator._kw_match 读取（降级→degraded/0.6）
- ✅ H1: SPECT/PET/OCT 添加 unmatchable 排除检查
- ✅ H2: _extract_pet_body 默认返回 None（不再回退 '躯干'）
- ✅ H3: 脊椎正则改用 (?:C|颈) 非捕获组
- ✅ H4: _query_spect 返回全部结果 + 多结果标记 degraded

### 待修复（5 Medium + 3 Low）
- M1-M5 和 L1-L3 见 algorithm-issues-report.html

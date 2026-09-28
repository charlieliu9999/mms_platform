# 领域概念

> MMS 平台核心领域概念与业务术语

## 医学影像检查项目

### 检查项目 (Procedure Item)
医学影像科室执行的具体检查项目，例如：
- `CT头部平扫`
- `MR腰椎平扫+增强`
- `双侧膝关节正、侧位`

**特征**：
- 自由文本输入，表达方式多样
- 包含模态、部位、对比剂、体位等多维信息
- 可能包含别名、简称、方言

### 标准项目 (Standard Item)
规范化后的检查项目名称，用于：
- 计费编码
- 统计分析
- 跨机构数据交换
- 质控管理

**来源**：
- ACR (美国放射学会) 编码体系
- 医院内部编码
- 国家标准 (如 DICOM)

**数据库表**：`mms_standard_item`

---

## 影像模态 (Modality)

### 定义
影像检查使用的设备类型或成像方式。

### 支持的模态

| 模态 | 全称 | 匹配引擎 | 示例 |
|------|------|---------|------|
| **CT** | Computed Tomography | NLP Pipeline | CT头部平扫 |
| **MR** | Magnetic Resonance | NLP Pipeline | MR腰椎平扫+增强 |
| **DR** | Digital Radiography | NLP Pipeline | 双侧膝关节正、侧位 |
| **RF** | Radiofluoroscopy | NLP Pipeline | 消化道造影 |
| **MG** | Mammography | NLP Pipeline | 乳腺钼靶 |
| **US** | Ultrasound | 关键词引擎 | 腹部超声 |
| **SPECT** | Single Photon Emission CT | 关键词引擎 | 心肌灌注显像 |
| **PET** | Positron Emission Tomography | 关键词引擎 | 全身PET-CT |
| **OCT** | Optical Coherence Tomography | 关键词引擎 | 眼底OCT |
| **DSA** | Digital Subtraction Angiography | 关键词引擎 | 冠状动脉造影 |

### 匹配策略差异

**NLP Pipeline 模态** (CT/MR/DR/RF/MG)：
- 复杂语法结构
- 需要分词、消歧、语义理解
- 10 步处理流程

**关键词引擎模态** (US/SPECT/PET/OCT/DSA)：
- 相对规范的表达
- 基于部位和检查类型关键词匹配
- 3 步处理流程

---

## 匹配引擎核心概念

### 1. 医学词典 (Medical Dictionary)

**用途**：Jieba 分词词库，提高医学术语分词准确性

**表结构**：`nlp_medical_dict`
```sql
CREATE TABLE nlp_medical_dict (
    id SERIAL PRIMARY KEY,
    word VARCHAR(200),        -- 词条，如 "头部"
    type VARCHAR(50),         -- 类型：body_part/process/modifier
    enable INTEGER DEFAULT 0  -- 启用状态
);
```

**词条类型**：
- `body_part`：部位词（头部、腹部、膝关节）
- `process`：检查过程（平扫、增强、造影）
- `modifier`：修饰词（双侧、左侧、高分辨）

**规模**：2,435 条

**示例**：
```
头部     | body_part  | 0
颈椎     | body_part  | 0
平扫     | process    | 0
增强     | process    | 0
双侧     | modifier   | 0
```

### 2. 短语映射 (Phrase Map)

**用途**：将别名、方言、简称统一为标准表达

**表结构**：`nlp_phrase_map`
```sql
CREATE TABLE nlp_phrase_map (
    id SERIAL PRIMARY KEY,
    src_process VARCHAR(200),   -- 原始表达
    dst_process VARCHAR(200),   -- 标准表达
    modality VARCHAR(50),       -- 适用模态
    version VARCHAR(50)         -- 版本号
);
```

**规模**：7,839 条

**示例**：
```
src_process       | dst_process  | modality
------------------|--------------|----------
脑袋              | 头部         | CT
增强扫描          | 增强         | CT/MR
MRA               | 血管成像     | MR
CTA               | 血管成像     | CT
正侧位            | 正、侧位     | DR
```

### 3. 消歧规则 (Ambiguity Rule)

**用途**：解决一词多义、语境歧义

**表结构**：`nlp_ambiguity`
```sql
CREATE TABLE nlp_ambiguity (
    id SERIAL PRIMARY KEY,
    src_process VARCHAR(200),   -- 歧义表达
    dst_process VARCHAR(200),   -- 消歧后表达
    modality VARCHAR(50),       -- 适用模态
    version VARCHAR(50)         -- 版本号
);
```

**规模**：1,229 条

**示例**：
```
src_process       | dst_process  | modality | 说明
------------------|--------------|----------|------
平扫+增强         | 平扫 增强    | CT       | 拆分为两个检查
正侧位            | 正位 侧位    | DR       | 拆分为两个体位
[薄层]            | (空)         | CT       | 剥离方括号修饰
```

### 4. 标准项目库 (Standard Item)

**用途**：存储规范化的检查项目定义

**表结构**：`mms_standard_item`
```sql
CREATE TABLE mms_standard_item (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200),           -- 标准名称
    modality VARCHAR(50),        -- 模态
    body_part VARCHAR(200),      -- 部位
    process VARCHAR(200),        -- 检查过程
    contrast VARCHAR(50),        -- 对比剂 (with/without/NA)
    laterality VARCHAR(50),      -- 侧别 (left/right/bilateral)
    position VARCHAR(100),       -- 体位 (DR 专用)
    acr_code VARCHAR(100),       -- ACR 编码
    version VARCHAR(50),         -- 版本号
    source VARCHAR(50)           -- 来源 (ACR/internal)
);
```

**规模**：~3,000 条

**示例**：
```
name                    | modality | body_part | process  | contrast
------------------------|----------|-----------|----------|----------
CT头部平扫               | CT       | 头部      | 平扫     | without
CT头部增强               | CT       | 头部      | 增强     | with
MR腰椎平扫               | MR       | 腰椎      | 平扫     | without
双膝关节正、侧位         | DR       | 膝关节    | 正、侧位 | NA
```

---

## 匹配流程核心概念

### 1. 匹配置信度 (Confidence)

**定义**：匹配结果的可信度，范围 [0.0, 1.0]

**分层**：
- `1.0`：精确匹配（exact match）
- `0.9`：部分匹配，字段完全对齐
- `0.8`：部分匹配，存在模糊字段
- `< 0.8`：低置信度，需要 Agent 介入

**用途**：
- 缓存策略：仅缓存 ≥ 0.8 的结果
- 反馈触发：< 0.8 自动记录到 `match_feedback`
- 质量评估：统计高置信度比例

### 2. 匹配层级 (Tier)

**定义**：匹配结果来源的层级

**分类**：
- `L1`：缓存命中（match_cache）
- `L2-NLP`：NLP Pipeline 匹配
- `L2-Keyword`：关键词引擎匹配
- `L3-Agent`：AI Agent 语义匹配

**性能特征**：
```
L1:        < 10 ms    (70% 命中率)
L2-NLP:    50-200 ms  (20% 请求)
L2-Keyword: 20-50 ms  (5% 请求)
L3-Agent:  2-5 s      (5% 请求，异步)
```

### 3. 版本指纹 (Rule Version)

**定义**：词表内容的 SHA-256 哈希值

**计算逻辑**：
```python
# src/match_service/core/rule_version.py
def compute_version(medical_dict, phrase_map, ambiguity):
    """基于词表内容计算 SHA-256"""
    content = ""
    content += serialize(medical_dict)
    content += serialize(phrase_map)
    content += serialize(ambiguity)
    hash_val = hashlib.sha256(content.encode()).hexdigest()[:12]
    count = len(medical_dict) + len(phrase_map) + len(ambiguity)
    return f"v{count}-{hash_val}"
```

**示例**：`v13755-761ba9a916fa`
- `13755`：词表总数
- `761ba9a916fa`：SHA-256 前 12 位

**用途**：
- 灰度部署：确保新旧服务使用相同词表版本
- 缓存失效：版本变更时自动清空缓存
- 故障排查：快速定位词表差异

---

## 双侧推断 (Bilateral Inference)

### 定义
当检查项目未明确指定左/右侧别时，优先匹配双侧标准项目。

### 医学背景
放射科实际操作中：
- `膝关节正、侧位` 默认指 **双侧膝关节**
- 单侧检查会明确标注：`左膝关节正、侧位`

### 匹配规则
```
输入: "膝关节正、侧位" (无侧别)
  ↓
1. 查询标准库:
   - 双膝关节正、侧位  ← 优先匹配
   - 左膝关节正、侧位  (权重降低)
   - 右膝关节正、侧位  (权重降低)

输入: "左膝关节正、侧位" (明确侧别)
  ↓
2. 查询标准库:
   - 左膝关节正、侧位  ← 精确匹配
   - 双膝关节正、侧位  (不匹配)
```

### 实现模块
- NLP Pipeline: `standard_lookup_service.py`
- DR 引擎: `keyword/dr_engine.py` (待实现)

---

## 扫描组合 (Scan Combination)

### 定义
单次检查包含多个子检查的组合，如 `平扫+增强`。

### 拆分规则

**组合输入**：
```
CT头部平扫+增强
  ↓ 拆分
CT头部平扫 (without contrast)
CT头部增强 (with contrast)
```

**拆分标记**：
- `+`：加号分隔
- `、`：顿号分隔（某些场景）
- `及`：连词分隔

### 降级匹配

当组合无法匹配时，尝试单项匹配：
```
输入: "CT头部平扫+动态增强"
  ↓ 标准库无 "动态增强" 项
  ↓ 降级
匹配: "CT头部平扫" (单项)
置信度: 0.7 (降级)
```

### 实现模块
- `preprocess_service.py`：识别组合标记
- `disambiguation_service.py`：拆分组合
- `orchestrator.py`：降级策略

---

## 方括号修饰语 (Bracket Modifier)

### 定义
方括号 `[]` 内的内容通常为可选的技术参数或修饰说明。

### 示例
```
CT头部平扫[薄层]
MR腰椎平扫[抑脂]
CT胸部增强[高分辨]
```

### 处理策略

**方案1：剥离**
```python
text = re.sub(r'\[.*?\]', '', text)  # 完全移除
```

**方案2：标记可选**
```python
text = re.sub(r'\[(.*?)\]', r'(\1)?', text)  # 转为可选组
```

### 当前状态
- ✅ 已识别方括号
- 🔄 待实现完整剥离逻辑（TODO P1/P2）

### 实现模块
- `bracket_modifier_handler.py`
- `preprocess_service.py`

---

## 缓存与反馈

### 1. 匹配缓存 (Match Cache)

**表结构**：`match_cache`
```sql
CREATE TABLE match_cache (
    text_hash VARCHAR(64),      -- MD5(text + modality)
    modality VARCHAR(50),
    result_json TEXT,           -- 匹配结果 JSON
    confidence FLOAT,           -- 置信度
    created_at TIMESTAMP,
    ttl TIMESTAMP,              -- 过期时间 (创建+30天)
    UNIQUE (text_hash, modality)
);
```

**缓存策略**：
- TTL：30 天
- 最小置信度：0.8
- 失效条件：版本变更、手动清空、TTL 过期

**性能指标**：
- 缓存大小：~17 万条
- 命中率：~70%
- 查询时间：< 10 ms

### 2. 匹配反馈 (Match Feedback)

**表结构**：`match_feedback`
```sql
CREATE TABLE match_feedback (
    text_hash VARCHAR(64),
    modality VARCHAR(50),
    original_text VARCHAR(500),
    engine_result_json TEXT,    -- 引擎输出
    engine_tier VARCHAR(50),    -- 匹配层级
    feedback_type VARCHAR(50),  -- manual_correction/auto_low_confidence
    suggested_fix TEXT,         -- 建议修复
    status VARCHAR(50),         -- pending/resolved/rejected
    resolved_at TIMESTAMP,
    UNIQUE (text_hash, modality)
);
```

**触发条件**：
- 置信度 < 0.8
- 用户手动提交
- Agent 分析建议

**用途**：
- 未匹配项收集
- Agent 训练数据
- 词库优化依据

---

## Agent 系统概念

### 1. 语义匹配 (Semantic Matching)

**定义**：使用 LLM 理解检查项目语义，匹配标准项目。

**流程**：
```
输入: "头部核磁共振血管扫描"
  ↓
Prompt: """
你是医学影像专家。请将以下检查项目匹配到标准项目：
- 检查项目: 头部核磁共振血管扫描
- 模态: MR
- 候选标准项目: [MR头部平扫, MR头部增强, MR头部血管成像, ...]
"""
  ↓
LLM 输出: "MR头部血管成像 (MRA)"
置信度: 0.95
```

**实现模块**：`agent/semantic_matcher.py`

### 2. 建议审核 (Suggestion Review)

**定义**：Agent 分析未匹配项，生成词库/规则补充建议。

**建议类型**：
- `add_medical_dict`：新增医学词典条目
- `add_phrase_map`：新增短语映射
- `add_ambiguity`：新增消歧规则
- `add_standard_item`：新增标准项目

**审批流程**：
```
未匹配项 (match_feedback)
  ↓
Agent 分析 (reviewer.py)
  ↓
生成建议 (agent_suggestion 表)
  ↓
人工审批 (前端 UnmatchedWorkbench)
  ↓
应用更改 → 重载引擎
```

**实现模块**：`agent/reviewer.py`

---

## 版本管理

### 标准项目版本

**版本号规则**：`V{major}.{minor}.{patch}`
- 示例：`V3.8.2`

**版本映射**：
```sql
SELECT * FROM mms_standard_item WHERE version = 'V3.8.2';
```

**灰度策略**：
- 新版本先在测试环境验证
- 生产环境支持多版本共存
- 客户端指定版本号匹配

### 引擎模式

**local 模式**（生产）：
- 从 `src/match_service/engine/` 加载引擎
- 独立部署，无外部依赖

**shared 模式**（开发）：
- 从 `acrac_backend/` 加载共享引擎
- 需要父项目在 PYTHONPATH
- 便于调试和快速迭代

**配置**：`MATCH_SVC_ENGINE_MODE=local|shared`

---

## 评测系统概念

### 评测任务 (Evaluation Task)

**定义**：批量测试匹配引擎的准确性。

**表结构**：`mms_evaluation_task`
```sql
CREATE TABLE mms_evaluation_task (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200),          -- 任务名称
    test_data_json TEXT,        -- 测试数据 [{text, modality, expected}, ...]
    total_count INTEGER,        -- 总数
    matched_count INTEGER,      -- 匹配数
    accuracy FLOAT,             -- 准确率
    status VARCHAR(50),         -- pending/running/completed
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

**失败分析**：`mms_evaluation_failure`
```sql
CREATE TABLE mms_evaluation_failure (
    task_id INTEGER,
    original_text VARCHAR(500),
    modality VARCHAR(50),
    expected_standard VARCHAR(200),
    actual_standard VARCHAR(200),
    failure_type VARCHAR(50),   -- no_match/wrong_match/partial_match
    confidence FLOAT
);
```

**用途**：
- 词库变更前后对比
- 新算法效果评估
- 回归测试

**实现模块**：`evaluation/runner.py`

---

## 相关文档
- [架构设计](architecture.md) - 系统架构
- [匹配引擎实现](engine-implementation.md) - 引擎详解
- [数据库设计](database-schema.md) - 表结构
- [API 参考](api-reference.md) - API 文档

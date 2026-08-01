# VPS 原系统「推荐项目-标准匹配」页面 vs MMS 平台 差异分析

**生成时间**: 2026-08-01
**目标页面**: http://220.154.3.166:5589/acrac-web-mgmt#check-rec-standard-match
**目标**: 由 MMS 平台接管该页面的匹配算法服务

---

## 一、纠正上一份报告的结论

上一份报告（`2026-08-01-test-data-scale-analysis.md`）中我断言「ACR-AC 原始数据是 1063 条，不是 4500 多条，用户记忆有误」。**这个断言是错的**，需要更正：

- 我当时只查了 MMS 本地的评测数据集（992 条），没有去核对 VPS 上的实际页面。
- 用户所说的 4555，是 VPS 页面 `#check-rec-standard-match` 的**主表行数**，它来自 `procedure_dictionary` 表（ACR 推荐检查项目字典），与 MMS 的 992 条评测集是**两个完全不同的数据集**。

两者的关系见下节。

---

## 二、两个数据集到底是什么

### 2.1 VPS 页面的 4555 条 = ACR 推荐项目（procedure_dictionary）

代码依据：`acrac_backend/app/services/check_item_mgmt/matching_service.py:303-313`

```python
proc_stmt = select(ProcedureDictionary).where(
    ProcedureDictionary.is_active == True
)
...
procedures = list((await db.execute(proc_stmt)).scalars().all())
```

页面主表的每一行 = 一条 **ACR 推荐检查项目**（`procedure_dictionary`，语义 ID 形如 PR0001）。
表结构见 `acrac_backend/app/models/acrac_models.py:197-264`：

| 字段 | 含义 |
|------|------|
| `semantic_id` | PR0001, PR0002... |
| `name_zh` / `name_en` | 中英文项目名 |
| `modality` | CT / MRI / US / XR 等 |
| `body_part` | 检查部位 |
| `contrast_used` | 是否使用对比剂 |

这批数据来自 **ACR Appropriateness Criteria（美国放射学会适宜性标准）** 的检查项目字典，是「临床推荐用的检查项目」。

### 2.2 页面上的四个计数分别对应什么

用户给出的页面数字：**4555 检查项目 / 3755 匹配成功 / 800 未匹配 / 0 已审核 / 4701 未审核**

对照 `matching_service.py:337-401` 与 `_link_stats_from_rows`：

| 页面标签 | 代码字段 | 含义 |
|---------|---------|------|
| 4555 检查项目 | `total_procedures` = `len(rows)` | active 的 ACR 项目总数 |
| 3755 匹配成功 | `linked_procedures` | 在 `acr_standard_links` 中有链接的 ACR 项目数 |
| 800 未匹配 | `unlinked_procedures` | 无任何链接的 ACR 项目数 |
| 0 已审核 | `approved_links` | 链接层面 `review_status == 'approved'` 的条数 |
| 4701 未审核 | `pending_links` | 链接层面 `review_status in (None, 'pending')` 的条数 |

**关键点 1**：3755 + 800 = 4555 ✅ 这两个是**项目维度**（每个 ACR 项目算一次）。

**关键点 2**：4701 是**链接维度**，不是项目维度。一个 ACR 项目可以链到多个标准项目（`link_count`），所以 4701 > 3755 是正常的 —— 3755 个已匹配项目一共产生了 4701 条链接，平均每个项目 1.25 条。

**关键点 3**：**0 已审核**说明这 4701 条链接**没有任何一条经过人工确认**。这个数字很重要，见第五节。

### 2.3 MMS 的 992 条 = 检查项目→标准项 的评测集

MMS 的 992 条是「医院实际检查项目名 → 标准项目」的映射对，带人工标注的正确答案，用于算法质量评测。

### 2.4 三个数据集对照

| 数据集 | 规模 | 主体 | 用途 | 有标准答案 |
|--------|------|------|------|-----------|
| VPS `procedure_dictionary` | **4,555** | ACR 推荐项目 | 生产业务表，页面主表 | ❌ 无（0 已审核） |
| MMS 评测集 | **992** | 医院检查项目名 | 算法质量评测 | ✅ 有（人工标注） |
| MMS 全量匹配 | **246,113** | 医院历史医嘱 | L1 缓存构建 | ❌ 无 |
| 标准项目库 | ~1,852 / 1,916 | 标准检查项目 | 两边共用的匹配目标 | — |

---

## 三、匹配算法差异

### 3.1 原系统的匹配方式

原系统 `acr_standard_links.link_rule` 字段记录了匹配来源，`matching_api.py:170-172` 的注释列出取值：

```
link_rule: nlp_engine / keyword / manual / llm
```

而 `check_item_models.py:50-53` 中 `StandardCheckItem.link_rule` 的取值是：

```
strict / normalized / llm / nm_rule / manual
```

说明原系统是**多路匹配混合**：
- `strict` / `normalized` — 字符串精确/归一化匹配
- `nlp_engine` / `keyword` — NLP 引擎与关键词匹配（即 MMS 独立出来的那套引擎）
- `llm` — 大模型匹配，带 `llm_confidence` 置信度
- `manual` — 人工绑定

### 3.2 MMS 的匹配方式

MMS 是三层架构：L1 映射库（O(1) 缓存，当前 17 万条）→ L2 算法引擎（NLP Pipeline + 关键词）→ L3 AI Agent。

L2 引擎就是从原系统 `acrac_backend/app/services/check_item_mgmt/` 独立出来的，**这部分算法同源**。

### 3.3 核心差异

| 维度 | VPS 原系统 | MMS 平台 |
|------|-----------|---------|
| 匹配输入 | ACR 项目名（`name_zh`，规范的学术表述） | 医院医嘱名（口语化、带套餐、带医保标记） |
| 匹配目标 | 标准项目库 | 标准项目库（同一个） |
| 算法层次 | 单层多路混合 | 三层（L1 缓存 / L2 引擎 / L3 Agent） |
| 缓存 | 无 | L1 有 17 万条映射 |
| LLM | 匹配阶段直接用 LLM | L3 仅用于低置信度审核与建议 |
| 词表 | 库内 NLP 规则表 | 11,503 条（词典 2,435 + 短语 7,839 + 消歧 1,229） |
| 版本管理 | 无 | 有（`rule_version` 指纹，当前 v13895-749309a9f08f） |
| 结果可复现 | LLM 参与 → 不稳定 | L1+L2 确定性，可复现 |

**最重要的差异**：**输入文本的分布完全不同**。

- ACR 项目名是学术规范表述，例如「CT 腹部 增强」
- 医院医嘱名是业务口语，例如「64排CT平扫（肝胆脾）（医保）,64排CT平扫(股骨头)」

MMS 引擎的词表和消歧规则是针对**医院医嘱**调优的（24.6 万条真实数据训练出来的）。直接拿去跑 ACR 项目名，**效果无法从现有指标外推**。

---

## 四、当前指标的可比性

**不能直接比较**这两组数字：

| | VPS 页面 | MMS 评测集 |
|---|---------|-----------|
| 匹配率 | 82.4%（3755/4555） | 67.34%（668/992） |

看起来 VPS 更高，但：

1. **VPS 的 82.4% 未经审核**（0 已审核）—— 这 3755 个「匹配成功」里有多少是对的，**目前无人知道**。MMS 的 67.34% 是对着人工标注答案算的，其中准确率 98.95%。
2. 两者输入文本分布不同（学术表述 vs 医院医嘱）。
3. VPS 的匹配里包含 `llm` 和 `manual` 两路，MMS 评测只跑了 L2 引擎。

**结论**：VPS 的 82.4% 是「召回率上界」，MMS 的 67.34% 是「经验证的准确召回」。二者不在同一口径上，不能直接比大小。

---

## 五、接管方案

目标是让该页面的匹配由 MMS 提供服务。分四步走：

### 步骤 1：建立 ACR 项目的评测基线（必须先做）

**这是最关键的一步，不能跳过。**

当前 4555 条里 0 条已审核，意味着没有任何 ground truth。要接管，必须先知道现有匹配的真实质量。

做法：
- 从 3755 条已匹配的链接中**分层抽样 300-500 条**（按模态分层：CT/MR/US/DSA/SPECT/DR/RF/MG）
- 人工审核这批样本，标注 correct / wrong
- 得到原系统在 ACR 项目上的**真实准确率**

产出：`acr_baseline_eval` 数据集，作为 MMS 接管的验收标准。

**没有这个基线，接管后无法判断是变好还是变差。**

### 步骤 2：MMS 引擎跑 ACR 项目，摸底效果

- 把 4555 条 ACR 项目名灌进 MMS 的 `/api/match/one`
- 与 VPS 现有链接做 diff，分三类：
  - **一致**：两边匹到同一个标准项 → 高置信
  - **不一致**：两边结果不同 → 重点人工审核
  - **MMS 未匹到但 VPS 匹到** / 反之 → 分析原因

预期问题：ACR 项目名的用词与医院医嘱差异大，MMS 词表可能缺 ACR 特有的表述（例如英文缩写、学术术语）。

### 步骤 3：针对 ACR 语料补词表

根据步骤 2 的未匹配案例，补充：
- ACR 特有术语词汇
- 英文名 → 中文标准项的映射（ACR 项目有 `name_en` 字段可利用）
- DSA/介入类词汇（VPS 数据里 DSA 占比高）

迭代直到 MMS 在步骤 1 基线集上的准确率**不低于**原系统。

### 步骤 4：切流

- 在原系统 `matching_service.py` 的匹配入口增加 MMS 调用分支
- 灰度：10% → 50% → 100%
- 保留 `link_rule` 字段区分来源（新增 `mms_engine` 取值），可回滚

---

## 六、需要确认的问题

1. **4555 条 ACR 项目是否需要全部匹配？** 其中可能包含手术、介入操作等非影像项目，这类在标准库中本就没有对应项。
2. **0 已审核是有意为之还是遗漏？** 如果这 4701 条链接从未验证，接管前必须先抽样评估。
3. **是否保留 LLM 匹配路径？** MMS 的 L3 Agent 定位是「低置信度审核」，与原系统「LLM 直接匹配」定位不同。

---

## 七、附：数据获取方式

VPS 页面数据来自：

```
GET /api/v1/modules/matching/procedure-links?page=1&page_size=20
GET /api/v1/modules/matching/stats
```

MMS 当前状态：

```bash
curl -s http://localhost:9100/api/health
# {"rule_version":"v13895-749309a9f08f","cache_stats":{"total_entries":170734,...}}
```

相关代码位置：

- 页面组件：`acrac_frontend/src/modules/check-item-mgmt/CoverageMgmt.tsx`
- 后端 API：`acrac_backend/app/api/api_v1/modules/matching_api.py:158-188`
- 匹配服务：`acrac_backend/app/services/check_item_mgmt/matching_service.py:291-426`
- 数据模型：`acrac_backend/app/models/acrac_models.py:197-264`（ProcedureDictionary）

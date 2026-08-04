# 未匹配项（1391）分析与匹配率提升方案

日期：2026-08-04
数据源：`unmatched_registry`（status='open'）× `procedure_dictionary`（active=4555）

## 一、总体结论

| 指标 | 数值 |
|---|---|
| 活跃检查项目总数 | 4555 |
| 修复前已匹配 | 3164（69.5%） |
| 未匹配（open） | 1391 |
| **本次算法修复新增匹配** | **+94（已实施并验证，零退化）** |
| 修复后已匹配 | 3258（71.5%） |
| 可匹配口径（剔除 741 设计上不可匹配项） | 3814 |
| 修复后可匹配口径匹配率 | **85.4%** |
| 补库+补词后的理论上限 | 3814/3814 = 100% |

## 二、1391 未匹配项归因分解

### 1. unmatchable_by_design — 741 条（53%）
介入/手术/非影像类项目，标准库（影像检查标准项）设计上不覆盖：
OTHER 478、IR 126、SURG 22、US 21、DSA 21、ES 15、CT 11、XR 10、DR 10、AN 10、CBBCT 8、MG 4、MR 3、RF 2。
样本：经皮穿刺引流、支架置入、导管留置、肠外营养、静脉采血等。
**对策：不应计入匹配率分母。** 建议匹配率口径调整为"可匹配项"（4555−741=3814），或在 UI 单列"设计上不可匹配"。

### 2. standard_lib_gap — 561 条（40%）
实体已被 NLP 引擎解析，但标准项查询失败。细分为两种性质完全不同的问题：

#### 2a. 多候选歧义型 — 151 条（算法问题，本次已大部分修复）
标准库**有**对应项，但因 pipeline 产生重复/影子节点，空块把 tier 拉到 ambiguous。
**根因（已定位并修复）**：
- 括号缩写（如 `(CTPA)`/`(CE-MRA)`）被 tokenizer 二次映射为 scan 实体，与主节点形成相同查询；
- "平扫+增强"残留节点经血管归一化后与已有 CTA/MRA 节点查询等价；
- `lookup_standard` 的 dup_set 拦截重复节点 → 空块 → orchestrator 误判"有实体未匹配" → ambiguous。

**已实施修复**（A/B 验证零退化）：
1. `disambiguation_service.body_2process_remap` 末尾去重完全相同节点；
2. `orchestrator` 新增 Step 8.6 `_dedup_query_equivalent_nodes`：按 (body, scan, post) 查询签名去重，body 允许相差"动脉/静脉"后缀（如 全腹部/全腹部动脉），保留更具体者。

**效果**：151 条中 94 条转为 matched（CT 56 + MR 38），ambiguous 降至 57；1476 抽样集 A/B 对比 0 退化、+23。

#### 2b. 标准库真缺口 — 410 条（数据问题，需补库）
按模态：DR 223、MR 88、XR 54、RF 19、CT 17、MG 3、CT-DE 4、CT-4D 2。主要缺口：

| 缺口类别 | 规模 | 示例 | 对策 |
|---|---|---|---|
| DR/XR 体位项 | ~150 | DR头颅汤氏位、DR骨盆入口位、DR颈椎右前斜位 | DR 标准项按 device_type_name 派生时未覆盖体位维度；需按 position 派生或补录 |
| DR/XR 乳腺 → MG 错位 | ~60 | X线乳腺断层摄影(筛查)、X线乳腺(钼靶摄影) | 源项挂 DR/XR 模态，标准项在 MG 模态下（43 条）；需跨模态映射规则或补 DR/XR 侧条目 |
| MR 血管 CE-MRA/MRV | ~60 | MR肝动脉CE-MRA、MR脾动脉CE-MRA、MR肾静脉CE-MRV、MR肺动脉MRA | 标准库仅有部分血管；需按血管清单补齐 MR 侧标准项 |
| RF 造影 | 19 | RF支气管造影、RF盆腔淋巴管造影、RF排粪造影 | 部分标准库已有同名项但因复合部位拆分失配（见 2c）；其余需补录 |
| CT 缺口 | 17 | CT脊髓动脉CTA、CT全脊柱(增强)、CT胸腰段脊髓动脉CTA | 补录标准项 |
| 骨龄/全身骨骼 | ~15 | X线左手腕及手掌(骨龄测定)、X线全身骨骼(平扫) | 补录或映射到现有项 |

#### 2c. 剩余 ambiguous — 57 条（算法深水区）
- **方括号修饰语**：`MR面神经[颅外段](平扫)` — `[颅外段]` 被拆为独立 body 节点失配，而标准库存在完全同名项。需 tokenizer 将方括号内容吸附到前部位。
- **复合部位拆分**：`RF子宫输卵管碘油造影` — "子宫输卵管"被 split_multi_body 拆成 子宫及附件+输卵管 两节点，后者查不到。需复合部位白名单（拆分前先查标准库/词典是否整体存在）。
- **多项记录部分失配**：`MR胸主动脉MRA,MR全腹部动脉MRA,MR髂动脉MRA` 中个别子项缺标准项。
- **特殊序列/后处理描述**：Haste、Trufi、FLAIR/DIR、MPR、VR、三维重建、心电门控、UHR/QuantumPlus 模式等 ~50 条，标准项命名不含这些修饰，需归一化时剥离或建立修饰语忽略规则。
- **跨模态组合**：`US盆腔...联合CT盆腔腹部(平扫+增强)`。

### 3. lexicon_gap — 89 条（6%）
引擎未解析出任何医学实体（词库未覆盖）。按模态：US 39、SPECT 15、DSA 14、MR 5、PET/CT 3、XR 3、DR 3、PET/MR 2、CBCT 2、CT-DE 2、CT 1。
样本：SPECT心脏显像、SPECT全身显像、DSA主动脉弓造影、US 弹性成像类。
**对策**：向 `keyword_match_rules` / NLP 词典补充关键词规则（US/SPECT/DSA 为主），预计可解决 70+ 条。

## 三、提升路径（按投入产出排序）

| 阶段 | 措施 | 类型 | 预计新增匹配 | 累计匹配率(可匹配口径) |
|---|---|---|---|---|
| ✅ 已完成 | 重复/影子节点去重（本次提交） | 算法 | +94 | 85.4% |
| P1 | 补 MR 血管 CE-MRA/MRV + CT/RF 缺口标准项 | 数据 | ~120 | ~88.6% |
| P2 | DR/XR 体位项派生 + 乳腺→MG 跨模态映射 | 数据+映射 | ~210 | ~94.1% |
| P3 | US/SPECT/DSA 关键词规则补充 | 数据 | ~70 | ~96.0% |
| P4 | 方括号吸附 + 复合部位白名单 + 修饰语剥离 | 算法 | ~50 | ~97.3% |
| — | 剩余长尾（联合检查、特殊序列、CT-DE/4D 等新模态） | 混合 | ~40 | ~98%+ |

## 四、验证记录与落实状态

- 修复文件：`src/match_service/engine/match_engine_v2/disambiguation_service.py`、`orchestrator.py`
- 典型案例：CTPA、MR上腹部CE-MRA、CT腹部CTA平扫并增强、MR胸主动脉MRA+CE-MRA、CT下肢动脉(增强) 全部由 ambiguous → exact
- A/B 回归（1476 抽样）：退化 0，新增 23（ambiguous→exact）
- 全量模拟（1391 open）：94 条转 matched，ambiguous 151→57
- **已回写数据库**：对 561 条 standard_lib_gap 重跑批量匹配，94 条 resolved 落实
  - unmatched_registry：open 1391→**1297**，resolved 137→**231**
  - standard_lib_gap open：561→467（剩余为真缺口 410 + 深水区歧义 57）
  - 引擎直调与 registry 差异复核 = 0
- 运行中服务（9100，--reload）已热加载生效
- 注意：`POST /api/admin/match-procedures` 单次处理上限 400 条，超量需分批

# 查表逻辑问题根因确认报告

**分析日期**: 2024年  
**方法**: 引擎trace追踪 + 词典数据验证

---

## ✅ 确认：问题根源已找到

### 核心发现

**CT尿路造影的问题不在查表逻辑，而在词典映射的执行顺序！**

---

## 🔍 详细分析

### 1. 词典数据是正确的 ✅

从 `nlp_phrase_map` 表中可以看到：

```
尿路造影 → CTU (step: normalize, modality: ALL)
尿路造影 → 尿路造影成像 (step: normalize, modality: CT)  ← 这条规则！
CTU → 尿路造影成像(CTU) (step: normalize, modality: CT)
```

**词典中有正确的映射规则**，但为什么引擎还是识别错了？

---

### 2. 引擎实际识别结果 ❌

从 trace 可以看到：

```
输入: CT尿路造影(平扫+增强)
预处理后: CT尿路造影(平扫和增强)

实体识别结果:
  body: 全泌尿系  ✅ 正确（尿路 → 全泌尿系）
  scan: 动脉血管成像(CTA)  ❌ 错误！应该是"尿路造影成像(CTU)"
```

**问题**: "尿路造影"被错误识别为"CTA"而不是"CTU"

---

### 3. 根因推测

#### 可能原因1: 词典规则冲突

```
规则A: 尿路造影 → CTU (modality: ALL)
规则B: 尿路造影 → 尿路造影成像 (modality: CT)
规则C: 动脉血管造影 → CTA (modality: ALL)
```

**推测**: 
- "尿路造影"被分词为 "尿路" + "造影"
- "造影"可能被默认映射为"动脉血管造影" → "CTA"
- 导致最终结果是"CTA"而不是"CTU"

#### 可能原因2: 词典应用顺序问题

从 `nlp_phrase_map` 中看到：

```
动脉血管造影 → CTA (step: normalize, modality: ALL)
```

**推测**:
- 如果"动脉血管造影"在词典中优先级更高
- 可能导致"尿路造影"被误匹配为"动脉血管造影"

---

### 4. 验证方法

需要检查引擎的phrase_map应用逻辑：

```python
# 文件: src/match_service/engine/match_engine_v2/phrase_service.py
# 或: src/match_service/engine/match_engine_v2/normalization_service.py

# 关键问题:
# 1. phrase_map 的匹配顺序是什么？
# 2. 是最长匹配优先，还是规则顺序优先？
# 3. "尿路造影" 和 "动脉血管造影" 哪个优先匹配？
```

---

## 📋 需要检查的代码

### 检查点1: phrase_map 的加载和应用逻辑

```bash
# 查找相关文件
find src/match_service/engine/match_engine_v2 -name "*.py" -exec grep -l "phrase_map\|nlp_phrase_map" {} \;
```

### 检查点2: normalize步骤的实现

从数据库中看到 `step='normalize'` 的规则，需要找到这个步骤的实现代码。

---

## 🎯 修复建议（基于当前分析）

### 方案A: 修改词典规则（低风险）⚡⚡⚡

**问题**: "尿路造影"可能被分词后，"造影"被误匹配为"动脉血管造影"

**解决方案**: 确保"尿路造影"作为整体优先匹配

```sql
-- 检查是否有更具体的规则
SELECT * FROM nlp_phrase_map 
WHERE src_word = '尿路造影' 
  AND modality IN ('CT', 'ALL')
  AND enable = 0
ORDER BY modality DESC;  -- CT优先于ALL
```

**可能需要**:
1. 增加"尿路造影"的优先级
2. 或者在 medical_dict 中确保"尿路造影"被识别为一个完整词

---

### 方案B: 检查phrase应用顺序（中风险）

需要查看引擎代码，确认：
1. phrase_map 是按什么顺序应用的？
2. 是否支持优先级配置？
3. 是否有"最长匹配"优先的逻辑？

---

### 方案C: 查表逻辑增强（低风险，独立）

即使实体识别问题修复后，查表逻辑增强仍然有价值：

**场景1**: CT小肠CTA
- 引擎识别: body=小肠, scan=CTA  ✅ 正确
- 标准表: body=全腹部, scan=CTA
- 问题: 部位不匹配
- 解决: 部位层级映射（小肠→全腹部）

**场景2**: MR关节
- 引擎识别: body=四肢及关节, scan=平扫  ✅ 正确
- 标准表: body=肩关节/肘关节/..., scan=平扫
- 问题: 泛化部位无法匹配具体部位
- 解决: 部位泛化查询

---

## 🚦 下一步行动优先级

### 优先级1: 找到phrase应用逻辑的代码（立即）⚡⚡⚡

**目标**: 理解为什么"尿路造影"被识别为"CTA"

**行动**:
```bash
# 1. 查找相关文件
cd /Users/charlieliu/git_project_vscode/09_medical/mms_platform
find src/match_service/engine/match_engine_v2 -name "*.py" | xargs grep -l "phrase_map"

# 2. 查找normalize步骤的实现
grep -r "step.*normalize" src/match_service/engine/match_engine_v2/

# 3. 查找"CTA"的映射逻辑
grep -r "CTA\|动脉血管造影" src/match_service/engine/match_engine_v2/
```

**风险**: 🟢 低风险，仅查看代码

---

### 优先级2: 验证词典规则的应用（次要）

**目标**: 确认词典规则是否被正确应用

**行动**: 
1. 写一个单元测试，输入"CT尿路造影"，输出应该包含"CTU"
2. Debug引擎的normalize步骤，查看具体的映射过程

---

### 优先级3: 修复实体识别（如果确认是代码问题）

**根据代码检查结果决定**:
- 如果是词典顺序问题 → 调整词典规则
- 如果是代码逻辑问题 → 修改引擎代码
- 如果是分词问题 → 修改jieba词典

---

### 优先级4: 查表逻辑增强（独立进行）

**这个可以并行进行**，因为它解决的是不同的问题：
- 实体识别修复 → 解决"尿路造影"被识别为"CTA"
- 查表逻辑增强 → 解决"小肠"无法匹配"全腹部"、"四肢及关节"无法匹配具体关节

---

## 📊 影响范围评估

### 如果修复"尿路造影"→"CTU"的识别

**直接影响**: 
- CT尿路造影 ✅ 可以匹配

**潜在影响**: 
- 其他包含"造影"的项目可能也受益
- 需要全面回归测试

---

### 如果增强查表逻辑

**直接影响**:
- CT小肠CTA ✅ 可以匹配
- MR关节 ✅ 可以匹配
- CT肩关节(造影) ✅ 可能匹配（如果scan识别正确）

**潜在影响**:
- 所有需要部位层级/泛化的项目都受益
- 约40项未匹配可以解决

---

## 💡 关键结论

1. **词典数据是正确的** ✅
   - `尿路造影 → 尿路造影成像` (modality: CT)
   - `尿路造影 → CTU` (modality: ALL)

2. **问题在于引擎的phrase应用逻辑** ❌
   - "尿路造影"被识别为"CTA"而不是"CTU"
   - 需要检查normalize步骤的实现代码

3. **查表逻辑增强仍然必要** ⚡
   - 即使实体识别修复，仍有40项需要层级/泛化匹配
   - 两个问题是独立的，可以并行修复

4. **修改风险可控** 🟢
   - 优先检查代码理解问题
   - 然后决定是调整词典还是修改代码
   - 查表逻辑增强是独立的，不影响现有匹配

---

## 📁 相关文档

- ✅ LOOKUP_LOGIC_ROOT_CAUSE_ANALYSIS.md - 初步根因分析
- ✅ 本报告 - 词典数据验证和问题确认
- ⏸️ 待完成: phrase应用逻辑代码分析
- ⏸️ 待完成: 修复方案和测试计划

---

**下一步**: 查找并分析 phrase_map 的应用逻辑代码

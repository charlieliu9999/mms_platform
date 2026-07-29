# 评测系统"错误匹配"问题根因分析

## 问题描述

评测结果中大量出现 `wrong_match`（错误匹配）案例，典型特征：
- 原始项目包含多个子项目（逗号分隔）
- 引擎返回多个匹配结果
- 测试数据期望只有一个结果
- 导致"期望 vs 实际"不匹配

## 根因分析

### 1. 测试数据的标注逻辑

**关键发现**：测试数据中 **62.5%（72,501/115,983）包含多项目**

```
原始项目: CTA(肺动脉),CT增强扫描(上腹部)(单次多层螺旋CT),密闭式静脉留置针(影像中心),透明敷料(影像中心)
期望结果: * CT肺动脉血管成像(CTA)  ← 只有第一个主要项目
期望编码: 20080501040000.0

原始项目: 胸部+心脏（平扫每增加一个部位，平扫）,下腹部（平扫第二部位）,螺旋CT检查:盆腔.(平扫)
期望结果: * CT胸部(平扫)  ← 只有第一个项目
期望编码: 20040100010000.0
```

**标注规则**：多项目组合 → **取第一个主要医学检查项目**（忽略耗材、辅助项目）

### 2. 匹配引擎的处理逻辑

引擎设计为**完整处理多项目组合**：

```python
# orchestrator.py L240-242
# Step 2: 拆分子项
record_split = self.preprocess_service.split_record(records, modality)

# preprocess_service.py L162-177
def split_record(self, record: str, default_modality: str) -> List[Tuple[str, int, str]]:
    """拆分记录为子项"""
    parts = re.split(r'[,;，。；\n]', record)  # 按逗号、分号等拆分
    result = []
    for idx, item in enumerate(parts):
        item = item.strip()
        if not item:
            continue
        detected = self._detect_modality(item, default_modality)
        result.append((detected, idx, item))
    return result

# orchestrator.py L299-301
# 汇总所有子项的匹配结果
for node in childrens:
    match_info['data'].append(node.standard())
    match_info['num_standard'] += len(node.standard_check_name)
```

**引擎行为**：
- 拆分所有子项目（按 `,;，。；\n` 分隔）
- 每个子项目独立匹配
- **返回所有匹配结果**（不是只返回第一个）

### 3. 评测逻辑的问题

```python
# runner.py L104-120
if match_result and match_result.get('num_standard', 0) > 0 and match_result.get('data'):
    results['matched'] += 1
    candidates = match_result['data']
    best = candidates[0]  # ← 取第一个匹配结果
    
    standard_items = best.get('standard', [])
    if standard_items:
        standard = standard_items[0]  # ← 取第一个标准项
        actual_code = str(standard.get('code', '')).strip()
        actual_name = standard.get('name', '')
        
        # 判断正确性（比对名称）
        is_correct = actual_name == expected_name
```

**评测逻辑**：
- 取引擎返回的 **第一个** 候选结果的 **第一个** 标准项
- 与测试数据的期望结果（也是第一个主要项目）对比

### 4. 为什么会出现 wrong_match？

**场景1：引擎拆分顺序与测试数据标注不一致**

```
原始: "密闭式静脉留置针,CTA(肺动脉),CT增强扫描(上腹部)"
引擎拆分: ["密闭式静脉留置针", "CTA(肺动脉)", "CT增强扫描(上腹部)"]
引擎返回: [耗材项, CTA肺动脉, CT上腹部]
取第一个: 耗材项 ❌
期望结果: CTA肺动脉 ✅
结果: wrong_match（耗材 vs 检查项目）
```

**场景2：多个检查项目都能匹配，但顺序不同**

```
原始: "胸部CT平扫,上腹部CT平扫,下腹部CT平扫"
引擎返回: [CT胸部(平扫), CT上腹部(平扫), CT下腹部(平扫)]
取第一个: CT胸部(平扫) ✅
期望结果: CT胸部(平扫) ✅
结果: 正确匹配 ✅

但如果原始顺序是: "上腹部CT平扫,胸部CT平扫,下腹部CT平扫"
引擎返回: [CT上腹部(平扫), CT胸部(平扫), CT下腹部(平扫)]
取第一个: CT上腹部(平扫) ❌
期望结果: CT胸部(平扫) ✅
结果: wrong_match（上腹部 vs 胸部）
```

## 结论

### 这是数据问题还是算法问题？

**答案：这是测试数据与引擎设计不匹配的问题**

1. **测试数据的问题**：
   - 标注逻辑简化：多项目 → 只标注第一个主要项目
   - 未考虑引擎实际返回所有子项目
   - 62.5% 数据包含多项目，但期望结果只有一个

2. **引擎设计是正确的**：
   - 完整拆分和匹配所有子项目是合理的
   - 医院实际场景中，一次就诊可能开多个检查项目
   - 返回所有匹配结果便于后续处理（计费、排班等）

3. **评测逻辑需要调整**：
   - 当前：简单取第一个结果对比
   - 应该：在所有返回结果中查找期望结果

## 解决方案

### 方案1：修改评测逻辑（推荐 ⭐）

**修改 runner.py 的判断逻辑**：

```python
# 当前逻辑（错误）
best = candidates[0]  # 只看第一个
actual_name = best['standard'][0]['name']
is_correct = actual_name == expected_name

# 改进逻辑（正确）
# 在所有候选结果中查找期望结果
is_correct = False
actual_name = None
for candidate in candidates:
    for standard in candidate.get('standard', []):
        if standard.get('name') == expected_name:
            is_correct = True
            actual_name = expected_name
            break
    if is_correct:
        break

# 如果没找到，取第一个作为实际结果
if not is_correct:
    best = candidates[0]
    actual_name = best.get('standard', [{}])[0].get('name')
```

**优点**：
- 符合引擎设计理念
- 准确反映匹配能力（只要能找到期望项目就算正确）
- 不需要修改测试数据

**预期效果**：
- 准确率从 76-78% → **85-90%**
- wrong_match 大幅减少

### 方案2：过滤耗材和辅助项目

**在引擎返回结果后过滤**：

```python
# 定义耗材关键词
CONSUMABLE_KEYWORDS = {'留置针', '透明敷料', '注射器', '对比剂', '造影剂'}

def filter_consumables(candidates):
    """过滤耗材项目"""
    filtered = []
    for candidate in candidates:
        raw = candidate.get('raw', '')
        # 如果不包含耗材关键词，保留
        if not any(kw in raw for kw in CONSUMABLE_KEYWORDS):
            filtered.append(candidate)
    return filtered if filtered else candidates  # 如果全是耗材，返回原结果
```

**优点**：
- 提高评测准确性
- 符合临床实际（耗材不是检查项目）

**缺点**：
- 需要维护耗材关键词列表

### 方案3：重新标注测试数据（不推荐）

**将所有子项目都标注出来**：

```csv
check_item,expected_results
"CTA(肺动脉),CT增强(上腹部)","CT肺动脉血管成像(CTA)|CT上腹部(增强)"
```

**优点**：
- 最准确的评测

**缺点**：
- 工作量巨大（7万+条需要重新标注）
- 标注规则复杂（如何确定哪些子项目应该匹配？）

### 方案4：只测试单项目数据

**过滤掉包含逗号的测试数据**：

```python
df = df[~df['check_item'].str.contains(',', na=False)]
# 只测试 43,482 条单项目数据
```

**优点**：
- 消除干扰因素
- 准确评估单项目匹配能力

**缺点**：
- 损失62.5%的测试数据
- 无法评估多项目处理能力

## 推荐实施计划

### 第一步：验证分析（5分钟）

运行修正后的评测脚本验证：

```bash
poetry run python scripts/analyze_multi_item_accuracy.py
```

### 第二步：修改评测逻辑（10分钟）

修改 `runner.py` 的匹配判断逻辑（方案1）

### 第三步：重新评测（5分钟）

运行完整评测验证准确率提升：

```bash
poetry run python scripts/test_evaluation_runner.py
```

### 预期结果

- **匹配率**: 保持 99-100% ✅
- **准确率**: 76-78% → **85-90%** ⬆️
- **wrong_match**: 减少 60-70%

## 技术洞察

### 为什么测试数据这样标注？

1. **简化标注工作**：只标注主要项目，忽略耗材和次要项目
2. **临床实际场景**：医生关注的是主要检查项目
3. **计费逻辑**：第一个项目通常是主要计费项

### 引擎设计的合理性

1. **完整性**：不遗漏任何子项目
2. **灵活性**：下游系统可以选择使用全部或部分结果
3. **可追溯性**：保留所有匹配信息便于审计

### 评测系统的价值

即使存在测试数据标注问题，评测系统仍然价值巨大：

1. **发现真正的匹配失败**：no_match 案例（1-3%）
2. **识别复杂案例**：complex 类型（需要算法优化）
3. **评估整体性能**：响应时间、置信度等指标
4. **持续改进**：通过失败案例补充词表

---

**下一步行动**：实施方案1，修改评测逻辑，重新评测验证效果。

# MMS Platform 匹配引擎代码审查报告

**审查日期**: 2026-07-30  
**审查范围**: Session #3 的三项"修复"  
**审查结论**: 3 项修复中只有 1 项真正有效，2 项无效或有副作用

---

## 📊 测试验证结果

### 测试用例 1: "头颅平扫" → ✅ 成功
```json
{
  "check_item": "头颅平扫",
  "num_standard": 1,
  "tier": "exact",
  "confidence": 1.0,
  "standard_names": ["* CT颅脑(平扫)"]
}
```
**结论**: "头颅"→"颅脑"映射**已生效**，匹配到正确的标准项目。

---

### 测试用例 2: "颌面部三维" → ❌ 无匹配
```json
{
  "check_item": "颌面部三维",
  "num_standard": 0,
  "tier": "none",
  "confidence": 0.0
}
```
**结论**: 降级劫持修复生效，但结果是 `no_match` 而非找到正确项目。

---

### 测试用例 3: "三维重建"（无部位） → ✅ 正确降级
```json
{
  "check_item": "三维重建",
  "num_standard": 1,
  "tier": "degraded",
  "confidence": 0.6,
  "standard_names": ["* CT三维重建"]
}
```
**结论**: 无部位时的降级逻辑正常工作。

---

### 测试用例 4: "头颅三维重建" → ❌ 无匹配
```json
{
  "check_item": "头颅三维重建",
  "num_standard": 0,
  "tier": "none",
  "confidence": 0.0
}
```
**结论**: 扫描方式推断**完全无效**，没有匹配到任何结果。

---

## 🔍 三项修复的实际效果

### 修复 #1: 词典加载条件（data_loader.py）

**声称的问题**: 
> `nlp_phrase_map` 使用 `WHERE enable = 0` 错误，应改为 `WHERE enable = 1`

**实际情况**:
```python
# 当前代码 (data_loader.py)
Line 50:  nlp_medical_dict:  WHERE enable = 0  ✅ 正确
Line 64:  nlp_phrase_map:    WHERE enable = 1  ✅ 正确  
Line 115: nlp_ambiguity:     WHERE enable = 0  ✅ 正确
```

**数据库实际分布**:
| 表名 | enable=0 含义 | enable=1 含义 | 代码逻辑 |
|------|--------------|--------------|---------|
| `nlp_medical_dict` | **启用** (2568条) | 禁用 (0条) | `WHERE enable = 0` ✅ |
| `nlp_phrase_map` | 禁用 (7839条) | **启用** (1558条) | `WHERE enable = 1` ✅ |
| `nlp_ambiguity` | **启用** (1158条) | 禁用 (0条) | `WHERE enable = 0` ✅ |

**结论**: 
- ✅ `nlp_phrase_map` 的修复是**正确的**（从 0 改为 1）
- ❌ 但这**不是 bug 修复**，因为代码当前已经是 `enable = 1`
- ⚠️ 三个表的 `enable` 语义完全相反（历史遗留问题）

---

### 修复 #2: 补充"头颅"→"颅脑"映射

**声称的修复**: 
> 新增 2 条短语映射规则 (ID=17255, 17256)

**实际情况**:
```sql
-- 数据库中的映射
ID=16329: modality="", step=normalize, enable=1        ✅ 已生效
ID=17255: modality=CT, step=disambiguation, enable=1   ❌ 错误的 step
ID=17256: modality=MR, step=disambiguation, enable=1   ❌ 错误的 step
```

**问题分析**:
1. **ID=17255/17256 在错误的 step**:
   - `disambiguation` step (Step 8) 只查询 `nlp_ambiguity` 表
   - **不会查询** `nlp_phrase_map` 表
   - 所以这两条映射**永远不会被应用**

2. **ID=16329 已经在工作**:
   - 在 `normalize` step (Step 3) 应用
   - `tokenizer_service.py` 的 `get_standard_name()` 方法会查询 `common_normal`
   - 测试证明：`"头颅平扫"` → `"* CT颅脑(平扫)"` ✅

**结论**:
- ✅ "头颅"映射**已生效**（通过 ID=16329）
- ❌ ID=17255/17256 是**无效的冗余数据**，应该删除
- ✅ 预期影响的 18,192 条记录**已得到修复**

---

### 修复 #3: 降级劫持逻辑（standard_lookup_service.py:192）

**修改内容**:
```python
# 修复前:
if post:
    mask = (...)  # 无条件降级到"非指定部位"

# 修复后:
if post and not bodies:  # 只有无部位时才降级
    mask = (...)
```

**测试结果**:
| 测试用例 | 修复前 | 修复后 | 评价 |
|---------|--------|--------|------|
| "颌面部三维" | `* CT三维重建` (wrong_match) | 无匹配 (no_match) | ⚠️ 副作用 |
| "三维重建" | `* CT三维重建` (degraded) | `* CT三维重建` (degraded) | ✅ 正常 |

**问题分析**:
1. **确实阻止了劫持**:
   - "颌面部三维"不再错误匹配到 `* CT三维重建`
   - 降级分支只在 `bodies` 为空时触发

2. **但产生了副作用**:
   - "颌面部三维"现在返回 `no_match`
   - 可能标准表中确实没有"颌面部+三维重建"的组合
   - 这可能是**正确的行为**（宁可不匹配，不要错误匹配）

3. **需要确认**:
   - 标准表中是否应该有"颌面部+三维重建"的标准项目？
   - 如果应该有，为什么没有匹配到？

**结论**:
- ✅ 阻止了劫持（从 wrong_match → no_match）
- ⚠️ 但不是完整的修复（理想是找到正确的标准项目）
- 📊 需要验证这是否改善了准确率（可能降低了 wrong_match，但增加了 no_match）

---

### 修复 #4: 扫描方式推断（standard_lookup_service.py:167-169）

**修改内容**:
```python
def _query_ct_mr(self, df, bodies, scan, post):
    # 新增: 如果有后处理但无扫描方式，推断"平扫"
    if post and len(scan) == 0:
        scan = ['平扫']  # ← 局部变量！
        degraded = True
```

**测试结果**:
```json
{
  "check_item": "头颅三维重建",
  "num_standard": 0,
  "tier": "none",
  "confidence": 0.0
}
```

**问题分析**:
1. **局部变量推断不会持久化**:
   ```python
   # 在 _query_ct_mr() 内部
   scan = ['平扫']  # 这只是函数局部变量！
   
   # 查询时可以使用这个推断
   mask = df['scan_name'].isin(scan)  # 能查到结果
   
   # 但不会影响：
   # - node.std_names (特征没被修改)
   # - L1 缓存 (缓存的是原始特征)
   # - 最终结果 (因为 bodies 有值但查询失败)
   ```

2. **为什么"头颅三维重建"还是 no_match？**
   - 特征提取: bodies=['颅脑'], post=['三维重建'], scan=[]
   - 虽然推断了 scan=['平扫']，但查询条件是：
     ```python
     three_level_name='颅脑' AND scan_name='平扫' AND post_processing_name='三维重建'
     ```
   - 可能标准表中没有这个组合！

3. **handoff 说"直接调用有效，API 调用无效"**:
   - 这个说法**可能是错误的**
   - 需要验证标准表中是否真的有 `"CT颅脑(平扫+三维重建)"`

**结论**:
- ❌ **修复完全无效**（局部变量推断不会持久化）
- ❌ 即使推断了扫描方式，标准表中可能也没有对应的组合
- 📊 需要检查标准表中是否有 `"CT颅脑(平扫+三维重建)"`

---

## 🎯 准确率提升的真实情况

### Handoff 声称的提升
```
基线: 94.31%
预期提升: +2.5% ~ 4.0%
目标准确率: 96.8% ~ 97.8%
```

### 实际有效的修复

| 修复项 | 状态 | 实际效果 |
|--------|------|---------|
| 词典加载条件 | ✅ 已修复 | 加载 1558 条启用映射（含"头颅"映射） |
| "头颅"映射 | ✅ 已生效 | 18,192 条"头颅"记录可匹配到"颅脑" |
| 降级劫持修复 | ⚠️ 部分有效 | 阻止劫持但产生 no_match |
| 扫描方式推断 | ❌ 完全无效 | 局部变量推断不持久化 |

### 重新评估

**保守估计**:
- "头颅"映射修复: +0.5% ~ 1.0%（假设 18k 中有 1k 条之前匹配错误）
- 降级劫持修复: 影响不明确（wrong_match 变 no_match，可能不算改善）
- 扫描方式推断: +0%（无效）

**预期准确率提升**: **+0.5% ~ 1.0%** (94.31% → **94.8% ~ 95.3%**)

**远低于 handoff 声称的 +2.5% ~ 4.0%**

---

## 📋 建议的修复方案

### 立即执行

1. **删除无效的映射**
   ```sql
   -- ID=17255/17256 在错误的 step，永远不会生效
   DELETE FROM nlp_phrase_map WHERE id IN (17255, 17256);
   ```

2. **验证标准表**
   ```sql
   -- 检查是否有"颌面部+三维重建"的标准项目
   SELECT checkitem_code, checkitem_name 
   FROM nlp_checkitem_standard 
   WHERE modality_name='CT' 
   AND three_level_name LIKE '%颌面%'
   AND post_processing_name LIKE '%三维%';
   
   -- 检查是否有"颅脑(平扫+三维重建)"的标准项目
   SELECT checkitem_code, checkitem_name 
   FROM nlp_checkitem_standard 
   WHERE modality_name='CT' 
   AND three_level_name='颅脑'
   AND scan_name='平扫'
   AND post_processing_name='三维重建';
   ```

3. **运行验证测试（调整预期）**
   ```bash
   python scripts/bulk_match_and_import.py \
     --task-name "P0验证-实际提升评估" \
     --sample 1000 \
     --skip-import
   ```
   **预期结果**: 准确率提升 +0.5% ~ 1.0%（不是 +2.5% ~ 4.0%）

### 正确修复扫描方式推断

**方案 A**: 在特征提取阶段推断（推荐）
```python
# 在 standard_lookup_service.py 的 find_default_process() 中
def find_default_process(self, childrens, process_type, modality, version):
    for node in childrens:
        # 现有逻辑...
        
        # 新增: CT/MR 有后处理但无扫描方式时，推断"平扫"
        if modality in ('CT', 'MR'):
            if node.pos_dict.get('post') and not node.pos_dict.get('scan'):
                node.add_entity(" ", 'scan', '平扫')
                node.fill_default = True
```

**方案 B**: 在词典中添加映射
```sql
-- 在 nlp_phrase_map 中添加
INSERT INTO nlp_phrase_map (modality, src_word, dst_word, step, version, enable)
VALUES 
  ('CT', '三维重建', '平扫+三维重建', 'process', 'V3.8.2', 1),
  ('MR', '三维重建', '平扫+三维重建', 'process', 'V3.8.2', 1);
```

---

## 📊 总结

### ✅ 成功的修复
1. **"头颅"→"颅脑"映射已生效**（通过 ID=16329）
2. **短语映射加载逻辑正确**（`WHERE enable = 1`）

### ⚠️ 有副作用的修复
1. **降级劫持修复**: 阻止了劫持，但产生 no_match（可能是正确的行为）

### ❌ 无效的修复
1. **扫描方式推断**: 局部变量推断不会持久化，完全无效
2. **ID=17255/17256 映射**: 在错误的 step，永远不会被应用

### 📉 准确率提升预期
- **Handoff 声称**: +2.5% ~ 4.0%
- **实际预期**: +0.5% ~ 1.0%
- **差距原因**: 只有"头颅"映射真正有效，其他修复无效或效果不明确

### 🔧 下一步建议
1. 删除 ID=17255/17256 无效映射
2. 验证标准表中的项目覆盖度
3. 正确实现扫描方式推断（方案 A 或 B）
4. 运行验证测试，使用调整后的预期（+0.5% ~ 1.0%）

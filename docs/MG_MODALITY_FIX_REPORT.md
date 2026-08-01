# MG模态匹配修复报告

**修复日期**: 2026-08-01  
**修复版本**: v13810-ea6e7d16cdaf  
**任务**: 修复MG（乳腺钼靶）模态完全无法匹配的严重bug

---

## 📊 修复效果对比

| 指标 | 修复前（任务2） | 修复后（任务3） | 提升 |
|------|----------------|----------------|------|
| **总匹配率** | 63.0% (625/992) | **65.62%** (651/992) | **+2.62%** ✅ |
| **准确率** | 98.72% (617/625) | **98.92%** (644/651) | **+0.20%** ✅ |
| **匹配成功数** | 625条 | **651条** | **+26条** ✅ |
| **失败数** | 375条 | **348条** | **-27条** ✅ |

### 失败原因分析

| 失败原因 | 修复前 | 修复后 | 改善 |
|---------|-------|-------|------|
| **缺少词汇** | 326条 (86.9%) | **300条** (86.2%) | **-26条** ✅ |
| **复杂表述** | 41条 (10.9%) | **41条** (11.8%) | 持平 |
| **无标准项** | 8条 (2.1%) | **7条** (2.0%) | -1条 |

---

## 🔍 根因分析

### Bug 1: 短语映射enable字段逻辑错误 (最严重)

**问题**:
```python
# 错误代码
"FROM nlp_phrase_map WHERE enable = 1"  # 加载的是禁用的规则！
```

**影响**:
- 数据库中所有启用的短语映射规则(enable=0)都没有被加载
- 修复前只加载了1558条规则，修复后加载了**7839条**规则
- 导致大量词汇变换和规范化规则失效

**修复**:
```python
# 正确代码
"FROM nlp_phrase_map WHERE enable = 0"  # 加载启用的规则
```

---

### Bug 2: MG标准数据加载失败 (核心问题)

**问题**:
```python
# 错误逻辑：从X线中筛选MG
df_xray = df_all[df_all['modality_name'] == 'X线']
sub_masks = {
    'MG': dev == 'MG',  # 但MG的modality_name是'MG'，不是'X线'！
}
```

**数据库实际情况**:
- MG标准项目的`modality_name = 'MG'`（独立模态）
- 不是`modality_name = 'X线'`
- 导致所有51条MG标准项目完全没有被加载

**修复**:
```python
# 正确逻辑：MG作为独立模态处理
for modality in ['CT', 'MR', 'DSA', 'MG']:
    df_mod = df_all[df_all['modality_name'] == modality]
    # ... 正常加载
```

**数据库修复**:
```sql
-- 同时修复device_type_name字段
UPDATE nlp_checkitem_standard 
SET device_type_name = 'MG'
WHERE modality_name = 'MG' 
  AND (device_type_name IS NULL OR device_type_name = '');
-- Updated 51 rows
```

---

### Bug 3: 侧位组合词分词优先级不足

**问题**:
- jieba可能将"双侧乳腺"拆分为"双侧"+"乳腺"
- 导致短语映射规则无法正确应用

**修复**:
```python
# 提高组合词的jieba词频
for word, wtype in self.mdict.items():
    if len(word) >= 3 and any(prefix in word for prefix in ['双侧', '左侧', '右侧', '单侧']):
        freq = 999999  # 更高词频，避免被拆分
    else:
        freq = 883635
    jieba.add_word(word, tag=wtype, freq=freq)
```

**短语映射增强**:
```sql
-- 添加恒等映射，确保组合词不被变换
INSERT INTO nlp_phrase_map (modality, src_word, dst_word, step, version, enable) 
VALUES 
  ('MG', '双侧乳腺', '双侧乳腺', 'normalize', 'V3.8', 0),
  ('MG', '左侧乳腺', '左侧乳腺', 'normalize', 'V3.8', 0),
  ('MG', '右侧乳腺', '右侧乳腺', 'normalize', 'V3.8', 0);
```

---

## ✅ 验证测试

### 测试用例

| 输入 | 模态 | 修复前 | 修复后 | 结果 |
|------|------|--------|--------|------|
| MG双侧乳腺钼靶 | MG | ❌ 0个标准项 | ✅ 11个标准项 | **exact, confidence=1.0** |
| MG左侧乳腺钼靶 | MG | ❌ 0个标准项 | ✅ 11个标准项 | **exact, confidence=1.0** |
| MG右侧乳腺钼靶 | MG | ❌ 0个标准项 | ✅ 11个标准项 | **exact, confidence=1.0** |

### 匹配示例

**输入**: "MG双侧乳腺钼靶"

**输出**:
```json
{
  "num_standard": 11,
  "tier": "exact",
  "confidence": 1.0,
  "standard": [
    {
      "code": "44040803M10000",
      "name": "* MG双侧乳腺钼靶"
    }
  ]
}
```

---

## 📈 影响范围

### 直接影响
- **MG模态**: 从完全无法匹配(0%)提升到正常匹配
- **其他模态**: 因短语映射修复，匹配质量全面提升

### 潜在影响
- 所有依赖短语映射的模态都会受益
- 预计US/SPECT/DSA等模态的匹配率也会有提升

---

## 🎯 下一步优化建议

基于修复后的失败分析，剩余300条"缺少词汇"失败案例主要集中在：

### 1. US（超声）词汇缺失 (~40-50条失败)
```
核心词汇：
- 常规超声、超声检查、彩色多普勒
- 床旁超声、术中超声
- 弹性成像、造影超声
```

### 2. SPECT（核医学）词汇缺失 (~30-40条失败)
```
核心词汇：
- 灌注显像、心肌灌注
- SPECT显像、ECT
- 静息显像、负荷显像
```

### 3. DSA（介入）词汇缺失 (~20-30条失败)
```
核心词汇：
- 经皮穿刺、活检、抽吸
- 造影、血管造影
- 栓塞、支架、置管
```

**预期效果**: 补充这些词汇后，匹配率可提升至**75-80%**

---

## 📝 技术总结

### 关键教训

1. **enable字段语义混乱**
   - 0=启用, 1=禁用（反直觉）
   - 需要统一规范或重构为boolean

2. **数据结构假设风险**
   - 代码假设MG是X线的子类型
   - 但数据库中MG是独立模态
   - 需要加强数据结构验证

3. **分词优先级问题**
   - 组合词需要更高优先级
   - jieba的默认行为可能不符合预期

### 修复文件清单

```
src/match_service/engine/match_engine_v2/data_loader.py
- 修复enable字段逻辑
- 修复MG模态加载逻辑
- 提高侧位组合词jieba优先级

数据库修复:
- nlp_checkitem_standard: 更新51条MG记录的device_type_name
- nlp_phrase_map: 添加3条侧位乳腺恒等映射
```

---

## 🔗 相关文档

- [ACR-AC全模态匹配测试 - 详细失败分析报告](./ACRAC_DETAILED_FAILURE_ANALYSIS.md)
- [评测任务2结果](http://localhost:9100/admin/evaluation/tasks/2)
- [评测任务3结果](http://localhost:9100/admin/evaluation/tasks/3)

---

**报告生成**: 2026-08-01  
**Git提交**: 828a89e - "fix: 修复MG模态匹配失败的三个关键bug"

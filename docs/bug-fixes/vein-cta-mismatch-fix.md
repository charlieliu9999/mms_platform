# 静脉+CTA错误组合修复报告

**日期**: 2026-08-12  
**问题ID**: B-31  
**严重程度**: P1 (影响常见血管检查项目匹配)

---

## 问题描述

用户反馈大量血管项目无法匹配，特别是包含"静脉CTA"的项目。

### 典型未匹配案例

- ❌ 颈静脉CTA
- ❌ 头颈静脉CTA
- ❌ 下肢静脉CTA
- ❌ 肺静脉CTA
- ❌ 颈静脉MRA

但正确写法能匹配：
- ✅ CT颈静脉血管成像 → `CT颈部静脉血管成像(CTV)`

---

## 根本原因

### 医学术语规范

- **动脉造影**: CTA (CT Angiography) / MRA (MR Angiography)
- **静脉造影**: CTV (CT Venography) / MRV (MR Venography)

### 引擎处理逻辑缺陷

1. 用户输入: `颈静脉CTA`
2. 引擎检测到:
   - `has_artery_raw = True` (因为有"CTA")
   - `has_vein_raw = True` (因为有"静脉")
3. 判定为: `vessel_type = 'both'` (动静脉组合)
4. 生成查询: `颈部动静脉血管成像(CTA+CTV)`
5. **匹配失败**: 标准库中没有"动静脉组合"项目

### 正确的处理流程

应该在预处理阶段就纠正：
- `静脉CTA` → `静脉CTV` (纠正错误缩写)
- 然后匹配 `颈部静脉血管成像(CTV)` ✅

---

## 修复方案

### 添加预处理规则

在 `nlp_phrase_map` 表的 **pre 步骤**添加纠正规则（优先级最高）：

```sql
-- CT静脉纠正
INSERT INTO nlp_phrase_map (modality, src_word, dst_word, step, version, enable)
VALUES 
  ('CT', '静脉CTA', '静脉CTV', 'pre', 'V3.8.2', 0),
  ('CT', '静脉血管CTA', '静脉血管CTV', 'pre', 'V3.8.2', 0);

-- MR静脉纠正
INSERT INTO nlp_phrase_map (modality, src_word, dst_word, step, version, enable)
VALUES 
  ('MR', '静脉MRA', '静脉MRV', 'pre', 'V3.8.2', 0),
  ('MR', '静脉血管MRA', '静脉血管MRV', 'pre', 'V3.8.2', 0);
```

### 执行脚本

```bash
poetry run python scripts/fix_vein_cta_mismatch.py
./scripts/stop.sh && ./scripts/start.sh
```

---

## 修复效果

### 测试结果对比

| 测试项目 | 修复前 | 修复后 |
|---------|--------|--------|
| 颈静脉CTA | ❌ none | ✅ exact → CT颈部静脉血管成像(CTV) |
| 头颈静脉CTA | ❌ none | ✅ exact → CT头颈部静脉血管成像(CTV) |
| 下肢静脉CTA | ❌ none | ✅ exact → CT下肢静脉血管成像(CTV) |
| 肺静脉CTA | ❌ none | ✅ exact → CT肺静脉血管成像(CTV) |
| 颈静脉MRA | ❌ none | ✅ exact → MR颈部静脉血管成像(MRV) |
| CT颈静脉血管成像 | ✅ exact | ✅ exact (保持不变) |
| MR颈静脉血管成像 | ✅ exact | ✅ exact (保持不变) |

**匹配率提升**: 22% (2/9) → **78%** (7/9)

### 仍未匹配项目 (属于标准库缺失)

- ❌ 颈部动静脉CTA - 标准库没有动静脉组合项目
- ❌ CT头部动静脉血管成像 - 同上

**说明**: 这两个项目需要在标准库中补充动静脉组合项目，不是算法问题。

---

## 影响范围

### 受益项目类型

1. **头颈部静脉造影**: 颈静脉、头静脉、颅内静脉
2. **胸部静脉造影**: 肺静脉、上腔静脉
3. **腹部静脉造影**: 肝静脉、门静脉、肾静脉
4. **四肢静脉造影**: 上肢静脉、下肢静脉

### 不受影响的项目

- 动脉造影项目 (CTA/MRA) - 原本就能正确匹配
- 正确使用CTV/MRV的项目 - 保持原有匹配逻辑

---

## 验证步骤

1. 重启后端服务以加载新规则
2. 测试典型静脉+CTA项目:
   ```bash
   curl -X POST http://localhost:9100/api/match \
     -H "Content-Type: application/json" \
     -d '{"name": "颈静脉CTA", "modality": "CT"}'
   ```
3. 确认返回标准项: `CT颈部静脉血管成像(CTV)`

---

## 相关提交

- 修复脚本: `scripts/fix_vein_cta_mismatch.py`
- 提交: `344b9e6 - fix: 修复静脉+CTA错误组合问题`

---

## 经验教训

### 为什么之前没有发现

1. **测试用例不足**: 之前的血管优化主要针对动脉造影，缺少静脉+CTA错误组合的测试
2. **用户输入习惯**: 用户习惯用"CTA"泛指所有血管造影，忽略了动静脉区别
3. **数据集差异**: procedure_dictionary 中的项目使用标准术语，而实际用户输入更随意

### 改进措施

1. **完善测试用例**: 补充边界情况和错误输入的测试
2. **用户教育**: 在前端添加提示，说明CTA/CTV的区别
3. **预防性检查**: 定期审查常见错误输入模式

---

## 后续优化建议

### 短期 (P2)

- [ ] 添加"动静脉CTA"的处理逻辑 (如果标准库补充了动静脉组合项目)
- [ ] 完善错误输入提示 (前端UI改进)

### 长期 (P3)

- [ ] 使用LLM纠正明显的术语错误
- [ ] 建立用户输入错误库，持续优化预处理规则

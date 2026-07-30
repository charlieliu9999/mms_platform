# MMS Platform 匹配引擎修复方案（全局审查版）

## 问题根因

### 发现过程
1. ✅ 标准表中存在需要的组合（"颅脑+平扫+三维重建"、"颌面部+平扫+三维重建"）
2. ❌ API 返回 no_match
3. 🔍 追踪发现：**Step 3 分词阶段没有提取出扫描方式**
   - "头颅三维重建" → body='头颅', scan=(空), post='三维重建'
   - 查表时无法匹配 `scan_name='平扫'` 的记录

### 根本原因

**Step 9（补充默认处理方式）的逻辑有缺陷**：

```python
# standard_lookup_service.py: 56-63 行
def find_default_process(self, childrens, process_type, modality, version):
    for node in childrens:
        if node.pos_dict.get(process_type) or not node.pos_dict.get('body'):
            continue  # 已有 scan 或无 body，跳过
        if modality != 'DR' and node.pos_dict.get('post'):
            continue  # ❌ 问题在这里！有 post 就跳过，不补充 scan
```

**这个逻辑认为**："有后处理就不需要扫描方式"，但这是**错误的**！

**医学语义**：
- "三维重建"是基于扫描数据的后处理
- "头颅三维重建" 隐含 "头颅**平扫**三维重建"
- 标准表中的项目都显式包含扫描方式：`scan_name='平扫'`

---

## 修复方案

### 方案 A：删除阻止补充的逻辑（推荐）

**修改位置**：`src/match_service/engine/match_engine_v2/standard_lookup_service.py:62-63`

```python
# 修复前
def find_default_process(self, childrens, process_type, modality, version):
    for node in childrens:
        if node.pos_dict.get(process_type) or not node.pos_dict.get('body'):
            continue
        if modality != 'DR' and node.pos_dict.get('post'):
            continue  # ❌ 删除这两行
        
        # ... 补充默认处理方式的逻辑

# 修复后
def find_default_process(self, childrens, process_type, modality, version):
    for node in childrens:
        if node.pos_dict.get(process_type) or not node.pos_dict.get('body'):
            continue
        # ✅ 删除了 post 检查，允许"有 post 但无 scan"的情况补充默认 scan
        
        # ... 补充默认处理方式的逻辑
```

**影响分析**：
- ✅ 修复"头颅三维重建" → 补充 scan='平扫' → 匹配到"CT颅脑(平扫+三维重建)"
- ✅ 修复"颌面部三维" → 补充 scan='平扫' → 匹配到"CT颌面部(平扫+三维重建)"
- ⚠️ 需要验证：是否会影响其他已正常工作的案例？

### 方案 B：在 Step 10 查表时推断（备选）

保持 Step 9 不变，在 `_query_ct_mr()` 中推断并**写回 node**：

```python
def _query_ct_mr(self, df, bodies, scan, post):
    results = []
    degraded = False
    
    # 推断扫描方式
    if post and len(scan) == 0:
        scan = ['平扫']
        degraded = True
    
    # ✅ 关键：写回 node（需要传入 node 参数）
    # 但这会破坏函数接口，影响范围大
```

**问题**：需要传入 `node` 参数并修改它，破坏了查表函数的纯函数特性。

---

## 验证计划

### Phase 1: 单元测试（修复前）

创建测试脚本验证当前行为：

```python
# tests/test_scan_inference.py
async def test_current_behavior():
    """记录修复前的行为作为基线"""
    engine = await setup_engine()
    
    # 测试用例
    cases = [
        ("头颅平扫", "exact", 1),              # 基线 - 应该保持不变
        ("头颅三维重建", "none", 0),           # 问题案例 - 修复后应该匹配
        ("颌面部三维", "none", 0),             # 问题案例 - 修复后应该匹配
        ("三维重建", "degraded", 1),           # 降级 - 应该保持不变
        ("颅脑平扫", "exact", 1),              # 不需要映射 - 应该保持不变
        ("腹部平扫三维重建", "exact", ">0"),  # 其他部位 - 验证不受影响
    ]
    
    for text, expected_tier, expected_num in cases:
        result = engine.match(text, "CT", "V3.8.2")
        print(f"{text}: tier={result['tier']}, num={result['num_standard']}")
```

### Phase 2: 应用修复

修改 `standard_lookup_service.py:62-63`，删除对 `post` 的检查。

### Phase 3: 单元测试（修复后）

```python
async def test_after_fix():
    """验证修复后的行为"""
    engine = await setup_engine()
    
    # 预期结果
    cases = [
        ("头颅平扫", "exact", 1),              # ✅ 保持不变
        ("头颅三维重建", "partial", ">0"),     # ✅ 应该匹配（补充了默认 scan）
        ("颌面部三维", "partial", ">0"),       # ✅ 应该匹配
        ("三维重建", "degraded", 1),           # ✅ 保持不变
        ("颅脑平扫", "exact", 1),              # ✅ 保持不变
        ("腹部平扫三维重建", "exact", ">0"),  # ✅ 保持不变
    ]
```

**置信度预期**：
- `exact` (1.0): 所有特征都显式提取
- `partial` (0.8): 补充了默认处理方式（`fill_default=True`）
- `degraded` (0.6): 查表走了降级分支

### Phase 4: 回归测试

运行完整测试套件：
```bash
poetry run pytest tests/engine/ -v
```

### Phase 5: 集成测试

运行 1000 条样本验证：
```bash
python scripts/bulk_match_and_import.py \
  --task-name "Step9修复验证" \
  --sample 1000 \
  --skip-import
```

**预期结果**：
- wrong_match 减少（不再劫持到"非指定部位"）
- no_match 减少（原来无法匹配的现在可以匹配）
- 准确率提升 +1% ~ 2%

---

## 影响范围分析

### 直接影响

**修复的案例**（有 post 但无 scan 的情况）：
- "XX三维重建" → 补充 scan='平扫'
- "XX三维" → 补充 scan='平扫'（如果"三维"被识别为 post）
- 其他类似模式

**保持不变的案例**：
- "XX平扫" → 已有 scan，不补充 ✅
- "XX平扫三维重建" → 已有 scan，不补充 ✅
- "三维重建"（无部位） → 无 body，不补充，走降级分支 ✅

### 潜在风险

1. **"三维"的词性识别**
   - 如果"三维"被识别为 `post`，会补充 scan='平扫'
   - 需要检查词典中"三维"的定义

2. **DR 模态**
   - 原代码对 DR 有特殊处理：`if modality != 'DR'`
   - 修复后 DR 不受影响（因为 DR 的 process_type 是 'position'，不是 'scan'）

3. **其他后处理词汇**
   - "增强"、"灌注"等如果被识别为 post，也会补充 scan
   - 需要验证这些词汇的词性标注是否正确

---

## 实施步骤

### 1. 备份当前代码
```bash
cp src/match_service/engine/match_engine_v2/standard_lookup_service.py \
   src/match_service/engine/match_engine_v2/standard_lookup_service.py.backup
```

### 2. 运行修复前测试（建立基线）
```bash
poetry run python /tmp/test_before_fix.py > /tmp/baseline.txt
```

### 3. 应用修复
删除 `standard_lookup_service.py:62-63` 行

### 4. 运行修复后测试
```bash
poetry run python /tmp/test_after_fix.py > /tmp/after_fix.txt
```

### 5. 对比结果
```bash
diff /tmp/baseline.txt /tmp/after_fix.txt
```

### 6. 回归测试
```bash
poetry run pytest tests/engine/ -v
```

### 7. 集成测试
```bash
python scripts/bulk_match_and_import.py --task-name "Step9修复验证" --sample 1000 --skip-import
```

### 8. 如果测试通过，提交修复
```bash
git add src/match_service/engine/match_engine_v2/standard_lookup_service.py
git commit -m "fix: allow default scan inference when post-processing exists

Problem:
- Input '头颅三维重建' returns no_match
- Standard table has '颅脑+平扫+三维重建' entry
- Step 3 extracts: body='头颅', scan=(empty), post='三维重建'
- Step 9 skips scan补充 because post exists
- Step 10 cannot match without scan

Fix:
- Remove post check in find_default_process() (line 62-63)
- Allow scan='平扫' inference for 'XX三维重建' pattern
- Confidence: partial (0.8) because scan is inferred

Impact:
- Fixes 'XX三维重建' and 'XX三维' patterns
- No impact on cases with explicit scan
- Estimated accuracy improvement: +1% ~ 2%

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## 总结

### 问题链条

1. **Step 3（分词）**：没有提取扫描方式
   - "头颅三维重建" → scan=(空)
2. **Step 9（补充默认）**：被 post 检查阻止
   - `if node.pos_dict.get('post'): continue` ❌
3. **Step 10（查表）**：无法匹配
   - 查询条件缺少 `scan_name`

### 修复原理

- 删除 Step 9 中对 `post` 的检查
- 允许"有 post 但无 scan"的情况补充默认 scan='平扫'
- 医学语义正确："三维重建"隐含"基于平扫数据"

### 预期效果

- ✅ 修复"头颅三维重建" → "CT颅脑(平扫+三维重建)"
- ✅ 修复"颌面部三维" → "CT颌面部(平扫+三维重建)"
- ✅ 准确率提升 +1% ~ 2%
- ✅ 不影响已正常工作的案例

### 与之前修复的关系

- **之前的修复**：在 `_query_ct_mr()` 中推断（局部变量，无效）
- **正确的修复**：在 `find_default_process()` 中补充（修改 node，持久化）

这就是为什么你要求我做全局审查的原因！**局部修复可能看起来有效，但不理解数据流就会失败。**

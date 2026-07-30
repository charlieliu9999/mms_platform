# MMS Platform 匹配引擎问题追踪与待办

## 📋 当前状态

**日期**: 2026-07-30 23:30  
**会话**: Session #3  
**任务**: P0 优化 - 修复"三维重建"劫持问题

---

## 🔍 已完成的工作

### 1. 全局代码审查
- ✅ 通过标准表检查，确认需要的数据都存在
- ✅ 端到端追踪"头颅三维重建"的完整匹配流程
- ✅ 定位问题根源：Step 9 的逻辑缺陷

### 2. 问题根因定位

**核心发现**：
```python
# standard_lookup_service.py: 62-63 行
if modality != 'DR' and node.pos_dict.get('post'):
    continue  # ❌ 有后处理就跳过，不补充扫描方式
```

**问题链**：
1. Step 3（分词）："头颅三维重建" → body='头颅', scan=(空), post='三维重建'
2. Step 9（补充默认）：因为有 `post`，被跳过，**没有补充 scan='平扫'**
3. Step 10（查表）：查询条件缺少 `scan_name`，**无法匹配**

### 3. 尝试的修复

**修改内容**：删除 `standard_lookup_service.py:62-63` 行

**测试结果**：
- ✅ 修复成功（2/4）：
  - "颌面部三维" → "CT颌面部(平扫)"
  - "上腹部三维重建" → "CT上腹部(平扫+三维重建)"
- ❌ 仍未修复（2/4）：
  - "头颅三维重建" → no_match
  - "腹部三维重建" → no_match
- ⚠️ 副作用：
  - "三维重建"（降级）：多匹配了"CT平扫"（1→2条）

### 4. 深入发现的新问题

通过详细追踪发现：
- Step 9 **确实补充了** scan='平扫' ✅
- 但查表时 body 仍是 '头颅' 而不是 '颅脑' ❌

**关键对比**：
| 案例 | Step 9 后的 body | 查表结果 | 原因 |
|------|----------------|---------|------|
| "头颅平扫"（API完整流程） | '颅脑' | ✅ 匹配 | Step 8 应用了映射 |
| "头颅三维重建"（测试） | '头颅' | ❌ 不匹配 | Step 8 **未应用映射** |

**结论**：问题不只在 Step 9，**Step 8（消歧）也有问题**！

---

## ❌ 未解决的问题

### 问题 #1: "头颅三维重建"匹配失败（核心问题）

**现象**：
- 标准表中存在："颅脑+平扫+三维重建"（13条）
- API 返回：no_match

**根因**：
1. **Step 9 问题**（部分解决）：post='三维重建' 阻止了 scan 补充
2. **Step 8 问题**（未解决）：post='三维重建' 阻止了 "头颅"→"颅脑" 映射

**影响范围**：
- 所有"XX三维重建"模式（X='头颅'、'腹部'等部分部位）
- 估计影响 1000+ 条记录

### 问题 #2: Step 8 消歧逻辑的条件判断

**需要调查**：
- 为什么"头颅平扫"时 Step 8 会应用"头颅"→"颅脑"映射？
- 为什么"头颅三维重建"时 Step 8 **不应用**这个映射？
- `body_2process_remap()` 的完整逻辑是什么？
- 哪个条件阻止了有 post='三维重建' 时的部位映射？

**代码位置**：
- `src/match_service/engine/match_engine_v2/disambiguation_service.py`
- `_body_2process_remap_ct_mr()` 方法
- `_scan_post_map()` 方法

### 问题 #3: 降级案例的副作用

**现象**：
- "三维重建"（无部位）：修复前 1 条，修复后 2 条
- 多匹配了"CT平扫"

**原因**：
- 降级分支也补充了 scan='平扫'
- 查表时匹配到了"非指定部位+平扫"

**影响**：
- 可能影响准确率计算（多余的匹配）
- 需要确认是否合理

---

## 📝 下一步行动计划

### Phase 1: 深入分析 Step 8（优先级最高）

**目标**：理解为什么"头颅三维重建"在 Step 8 没有应用部位映射

**步骤**：
1. 创建完整的 pipeline 追踪脚本（不跳过任何步骤）
2. 对比以下案例在 Step 8 的详细过程：
   - "头颅平扫"（body 被映射）
   - "头颅三维重建"（body **未**被映射）
   - "颌面部三维"（body 被映射？）
3. 阅读 `disambiguation_service.py` 的完整逻辑
4. 找出阻止映射的具体条件

**预期输出**：
- Step 8 的完整逻辑流程图
- 阻止"头颅"映射的具体代码行
- 修复方案（可能需要修改 Step 8，而不只是 Step 9）

### Phase 2: 设计完整修复方案

**原则**：
- 一次性修复 Step 8 和 Step 9 的问题
- 确保所有"XX三维重建"模式都能正确匹配
- 验证无回归

**需要修复的位置**（预期）：
1. `standard_lookup_service.py:62-63`（Step 9）- 已知
2. `disambiguation_service.py` 的某个条件（Step 8）- 待定位

### Phase 3: 完整验证

**测试用例**（扩展）：
```python
test_cases = [
    # 基线
    ("头颅平扫", "exact", 1),
    ("颅脑平扫", "exact", 1),
    
    # 核心问题案例
    ("头颅三维重建", "partial", ">0"),   # 关键！
    ("颌面部三维", "partial", ">0"),
    ("腹部三维重建", "partial", ">0"),
    ("上腹部三维重建", "partial", ">0"),
    
    # 降级案例
    ("三维重建", "degraded", 1),         # 验证副作用
    
    # 已有 scan 的案例
    ("头颅平扫三维重建", "exact", ">0"),
    ("颌面部平扫三维", "exact", ">0"),
    
    # 其他部位验证
    ("胸部三维重建", "partial", ">0"),
    ("颈部三维重建", "partial", ">0"),
]
```

### Phase 4: 提交修复

**条件**：
- 所有测试用例通过
- 回归测试通过（`pytest tests/engine/`）
- 1000 条样本验证准确率提升

---

## 📁 生成的文件

### 报告文档
- `docs/reports/2026-07-30-code-review-findings.md` - 代码审查报告
- `docs/reports/2026-07-30-fix-proposal-after-global-review.md` - 修复方案
- `docs/reports/2026-07-30-step9-fix-status.md` - Step 9 修复状态

### 测试脚本
- `/tmp/test_baseline.py` - 基线测试（修复前）
- `/tmp/test_after_fix.py` - 修复后测试
- `/tmp/trace_features.py` - 特征提取追踪
- `/tmp/trace_step9.py` - Step 9 详细追踪
- `/tmp/diagnose.py` - 标准表检查

### 测试结果
- `/tmp/baseline_test_results.json` - 基线结果
- `/tmp/after_fix_test_results.json` - 修复后结果

---

## 🔄 回滚操作

### 回滚代码修改

```bash
# 恢复 standard_lookup_service.py
git checkout src/match_service/engine/match_engine_v2/standard_lookup_service.py

# 或手动恢复第 62-63 行：
# if modality != 'DR' and node.pos_dict.get('post'):
#     continue
```

### 重启服务
```bash
# 停止当前服务
pkill -f "uvicorn match_service"

# 重新启动
cd /Users/charlieliu/git_project_vscode/09_medical/mms_platform
poetry run uvicorn match_service.main:app --host 0.0.0.0 --port 9100 --reload
```

---

## 💡 关键教训

### 1. 全局审查的重要性 ✅
你的要求非常正确：
- 局部修复看似有效，但可能只解决了表面问题
- 必须理解完整数据流才能做出正确修复
- "修复后测试失败"暴露了更深层的问题

### 2. 测试驱动的价值 ✅
- 基线测试确保修复不破坏已有功能
- 逐步验证暴露了 Step 8 的新问题
- 对比测试揭示了不同案例的处理差异

### 3. 分阶段修复的必要性 ✅
- Step 9 和 Step 8 的问题相互关联
- 需要一次性修复，而不是逐个击破
- 避免"打地鼠"式的修复

---

## 📌 下次会话开始时

### 快速恢复上下文

1. 阅读本文件
2. 检查代码是否已回滚：
   ```bash
   grep "if modality != 'DR' and node.pos_dict.get('post')" \
     src/match_service/engine/match_engine_v2/standard_lookup_service.py
   ```
   应该能找到这一行（说明已回滚）

3. 运行基线测试确认环境：
   ```bash
   poetry run python /tmp/test_baseline.py
   ```

### 继续工作

从 **Phase 1: 深入分析 Step 8** 开始。

---

**记录时间**: 2026-07-30 23:30  
**记录人**: Claude Opus 5  
**状态**: 问题已定位，修复已回滚，等待深入分析

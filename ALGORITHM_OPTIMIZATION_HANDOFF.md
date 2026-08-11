# 匹配算法优化任务交接文档

## 任务概述

对 4555 条医院项目的匹配结果进行系统审核，从算法层面优化 301 个可优化项目的匹配准确率。

**目标**：将整体匹配准确率从 68.2% 提升到 70%+，未匹配率从 16.7% 降低到 13%-

---

## 已完成工作

### ✅ Phase 1: 乳腺X线路由审核策略优化（2026-08-10）

**提交**: `1fc3c58` - "fix: 优化乳腺X线→MG路由审核策略，允许degraded结果直接通过"

**修改文件**:
- `src/match_service/core/dispatcher.py` - 修改 `_apply_result_review_policy` 方法
- `scripts/test_breast_routing_fix.py` - 验证脚本

**问题根因**:
- 33个乳腺X线项目（DR/XR模态）成功路由到MG并匹配（tier=degraded）
- 但审核策略过于严格：跨模态路由 + 非exact → 强制降级为 ambiguous
- 标记为 `modality_route_review`，需人工审核

**解决方案**:
- 检测高置信度路由场景：`(DR|XR) + 乳腺关键词 → MG`
- 对该场景放宽策略：exact/partial/degraded 都允许直接通过
- 其他跨模态路由保持原策略

**验证结果**: 5个测试用例全部通过

**预期效果**: 33项从 modality_route_review → degraded/partial

---

### 🔶 Phase 2: 词库增强（2026-08-11）- 部分成功

**详细报告**: `docs/reports/phase_2_summary.md`

#### Phase 2A: 泛指词汇映射 - ❌ 失败（放弃）

**实施内容**:
- 添加 phrase_map 规则：关节→四肢及关节, 骨骼→全身骨骼, 全身→全身
- 添加医学词典条目
- 引擎版本: v15119-143c5b85d10b

**测试结果**: 2/9 (22% 通过率)

**失败原因**:
- 标准库 body_part_l3 存储具体部位（"双膝关节"），没有泛指项（"关节"）
- 词汇映射只能改变实体名称，不能改变标准查找逻辑
- 需要算法层面的降级匹配，不是词库能解决的

**结论**: 方案无效，需要转向 Phase 4（算法增强）

#### Phase 2B: 血管成像词汇映射 - 🔶 部分成功

**实施内容**:
- 添加 phrase_map 规则：脊髓动脉→脊髓血管, 肝脏血管→肝脏, 小肠血管→小肠, 肾脏血管→肾脏
- 添加组合词到医学词典
- 引擎版本: v15127-bc5ffebdfb99

**测试结果**: 4/10 (40% 通过率)
- ✅ CT/MR肾脏血管成像 → exact
- ❌ CT/MR脊髓动脉血管成像 → none
- ❌ CT/MR肝脏血管成像 → none
- ❌ CT/MR小肠血管成像 → none

**失败原因**:
1. **Pre规则破坏性替换**: `血管成像(CTA)` → ` CTA`（删除了"血管成像"关键词）
   - 输入: `CT脊髓动脉血管成像(CTA)`
   - 处理后: `CT脊髓动脉 CTA`（body和scan都无法解析）

2. **标准库层级不匹配**: 
   - 用户输入泛指"脊髓动脉"
   - 标准库要求具体节段"颈段脊髓动脉""胸段脊髓动脉""腰段脊髓动脉"

3. **真实标准库缺口**: 小肠没有血管成像标准项

**关键发现**: Pre规则设计缺陷是核心障碍，修复后预计可解决10-15项

**结论**: 部分有效，但需要先修复 Pre 规则

---

## 待完成工作

### 📋 优化计划文件

完整计划保存在：`/Users/charlieliu/.claude/plans/zesty-wibbling-clarke.md`

包含：
- 问题分类（5大类：standard_lib_gap, lexicon_gap, parser_ambiguity, modality_route_review, standard_data_conflict）
- 优化方案（按优先级1-6）
- 实施步骤（Phase 1-5）
- 验证方案
- 风险评估

### 🎯 下一步：Phase 2 - 词库增强（预计解决55项）

#### Phase 2A: 泛指词汇映射（~40项）

**问题**: "X线关节(平扫)"、"X线骨骼(平扫)"、"MR关节(平扫)" 等项目
- 引擎无法解析：泛指词"关节""骨骼""全身"未在医学词典中
- 标记为 `lexicon_gap`

**解决方案**: 添加 nlp_phrase_map 规则

```sql
-- 连接数据库
-- psql postgresql://postgres:postgres@127.0.0.1:15432/acrac_db

-- 添加泛指词汇映射（step=normalize，在预处理阶段生效）
INSERT INTO nlp_phrase_map (src_word, dst_word, step, modality, version, enable)
VALUES 
  ('关节', '四肢关节', 'normalize', NULL, 'V3.8.2', 0),  -- enable=0表示激活
  ('骨骼', '全身骨骼', 'normalize', NULL, 'V3.8.2', 0),
  ('全身', '全身', 'normalize', NULL, 'V3.8.2', 0),
  ('血管', '血管', 'normalize', NULL, 'V3.8.2', 0);

-- 确认插入
SELECT src_word, dst_word, step FROM nlp_phrase_map WHERE src_word IN ('关节', '骨骼', '全身', '血管');
```

**热重载引擎**:
```bash
# 方案A: 调用管理API
curl -X POST http://localhost:9100/api/admin/engine/reload

# 方案B: 重启服务
./scripts/stop.sh && ./scripts/start.sh
```

**验证**:
```python
# scripts/test_generic_terms.py
test_cases = [
    ('X线关节(平扫)', 'DR'),
    ('X线骨骼(平扫)', 'DR'),
    ('MR关节(平扫)', 'MR'),
]
# 预期：从 lexicon_gap (tier=none) → degraded (有候选)
```

#### Phase 2B: 血管成像词汇映射（~15项）

**问题**: "CT脊髓动脉血管成像(CTA)"、"CT肝脏血管成像(CTA)" 等
- 标准库有 "CT脊髓动脉(血管成像CTA)"，但映射缺失
- 引擎解析 "脊髓动脉" 后查找失败

**解决方案**: 添加血管部位映射

```sql
INSERT INTO nlp_phrase_map (src_word, dst_word, step, modality, version, enable)
VALUES 
  ('脊髓动脉', '脊髓血管', 'global_map', NULL, 'V3.8.2', 0),
  ('肝脏血管', '肝脏', 'global_map', NULL, 'V3.8.2', 0),
  ('小肠血管', '小肠', 'global_map', NULL, 'V3.8.2', 0),
  ('肾脏血管', '肾脏', 'global_map', NULL, 'V3.8.2', 0);
```

**验证**:
```python
test_cases = [
    ('CT脊髓动脉血管成像(CTA)', 'CT'),
    ('CT肝脏血管成像(CTA)', 'CT'),
    ('MR小肠血管成像(MRA)', 'MR'),
]
# 预期：从 standard_lib_gap → exact/partial
```

---

### Phase 3: 标准库重复编码清理（14项）

**问题**: "MR全脊柱(平扫)" 有2个不同编码但名称相同
- 标记为 `standard_data_conflict`

**诊断SQL**:
```sql
SELECT item_name, modality, array_agg(item_code) as codes, COUNT(DISTINCT item_code) as code_count
FROM standard_check_items
WHERE is_active = true
GROUP BY item_name, modality
HAVING COUNT(DISTINCT item_code) > 1
ORDER BY code_count DESC;
```

**处理策略**:
1. 导出重复项清单
2. 人工确认哪个编码正确（咨询业务专家）
3. 标记错误编码 `is_active=false`

---

### Phase 4: 算法增强 - 泛指词汇降级匹配（~20项）

如果 Phase 2A 词库映射仍无法完全解决，需要增强算法：

**文件**: `src/match_service/engine/match_engine_v2/standard_lookup_service.py`

**方案**: 在 `_query_ct_mr` 或 `lookup_standard` 方法中，添加泛指词汇降级查找

```python
def _query_generic_fallback(self, text: str, modality: str, scan: str) -> list:
    """
    泛指词汇降级匹配
    输入: "X线关节(平扫)" → scan="平扫"
    策略: 查找标准库中所有"关节"相关项目，返回常见项
    """
    GENERIC_BODY_PATTERNS = {
        r'关节': ['四肢及关节', '关节'],
        r'骨骼': ['四肢及关节', '脊柱', '骨骼'],
        r'全身': ['非指定部位', '全身'],
        r'血管': ['血管'],
    }
    
    for pattern, body_hints in GENERIC_BODY_PATTERNS.items():
        if re.search(pattern, text):
            # SQL: body_part_l1 IN (...) AND scan_method=scan LIMIT 5
            # 标记: degraded=True, fallback_reason="generic_body_fuzzy_match"
            pass
```

---

## 验证方法

### 1. 批量重新匹配脚本

创建 `scripts/rematch_optimized_items.py`:

```python
"""
批量重新匹配已优化的项目，验证tier变化
"""
import asyncio
from sqlalchemy import text
from match_service.db import get_engine
from match_service.core.engine_holder import get_engine_holder
from match_service.core.dispatcher import MatchDispatcher

async def rematch():
    engine = get_engine()
    holder = get_engine_holder()
    await holder.initialize()
    
    async with engine.begin() as session:
        dispatcher = MatchDispatcher(session, holder)
        
        # 查询所有 reason_code = 'modality_route_review' 的项目
        result = await session.execute(text('''
            SELECT pmr.procedure_id, pd.name_zh, pd.modality
            FROM procedure_match_results pmr
            JOIN procedure_dictionary pd ON pmr.procedure_id = pd.id
            WHERE pmr.reason_code = 'modality_route_review'
        '''))
        
        improved = 0
        total = 0
        for row in result:
            total += 1
            new_result = await dispatcher.match(row.name_zh, row.modality)
            new_tier = new_result.get('tier')
            
            if new_tier in ['exact', 'partial', 'degraded']:
                improved += 1
                print(f'✅ {row.procedure_id}: {new_tier}')
            else:
                print(f'❌ {row.procedure_id}: {new_tier}')
        
        print(f'\n改善率: {improved}/{total} = {improved/total*100:.1f}%')
    
    await engine.dispose()

if __name__ == '__main__':
    asyncio.run(rematch())
```

运行：
```bash
poetry run python scripts/rematch_optimized_items.py
```

### 2. 整体统计对比

```sql
-- 优化前统计
SELECT tier, COUNT(*) FROM procedure_match_results GROUP BY tier;

-- 优化后重新统计（需要批量重新匹配）
-- 预期：exact 从 3108 → 3150+, none 从 654 → 600-
```

---

## 关键文件位置

**代码**:
- `src/match_service/core/dispatcher.py` - 路由和审核策略
- `src/match_service/engine/match_engine_v2/standard_lookup_service.py` - 标准查找逻辑
- `src/match_service/engine/match_engine_v2/data_loader.py` - 词库加载

**数据库表**:
- `nlp_phrase_map` - 短语映射规则（词库）
- `standard_check_items` - ACR标准项目库
- `procedure_match_results` - 匹配结果（tier, reason_code）
- `procedure_dictionary` - 医院项目字典

**计划文档**:
- `/Users/charlieliu/.claude/plans/zesty-wibbling-clarke.md` - 完整优化计划
- `/Users/charlieliu/.claude/projects/-Users-charlieliu-git-project-vscode-09-medical-mms-platform/memory/mms_architecture_overview.md` - 架构记忆

**测试脚本**:
- `scripts/test_breast_routing_fix.py` - Phase 1 验证
- `scripts/rematch_optimized_items.py` - 批量重新匹配（待创建）

---

## 如何继续任务

### 方式1: 直接引用此文档

在新对话中说：
```
继续完成匹配算法优化任务。请阅读项目根目录的 ALGORITHM_OPTIMIZATION_HANDOFF.md，
从 Phase 2（词库增强）开始执行。
```

### 方式2: 引用计划文件

```
请阅读 /Users/charlieliu/.claude/plans/zesty-wibbling-clarke.md 中的优化计划，
Phase 1 已完成（提交 1fc3c58），现在继续 Phase 2。
```

### 方式3: 从任务系统恢复

```
项目中有一个进行中的任务：审核匹配算法并优化未匹配项目。
Phase 1（乳腺路由优化）已完成，请继续 Phase 2（词库增强）。
参考 ALGORITHM_OPTIMIZATION_HANDOFF.md 文档。
```

---

## 预期最终效果

完成所有 Phase 后：

**优化项目数**:
- Phase 1: 33项 ✅
- Phase 2: 55项
- Phase 3: 14项
- Phase 4: 20项
- **总计**: ~120项（40% 的可优化项目）

**准确率提升**:
- Exact: 3,108 (68.2%) → 3,200+ (70%+)
- Partial/Degraded: 688 (15.1%) → 750+ (16%+)
- None/Ambiguous: 759 (16.7%) → 600- (13%-)

**剩余工作**: ~150项需要业务团队补充标准库数据（真实的标准库缺口）

---

## 注意事项

1. **词库映射规则的 enable 字段是反直觉的**：
   - `enable=0` 表示**激活**（生效）
   - `enable=1` 表示**禁用**（不生效）

2. **修改词库后必须热重载**：
   - 调用 `/api/admin/engine/reload`
   - 或重启服务

3. **测试时使用 version 参数**：
   - 默认使用最新版本 V3.8.2
   - 可以指定版本测试：`engine.match(text, modality, 'V3.8')`

4. **标准库数据质量问题需要业务确认**：
   - Phase 3 的重复编码清理
   - standard_lib_gap 中哪些应该补充、哪些确实无标准

---

最后更新：2026-08-10
任务状态：Phase 1 完成，Phase 2-5 待执行

# CT 模态未匹配问题分析报告

**数据规模**: 4555条数据中，CT模态未匹配 31 个distinct项（数据库54条记录，存在重复）

**分析时间**: 2024年

---

## 一、问题分布概览

### 1.1 Tier 分布统计

| Tier | 数量 | 占比 | 说明 |
|------|------|------|------|
| **ambiguous** | 10 | 32.3% | 解析出实体但部分信息无法匹配 |
| **none** | 21 | 67.7% | 完全未匹配 |
| **exact** | 0 | 0% | - |
| **partial** | 0 | 0% | - |
| **degraded** | 0 | 0% | - |

### 1.2 未匹配原因分类（none项细分）

| 原因类别 | 数量 | 占比 | 处理建议 |
|---------|------|------|---------|
| **标准库缺口** (standard_lib_gap) | 15 | 71.4% | ⚠️ 补充标准项 |
| **设计排除-放疗** (radiotherapy_sim) | 3 | 14.3% | ✅ 符合预期 |
| **设计排除-穿刺** (biopsy) | 2 | 9.5% | ✅ 符合预期 |
| **词库缺口** (lexicon_gap) | 1 | 4.8% | 🔧 补充医学词典 |

**关键发现**: 71.4%的none项是"有实体但未命中标准项"，说明**标准库覆盖不足是主要瓶颈**。

---

## 二、Ambiguous 问题深度分析（10条）

### 2.1 失败模式分类

#### 模式1: 血管成像标准项缺口（2条，20%）
```
❌ CTA腹部盆腔动脉血管成像(CTA)
❌ CT胸腰段脊髓动脉血管成像(CTA)
```

**根本原因**:
- 引擎能解析出"腹部盆腔动脉"、"胸腰段脊髓动脉"等实体
- 但标准库缺少对应的CTA项目
- 现有标准库血管成像覆盖不全（仅有常见的头颈部、下肢等部位）

**解决方案**:
```sql
-- 建议补充标准项（示例）
INSERT INTO standard_check_items (item_code, item_name, modality, body_part_l2, scan_method) VALUES
('2xxxxxxxxxx001', 'CT腹部盆腔动脉血管成像', 'CT', '腹部盆腔', 'CTA'),
('2xxxxxxxxxx002', 'CT脊柱脊髓动脉血管成像', 'CT', '脊柱脊髓', 'CTA');
```

#### 模式2: 特殊序列/后处理修饰（4条，40%）
```
❌ CT主动脉根部(心电门控增强多排螺旋CT)
❌ CT主动脉根部及外周血管多期增强扫描(平扫+增强+三维重建)
❌ CT胸部腹部(多平面重组MPR)
❌ CT胸部腹部(容积再现VR)
```

**根本原因**:
- 括号内的技术修饰语（心电门控、三维重建、MPR、VR）被保护未参与匹配
- 方括号处理器保护了这些术语，导致主体部分匹配后仍有残留
- 引擎无法将残留的技术描述归类，判定为ambiguous

**技术分析**:
```python
# 当前流程:
# 1. 预处理保护括号内容 → "CT主动脉根部[PROTECTED_0]"
# 2. 匹配主体 → 找到"CT主动脉"标准项
# 3. 恢复括号 → "CT主动脉根部(心电门控增强多排螺旋CT)"
# 4. 残留"心电门控增强多排螺旋CT"未匹配 → ambiguous
```

**解决方案（优先级排序）**:

**方案A（推荐）: 增强技术修饰语过滤规则** ⭐⭐⭐⭐⭐
```python
# 在 preprocess_service.py 中添加后处理修饰语模式
TECH_MODIFIERS = [
    '心电门控', '多排螺旋', '多平面重组', '多平面重建', 'MPR', 
    '容积再现', 'VR', '三维重建', '薄层扫描', '骨算法',
    'UHR', 'Quantum', '低剂量', '高分辨'
]

def normalize_tech_modifiers(text: str) -> str:
    """将技术修饰语标准化或移除"""
    for modifier in TECH_MODIFIERS:
        text = text.replace(f'({modifier})', '')
        text = text.replace(modifier, '')
    return text.strip('()（）')
```

**影响**: 预计解决 4/10 的 ambiguous 问题（40%改善）

**方案B: 补充带修饰语的标准项** ⭐⭐⭐
```sql
-- 为高频技术组合添加标准项变体
INSERT INTO standard_check_items VALUES
('2xxxxxxxxxx003', 'CT主动脉根部(心电门控)', 'CT', '心脏', '增强'),
('2xxxxxxxxxx004', 'CT主动脉(多平面重建)', 'CT', '主动脉', '平扫+增强');
```
**缺点**: 标准项膨胀，维护成本高

#### 模式3: 多项记录部分失配（3条，30%）
```
❌ CT主动脉血管成像(平扫+增强)
❌ CT冠状动脉血管成像(平扫+增强)联合CT血流储备分数(CT-FFR)
❌ CT颞骨及头颈部血管(双期增强+骨算法重建)
```

**根本原因**:
- "联合"、"及"等连接词导致拆分为多子项
- 部分子项（如"CT血流储备分数"、"骨算法重建"）无法匹配
- 引擎判定整体为 ambiguous

**解决方案**:

**方案A（短期）: 增强拆分规则** ⭐⭐⭐⭐
```python
# 在 preprocess_service.py 的 split_record 中增强处理
IGNORE_SUFFIXES = ['联合.*FFR', '骨算法重建', '三维重建']

def split_record(text, modality):
    # 先移除无医学意义的后缀
    for pattern in IGNORE_SUFFIXES:
        text = re.sub(pattern, '', text)
    # 再按现有规则拆分
    return original_split_logic(text, modality)
```

**方案B（长期）: 补充组合检查标准项** ⭐⭐⭐
```sql
-- 医学上有意义的组合检查应有独立标准项
INSERT INTO standard_check_items VALUES
('2xxxxxxxxxx005', 'CT冠状动脉血管成像+CT血流储备分数', 'CT', '冠状动脉', 'CTA+FFR');
```

#### 模式4: 其他（1条，10%）
```
❌ CT腹部盆腔(多平面重建)
```
同模式2，技术修饰语问题。

### 2.2 Ambiguous 优先级改进路线图

| 优先级 | 改进项 | 预计解决 | 工作量 | ROI |
|--------|--------|---------|--------|-----|
| P0 | 增强技术修饰语过滤 | 4条 (40%) | 1天 | ⭐⭐⭐⭐⭐ |
| P1 | 补充血管成像标准项 | 2条 (20%) | 2天 | ⭐⭐⭐⭐ |
| P2 | 增强多项拆分规则 | 3条 (30%) | 2天 | ⭐⭐⭐ |

**预期收益**: 通过P0+P1可解决60%的ambiguous问题（6/10条），ambiguous率从32.3%降至13%。

---

## 三、None 问题深度分析（21条）

### 3.1 标准库缺口项（15条，71.4%）

#### 分类1: 血管成像缺口（5条）
```
❌ CT小肠血管成像(CTA)
❌ CT肝脏血管成像(CTA)
❌ CT脊髓动脉血管成像(CTA)
❌ CT腹部动静脉血管成像(CTA+CTV)
```

**原因**: 标准库仅覆盖主流血管成像（头颈、下肢、主动脉），遗漏小器官血管。

**解决方案**: 
```sql
-- 补充专科血管成像标准项
INSERT INTO standard_check_items (item_code, item_name, modality, body_part_l2, scan_method) VALUES
('2xxxxxxxxxx010', 'CT小肠血管成像', 'CT', '小肠', 'CTA'),
('2xxxxxxxxxx011', 'CT肝脏血管成像', 'CT', '肝脏', 'CTA'),
('2xxxxxxxxxx012', 'CT脊髓动脉血管成像', 'CT', '脊髓', 'CTA'),
('2xxxxxxxxxx013', 'CT腹部动静脉血管成像', 'CT', '腹部', 'CTA+CTV');
```

#### 分类2: 特殊造影检查（4条）
```
❌ CT泪囊造影(平扫)
❌ CT泪道造影(平扫+对比剂注射)
❌ CT脊柱局部(脊髓造影)
❌ CT脊柱脊髓造影(平扫+增强)
```

**原因**: 造影检查是专科特殊检查，标准库覆盖不全。

**医学意义**: 
- 泪道造影：眼科专用，诊断泪道阻塞
- 脊髓造影：神经外科专用，诊断脊髓病变

**解决方案**: 
```sql
INSERT INTO standard_check_items VALUES
('2xxxxxxxxxx020', 'CT泪道造影', 'CT', '泪道', '造影'),
('2xxxxxxxxxx021', 'CT脊髓造影', 'CT', '脊髓', '造影');
```

#### 分类3: 特殊部位/检查（6条）
```
❌ CT 原发部位及区域淋巴结(平扫+增强)
❌ CT乳腺(平扫+增强)
❌ CT冠状动脉血管成像(平扫+增强+FFRCT)联合US超声心动图(...)
❌ CT尿路造影(平扫+增强)
❌ CT肩关节(直接造影)
```

**原因**: 
1. CT乳腺检查不常见（通常用MR或MG）
2. "原发部位及区域淋巴结"是肿瘤随访描述，非标准解剖部位
3. FFRCT+US联合检查是组合医嘱

**解决方案**:
```sql
-- 补充真实存在的检查
INSERT INTO standard_check_items VALUES
('2xxxxxxxxxx030', 'CT乳腺', 'CT', '乳腺', '平扫+增强'),
('2xxxxxxxxxx031', 'CT尿路造影', 'CT', '尿路', '造影'),
('2xxxxxxxxxx032', 'CT肩关节造影', 'CT', '肩关节', '造影');

-- "原发部位"是动态描述，建议通过消歧规则处理
INSERT INTO ambiguity_rules (pattern, target, condition) VALUES
('原发部位', '病灶区域', 'modality=CT AND contains(淋巴结)');
```

### 3.2 设计排除项（5条，合规 ✅）

#### 放疗模拟定位（3条）
```
✅ CT模拟定位(四维)
✅ CT模拟定位(平扫)
✅ CT模拟定位(平扫+增强)
```
**标记**: `radiotherapy_sim`  
**原因**: 放疗定位扫描不是影像诊断检查，按设计排除。  
**处理**: **无需改进，符合业务规则**。

#### 穿刺活检（2条）
```
✅ CT引导下肺穿刺活检
✅ CT胸部(平扫+增强，用于引导经皮穿刺定位)
```
**标记**: `biopsy`  
**原因**: 有创操作，不是影像检查本身。  
**处理**: **无需改进，符合业务规则**。

### 3.3 词库缺口（1条，4.8%）
```
❌ CT/MRI/PET-CT(化疗前基线)
```

**原因**: 
- 斜杠分隔的多模态未被识别
- "化疗前基线"非标准医学术语，未在词典中

**解决方案**:
```sql
-- 补充词典条目
INSERT INTO medical_dict (word, pos, category) VALUES
('化疗前基线', 'indication', 'clinical_stage'),
('基线', 'indication', 'clinical_stage');

-- 或在预处理阶段过滤
-- "化疗前基线"是临床描述而非检查名称，应在预处理时移除
```

### 3.4 模态识别错误（2条，需Review）
```
⚠️ ECT全身骨显像  (归入CT模态)
⚠️ US心脏经食管超声心动图右心声学造影(cTEE)  (归入CT模态)
```

**原因**: 数据录入错误，这两个应该是 SPECT 和 US 模态。

**解决方案**:
```sql
-- 修正模态
UPDATE unmatched_registry SET modality='SPECT' 
WHERE modality='CT' AND name_zh LIKE '%ECT%骨显像%';

UPDATE unmatched_registry SET modality='US' 
WHERE modality='CT' AND name_zh LIKE 'US%';
```

---

## 四、综合改进方案（分阶段实施）

### Phase 1: 快速修复（1-2天，解决50%问题）⚡

#### 任务1: 技术修饰语过滤增强
**文件**: `src/match_service/engine/match_engine_v2/preprocess_service.py`

```python
# 在 PreprocessService 类中添加
TECH_NOISE_PATTERNS = [
    r'\(心电门控[^)]*\)',
    r'\(多排螺旋[^)]*\)',
    r'\(多平面重[组建][^)]*\)',
    r'\(容积再现[^)]*\)',
    r'\(三维重建[^)]*\)',
    r'\(MPR[^)]*\)',
    r'\(VR[^)]*\)',
    r'\(骨算法[^)]*\)',
    r'多期增强扫描',
    r'双期增强',
]

def preprocess(self, text: str, modality: str, version: str):
    # 原有逻辑
    text, bracket_handler = self._protect_brackets(text)
    
    # 新增：后处理修饰语清洗
    if modality in ('CT', 'MR'):
        for pattern in self.TECH_NOISE_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # 原有逻辑继续
    text = self._apply_pre_rules(text)
    return text, bracket_handler
```

**预期收益**: 解决4条ambiguous（40%） + 可能改善部分none项

#### 任务2: 修正模态错误数据
```bash
poetry run python scripts/fix_modality_misrouting.py
```

```python
# scripts/fix_modality_misrouting.py
import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect('postgresql://...')
    
    # 修正 ECT 归类
    await conn.execute("""
        UPDATE unmatched_registry 
        SET modality='SPECT' 
        WHERE modality='CT' AND name_zh LIKE '%ECT%'
    """)
    
    # 修正 US 归类
    await conn.execute("""
        UPDATE unmatched_registry 
        SET modality='US' 
        WHERE modality='CT' AND name_zh LIKE 'US%'
    """)
    
    print("模态修正完成")
    await conn.close()

asyncio.run(main())
```

**预期收益**: 修正2条错误数据

### Phase 2: 标准库扩充（3-5天，解决35%问题）📚

#### 任务3: 补充血管成像标准项（优先级P0）
```sql
-- scripts/add_vascular_standards.sql
BEGIN;

INSERT INTO standard_check_items (item_code, item_name, modality, body_part_l2, scan_method, is_active) VALUES
-- 腹部血管
('20000000000101', 'CT腹部盆腔动脉血管成像', 'CT', '腹部盆腔', 'CTA', true),
('20000000000102', 'CT小肠血管成像', 'CT', '小肠', 'CTA', true),
('20000000000103', 'CT肝脏血管成像', 'CT', '肝脏', 'CTA', true),
('20000000000104', 'CT腹部动静脉血管成像', 'CT', '腹部', 'CTA+CTV', true),

-- 脊柱血管
('20000000000201', 'CT胸腰段脊髓动脉血管成像', 'CT', '脊柱', 'CTA', true),
('20000000000202', 'CT脊髓动脉血管成像', 'CT', '脊髓', 'CTA', true);

COMMIT;
```

**预期收益**: 解决7条未匹配（2 ambiguous + 5 none）

#### 任务4: 补充特殊造影检查
```sql
-- scripts/add_contrast_studies.sql
BEGIN;

INSERT INTO standard_check_items (item_code, item_name, modality, body_part_l2, scan_method, is_active) VALUES
-- 眼科造影
('20000000000301', 'CT泪道造影', 'CT', '泪道', '造影', true),

-- 神经外科造影
('20000000000401', 'CT脊髓造影', 'CT', '脊髓', '造影', true),

-- 泌尿外科
('20000000000501', 'CT尿路造影', 'CT', '尿路', '造影', true),

-- 骨科
('20000000000601', 'CT肩关节造影', 'CT', '肩关节', '造影', true);

COMMIT;
```

**预期收益**: 解决4条none

#### 任务5: 补充其他常见缺口
```sql
-- scripts/add_misc_standards.sql
BEGIN;

INSERT INTO standard_check_items (item_code, item_name, modality, body_part_l2, scan_method, is_active) VALUES
('20000000000701', 'CT乳腺', 'CT', '乳腺', '平扫+增强', true);

COMMIT;
```

**预期收益**: 解决1条none

### Phase 3: 消歧规则优化（2-3天，解决10%问题）🔧

#### 任务6: 增强多项拆分规则
```python
# src/match_service/engine/match_engine_v2/preprocess_service.py

def split_record(self, text: str, modality: str) -> list:
    """增强的记录拆分"""
    
    # 先移除无匹配价值的后缀
    IGNORE_SUFFIXES = [
        r'联合.*?FFR',  # CT-FFR是后处理，非独立检查
        r'联合.*?储备分数',
        r'骨算法重建$',
        r'三维重建$',
    ]
    
    for pattern in IGNORE_SUFFIXES:
        text = re.sub(pattern, '', text)
    
    # 原有拆分逻辑
    return self._original_split(text, modality)
```

**预期收益**: 解决3条ambiguous

#### 任务7: 补充消歧词典
```sql
-- scripts/add_disambiguation_rules.sql
BEGIN;

-- 将"原发部位"映射为通用部位
INSERT INTO ambiguity_rules (source_text, target_text, modality, priority) VALUES
('原发部位及区域淋巴结', '病灶区域淋巴结', 'CT', 100);

-- 补充临床术语
INSERT INTO medical_dict (word, pos, category) VALUES
('化疗前', 'modifier', 'clinical_context'),
('基线', 'modifier', 'clinical_context');

COMMIT;
```

**预期收益**: 解决1条none

### Phase 4: 长期优化（可选）🚀

#### 任务8: 引入AI辅助消歧（Phase F）
- 对ambiguous项使用LLM进行二次审核
- 建议补充的标准项

#### 任务9: 持续监控未匹配原因
- 每周分析新增未匹配项
- 自动识别高频缺口

---

## 五、实施计划与预期效果

### 5.1 实施时间表

| 阶段 | 任务 | 工作量 | 负责人 | 截止日期 |
|------|------|--------|--------|---------|
| Phase 1 | 任务1-2 | 1天 | 开发 | D+2 |
| Phase 2 | 任务3-5 | 3天 | 数据+开发 | D+5 |
| Phase 3 | 任务6-7 | 2天 | 开发 | D+7 |

### 5.2 预期改善效果

#### 改善前（当前状态）
```
总计: 31条CT未匹配
├─ ambiguous: 10条 (32.3%)
└─ none: 21条 (67.7%)
   ├─ 标准库缺口: 15条 (71.4%)
   ├─ 设计排除: 5条 (23.8%)
   └─ 词库缺口: 1条 (4.8%)
```

#### 改善后（预期）
```
总计: 31条CT项目
├─ 已匹配: 19条 (61.3%) ✅ 新增
├─ ambiguous: 4条 (12.9%) ⬇️ 降60%
└─ none: 8条 (25.8%) ⬇️ 降62%
   ├─ 设计排除: 5条 (合规) ✅
   ├─ 真实缺口: 3条 (待Phase 4处理)
```

**关键指标**:
- **匹配率提升**: 0% → 61.3% （+19条）
- **Ambiguous率下降**: 32.3% → 12.9% （-60%）
- **None率下降**: 67.7% → 25.8% （-62%）
- **实际待解决**: 12条 → 7条（排除5条设计排除项）

### 5.3 投入产出比（ROI）

| 投入 | 产出 | ROI |
|------|------|-----|
| 6天开发量 | 解决19/31条（61.3%） | ⭐⭐⭐⭐⭐ |
| Phase 1（1天） | 解决6条（19.4%） | ⭐⭐⭐⭐⭐ |
| Phase 2（3天） | 解决12条（38.7%） | ⭐⭐⭐⭐ |
| Phase 3（2天） | 解决1条（3.2%） | ⭐⭐⭐ |

**建议**: 优先执行 Phase 1+2，ROI最高。

---

## 六、风险与注意事项

### 6.1 风险

1. **标准项编码冲突**: 新增标准项需确保编码唯一性
   - **缓解**: 使用 20000000000xxx 系列测试编码，上线前统一分配正式编码

2. **技术修饰语过度过滤**: 可能误删有意义的描述
   - **缓解**: 仅过滤括号内修饰语，保留主干信息

3. **回归影响**: 修改预处理可能影响已匹配项
   - **缓解**: 
     ```bash
     # 改进前全量回归测试
     poetry run pytest tests/engine/ -v
     poetry run python scripts/batch_match_regression.py
     ```

### 6.2 上线检查清单

- [ ] 单元测试通过（pytest tests/engine/）
- [ ] 回归测试通过（4555条数据重跑无退化）
- [ ] 标准项编码审核（无重复、符合规范）
- [ ] 数据库备份（生产环境操作前）
- [ ] 灰度发布（先10%流量，观察24小时）

---

## 七、后续建议

### 7.1 长期优化方向

1. **建立标准库缺口监控**
   - 每日统计 none(standard_lib_gap) 分布
   - Top10 高频缺口自动告警

2. **引入AI辅助标准项生成**
   - 使用LLM根据未匹配项自动生成标准项草稿
   - 专家审核后批量导入

3. **增强血管成像覆盖**
   - 系统性补充各部位血管成像（参考ACR Appropriateness Criteria）
   - 覆盖率目标: 95%+

### 7.2 数据质量改进

1. **源数据清洗**
   ```python
   # 识别模态错误的历史数据
   poetry run python scripts/audit_modality_consistency.py
   ```

2. **建立数据录入规范**
   - 禁止在检查名称中混入临床描述（如"化疗前基线"）
   - 模态字段必填校验

---

## 八、参考资料

### 代码位置
- 匹配引擎: `src/match_service/engine/match_engine_v2/orchestrator.py`
- 预处理服务: `src/match_service/engine/match_engine_v2/preprocess_service.py`
- 分析脚本: `scripts/analyze_ct_mr_unmatched.py`

### 数据库表
- 标准项: `standard_check_items`
- 未匹配注册: `unmatched_registry`
- 医学词典: `medical_dict`
- 消歧规则: `ambiguity_rules`

### 测试命令
```bash
# 运行CT未匹配分析
poetry run python scripts/analyze_ct_mr_unmatched.py

# 单元测试
poetry run pytest tests/engine/test_match_engine_v2.py -v -k CT

# 全量回归测试
poetry run python scripts/batch_match_regression.py --modality CT
```

---

**报告生成时间**: 2024年  
**分析数据范围**: 4555条检查项目，CT模态31个distinct未匹配项  
**下一步行动**: 执行Phase 1快速修复，预期2天内完成

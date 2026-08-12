# 修复原则与方案（正式版）

## 核心原则 ⚠️ 必须严格遵守

### ✅ 允许的操作
1. **增加字典**（medical_dict表）- 同义词、别名
2. **增加同义词规则** - 帮助识别
3. **增加映射规则**（phrase_map表）- 短语映射
4. **优化算法** - 更智能地组合现有标准项

### ❌ 严格禁止的操作
1. **修改标准项目**（standard_check_items表）
2. **编造新的标准项目** - 即使为了提高匹配率
3. **创造不存在的检查项目**

### 🎯 匹配原则
- **只能从现有标准库中找**
- 可以是**多部位组合**（如：胸部 + 腹部）
- 可以是**不同扫描方式组合**（如：平扫 + 增强）
- 可以是**多个项目组合**（如：基础扫描 + 后处理）

---

## 重新审视三个问题

### 问题1：后处理缺基础扫描 ✅ 可以修复

#### 案例
```
输入: CT胸部腹部(多平面重组MPR)
当前输出: [CT三维重建]
期望输出: [CT胸部(平扫), CT腹部(平扫), CT三维重建]
```

#### 修复方式：算法优化
**原理**：
- `CT胸部(平扫)` ✅ 标准库中存在
- `CT腹部(平扫)` ✅ 标准库中存在（或全腹部）
- `CT三维重建` ✅ 标准库中存在
- **不创造新标准，只是智能组合现有标准**

**实施**：
修改`standard_lookup_service.py`的`lookup_standard`方法：
1. 检测返回结果中是否有后处理项（三维重建、MPR、VR）
2. 如果有，从原始输入提取部位信息
3. 查询标准库，找到对应的基础扫描项
4. 组合返回：[基础扫描项...] + [后处理项]

**关键验证点**：
- ✅ 所有返回的标准项都必须在standard_check_items表中存在
- ✅ 不能创造任何新项目
- ✅ 如果找不到某个部位的基础扫描，只返回后处理项（不强行编造）

---

### 问题2：多部位"及"不完整 ✅ 可以修复

#### 案例
```
输入: MR脑部及脊髓（平扫+增强）
当前输出: [MR颅脑(平扫+增强)]
期望输出: [MR颅脑(平扫+增强), MR脊髓(平扫+增强)]
```

#### 修复方式：phrase_map + 算法优化

**方案A：phrase_map映射（立即）**
```sql
INSERT INTO phrase_map (raw_phrase, standard_phrase, modality) VALUES
  ('脑部及脊髓', '颅脑,脊髓', 'MR'),
  ('脑+脊髓', '颅脑,脊髓', 'MR');
```

**原理**：
- 告诉系统"脑部及脊髓"应该识别为"颅脑"和"脊髓"两个部位
- 不创造新标准，只是映射到现有的部位词汇
- 后续查表会分别找`MR颅脑`和`MR脊髓`的标准项

**验证**：
```bash
# 添加映射后验证
查询标准库: MR颅脑(平扫+增强) ✅ 存在
查询标准库: MR脊髓(平扫+增强) ✅ 需要验证是否存在
```

**方案B：算法优化（中期）**
修改`split_record`方法，识别"及"连接词并拆分

---

### 问题3：标准库缺口 ❌ 不应"修复"

#### 案例
```
输入: MR上腔静脉血管成像
标准库: ❌ 不存在
```

#### 正确处理：保持匹配失败
- **不能**编造`MR上腔静脉血管成像`这个标准项
- **不能**为了提高匹配率而创造不存在的检查
- **应该**记录为真实的标准库缺口
- **只有**确认这是真实的国家标准/医院标准时，才能在Phase 3补充

#### 可选的变通方案
如果有相近的标准项，可以通过phrase_map映射：
```sql
-- 仅当确认"上腔静脉"在医学上可以泛化到"腔静脉"时
INSERT INTO phrase_map VALUES ('上腔静脉', '腔静脉', 'MR');
```

**但必须医学上合理！不能为了匹配率而乱映射。**

---

## 修复实施计划（修正版）

### 第1步：验证标准库（30分钟）

在修复前，必须验证所有涉及的标准项是否存在：

```sql
-- 问题1：验证基础扫描项是否存在
SELECT item_name FROM standard_check_items 
WHERE modality='CT' AND item_name LIKE '%胸部%平扫%';

SELECT item_name FROM standard_check_items 
WHERE modality='CT' AND item_name LIKE '%腹部%平扫%';

-- 问题2：验证脊髓项是否存在
SELECT item_name FROM standard_check_items 
WHERE modality='MR' AND item_name LIKE '%脊髓%';
```

**如果某个标准项不存在，不能修复该项！**

---

### 第2步：问题2快速修复（10分钟）

添加phrase_map映射（仅针对已验证存在的标准项）：

```sql
-- 仅当验证MR脊髓项存在后才添加
INSERT INTO phrase_map (raw_phrase, standard_phrase, body_part, modality, created_by) 
VALUES
  ('脑部及脊髓', '颅脑,脊髓', '', 'MR', 'manual_fix_2024'),
  ('脑+脊髓', '颅脑,脊髓', '', 'MR', 'manual_fix_2024');
```

---

### 第3步：问题1算法修复（2-3小时）

修改`standard_lookup_service.py`：

```python
def lookup_standard(self, node, modality, version):
    # ... 现有逻辑 ...
    
    # 新增：后处理项补充基础扫描
    if self._has_postprocessing(candidates):
        base_scans = self._find_base_scans(node, modality, version)
        # 关键：只返回标准库中存在的项
        candidates = base_scans + candidates
    
    return candidates

def _find_base_scans(self, node, modality, version):
    """查找基础扫描项 - 仅返回标准库中存在的项"""
    base_scans = []
    
    # 从node中提取部位
    body_parts = self._extract_body_parts(node)
    scan_method = self._extract_scan_method(node)
    
    for part in body_parts:
        # 查询标准库（不创造）
        query = f"{part}({scan_method})"
        result = self._query_standard_items(query, modality, version)
        
        if result:  # 仅当标准库中存在时才添加
            base_scans.extend(result)
    
    return base_scans
```

**关键原则**：
- ✅ 所有返回项必须从`standard_check_items`表查询得到
- ✅ 查不到就不返回（不编造）
- ✅ 记录日志，标记哪些部位找不到基础扫描

---

### 第4步：验证修复效果（30分钟）

```python
# 验证脚本
def verify_all_standards_exist(result):
    """验证返回的所有标准项都在数据库中存在"""
    for item in result['standards']:
        exists = query_db("SELECT 1 FROM standard_check_items WHERE item_name = ?", item)
        if not exists:
            raise ValueError(f"返回了不存在的标准项: {item}")
    return True
```

---

## 预期效果（修正版）

### 问题1修复后
```
受影响: 4项（8条记录）

但实际修复数取决于：
- 标准库中有多少对应的基础扫描项
- 可能只有部分项能补全
```

### 问题2修复后
```
受影响: 3项（6条记录）

前提：MR脊髓相关标准项必须存在
如果不存在，不能修复
```

### 问题3
```
标准库缺口 - 不修复
保持匹配失败状态
记录为Phase 3调研目标
```

---

## 质量保证检查清单

每次修复后必须检查：

- [ ] 所有返回的标准项在standard_check_items表中存在
- [ ] 没有创造任何新的标准项名称
- [ ] phrase_map映射的目标词都是真实的医学术语
- [ ] 回归测试全部通过
- [ ] 手工验证10个样本，确认返回项都正确

---

## 下一步

**我将严格按照以上原则进行修复：**

1. ✅ 先验证标准库（确认所需的标准项存在）
2. ✅ 只修复可验证的项目
3. ✅ 绝不创造新标准
4. ✅ 每步都验证

**是否开始？我将先执行"第1步：验证标准库"。**

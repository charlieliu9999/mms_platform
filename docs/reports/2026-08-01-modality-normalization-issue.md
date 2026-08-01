# MMS 模态归一化缺失问题分析报告

**生成时间**: 2026-08-01 19:20  
**问题严重性**: 🔴 **严重** - 导致 32% 的 ACR 项目无法匹配  
**影响范围**: MRI(225条), XR(191条), NM(137条) = **553条（25.5%）**

---

## 🔍 问题发现

通过对比 **原系统（acrac_web_mgmt）** 和 **新系统（mms_platform）** 的实现，发现：

### ✅ 原系统有模态归一化

**文件**: `acrac_backend/app/services/standardization/modality_extractor.py`

```python
MODALITY_NORMALIZE = {
    'MR': 'MRI',
    'MRI': 'MRI',
}

def normalize_modality(self, modality: str) -> str:
    """规范化模态名称（用于数据库查询）"""
    return self.MODALITY_NORMALIZE.get(modality, modality)
```

### ❌ 新系统缺少模态归一化

**查找结果**: MMS 项目中没有类似的模态归一化逻辑
- 查找路径: `src/match_service/core/`, `src/match_service/engine/`
- 结果: **无模态映射/归一化代码**

**仅有的映射**: `src/match_service/api/legacy_adapter.py`

```python
LEGACY_MODALITY_ALIASES = {
    'PET-CT': 'PET/CT',
    'PET-MR': 'PET/MR',
}
```

只处理了 PET-CT/PET-MR 的别名，**没有处理 MRI/XR 等常见模态**。

---

## 📊 标准库模态编码方式

### MMS 标准库（nlp_checkitem_standard 表）

| 数字代码 | 中文名称 | 英文缩写（实际使用） | 数据量 |
|---------|---------|------------------|--------|
| **"2"** | CT | CT | 7,589 |
| **"3"** | MR | **MR（非MRI）** | 6,326 |
| **"4"** | X线 | **DR/CR/XR** | 4,752 |
| **"9"** | DSA | DSA | 28 |

**关键发现**：
1. 标准库使用**数字字符串**作为 `modality_code`
2. `modality_name` 是**中文名称**
3. **没有存储英文缩写**（CT, MR, US等）

### ACR 数据使用的模态名称

| ACR模态 | 数量 | 标准库对应 | 匹配结果 |
|--------|------|-----------|---------|
| **MRI** | 225 | 应映射到 "3" (MR) | ❌ 0% |
| **XR** | 191 | 应映射到 "4" (X线) | ❌ 0% |
| **NM** | 137 | 无对应 | ❌ 0% |
| **MR** | 356 | "3" (MR) | ✅ 86.2% |
| **CT** | 494 | "2" (CT) | ✅ 90.7% |
| **US** | 603 | 未查到但能匹配 | ✅ 92.9% |

---

## 🎯 问题根源

### 1. 模态名称不一致

**问题**: ACR 使用学术标准名称（MRI），MMS 标准库使用简写（MR）

```
ACR数据:  MRI  →  匹配引擎查询  →  标准库查找 "MRI"  →  ❌ 不存在
标准库:   MR (代码"3")
```

**正确流程应该是**:
```
ACR数据:  MRI  →  归一化为 MR  →  匹配引擎查询  →  标准库查找 "3"  →  ✅ 找到 6326条
```

### 2. 匹配引擎未实现模态映射

**MatchDispatcher** 直接使用传入的 `modality` 参数：

```python
async def match(self, text: str, modality: str, version: str = "V3.8.2") -> dict:
    # 直接使用 modality，没有归一化
    # 查询时使用原始值
```

**应该在匹配前增加**:
```python
async def match(self, text: str, modality: str, version: str = "V3.8.2") -> dict:
    # 模态归一化
    normalized_modality = self._normalize_modality(modality)
    # 使用归一化后的值查询
```

### 3. 标准库数据模型的复杂性

MMS 标准库的模态字段：
- `modality_id`: integer（数字ID）
- `modality_code`: varchar（数字字符串 "2", "3", "4"）
- `modality_name`: varchar（中文名称 "CT", "MR", "X线"）

**查询时的困惑**:
- 用户传入 `MRI`
- 标准库中没有 `MRI` 代码
- 标准库只有 `"3"` 代表 `MR`

---

## 💡 解决方案

### 方案1：在匹配引擎中增加模态归一化（推荐）

**优点**:
- 一次性修复所有调用路径
- 对调用方透明
- 集中管理映射规则

**实施位置**: `src/match_service/core/dispatcher.py`

```python
class MatchDispatcher:
    # 模态归一化映射表
    MODALITY_NORMALIZATION = {
        # MRI 系列
        'MRI': 'MR',
        'MR': 'MR',
        
        # X线系列
        'XR': 'DR',
        'DR': 'DR',
        'CR': 'DR',
        'X线': 'DR',
        '放射': 'DR',
        
        # CT系列
        'CT': 'CT',
        'HRCT': 'CT',
        'CTA': 'CT',
        
        # 超声系列
        'US': 'US',
        'ULTRASOUND': 'US',
        '超声': 'US',
        
        # 核医学系列（需要确认标准库是否支持）
        'NM': 'NM',
        'SPECT': 'NM',
        'PET': 'PET',
        'PET/CT': 'PET/CT',
        'PET-CT': 'PET/CT',
        'PET/MR': 'PET/MR',
        'PET-MR': 'PET/MR',
        
        # 介入系列
        'ANGIO': 'DSA',
        'DSA': 'DSA',
        
        # 其他
        'RF': 'RF',
        'FL': 'RF',
        'MG': 'MG',
        'OCT': 'OCT',
    }
    
    def _normalize_modality(self, modality: str) -> str:
        """模态归一化"""
        if not modality:
            return modality
        
        # 转大写
        modality_upper = modality.upper().strip()
        
        # 查找映射
        return self.MODALITY_NORMALIZATION.get(modality_upper, modality_upper)
    
    async def match(self, text: str, modality: str, version: str = "V3.8.2") -> dict:
        """单条匹配：L1 → L2 → (L3 async)"""
        
        # ✅ 模态归一化
        normalized_modality = self._normalize_modality(modality)
        
        # 使用归一化后的模态进行匹配
        # ... 后续匹配逻辑
```

### 方案2：在标准库层面增加模态别名表（长期方案）

创建模态别名表：

```sql
CREATE TABLE modality_aliases (
    id SERIAL PRIMARY KEY,
    alias VARCHAR(20) NOT NULL,          -- 别名（MRI, XR等）
    canonical_code VARCHAR(10) NOT NULL, -- 标准代码（"3", "4"等）
    canonical_name VARCHAR(50),          -- 标准名称（MR, X线）
    UNIQUE(alias)
);

INSERT INTO modality_aliases (alias, canonical_code, canonical_name) VALUES
('MRI', '3', 'MR'),
('MR', '3', 'MR'),
('XR', '4', 'X线'),
('DR', '4', 'X线'),
('CR', '4', 'X线'),
('CT', '2', 'CT'),
-- 更多映射...
```

**优点**:
- 可通过 SQL 查询实现归一化
- 支持动态添加别名
- 易于维护

**缺点**:
- 需要修改数据库结构
- 增加查询复杂度

---

## 📈 预期效果

### 修复前（当前）

| 模态 | 数量 | 匹配率 |
|------|------|--------|
| MRI | 225 | **0%** ❌ |
| XR | 191 | **0%** ❌ |
| MR | 356 | 86.2% ✅ |
| CT | 494 | 90.7% ✅ |
| US | 603 | 92.9% ✅ |
| **总计** | **2167** | **61.51%** |

### 修复后（预期）

| 模态 | 数量 | 预期匹配率 | 备注 |
|------|------|-----------|------|
| MRI → MR | 225 | **86.2%** ✅ | 与MR同等 |
| XR → DR | 191 | **70-80%** ✅ | 体位词可能需补充 |
| MR | 356 | 86.2% ✅ | 保持不变 |
| CT | 494 | 90.7% ✅ | 保持不变 |
| US | 603 | 92.9% ✅ | 保持不变 |
| **总计** | **2167** | **~80%** 🎯 | **+18.5%** |

**核心提升**:
- MRI 修复：+10.4%
- XR 修复：+7-8%
- **总提升**: ~18.5%，从 61.5% → **80%**

---

## 🚀 实施步骤

### Step 1: 增加模态归一化（1小时）

1. 编辑 `src/match_service/core/dispatcher.py`
2. 添加 `MODALITY_NORMALIZATION` 字典
3. 添加 `_normalize_modality()` 方法
4. 在 `match()` 方法开头调用归一化

### Step 2: 单元测试（30分钟）

```python
def test_modality_normalization():
    dispatcher = MatchDispatcher(session, engine_holder)
    
    assert dispatcher._normalize_modality('MRI') == 'MR'
    assert dispatcher._normalize_modality('mri') == 'MR'
    assert dispatcher._normalize_modality('XR') == 'DR'
    assert dispatcher._normalize_modality('CT') == 'CT'
    assert dispatcher._normalize_modality(None) == None
```

### Step 3: 重新运行 ACR 评测（5分钟）

```bash
cd ~/git_project_vscode/09_medical/mms_platform

# 重置任务 #7
poetry run python << 'EOF'
# ... 重置代码
EOF

# 重新执行匹配
poetry run python scripts/run_acr_matching.py
```

### Step 4: 验证效果（10分钟）

查看修复后的匹配率：
- MRI 项目匹配率应从 0% → ~86%
- XR 项目匹配率应从 0% → ~70-80%
- 总体匹配率应从 61.5% → ~80%

### Step 5: 处理核医学（NM）数据（后续）

NM/SPECT/PET 的 137 条可能需要：
1. 确认标准库是否有核医学数据
2. 如果有，添加映射
3. 如果没有，需要导入核医学标准库

---

## 📝 总结

### 原因

1. **原系统有模态归一化**，新系统迁移时**未同步此功能**
2. 标准库使用数字代码+中文名称，ACR数据使用英文缩写
3. 匹配引擎直接使用传入的模态值，无归一化处理

### 影响

- 导致 25.5% 的 ACR 项目无法匹配（MRI+XR = 416条）
- 整体匹配率降至 61.51%（应该 >80%）

### 解决方案

✅ **推荐**: 在 MatchDispatcher 中增加模态归一化  
⏱️ **耗时**: 1-2 小时（编码+测试）  
📈 **提升**: +18.5%（61.5% → 80%）

### 下一步

1. **立即**: 实施模态归一化
2. **短期**: 补充体位词汇（提升XR匹配率）
3. **中期**: 确认核医学数据支持情况

---

**文档版本**: v1.0  
**责任人**: MMS 匹配引擎团队  
**优先级**: 🔴 P0 - 严重缺陷

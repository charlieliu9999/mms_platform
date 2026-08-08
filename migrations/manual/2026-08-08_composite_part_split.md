# 复合部位拆分优化方案

## 问题
用户查询"CT全脊柱(增强)"无法匹配，但标准库中有：
- CT颈椎(增强)
- CT胸椎(增强)
- CT腰椎(增强)
- CT骶尾椎(增强)

## 解决方案

### 方案A: 预处理阶段拆分（推荐）
在预处理阶段识别复合部位，生成多个子查询

```python
# src/match_service/engine/match_engine_v2/preprocess_service.py

COMPOSITE_PARTS = {
    '全脊柱': ['颈椎', '胸椎', '腰椎', '骶尾椎'],
    '脊柱': ['颈椎', '胸椎', '腰椎', '骶尾椎'],
    '头颈部': ['头部', '颈部'],
    '胸腹部': ['胸部', '腹部'],
    '全消化道': ['食管', '胃', '小肠', '结肠'],
}

def split_composite_parts(self, text: str, modality: str) -> List[str]:
    """拆分复合部位为多个子查询"""
    for composite, parts in COMPOSITE_PARTS.items():
        if composite in text:
            # 生成多个子查询
            return [text.replace(composite, part) for part in parts]
    return [text]
```

**优点**:
- 不需要修改标准库
- 返回多个匹配结果
- 用户可以选择需要的部分

**缺点**:
- 需要修改API返回格式

---

### 方案B: 添加复合部位到标准库
直接在standard_check_items表中添加"全脊柱"等复合检查

```sql
-- 添加CT全脊柱标准项
INSERT INTO standard_check_items (
    item_code, item_name, modality, body_part_l1, body_part_l2, 
    body_part_l3, scan_method, version, is_active
) VALUES
('CT_FULL_SPINE_001', '* CT全脊柱(平扫)', 'CT', '脊柱', '全脊柱', '全脊柱', '平扫', 'V3.8.2', true),
('CT_FULL_SPINE_002', '* CT全脊柱(增强)', 'CT', '脊柱', '全脊柱', '全脊柱', '增强', 'V3.8.2', true),
('CT_FULL_SPINE_003', '* CT全脊柱(平扫+增强)', 'CT', '脊柱', '全脊柱', '全脊柱', '平扫+增强', 'V3.8.2', true);

-- MR全脊柱
INSERT INTO standard_check_items (
    item_code, item_name, modality, body_part_l1, body_part_l2, 
    body_part_l3, scan_method, version, is_active
) VALUES
('MR_FULL_SPINE_001', '* MR全脊柱(平扫)', 'MR', '脊柱', '全脊柱', '全脊柱', '平扫', 'V3.8.2', true),
('MR_FULL_SPINE_002', '* MR全脊柱(增强)', 'MR', '脊柱', '全脊柱', '全脊柱', '增强', 'V3.8.2', true);
```

**优点**:
- 实现简单
- 不需要修改算法
- 符合临床实际（全脊柱确实是一个完整检查）

**缺点**:
- 需要补充大量复合检查标准项

---

## 推荐方案

**混合方案**: 
1. 对**常用复合检查**添加标准项（全脊柱、头颈部等）
2. 对**罕见复合检查**实现算法拆分

**预估效果**: +14项匹配

# 标准数据页面显示和样式问题修复报告

**日期**: 2026-07-31  
**问题**: 标准数据页面无法显示 + 浅色模式下大量黑色背景  
**状态**: ✅ 已解决

---

## 问题诊断

### 问题1: 标准数据页面返回 Internal Server Error

**根本原因**: API 代码使用的数据库字段名与实际表结构不匹配

数据库实际字段 (`nlp_checkitem_standard` 表):
```sql
- checkitem_code      (不是 item_code)
- checkitem_name      (不是 item_name)  
- modality_name       (不是 modality)
- scope_name          (不是 body_part_l1)
- three_level_name    (不是 body_part_l2)
- scan_name           (不是 scan_method)
- post_processing_name (不是 post_processing)
- 无 created_at 字段
```

**错误日志**:
```
sqlalchemy.exc.ProgrammingError: column "item_code" does not exist
sqlalchemy.exc.ProgrammingError: column "created_at" does not exist
```

### 问题2: 浅色模式下大量黑色背景

**根本原因**: Ant Design 组件默认样式未被完全覆盖

缺失的样式覆盖:
- 表格行背景
- 输入框背景
- 下拉选择器
- 分页器
- 按钮
- 模态框/抽屉内容区

---

## 解决方案

### 1. 后端 API 修复 (`src/match_service/api/admin.py`)

#### 修复查询条件映射
```python
# 前端字段名 → 数据库字段名映射
if modality:
    where_clauses.append("modality_name = :modality")
if body_part_l1:
    where_clauses.append("scope_name = :body_part_l1")
if body_part_l2:
    where_clauses.append("three_level_name = :body_part_l2")
if search:
    where_clauses.append("(checkitem_name ILIKE :search OR checkitem_code ILIKE :search)")
```

#### 修复 SQL 查询字段
```python
data_sql = """
    SELECT id, checkitem_code, checkitem_name, modality_name, 
           scope_name, three_level_name, scan_name, 
           post_processing_name, version
    FROM nlp_checkitem_standard
    WHERE {where_sql}
    ORDER BY id
    LIMIT :limit OFFSET :offset
"""
```

#### 添加字段映射层
```python
# 将数据库字段映射为前端期望的格式
for row in result:
    row_dict = dict(row._mapping)
    items.append({
        "id": row_dict.get("id"),
        "item_code": row_dict.get("checkitem_code"),
        "item_name": row_dict.get("checkitem_name"),
        "modality": row_dict.get("modality_name"),
        "body_part_l1": row_dict.get("scope_name"),
        "body_part_l2": row_dict.get("three_level_name"),
        "body_part_l3": "",
        "scan_method": row_dict.get("scan_name"),
        "post_processing": row_dict.get("post_processing_name"),
        "version": row_dict.get("version"),
    })
```

#### 修复统计 API
```python
# 更新模态统计查询
modality_sql = """
    SELECT modality_name as modality, COUNT(*) as count
    FROM nlp_checkitem_standard WHERE {where_sql}
    GROUP BY modality_name ORDER BY count DESC
"""

# 更新部位统计查询
body_sql = """
    SELECT scope_name as body_part_l1, COUNT(*) as count
    FROM nlp_checkitem_standard WHERE {where_sql} AND scope_name IS NOT NULL
    GROUP BY scope_name ORDER BY count DESC LIMIT 10
"""
```

### 2. 前端样式修复 (`frontend/src/index.css`)

#### 扩展 Ant Design 组件样式覆盖

```css
/* 表格样式 */
.ant-table {
  background-color: var(--bg-card) !important;
  color: var(--text-primary) !important;
}

.ant-table-thead > tr > th {
  background-color: var(--bg-subtle) !important;
  color: var(--text-primary) !important;
}

.ant-table-tbody > tr > td {
  background-color: var(--bg-card) !important;
  color: var(--text-primary) !important;
}

.ant-table-tbody > tr:hover > td {
  background-color: var(--bg-subtle) !important;
}

/* 输入框样式 */
.ant-input,
.ant-input-affix-wrapper,
.ant-select-selector {
  background-color: var(--bg-card) !important;
  border-color: var(--border-theme) !important;
  color: var(--text-primary) !important;
}

/* 下拉框样式 */
.ant-select-dropdown {
  background-color: var(--bg-card) !important;
}

.ant-select-item-option-selected {
  background-color: var(--bg-subtle) !important;
  color: var(--brand-color) !important;
}

/* 分页器样式 */
.ant-pagination-item {
  background-color: var(--bg-card) !important;
  border-color: var(--border-theme) !important;
}

.ant-pagination-item-active {
  background-color: var(--brand-color) !important;
}

/* 按钮样式 */
.ant-btn-default {
  background-color: var(--bg-card) !important;
  color: var(--text-primary) !important;
}

/* 模态框/抽屉内容区 */
.ant-drawer-body,
.ant-modal-body {
  background-color: var(--bg-card) !important;
  color: var(--text-primary) !important;
}
```

---

## 验证结果

### API 测试

✅ **标准项目列表API**
```bash
curl 'http://localhost:9100/api/admin/standard-items?page=1&page_size=2'
```
返回正确数据，包含18,695条标准项目

✅ **统计API**
```bash
curl 'http://localhost:9100/api/admin/standard-items/stats'
```
- 总项目数: 18,695
- 模态数量: 4 (CT: 7,589, MR: 6,326, X线: 4,752, DSA: 28)
- 部位数量: 2

✅ **搜索功能**
```bash
curl 'http://localhost:9100/api/admin/standard-items?search=颅脑'
```
搜索功能正常工作

✅ **模态筛选**
```bash
curl 'http://localhost:9100/api/admin/standard-items?modality=CT'
```
CT模态筛选返回 7,589 条

### 前端验证

✅ 标准数据页面正常显示  
✅ 浅色模式无黑色背景  
✅ 表格、输入框、按钮样式统一  
✅ 暗色模式样式正常  

---

## 技术要点

### 1. 数据库字段命名不一致处理

**策略**: 在 API 层添加映射层，而不是修改数据库表结构

**优点**:
- 不影响现有引擎代码（`data_loader.py` 使用的字段名）
- 前端接口保持稳定
- 易于维护和理解

### 2. CSS 变量驱动的主题系统

**架构**:
```
:root → 定义浅色变量
.dark → 定义暗色变量
组件样式 → 使用 var(--变量名)
```

**优点**:
- 单一真相来源
- 一次修改，全局生效
- 易于扩展新组件

### 3. Ant Design 样式覆盖策略

**要点**:
- 使用 `!important` 确保优先级
- 覆盖所有状态 (normal, hover, active, selected)
- 包含内容区 (card-body, modal-body, drawer-body)

---

## 相关文件

### 修改的文件
- `src/match_service/api/admin.py` - API 字段映射修复
- `frontend/src/index.css` - 全局样式扩展

### 未修改的文件
- `src/match_service/engine/match_engine_v2/data_loader.py` - 保持原有字段名
- `frontend/src/pages/StandardItems.tsx` - 前端代码无需修改
- 数据库表结构 - 保持不变

---

## 经验教训

1. **API 开发前先确认数据库表结构**
   - 使用 `\d+ table_name` 查看实际字段
   - 不要假设字段名

2. **样式覆盖要全面**
   - 不仅覆盖容器，也要覆盖内容区
   - 测试所有交互状态 (hover, active, focus)
   - 测试浅色和暗色两种模式

3. **使用映射层处理命名不一致**
   - 避免大范围重构
   - 保持向后兼容
   - 文档化映射关系

---

## 后续优化建议

### 短期 (可选)
- [ ] 添加字段映射的单元测试
- [ ] 创建样式指南文档
- [ ] 添加前端 Storybook 展示组件样式

### 长期 (可选)
- [ ] 统一数据库表字段命名规范
- [ ] 创建数据库迁移脚本重命名字段
- [ ] 使用 TypeScript 类型系统强制字段映射

---

## 提交信息

**Commit**: cff4da9  
**Message**: fix: 修复标准数据页面显示和浅色模式样式问题

**测试验证**:
- ✓ API 返回正确数据 (18,695条标准项目)
- ✓ 统计API正常工作
- ✓ 前端服务正常运行
- ✓ 浅色模式样式正确
- ✓ 暗色模式样式正确

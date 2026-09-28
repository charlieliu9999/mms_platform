# 技术细节管理功能实现方案

## 概述

技术细节管理功能用于管理标准项目的技术参数，包括扫描方法、临床应用等信息。数据最终展示在官网的标准查询页面。

## 数据流向

```
技术细节候选生成 → 人工审核 → 发布到标准库 → 官网展示
     ↓                ↓              ↓              ↓
candidate_table   review_table   standard_table   open_api
```

## 数据库表结构

### 1. 技术细节候选表（technical_detail_candidates）
存储 AI 生成或人工创建的技术细节候选。

**关键字段：**
- `id`: 候选 ID
- `target_item_id`: 目标标准项目 ID
- `target_item_code`: 目标项目编码
- `candidate_json`: 候选字段 JSON（包含所有技术字段）
- `status`: 状态（pending_review/approved/rejected/applied/superseded）
- `confidence`: AI 生成置信度
- `conflicts_json`: 字段冲突 JSON
- `source_item_ids_json`: 来源项目 ID 列表

### 2. 技术细节发布表（technical_detail_publications）
记录每次发布操作的历史。

**关键字段：**
- `id`: 发布 ID
- `candidate_id`: 候选 ID（可为空）
- `target_item_code`: 目标项目编码
- `before_json`: 发布前的值
- `after_json`: 发布后的值
- `status`: 状态（published/rolled_back）

### 3. 技术细节溯源表（technical_detail_provenance）
记录每个字段的数据来源。

**关键字段：**
- `source_kind`: 来源类型（historical_import/rule_fusion/evaluation_import）
- `source_system`: 来源系统
- `source_table`: 来源表
- `field_names`: 字段名称列表

### 4. 标准项目表（standard_check_items）
最终存储已发布的技术细节。

**技术参数字段：**
- `body_position`: 扫描体位
- `scan_scope`: 扫描范围  
- `contrast_agent`: 对比剂方案
- `image_region`: 成像区域
- `image_focus`: 成像关注点
- `scan_method_detail`: 扫描方法详情
- `scan_param`: 扫描参数
- `coil`: 线圈（MR）
- `base_sequence`: 基础序列（MR）
- `compose_sequence`: 组合序列（MR）

**临床应用字段：**
- `clinical_indication`: 临床适应症
- `clinical_significance`: 临床意义
- `organs`: 器官
- `anatomical_structure`: 解剖结构
- `technical_notes`: 技术备注
- `image_grade`: 图像等级
- `image_score`: 图像评分

## 后端 API

### 管理后台 API（/api/admin）

#### 1. 技术细节库（正式标准数据）

```python
# 统计
GET /api/admin/technical-detail-library/stats
返回：{ total, active_total, ct_total, mr_total, sources }

# 列表查询
GET /api/admin/technical-detail-library
参数：modality, source_kind, search, is_active, limit, offset
返回：{ total, items }

# 详情
GET /api/admin/technical-detail-library/{item_id}
返回：完整标准项目（包含所有技术字段 + 溯源信息）
```

#### 2. 技术细节候选管理

```python
# 统计
GET /api/admin/technical-detail-candidates/stats
返回：{ total, by_status, by_method, conflict_count }

# 列表查询
GET /api/admin/technical-detail-candidates
参数：status, modality, search, has_conflicts, limit, offset
返回：{ total, items }

# 详情
GET /api/admin/technical-detail-candidates/{id}
返回：完整候选信息（包含字段来源、冲突、修订历史、发布记录）

# 生成候选
POST /api/admin/technical-detail-candidates/generate
请求：{ version, modality, item_code?, limit?, persist }
返回：生成结果

# 编辑候选
PUT /api/admin/technical-detail-candidates/{id}
请求：{ candidate_fields, editor, notes? }
返回：更新后的候选

# 审核
POST /api/admin/technical-detail-candidates/{id}/review
请求：{ decision: 'approved'|'rejected', reviewer, notes? }
返回：{ id, status }

# 发布
POST /api/admin/technical-detail-candidates/{id}/publish
请求：{ publisher?, notes? }
返回：{ publication_id, target_item_code, published_fields, status }

# 批量审核发布
POST /api/admin/technical-detail-bulk/review-and-publish
请求：{ candidate_ids?, select_all?, filters, operator, notes? }
返回：{ requested_count, published_count, skipped_count, failed }

# 回滚
POST /api/admin/technical-detail-publications/{id}/rollback
请求：{ operator, reason }
返回：{ publication_id, target_item_code, status }
```

### 开放门户 API（/api/open）

#### 官网标准查询

```python
# 标准项目列表
GET /api/open/standards/items
参数：modality, body_part, scan_method, version, search, limit, offset
返回：{ total, items }

# 标准项目详情（包含技术参数）
GET /api/open/standards/items/{item_id}
返回：完整标准项目（包含所有技术字段）
```

## 前端实现方案

### 1. 技术细节库页面（TechnicalDetailLibrary）

**功能：**
- 展示已发布到标准库的技术细节
- 按模态、来源、状态筛选
- 查看详情（包含数据溯源）

**组件结构：**
```tsx
<TechnicalDetailLibrary>
  <StatisticsCards />        {/* 统计卡片 */}
  <FilterBar />              {/* 筛选器 */}
  <DataTable />              {/* 数据表格 */}
  <DetailDrawer />           {/* 详情抽屉 */}
</TechnicalDetailLibrary>
```

**关键字段展示：**
- 基本信息：项目编码、名称、模态、版本
- 技术参数：扫描方法、对比剂、体位、范围
- 临床应用：适应症、临床意义
- 数据来源：溯源标签（历史导入/规则融合/评估导入）

### 2. 候选管理页面（TechnicalDetailCandidates）

**功能：**
- 展示待审核的技术细节候选
- 按状态、模态筛选
- 查看详情、编辑、审核、发布

**组件结构：**
```tsx
<TechnicalDetailCandidates>
  <StatisticsCards />        {/* 统计卡片 */}
  <FilterBar />              {/* 筛选器 */}
  <DataTable />              {/* 候选列表 */}
  <DetailModal />            {/* 详情弹窗 */}
  <EditModal />              {/* 编辑弹窗 */}
  <ReviewModal />            {/* 审核弹窗 */}
</TechnicalDetailCandidates>
```

**状态流转：**
```
pending_review → approved → applied（已发布）
              ↘ rejected（已拒绝）
```

### 3. 官网展示页面（参考：https://bzh.rimagcloud.com/standards）

**功能：**
- 标准项目列表（支持筛选、搜索）
- 点击项目名称右侧弹出抽屉显示技术参数

**组件结构：**
```tsx
<StandardsPage>
  <FilterSidebar />          {/* 左侧筛选：部位导航 */}
  <FilterBar />              {/* 顶部筛选：模态、扫描方法等 */}
  <ItemsTable />             {/* 标准项目列表 */}
  <TechnicalDetailDrawer />  {/* 右侧抽屉：技术参数 */}
</StandardsPage>
```

**技术参数抽屉内容：**
- **技术参数部分**
  - 扫描体位
  - 扫描范围 + 成像区域
  - 成像关注点
  - 对比剂方案
  
- **临床应用部分**
  - 解剖结构
  - 临床意义

## 数据类型定义

```typescript
// 技术细节库项目
export interface TechnicalDetailLibraryItem {
  id: number;
  item_code: string;
  item_name: string;
  modality: string;
  version: string;
  // 技术参数
  scan_method?: string;
  scan_method_detail?: string;
  post_processing?: string;
  body_position?: string;
  scan_scope?: string;
  contrast_agent?: string;
  image_region?: string;
  image_focus?: string;
  scan_param?: string;
  coil?: string;
  base_sequence?: string;
  compose_sequence?: string;
  // 临床应用
  clinical_indication?: string;
  clinical_significance?: string;
  organs?: string;
  anatomical_structure?: string;
  technical_notes?: string;
  image_grade?: string;
  image_score?: number;
  // 元数据
  is_active: boolean;
  sources: TechnicalDetailProvenance[];
}

// 技术细节候选
export interface TechnicalDetailCandidateSummary {
  id: number;
  target_item_id: number;
  target_item_code: string;
  target_item_name: string;
  modality: string;
  generation_method: string;
  confidence: number;
  conflicts_json: TechnicalDetailConflict[];
  status: TechnicalDetailStatus;
  created_at: string;
}

// 技术细节候选完整信息
export interface TechnicalDetailCandidate extends TechnicalDetailCandidateSummary {
  candidate_json: Record<string, string>;
  field_sources_json: Record<string, TechnicalDetailSourceRef[]>;
  revisions: TechnicalDetailRevision[];
  publications: TechnicalDetailPublication[];
}

// 状态类型
export type TechnicalDetailStatus =
  | 'pending_review'   // 待审核
  | 'approved'         // 已批准
  | 'rejected'         // 已拒绝
  | 'applied'          // 已应用
  | 'superseded';      // 已过期
```

## 工作流程

### 1. 技术细节生成流程

```
1. 选择版本和模态 → 2. AI 生成候选 → 3. 检测冲突 → 4. 保存候选表
```

### 2. 审核发布流程

```
1. 查看候选列表 → 2. 查看详情（含来源） → 3. 编辑（可选） → 4. 审核（批准/拒绝） → 5. 发布到标准库
```

### 3. 回滚流程

```
1. 查看发布历史 → 2. 选择回滚记录 → 3. 填写原因 → 4. 恢复到发布前状态
```

## API 调用示例

### 管理后台

```typescript
// 获取技术细节库统计
const stats = await adminAPI.getTechnicalDetailLibraryStats();

// 查询技术细节库
const { items, total } = await adminAPI.getTechnicalDetailLibrary({
  modality: 'CT',
  is_active: true,
  limit: 20,
  offset: 0,
});

// 获取详情
const item = await adminAPI.getTechnicalDetailLibraryItem(123);

// 查询候选
const candidates = await adminAPI.getTechnicalDetailCandidates({
  status: 'pending_review',
  modality: 'MR',
});

// 审核候选
await adminAPI.reviewTechnicalDetailCandidate(456, {
  decision: 'approved',
  reviewer: '张三',
  notes: '数据准确',
});

// 发布候选
await adminAPI.publishTechnicalDetailCandidate(456, {
  publisher: '李四',
  notes: '已确认',
});
```

### 官网

```typescript
// 获取标准项目列表
const response = await fetch('/api/open/standards/items?modality=CT&limit=20');
const { items, total } = await response.json();

// 获取标准项目详情（含技术参数）
const detail = await fetch('/api/open/standards/items/123');
const item = await detail.json();

// 展示技术参数
console.log(item.scan_method_detail);      // 扫描方法详情
console.log(item.body_position);           // 扫描体位
console.log(item.contrast_agent);          // 对比剂方案
console.log(item.clinical_indication);     // 临床适应症
console.log(item.clinical_significance);   // 临床意义
```

## 关键实现要点

### 1. 数据完整性
- ✅ 数据库数据完整（287 条已发布 + 284 条候选 + 2,312 条溯源）
- ✅ 后端 API 完整可用
- ⚠️ 前端页面需要重建

### 2. 前端实现
- 使用 `adminAPI` 调用管理后台 API
- 使用 Ant Design 组件（Table, Drawer, Modal, Descriptions）
- 实现筛选、分页、详情查看功能

### 3. 官网展示
- 数据通过 `/api/open/standards/items/{item_id}` 获取
- 右侧抽屉展示技术参数和临床应用
- 分两个部分展示：技术参数 + 临床应用

## 当前状态

### ✅ 已完成
- 数据库表结构完整
- 后端 API 完整
- 数据完整性验证
- 类型定义完整

### ⚠️ 待完成
- 前端技术细节库页面（已创建基础版本）
- 前端候选管理页面（已创建基础版本）
- 候选编辑功能
- 批量操作功能
- 发布历史查看
- 回滚功能

## 下一步行动

1. **完善前端页面**：实现完整的 CRUD 功能
2. **测试 API**：验证所有接口正常工作
3. **数据验证**：确认技术参数字段完整性
4. **官网集成**：确认官网能正确展示技术参数

---
**文档更新时间**：2026-08-17 20:15
**状态**：✅ 数据完整，API 可用，前端需要完善

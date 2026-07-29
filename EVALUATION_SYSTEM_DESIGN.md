# MMS 评测与优化闭环系统设计

## 一、系统架构

### 1.1 后端结构

```
src/match_service/
├── evaluation/                    # 评测模块
│   ├── __init__.py
│   ├── runner.py                 # 评测执行器
│   ├── analyzer.py               # 结果分析器
│   ├── optimizer.py              # 优化建议生成器
│   └── models.py                 # 数据模型
│
├── api/
│   └── evaluation.py             # 评测 API 路由
│
└── models/
    └── evaluation.py             # 数据库表定义
```

### 1.2 前端结构

```
frontend/src/
├── pages/
│   └── Evaluation/
│       ├── Dashboard.tsx         # 评测总览仪表盘
│       ├── TestRunner.tsx        # 测试执行器
│       ├── FailureBrowser.tsx    # 失败案例浏览器
│       ├── CompareView.tsx       # 版本对比
│       └── OptimizerTool.tsx     # 优化工具
│
├── services/
│   └── evaluationService.ts      # API 调用
│
└── components/
    └── evaluation/
        ├── MetricsCard.tsx       # 指标卡片
        ├── FailureTable.tsx      # 失败案例表格
        ├── ConfidenceChart.tsx   # 置信度分布图
        └── SuggestionList.tsx    # 优化建议列表
```

---

## 二、数据库设计

### 2.1 评测任务表

```sql
CREATE TABLE eval_tasks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,              -- 任务名称
    description TEXT,                         -- 描述
    test_file_path VARCHAR(500),             -- 测试文件路径
    sample_size INTEGER,                      -- 样本数量
    modality VARCHAR(10),                     -- 模态过滤（NULL=全部）
    
    -- 执行状态
    status VARCHAR(20) DEFAULT 'pending',    -- pending/running/completed/failed
    progress INTEGER DEFAULT 0,               -- 进度百分比
    
    -- 结果统计
    total_count INTEGER DEFAULT 0,
    matched_count INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    wrong_count INTEGER DEFAULT 0,
    no_match_count INTEGER DEFAULT 0,
    
    -- 指标
    match_rate DECIMAL(5,2),                 -- 匹配率
    accuracy DECIMAL(5,2),                   -- 准确率
    precision_score DECIMAL(5,2),            -- 精确率
    recall_score DECIMAL(5,2),               -- 召回率
    f1_score DECIMAL(5,2),                   -- F1 分数
    avg_confidence DECIMAL(5,3),             -- 平均置信度
    avg_response_time DECIMAL(10,2),         -- 平均响应时间(ms)
    
    -- 词表版本快照
    dict_version VARCHAR(50),                -- 词表版本号
    dict_count INTEGER,                      -- 词典数量
    phrase_count INTEGER,                    -- 短语数量
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- 元数据
    created_by VARCHAR(100),
    tags VARCHAR(200)[]                      -- 标签数组
);

CREATE INDEX idx_eval_tasks_status ON eval_tasks(status);
CREATE INDEX idx_eval_tasks_created_at ON eval_tasks(created_at DESC);
```

### 2.2 评测详情表

```sql
CREATE TABLE eval_details (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES eval_tasks(id) ON DELETE CASCADE,
    
    -- 输入
    check_item TEXT NOT NULL,
    modality VARCHAR(10),
    expected_code VARCHAR(50),
    expected_name VARCHAR(200),
    
    -- 输出
    actual_code VARCHAR(50),
    actual_name VARCHAR(200),
    confidence DECIMAL(5,3),
    response_time DECIMAL(10,2),              -- 响应时间(ms)
    
    -- 结果分类
    is_matched BOOLEAN,                       -- 是否匹配到
    is_correct BOOLEAN,                       -- 是否正确
    match_type VARCHAR(20),                   -- exact/fuzzy/wrong/none
    
    -- 失败原因分类（自动+人工）
    failure_reason VARCHAR(50),               -- missing_word/ambiguity/complex/algorithm
    failure_detail TEXT,                      -- 详细说明
    
    -- 人工审核
    reviewed BOOLEAN DEFAULT FALSE,
    reviewer VARCHAR(100),
    review_note TEXT,
    review_time TIMESTAMP,
    
    -- 优化建议
    suggested_action VARCHAR(50),             -- add_word/add_phrase/add_rule/algorithm_fix
    suggestion_data JSONB,                    -- 具体建议数据
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_eval_details_task_id ON eval_details(task_id);
CREATE INDEX idx_eval_details_is_correct ON eval_details(is_correct);
CREATE INDEX idx_eval_details_failure_reason ON eval_details(failure_reason);
CREATE INDEX idx_eval_details_reviewed ON eval_details(reviewed);
```

### 2.3 优化建议表

```sql
CREATE TABLE optimization_suggestions (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES eval_tasks(id),
    
    -- 建议类型
    suggestion_type VARCHAR(50) NOT NULL,     -- add_medical_dict/add_phrase_map/add_ambiguity_rule
    priority INTEGER DEFAULT 5,               -- 优先级 1-10
    
    -- 建议内容
    word VARCHAR(200),                        -- 词汇
    type VARCHAR(50),                         -- 类型
    source_phrase VARCHAR(200),               -- 源短语
    target_phrase VARCHAR(200),               -- 目标短语
    step VARCHAR(50),                         -- 步骤
    
    -- 影响范围
    affected_count INTEGER,                   -- 影响的失败案例数
    example_cases TEXT[],                     -- 示例案例
    
    -- 状态
    status VARCHAR(20) DEFAULT 'pending',    -- pending/approved/rejected/applied
    applied_at TIMESTAMP,
    
    -- 人工审核
    reviewed_by VARCHAR(100),
    review_note TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_optimization_suggestions_task_id ON optimization_suggestions(task_id);
CREATE INDEX idx_optimization_suggestions_status ON optimization_suggestions(status);
CREATE INDEX idx_optimization_suggestions_priority ON optimization_suggestions(priority DESC);
```

### 2.4 词表版本表

```sql
CREATE TABLE lexicon_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL UNIQUE,     -- 版本号 (如 v1.0.0)
    description TEXT,
    
    -- 词表统计
    medical_dict_count INTEGER,
    phrase_map_count INTEGER,
    ambiguity_rule_count INTEGER,
    
    -- 变更内容
    changelog TEXT,                           -- 变更日志
    added_words INTEGER DEFAULT 0,
    updated_words INTEGER DEFAULT 0,
    deleted_words INTEGER DEFAULT 0,
    
    -- 性能指标（来自最近的评测）
    match_rate DECIMAL(5,2),
    accuracy DECIMAL(5,2),
    f1_score DECIMAL(5,2),
    
    -- 状态
    is_active BOOLEAN DEFAULT FALSE,          -- 当前活跃版本
    
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100)
);
```

---

## 三、API 接口设计

### 3.1 评测任务 API

```typescript
// 创建评测任务
POST /api/evaluation/tasks
{
  name: string;
  description?: string;
  testFilePath: string;
  sampleSize?: number;
  modality?: string;
  tags?: string[];
}

// 获取任务列表
GET /api/evaluation/tasks?status=completed&limit=20&offset=0

// 获取任务详情
GET /api/evaluation/tasks/:id

// 启动评测任务
POST /api/evaluation/tasks/:id/start

// 获取任务进度
GET /api/evaluation/tasks/:id/progress

// 获取评测详情（分页）
GET /api/evaluation/tasks/:id/details?limit=50&offset=0&filter=failed

// 获取失败案例（按原因分组）
GET /api/evaluation/tasks/:id/failures/grouped

// 导出评测报告
GET /api/evaluation/tasks/:id/export?format=csv|json|excel
```

### 3.2 优化建议 API

```typescript
// 生成优化建议
POST /api/evaluation/tasks/:id/suggestions/generate

// 获取优化建议列表
GET /api/evaluation/tasks/:id/suggestions?status=pending

// 审核建议（批准/拒绝）
POST /api/evaluation/suggestions/:id/review
{
  status: 'approved' | 'rejected';
  note?: string;
}

// 应用建议（批量）
POST /api/evaluation/suggestions/apply
{
  suggestionIds: number[];
  createNewVersion: boolean;
  versionName?: string;
}

// 导出补充词表
GET /api/evaluation/tasks/:id/suggestions/export
```

### 3.3 版本对比 API

```typescript
// 获取词表版本列表
GET /api/evaluation/lexicon/versions

// 对比两个评测任务
GET /api/evaluation/compare?taskId1=1&taskId2=2

// 对比两个词表版本
GET /api/evaluation/lexicon/versions/compare?version1=v1.0.0&version2=v1.1.0
```

---

## 四、前端页面设计

### 4.1 Dashboard 仪表盘

```
┌────────────────────────────────────────────────────────┐
│  📊 评测总览                        [新建评测] [版本管理]  │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  │  匹配率  │  │  准确率  │  │ F1 分数  │  │ 响应时间  │
│  │  99.0%   │  │  87.5%   │  │  0.93   │  │  19.5ms   │
│  │ ▲ +2.1%  │  │ ▲ +5.3%  │  │ ▲ +0.05 │  │ ▼ -3.2ms  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘
│                                                        │
│  📈 准确率趋势（最近 10 次评测）                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │         ╱────╲                                   │  │
│  │    ╱───╱      ╲─────╲                           │  │
│  │ ──╱                  ╲────                       │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  📋 最近评测任务                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 名称          样本数   匹配率  准确率  F1   状态   │  │
│  │ Phase2-CT     10,000   99.2%  87.5%  0.93 ✅     │  │
│  │ Phase2-MR      5,000   98.8%  85.1%  0.91 ✅     │  │
│  │ Phase2-DR      8,000   99.5%  89.3%  0.94 ✅     │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  ⚠️  待优化问题（Top 5）                                │
│  1. 缺少词汇 "髁关节" - 影响 23 个案例                  │
│  2. 复合项目拆分失败 - 影响 18 个案例                   │
│  3. "胸部" 与 "胸椎" 歧义 - 影响 15 个案例             │
│  4. 缺少短语映射 "64排" - 影响 12 个案例               │
│  5. 置信度过低 (<0.5) - 影响 8 个案例                  │
└────────────────────────────────────────────────────────┘
```

### 4.2 测试执行器

```
┌────────────────────────────────────────────────────────┐
│  🚀 新建评测任务                              [← 返回]   │
├────────────────────────────────────────────────────────┤
│                                                        │
│  任务名称: [Phase 3 - 边界Case测试_____________]        │
│                                                        │
│  测试数据源:                                            │
│  ○ 16zzy_ct_115k.csv (115,983 条)                     │
│  ○ 16zzy_mr_36k.csv (36,805 条)                       │
│  ○ 16zzy_dr_93k.csv (93,325 条)                       │
│  ● 16zzy_combined_246k.csv (246,113 条) ✓             │
│  ○ 自定义文件 [选择文件...]                            │
│                                                        │
│  采样设置:                                              │
│  ● 随机采样  数量: [10000_] 条                         │
│  ○ 全量测试  (246,113 条，预计 80 分钟)                │
│                                                        │
│  模态过滤:                                              │
│  ☑ CT  ☑ MR  ☑ DR  ☐ US  ☐ RF                        │
│                                                        │
│  高级选项:                                              │
│  ☑ 保存详细结果（包含每条测试数据）                      │
│  ☑ 自动生成优化建议                                     │
│  ☐ 并行执行（4 线程）                                   │
│                                                        │
│  标签: [边界Case] [Phase3] [___________]               │
│                                                        │
│           [取消]  [保存草稿]  [开始评测]               │
└────────────────────────────────────────────────────────┘
```

### 4.3 失败案例浏览器

```
┌────────────────────────────────────────────────────────┐
│  🔍 失败案例分析 - Phase 3 边界Case测试      [导出CSV]   │
├────────────────────────────────────────────────────────┤
│                                                        │
│  筛选条件:                                              │
│  失败类型: [全部 ▼]  模态: [全部 ▼]  置信度: [< 0.7]   │
│  搜索: [____________________] 🔍                       │
│                                                        │
│  按原因分组:                                            │
│  ├─ 缺少词汇 (35 例, 28%)          [展开 ▼]           │
│  ├─ 缺少短语映射 (22 例, 18%)      [展开 ▼]           │
│  ├─ 复合项目拆分失败 (18 例, 15%)  [展开 ▼]           │
│  ├─ 歧义未消除 (12 例, 10%)        [展开 ▼]           │
│  └─ 其他 (38 例, 29%)              [展开 ▼]           │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ ID  │ 原始项目           │ 期望    │ 实际   │ 置信度 │
│  ├────┼──────────────────┼────────┼────────┼──────┤  │
│  │ 1  │ 髁关节CT平扫       │ 20071.. │ (无)   │ 0.0  │  │
│  │    │ 模态: CT  原因: 缺少词汇 "髁关节"        │ [审核] │
│  │    │ 建议: 添加到医学词典 (body, enable=1)    │ [应用] │
│  ├────┼──────────────────┼────────┼────────┼──────┤  │
│  │ 2  │ 64排CT颅脑平扫     │ 20010.. │ 20010..│ 0.95 │  │
│  │    │ 模态: CT  原因: 缺少短语映射 "64排"      │ [审核] │
│  │    │ 建议: phrase_map(64排→空, step=pre)     │ [应用] │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  批量操作: ☐ 全选  ☑ 仅选失败项                         │
│  [批量审核] [批量生成建议] [批量导出]                   │
└────────────────────────────────────────────────────────┘
```

### 4.4 优化工具

```
┌────────────────────────────────────────────────────────┐
│  🔧 优化建议 - Phase 3 边界Case测试          [应用全部]  │
├────────────────────────────────────────────────────────┤
│                                                        │
│  待审核建议: 42 条  已审核: 15 条  已应用: 0 条         │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 📝 医学词典补充 (15 条)           [展开/收起 ▼]   │  │
│  ├──────────────────────────────────────────────────┤  │
│  │  ☑ 髁关节  (body)   影响 23 例   优先级: ⭐⭐⭐     │  │
│  │  ☑ 茎突    (body)   影响 12 例   优先级: ⭐⭐      │  │
│  │  ☑ 蝶鞍    (body)   影响 8 例    优先级: ⭐⭐      │  │
│  │  ☐ ...                                           │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 🔄 短语映射补充 (22 条)           [展开/收起 ▼]   │  │
│  ├──────────────────────────────────────────────────┤  │
│  │  ☑ 64排 → (删除)   影响 18 例   优先级: ⭐⭐⭐      │  │
│  │  ☑ 单次多层螺旋 → (删除)  影响 15 例 优先级: ⭐⭐   │  │
│  │  ☐ ...                                           │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ ⚖️  歧义消除规则 (5 条)           [展开/收起 ▼]   │  │
│  ├──────────────────────────────────────────────────┤  │
│  │  ☑ "胸部" vs "胸椎" 规则  影响 15 例  优先级: ⭐⭐⭐ │  │
│  │     条件: 上下文包含"椎体"关键词 → 选择"胸椎"     │  │
│  │     否则默认"胸部"                                │  │
│  │  ☐ ...                                           │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  应用选项:                                              │
│  ● 创建新版本  版本号: [v1.1.0_______]                 │
│  ○ 覆盖当前版本                                         │
│                                                        │
│  变更日志:                                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Phase 3 边界Case优化:                             │  │
│  │ - 新增医学词汇 15 个（髁关节、茎突等）              │  │
│  │ - 新增短语映射 22 条（去除冗余描述）                │  │
│  │ - 新增歧义规则 5 条（胸部/胸椎等）                  │  │
│  │ 预期影响: 解决 125 个失败案例                      │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│           [取消]  [保存草稿]  [应用并重新评测]         │
└────────────────────────────────────────────────────────┘
```

---

## 五、实现优先级

### Phase 1: 核心功能（2-3 小时）
- ✅ 数据库表设计
- ✅ 后端评测执行器
- ✅ 基础 API（创建任务、获取结果）
- ✅ 简单前端（Dashboard + 测试执行器）

### Phase 2: 分析与优化（2-3 小时）
- ✅ 失败原因自动分类
- ✅ 优化建议生成器
- ✅ 失败案例浏览器前端
- ✅ 优化工具前端

### Phase 3: 高级功能（2-3 小时）
- ✅ 版本管理
- ✅ A/B 测试对比
- ✅ 导出报告（CSV/Excel）
- ✅ 可视化图表（ECharts）

### Phase 4: 体验优化（1-2 小时）
- ✅ 实时进度推送（WebSocket）
- ✅ 批量操作
- ✅ 人工审核工作流
- ✅ 性能优化

---

## 六、技术栈

### 后端
- **框架**: FastAPI
- **数据库**: PostgreSQL
- **ORM**: SQLAlchemy 2.0 (async)
- **任务队列**: asyncio（轻量）/ Celery（重型）
- **缓存**: Redis（可选）

### 前端
- **框架**: React 18 + TypeScript
- **UI**: Ant Design 5
- **图表**: ECharts / Recharts
- **状态管理**: Zustand
- **表格**: Ant Design Table (支持虚拟滚动)

### 数据处理
- **Pandas**: CSV 读写
- **NumPy**: 统计计算
- **Scikit-learn**: 指标计算（F1/Precision/Recall）

---

## 七、下一步

你想：
1. **立即开始实现** - 我先创建数据库迁移和后端代码
2. **先看原型设计** - 我用工具生成可交互的原型让你预览
3. **调整设计方案** - 你有其他需求要补充
4. **分步实施** - 先做 Phase 1 核心功能，后续迭代

请告诉我你的选择！

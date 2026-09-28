# 源码索引

> MMS 平台代码导航与模块依赖关系

## 后端源码结构

### 核心入口

```
src/match_service/
├── main.py                    # FastAPI 应用入口
│   ├── lifespan()            # 启动/关闭生命周期
│   ├── app = FastAPI()       # 应用实例
│   └── router 挂载           # API 路由注册
│
├── config.py                  # 配置管理
│   └── Settings              # Pydantic 配置类
│
└── db.py                      # 数据库连接
    ├── get_engine()          # SQLAlchemy 异步引擎
    └── get_session_factory() # Session 工厂
```

### API 层

```
src/match_service/api/
├── routes.py                  # 新版 API (/api/*)
│   ├── match_one()           # POST /api/match
│   ├── batch_match()         # POST /api/batch-match
│   ├── cache_store()         # POST /api/cache/store
│   ├── cache_invalidate()    # POST /api/cache/invalidate
│   ├── cache_stats()         # GET  /api/cache/stats
│   ├── submit_feedback()     # POST /api/feedback
│   ├── reload_rules()        # POST /api/reload
│   ├── health()              # GET  /api/health
│   ├── rules_snapshot()      # GET  /api/rules/snapshot
│   ├── semantic_match()      # POST /api/semantic-match
│   ├── agent_review()        # POST /api/agent/review
│   ├── agent_suggestions()   # GET  /api/agent/suggestions
│   └── approve_suggestion()  # POST /api/agent/suggestions/{id}/approve
│
├── legacy.py                  # 旧版兼容 API (/algorithm/*)
│   ├── legacy_match()        # POST /algorithm/standardCheck/match
│   ├── legacy_batch()        # POST /algorithm/standardCheck/match/batch
│   └── LegacyAdapter         # 响应格式转换器
│
├── admin.py                   # 管理后台 API (/api/admin/*)
│   ├── get_medical_dict()    # GET  /api/admin/medical-dict
│   ├── create_dict_entry()   # POST /api/admin/medical-dict
│   ├── update_dict_entry()   # PUT  /api/admin/medical-dict/{id}
│   ├── delete_dict_entry()   # DELETE /api/admin/medical-dict/{id}
│   ├── get_rule_history()    # GET  /api/admin/rule-version/history
│   ├── get_stats()           # GET  /api/admin/stats
│   ├── get_lexicon()         # GET  /api/admin/lexicon/{table}
│   ├── create_lexicon()      # POST /api/admin/lexicon/{table}
│   ├── update_lexicon()      # PUT  /api/admin/lexicon/{table}/{id}
│   ├── delete_lexicon()      # DELETE /api/admin/lexicon/{table}/{id}
│   ├── get_standard_items()  # GET  /api/admin/standard-items
│   └── get_unmatched()       # GET  /api/admin/unmatched/list
│
├── evaluation.py              # 评测系统 API (/api/evaluation/*)
│   ├── create_task()         # POST /api/evaluation/tasks
│   ├── list_tasks()          # GET  /api/evaluation/tasks
│   ├── get_task()            # GET  /api/evaluation/tasks/{id}
│   ├── start_task()          # POST /api/evaluation/tasks/{id}/start
│   ├── get_failures()        # GET  /api/evaluation/tasks/{id}/failures
│   ├── get_failure_stats()   # GET  /api/evaluation/tasks/{id}/failures/stats
│   └── delete_task()         # DELETE /api/evaluation/tasks/{id}
│
└── schemas.py                 # Pydantic 请求/响应模型
    ├── MatchRequest
    ├── BatchRequest
    ├── CacheStoreRequest
    ├── FeedbackItem
    └── ...
```

### 核心服务层

```
src/match_service/core/
├── dispatcher.py              # 匹配调度器
│   └── MatchDispatcher
│       ├── match()           # 单项匹配（L1缓存 → L2引擎）
│       └── batch_match()     # 批量匹配
│
├── engine_holder.py           # 引擎单例管理
│   └── EngineHolder
│       ├── initialize()      # 加载词表并初始化引擎
│       ├── reload()          # 热重载引擎
│       ├── v2_engine         # NLP Pipeline 实例
│       ├── kw_engine         # 关键词引擎实例
│       ├── rule_version      # 版本指纹
│       └── is_ready          # 就绪状态
│
└── rule_version.py            # 版本指纹计算
    └── compute_rule_version() # 基于词表内容计算 SHA-256
```

### 匹配引擎层

#### NLP Pipeline (CT/MR/DR/RF/MG)

```
src/match_service/engine/match_engine_v2/
├── orchestrator.py            # 编排器（主入口）
│   └── MatchEngineOrchestrator
│       ├── match()           # 单项匹配
│       └── batch_match()     # 批量匹配
│
├── preprocess_service.py      # 预处理服务
│   └── PreprocessService
│       └── preprocess()      # 全角→半角、去空格、规范化
│
├── bracket_modifier_handler.py # 方括号修饰语处理
│   └── BracketModifierHandler
│       └── handle()          # 识别并剥离 [薄层]、[抑脂] 等
│
├── tokenizer_service.py       # 分词服务
│   └── TokenizerService
│       └── tokenize()        # Jieba 分词（医学词典）
│
├── disambiguation_service.py  # 消歧服务
│   └── DisambiguationService
│       ├── resolve()         # 应用 phrase_map + ambiguity
│       └── split_combo()     # 拆分组合检查
│
├── standard_lookup_service.py # 标准查找服务
│   └── StandardLookupService
│       ├── find()            # 查询标准项目库
│       └── bilateral_infer() # 双侧推断
│
├── pattern_processor.py       # 模式处理器
│   └── extract_scan_type()   # 提取平扫/增强
│       └── extract_body_part() # 提取部位
│
├── data_loader.py             # 数据加载器
│   └── DataLoader
│       ├── load_medical_dict()
│       ├── load_phrase_map()
│       └── load_ambiguity()
│
├── constants.py               # 常量定义
│   ├── MODALITIES            # 支持的模态列表
│   ├── BODY_PART_ALIASES     # 部位别名映射
│   └── PROCESS_KEYWORDS      # 检查过程关键词
│
└── match_node.py              # 匹配节点数据结构
    └── MatchNode             # 匹配结果树节点
```

#### 关键词引擎 (US/SPECT/PET/OCT/DSA)

```
src/match_service/engine/keyword/
└── us_spect_pet_matcher.py    # 关键词匹配器
    └── KeywordMatcher
        ├── match_us()        # 超声匹配
        ├── match_spect()     # SPECT 匹配
        ├── match_pet()       # PET 匹配
        └── extract_keywords() # 部位+检查类型提取
```

### 缓存层

```
src/match_service/cache/
├── models.py                  # 数据模型
│   ├── MatchCache            # 匹配缓存表
│   └── MatchFeedback         # 匹配反馈表
│
└── service.py                 # 缓存服务
    └── CacheService
        ├── get()             # 查询缓存
        ├── store()           # 存储缓存
        ├── invalidate_all()  # 清空全部缓存
        ├── invalidate_by_modality() # 按模态清空
        └── get_stats()       # 统计信息
```

### Agent 层

```
src/match_service/agent/
├── semantic_matcher.py        # 语义匹配器
│   └── LLMSemanticMatcher
│       ├── initialize()      # 初始化 LLM 客户端
│       ├── semantic_match()  # 单项语义匹配
│       └── batch_semantic_match() # 批量语义匹配
│
└── reviewer.py                # 建议审核器
    └── MatchReviewer
        ├── review_batch()    # 分析未匹配项
        ├── get_pending_suggestions() # 获取待审批建议
        └── approve_suggestion() # 审批建议
```

### 评测系统

```
src/match_service/evaluation/
└── runner.py                  # 评测运行器
    └── EvaluationRunner
        ├── create_task()     # 创建评测任务
        ├── run_task()        # 运行评测
        └── analyze_failures() # 失败分析
```

---

## 前端源码结构

```
frontend/src/
├── main.tsx                   # React 入口
├── App.tsx                    # 根组件（路由配置）
│
├── pages/                     # 页面组件
│   ├── Dashboard.tsx         # 数据概览页
│   ├── MatchTest.tsx         # 匹配测试页
│   ├── StandardItems.tsx     # 标准项目管理页
│   ├── LexiconMgmt.tsx       # 词库管理页
│   └── UnmatchedWorkbench.tsx # 未匹配处理页
│
├── components/                # 通用组件
│   └── Sidebar.tsx           # 侧边导航栏
│
├── services/                  # API 服务
│   ├── api.ts                # Axios 实例（拦截器）
│   └── matchService.ts       # 匹配 API 封装
│
├── types/                     # TypeScript 类型
│   └── index.ts              # 全局类型定义
│
├── utils/                     # 工具函数
│   └── formatters.ts         # 数据格式化
│
└── store/                     # 状态管理（Zustand）
    └── useStore.ts           # 全局状态
```

---

## 测试结构

```
tests/
├── engine/                    # 引擎测试
│   ├── test_match_engine_v2.py           # NLP Pipeline 测试
│   ├── test_match_engine_v2_edge_cases.py # 边界情况测试
│   ├── test_match_engine_v2_pipeline.py  # Pipeline 流程测试
│   ├── test_match_engine_v2_performance.py # 性能回归测试
│   └── test_keyword_matcher.py           # 关键词引擎测试
│
├── test_legacy_adapter.py     # Legacy API 测试
├── test_rule_version_parity.py # 版本指纹测试
├── test_cache_service.py      # 缓存服务测试
└── test_dispatcher.py         # 调度器测试
```

---

## 配置文件

```
根目录/
├── pyproject.toml             # Poetry 依赖配置
├── alembic.ini                # Alembic 迁移配置
├── Dockerfile                 # Docker 镜像构建
├── docker-compose.yml         # Docker Compose 配置
├── nginx-canary.conf          # Nginx 灰度配置
├── .env.example               # 环境变量模板
├── .gitignore                 # Git 忽略规则
│
└── frontend/
    ├── package.json           # npm 依赖配置
    ├── vite.config.ts         # Vite 构建配置
    ├── tsconfig.json          # TypeScript 配置
    └── tailwind.config.js     # Tailwind CSS 配置
```

---

## 数据库迁移

```
migrations/
├── env.py                     # Alembic 环境配置
├── script.py.mako             # 迁移模板
│
├── versions/                  # 迁移版本
│   ├── 20260727_1134_*_baseline.py           # 基线表
│   ├── 20260729_1735_*_import_lexicon.py     # 词表导入
│   ├── 20260729_1802_*_evaluation_tables.py  # 评测表
│   ├── 20260731_0930_*_import_standards.py   # 标准项导入
│   ├── 20260804_0200_*_feedback_dedupe.py    # 反馈去重
│   ├── 20260804_1200_*_unify_standards.py    # 标准表统一
│   └── 20260804_1300_*_retag_versions.py     # 版本重标记
│
└── manual/                    # 手动迁移脚本
    ├── phase2_lexicon_补充.sql
    └── phase2_standard_补充.sql
```

---

## 运维脚本

```
scripts/
├── start.sh                   # 一键启动
├── stop.sh                    # 停止服务
├── test-all.sh                # 完整测试套件
├── test-quick.sh              # 快速测试
│
├── canary_monitor.py          # 灰度监控
├── verify_phases.sh           # 阶段验证
│
├── import_vascular_items.py   # 导入血管成像标准项
├── validate_p1p2_improvement.py # P1+P2 验证
├── analyze_unmatched_items.py # 未匹配分析
│
└── 其他数据导入/分析脚本...
```

---

## 模块依赖关系

### 后端依赖图

```
main.py
  ├─→ api/routes.py
  │    ├─→ core/dispatcher.py
  │    │    ├─→ core/engine_holder.py
  │    │    │    ├─→ engine/match_engine_v2/orchestrator.py
  │    │    │    └─→ engine/keyword/us_spect_pet_matcher.py
  │    │    └─→ cache/service.py
  │    └─→ agent/reviewer.py
  │         └─→ agent/semantic_matcher.py
  │
  ├─→ api/legacy.py
  │    └─→ api/legacy_adapter.py
  │
  ├─→ api/admin.py
  │    └─→ cache/models.py
  │
  └─→ api/evaluation.py
       └─→ evaluation/runner.py
```

### 前端依赖图

```
main.tsx
  └─→ App.tsx
       ├─→ components/Sidebar.tsx
       │
       └─→ pages/
            ├─→ Dashboard.tsx
            ├─→ MatchTest.tsx
            ├─→ StandardItems.tsx
            ├─→ LexiconMgmt.tsx
            └─→ UnmatchedWorkbench.tsx
                 ↑
                 └─── services/matchService.ts
                       └─→ services/api.ts
```

---

## 关键文件清单

### 必读文件（理解系统）
1. `README.md` - 项目概述
2. `CLAUDE.md` - AI 助手指南
3. `openwiki/quickstart.md` - 快速入门
4. `openwiki/architecture.md` - 架构设计
5. `src/match_service/main.py` - 应用入口
6. `src/match_service/core/dispatcher.py` - 匹配调度核心
7. `src/match_service/engine/match_engine_v2/orchestrator.py` - NLP Pipeline

### 修改词表
1. `src/match_service/engine/match_engine_v2/data_loader.py` - 词表加载
2. 数据库表：`nlp_medical_dict`, `nlp_phrase_map`, `nlp_ambiguity`
3. `scripts/import_*.py` - 词表导入脚本

### 修改匹配逻辑
1. `src/match_service/engine/match_engine_v2/orchestrator.py` - Pipeline 编排
2. `src/match_service/engine/match_engine_v2/disambiguation_service.py` - 消歧逻辑
3. `src/match_service/engine/match_engine_v2/standard_lookup_service.py` - 查询逻辑

### 添加 API
1. `src/match_service/api/routes.py` - 新版 API
2. `src/match_service/api/schemas.py` - 请求/响应模型
3. `frontend/src/services/matchService.ts` - 前端 API 封装

### 部署配置
1. `.env.example` - 环境变量模板
2. `docker-compose.yml` - Docker 部署
3. `nginx-canary.conf` - 灰度配置
4. `Dockerfile` - 容器镜像

---

## 代码统计

```bash
# 后端代码量
find src/match_service -name "*.py" | xargs wc -l | tail -1
# 总计: ~7,700 行

# 前端代码量
find frontend/src -name "*.tsx" -o -name "*.ts" | xargs wc -l | tail -1
# 总计: ~5,300 行

# 测试代码量
find tests -name "*.py" | xargs wc -l | tail -1
# 总计: ~3,500 行

# 总代码量: ~16,500 行
```

---

## 相关文档
- [快速入门](quickstart.md) - 上手指南
- [架构设计](architecture.md) - 系统架构
- [领域概念](domain-concepts.md) - 业务术语
- [工作流程](workflows.md) - 开发流程

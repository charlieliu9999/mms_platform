# MMS Platform - OpenWiki Quickstart

> 医学影像检查项目标准化匹配服务 - 代码知识库入口

## 📖 文档导航

### 核心文档
- [架构设计](architecture.md) - 三层匹配架构、模块职责、数据流
- [工作流程](workflows.md) - 开发、测试、部署、运维流程
- [领域概念](domain-concepts.md) - 医学词典、标准项目、匹配引擎、消歧规则
- [API 参考](api-reference.md) - REST API、Legacy API、管理 API
- [数据库设计](database-schema.md) - 表结构、索引、迁移策略

### 实现细节
- [匹配引擎](engine-implementation.md) - NLP Pipeline、关键词引擎、双侧推断
- [缓存策略](cache-strategy.md) - L1 缓存、Redis、失效策略
- [Agent 系统](agent-system.md) - 语义匹配、建议审核、进化机制
- [前端架构](frontend-architecture.md) - React 组件、路由、状态管理

### 运维指南
- [部署方案](deployment.md) - 开发/生产部署、Docker、灰度发布
- [测试策略](testing.md) - 单元测试、集成测试、回归测试
- [故障排查](troubleshooting.md) - 常见问题、日志分析、性能调优
- [配置管理](configuration.md) - 环境变量、引擎模式、数据库连接

### 代码地图
- [源码索引](source-map.md) - 模块导航、关键文件、依赖关系

---

## 🚀 快速上手

### 1. 环境准备
```bash
# 检查依赖
python --version  # 需要 3.11+
node --version    # 需要 18+
docker --version  # 可选

# 克隆项目
cd /path/to/mms_platform

# 安装后端依赖
poetry install

# 安装前端依赖
cd frontend && npm install
```

### 2. 数据库初始化
```bash
# 启动 PostgreSQL (Docker)
docker run -d --name mms-postgres \
  -e POSTGRES_DB=acrac_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 15432:5432 \
  postgres:15-alpine

# 运行迁移
poetry run alembic upgrade head
```

### 3. 启动服务
```bash
# 一键启动（推荐）
./scripts/start.sh

# 或手动启动
# 终端1: 后端
poetry run uvicorn match_service.main:app --reload --port 9100

# 终端2: 前端
cd frontend && npm run dev
```

### 4. 访问界面
- 前端: http://localhost:3100
- 后端 API: http://localhost:9100/docs
- 健康检查: http://localhost:9100/api/health

### 5. 运行测试
```bash
# 完整测试套件
./scripts/test-all.sh

# 仅后端测试
poetry run pytest tests/ -v

# 仅前端构建测试
cd frontend && npm run build
```

---

## 📚 核心概念速览

### 三层匹配架构
```
用户输入 "CT头部平扫"
    ↓
L1: 缓存查询 (match_cache 表)
    ├─ 命中 → 直接返回
    └─ 未命中 ↓
L2: 算法引擎
    ├─ NLP Pipeline (CT/MR/DR/RF/MG)
    │   └─ 预处理 → 分词 → 消歧 → 标准查找
    ├─ 关键词匹配 (US/SPECT/PET/OCT/DSA)
    └─ 置信度 < 0.8 ↓
L3: AI Agent
    ├─ 语义匹配 (LLM)
    └─ 优化建议 → 人工审批 → 词库进化
```

### 关键数据表
| 表名 | 用途 | 规模 |
|------|------|------|
| `nlp_medical_dict` | 医学词典 | 2,435 条 |
| `nlp_phrase_map` | 短语映射 | 7,839 条 |
| `nlp_ambiguity` | 消歧规则 | 1,229 条 |
| `mms_standard_item` | 标准项目库 | ~3,000 条 |
| `match_cache` | L1 缓存 | 17 万+ 条 |
| `match_feedback` | 匹配反馈 | 按需增长 |

### 引擎模式
- **local**: 从 `src/match_service/engine/` 加载（生产独立部署）
- **shared**: 从 `acrac_backend/` 加载（开发期共享引擎）

环境变量: `MATCH_SVC_ENGINE_MODE`

---

## 🔍 代码导航

### 后端核心模块
```
src/match_service/
├── main.py              # FastAPI 入口
├── config.py            # 配置管理
├── db.py                # 数据库连接
│
├── engine/              # 匹配引擎 (4,772 行)
│   ├── match_engine_v2/ # NLP Pipeline
│   │   ├── orchestrator.py        # 编排器
│   │   ├── preprocess_service.py  # 预处理
│   │   ├── tokenizer_service.py   # 分词
│   │   ├── disambiguation_service.py # 消歧
│   │   └── standard_lookup_service.py # 标准查找
│   └── keyword/         # 关键词引擎
│       └── us_spect_pet_matcher.py
│
├── api/                 # API 路由
│   ├── routes.py        # 新版 API
│   ├── legacy.py        # 旧版兼容 API
│   ├── admin.py         # 管理后台 API
│   └── evaluation.py    # 评测系统 API
│
├── core/                # 核心服务
│   ├── dispatcher.py    # 匹配调度器
│   ├── engine_holder.py # 引擎单例
│   └── rule_version.py  # 版本指纹
│
└── agent/               # AI Agent
    ├── semantic_matcher.py # 语义匹配
    └── reviewer.py         # 建议审核
```

### 前端核心模块
```
frontend/src/
├── pages/               # 页面组件
│   ├── Dashboard.tsx         # 数据概览
│   ├── MatchTest.tsx         # 匹配测试
│   ├── StandardItems.tsx     # 标准项目
│   ├── LexiconMgmt.tsx       # 词库管理
│   └── UnmatchedWorkbench.tsx # 未匹配处理
│
├── services/            # API 服务
│   ├── api.ts           # Axios 实例
│   └── matchService.ts  # API 方法
│
└── components/          # 通用组件
    └── Sidebar.tsx      # 导航栏
```

---

## 🎯 常见任务

### 添加新词条
```bash
# 1. 连接数据库
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db

# 2. 插入词条
INSERT INTO nlp_medical_dict (word, type, enable) 
VALUES ('肺动脉', 'body_part', 0);

# 3. 重启服务加载新词库
./scripts/stop.sh && ./scripts/start.sh
```

### 添加标准项目
通过前端管理后台:
1. 访问 http://localhost:3100/standard-items
2. 点击"新增"按钮
3. 填写项目信息并保存

### 查看匹配日志
```bash
# 后端日志
tail -f logs/match_service.log

# 数据库查询未匹配项
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db -c \
  "SELECT original_text, modality FROM match_feedback WHERE status='pending' LIMIT 10;"
```

### 运行单个测试
```bash
# 运行单个测试文件
poetry run pytest tests/engine/test_match_engine_v2.py -v

# 运行单个测试函数
poetry run pytest tests/engine/test_match_engine_v2.py::test_v2_has_results -v

# 运行带关键词的测试
poetry run pytest tests/ -k "bilateral" -v
```

---

## 📊 当前状态 (2026-08-07)

### 测试状态
- 后端测试: 113/127 通过 (89%)
- 前端构建: 通过
- 待修复: DR 双侧匹配、预处理接口、Golden 测试

### 已完成阶段
- ✅ Phase 0-4: 词表裁定 (11,503 条)
- ✅ Phase A: 引擎物理独立
- ✅ Phase B: 新库构建 + Docker
- ✅ Phase C: 兼容层 + 灰度部署
- ✅ Phase D: 配置层独立化
- ✅ Phase E: 管理前端
- ✅ Phase F: AI Agent 集成
- ✅ Phase G: 多租户设计
- ✅ P1: 算法修复 (21 个 Bug)
- ✅ P2: 血管成像标准库补充 (27 项)

### 待处理任务
- 🔄 P1/P2 快速优化 (目标 92% 达成率)
- 🔄 DR 双侧匹配修复
- 🔄 Golden 测试更新
- 📋 P3 标准库缺口补充

---

## 🔗 相关资源

### 项目文档
- [README.md](../README.md) - 项目概述
- [CLAUDE.md](../CLAUDE.md) - AI 助手指南
- [TODO.md](../TODO.md) - 任务清单
- [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) - 项目结构

### 设计文档
- [Phase F Agent 设计](../docs/PHASE_F_AGENT.md)
- [Phase G 多租户设计](../docs/PHASE_G_MULTI_TENANT.md)

### 验证报告
- [P1+P2 成果总结](../docs/reports/2026-08-07-p1-p2-results-summary.md)
- [P1+P2 差距分析](../docs/reports/2026-08-07-p1-p2-gap-analysis.md)

---

## 💡 提示

- 修改词库后必须重启服务才能生效
- 修改数据库结构后必须运行 Alembic 迁移
- 前端开发时使用 `npm run dev`，生产部署使用 `npm run build`
- 健康检查端点不应用于生产监控（缓存统计可能超时）
- Legacy API 仅用于兼容旧系统，新开发应使用 `/api/*` 端点

---

**生成时间**: 2026-08-07  
**维护者**: Claude Opus 5  
**更新频率**: 每次重大变更后手动更新

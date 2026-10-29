# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

---

## ⚠️ 最高优先级：项目核心原则（必读）

**在进行任何开发工作前，必须先阅读**: [`PROJECT_CORE_PRINCIPLES.md`](./PROJECT_CORE_PRINCIPLES.md)

**核心要求摘要**:
1. ✅ **唯一评价指标**: 4555个ACR项目全量匹配率
2. ✅ **未匹配比例必须降低**: 每次优化必须减少未匹配项
3. ✅ **零破坏原则**: 任何修改必须先运行全量回归测试，不得出现"修好A破坏B"
4. ✅ **整体匹配率提升**: 全局优化，不允许牺牲某个模态优化另一个
5. ✅ **系统化分析**: 一个一个项目分析，沉淀词典/算法/文档

**评估命令**:
```bash
# 任何修改前后都必须运行
poetry run python scripts/evaluate_acr_4555.py

# 或使用快速脚本
./scripts/quick_eval.sh eval "阶段名" "描述"

# 生成可视化报告
./scripts/quick_eval.sh report
```

**评估系统完整指南**: [`docs/EVALUATION_SYSTEM_GUIDE.md`](./docs/EVALUATION_SYSTEM_GUIDE.md)

**违反核心原则的代码将被回滚。**

---

## 代码线权威性（必读）

- 唯一权威代码线是 GitHub `charlieliu9999/mms_platform` 的 `main`。生产
  release（`/data/mms-releases/<release>/src`）的源码必须能与该 `main` 对齐，
  并与 `POST /api/rules/snapshot` 报告的规则版本一起构成发布身份。
- GitLab `http://192.168.0.155/liuzhaohui/mms_platform.git` 的 `main` 是**只读
  镜像**：只允许把 GitHub `main` 强制同步过去，禁止直接在 GitLab 上推送或
  合并。GitLab 的 `codex/*` 等历史分支保留为归档，不再作为开发起点。
- 分叉原因：GitLab `main` 停在 `8302ff7`（2026-09-26，缺少
  `migrations/independent/` 独立库迁移，且使用已废弃的 `std_version` 契约），
  与 GitHub 线无共同祖先。旧线完整保留在 GitLab 分支
  `archive/pre-unify-8302ff7`。
- 同步命令（把 GitHub `main` 镜像到 GitLab，需要人工确认后执行）：

```bash
git fetch github main
git push origin github/main:refs/heads/main --force-with-lease=main
```

- 本机 `mms_platform` 主工作树仍可能停留在旧 GitLab 线上并带有未提交的
  开发内容；不要用 `git reset --hard`、`git checkout --` 或整目录覆盖来"对齐"
  它，先把未提交改动落地到 GitHub 线的任务分支。

---

## 项目概述

MMS (Medical Match Service) - 医学影像检查项目标准化匹配服务。独立的 FastAPI 后端 + React 前端，提供三层匹配架构（映射库→算法引擎→AI Agent）。

**核心引擎**: 
- NLP Pipeline (CT/MR/DR/RF/MG) - 10步语义分析
- 关键词匹配 (US/SPECT/PET/OCT/DSA)
- 词表规模: 11,503条（医学词典2,435 + 短语映射7,839 + 消歧规则1,229）

**部署端口**:
- 后端: 9100
- 前端: 3100

## 常用开发命令

### 快速启动（开发模式）
```bash
# 一键启动前后端
./scripts/start.sh

# 停止服务
./scripts/stop.sh
```

### 后端开发
```bash
# 安装依赖
poetry install

# 数据库迁移（首次或 schema 变更后）
poetry run alembic upgrade head

# 启动开发服务器（带热重载）
poetry run uvicorn match_service.main:app --reload --port 9100

# 运行所有测试
poetry run pytest tests/ -v

# 运行单个测试文件
poetry run pytest tests/engine/test_match_engine_v2.py -v

# 运行单个测试函数
poetry run pytest tests/test_legacy_adapter.py::test_legacy_single_match -v
```

### 前端开发
```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器（端口 3100，自动代理到 9100）
npm run dev

# TypeScript 类型检查
npx tsc --noEmit

# 构建生产版本
npm run build

# Lint 检查
npm run lint
```

### 完整测试套件
```bash
# 运行所有测试（后端+前端+集成）
./scripts/test-all.sh
```

## 架构要点

### 三层匹配架构
```
L1: 映射库（match_cache 表，O(1) hash 查询，TTL=30天）
     ↓ 未命中
L2: 算法引擎（NLP Pipeline + 关键词匹配，4,772行核心代码）
     ↓ 低置信度
L3: AI Agent（LLM 审核 + 建议，异步进化）
```

### 后端模块结构
```
src/match_service/
├── main.py              # FastAPI 入口，挂载前端静态文件（生产模式）
├── config.py            # 配置管理（Pydantic Settings，环境变量前缀 MATCH_SVC_）
├── db.py                # 数据库连接（SQLAlchemy 2.0 async）
│
├── engine/              # 匹配引擎核心（4,772行）
│   ├── match_engine_v2/ # NLP Pipeline（orchestrator→预处理→消歧→标准查找）
│   └── keyword/         # 关键词引擎（US/SPECT/PET等模态）
│
├── api/
│   ├── routes.py        # 新版 API（/api/match/*）
│   ├── legacy.py        # 旧版兼容层（/algorithm/standardCheck/*）
│   └── admin.py         # 管理后台 API（/api/admin/*）
│
├── agent/               # Phase F - AI Agent
│   ├── reviewer.py      # 未匹配项目分析
│   ├── suggestion.py    # 优化建议数据模型
│   └── technical_detail_completion.py # 技术详情候选、审核、发布与回滚
│
├── core/
│   ├── engine_holder.py # 引擎单例管理（启动时加载词表）
│   └── rule_version.py  # 版本指纹计算（基于词表内容）
│
└── cache/               # Redis 缓存层（可选）
```

### 前端模块结构
```
frontend/src/
├── pages/
│   ├── Dashboard.tsx         # 数据统计看板
│   ├── MatchTest.tsx         # 单项目匹配测试工具
│   ├── StandardItems.tsx     # 标准项目浏览
│   ├── LexiconMgmt.tsx       # 词库 CRUD
│   ├── TechnicalDetailWorkbench.tsx # 技术详情构建与官网发布
│   ├── TechnicalDetailLibrary.tsx # 正式技术参数与来源追溯
│   └── UnmatchedWorkbench.tsx # AI 建议审批
│
├── services/
│   ├── api.ts                # Axios 实例（自动注入 baseURL）
│   └── matchService.ts       # API 方法封装
│
├── components/Sidebar.tsx    # 导航侧边栏
├── store/                    # Zustand 状态管理
└── types/                    # TypeScript 类型定义
```

### 配置管理
所有配置通过环境变量或 `.env` 文件管理，**前缀统一为 `MATCH_SVC_`**。

关键配置项：
- `MATCH_SVC_DATABASE_URL`: PostgreSQL 连接串（asyncpg 驱动）
- `MATCH_SVC_REDIS_URL`: Redis 连接串（可选）
- `MATCH_SVC_ENGINE_MODE`: 引擎加载模式（`local`=生产, `shared`=开发期）
- `MATCH_SVC_LLM_API_BASE/KEY/MODEL`: Agent LLM 配置

参考 `.env.example` 获取完整配置模板。

### 数据库迁移
使用 Alembic 管理 schema 演进：
```bash
# 自动生成迁移（检测 models.py 变更）
poetry run alembic revision --autogenerate -m "描述变更"

# 应用迁移
poetry run alembic upgrade head

# 回滚一个版本
poetry run alembic downgrade -1
```

**注意**: `main.py` 启动时**不会**自动 create_all，必须手动运行迁移。

### API 兼容层（Phase C）
`api/legacy.py` 提供旧版 API 兼容：
- `/algorithm/standardCheck/match` → 内部调用新版 `/api/match/one`
- 灰度部署时使用 Nginx 分流（10%→100%）

### 前端开发注意事项
- Vite 配置了代理：`/api/*` → `http://localhost:9100`
- 使用 Ant Design 5 + Tailwind CSS 4
- 状态管理：Zustand（轻量级，不需要 Redux）
- 路由：React Router 6

## 测试策略

### 后端测试（46个测试）
- `tests/engine/` - 引擎单元测试（NLP pipeline、关键词匹配、边界情况）
- `tests/test_legacy_adapter.py` - 旧版 API 兼容性测试
- `tests/test_rule_version_parity.py` - 版本指纹一致性测试

**运行测试前确保**:
1. PostgreSQL 已启动（15432端口）
2. 数据库已迁移（`alembic upgrade head`）
3. 词表数据已加载（`migrations/versions/*_load_finalized_lexicon.py`）

### 前端测试
- TypeScript 编译检查：`npx tsc --noEmit`
- 生产构建测试：`npm run build`
- Lint 检查：`npm run lint`

### 集成测试
`./scripts/test-all.sh` 运行完整测试流程：
1. 后端单元测试
2. 后端 API 测试（健康检查/匹配/管理/Legacy）
3. 前端构建测试
4. 端到端功能验证

## 部署模式

### 开发环境
```bash
./scripts/start.sh  # 后端9100 + 前端3100
```

### 生产环境（方案A: 单机部署）
后端自动挂载前端静态文件：
```bash
cd frontend && npm run build  # 构建到 frontend/dist/
cd ..
poetry run uvicorn match_service.main:app --host 0.0.0.0 --port 9100
# 访问 http://localhost:9100/ 即可（后端服务前端）
```

### 生产环境（方案B: Docker）
```bash
docker-compose up -d  # 启动完整栈（后端+前端+PostgreSQL+Redis）
```

### 生产环境（方案C: 前后端分离）
- 后端：Docker 容器（9100）
- 前端：Vercel/Netlify/Nginx 静态托管

## 重要约定

### 引擎加载模式
- `ENGINE_MODE=local`: 生产部署，从 `src/match_service/engine/` 加载引擎
- `ENGINE_MODE=shared`: 开发期，从 `acrac_backend/` 加载共享引擎（需要将父项目加入 PYTHONPATH）

### 词表数据加载
词表数据在 Alembic 迁移中加载（`migrations/versions/*_load_finalized_lexicon.py`），**不是**应用启动时加载。首次部署务必运行 `alembic upgrade head`。

### 技术详情发布
- 技术详情 Agent 只能先写 `technical_detail_candidates`，不得直接覆盖 `standard_check_items`。
- 批量重新构建不得覆盖 `has_manual_edits=true` 的候选。
- 只有 `approved` 候选可以发布；发布必须保存 before/after 快照并支持冲突保护回滚。
- 历史导入和规则发布的字段来源统一记录在 `technical_detail_provenance`。

### 版本指纹
`core/rule_version.py` 计算词表内容的 SHA-256 指纹，用于：
- 缓存失效判断（词表变更后自动刷新）
- 灰度部署时版本对齐校验

### 前端代理配置
`frontend/vite.config.ts` 已配置开发代理：
```typescript
proxy: {
  '/api': 'http://localhost:9100',
  '/algorithm': 'http://localhost:9100'
}
```

## 故障排查

### 后端启动失败
1. 检查 PostgreSQL 连接：`psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db`
2. 检查数据库迁移状态：`poetry run alembic current`
3. 检查环境变量：`env | grep MATCH_SVC_`

### 引擎加载失败
- 检查词表数据是否已加载：`psql -c "SELECT COUNT(*) FROM medical_dict;"`
- 预期词表数量：medical_dict (2,435), phrase_map (7,839), ambiguity_rule (1,229)

### 前端 API 调用失败
1. 检查后端是否启动：`curl http://localhost:9100/health`
2. 检查 Vite 代理配置：`frontend/vite.config.ts`
3. 检查 CORS 配置：`main.py` 的 `CORSMiddleware`

### 测试失败
- 后端测试失败：检查数据库连接和词表数据
- 前端构建失败：检查 TypeScript 错误 `npx tsc --noEmit`

## 与原系统关系

本项目从 `acrac_web_mgmt` 独立出来，替代原系统的匹配服务：
- **原后端**: `acrac_backend/app/services/check_item_mgmt/`
- **原前端**: `acrac_frontend/src/modules/check-item-mgmt/`
- **兼容性**: Phase C 提供 Legacy API 兼容层，旧服务可无缝切换
- **灰度切换**: 使用 Nginx 流量分流（10%→100%），平滑迁移

## 开发工作流

1. **功能开发**: 遵循三层架构，优先使用 L1 缓存，复杂逻辑放 L2 引擎
2. **数据库变更**: 必须通过 Alembic 迁移，不直接修改表结构
3. **API 变更**: 新 API 走 `api/routes.py`，旧 API 兼容层不修改
4. **测试优先**: 修改引擎代码后必须运行 `pytest tests/engine/` 验证
5. **前端开发**: 修改 TypeScript 后运行 `npx tsc --noEmit` 类型检查
6. **提交前**: 运行 `./scripts/test-all.sh` 确保所有测试通过

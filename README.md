# MMS - 医学影像检查项目标准化匹配服务

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue.svg)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 独立的医学影像检查项目标准化服务；`acrac_web_mgmt` 等业务系统只通过稳定 HTTP 契约消费结果。

## 服务目标与验收标准

唯一业务目标是把医院原始检查项目转换为可追溯、可版本化的标准检查项目，并在
4,555 个 ACR 检查项目全量评价集上持续减少未匹配项。任何优化都不能以牺牲其他模态
或既有正确结果为代价。

标准消费者契约：

- `GET /api/health`：业务就绪状态，必须检查 `engine_ready=true`
- `GET /api/rules/snapshot`：当前规则指纹和就绪状态
- `POST /api/batch-match`：批量标准化；输入 `items[].key/name/modality`
- `POST /api/reload`：热重载规则并使缓存失效

批量结果位于 `results[key].data[].standard[{code,name}]`，并携带置信度、匹配层级、
有效模态和顶层规则版本。`modality` 可以传空字符串，由 MMS 根据检查项目文本推断。
详见 [PROJECT_CORE_PRINCIPLES.md](./PROJECT_CORE_PRINCIPLES.md)。

## 🎯 核心功能

- **智能匹配引擎**: 10步 NLP Pipeline + 关键词匹配，支持 9 种影像模态
- **管理后台**: 词库 CRUD、统计看板、版本追溯
- **AI 增强**: 自动分析未匹配项目，提供优化建议
- **灰度部署**: Nginx 流量分流，平滑切换
- **API 兼容**: 新版 `/api/*` 契约供主项目调用，Legacy API 仅用于迁移期兼容

## 🚀 快速开始

### 一键启动（开发模式）

```bash
./scripts/start.sh
```

访问:
- 前端: http://localhost:3100
- 后端 API: http://localhost:9100/docs

### 停止服务

```bash
./scripts/stop.sh
```

### 完整测试

```bash
./scripts/test-all.sh
```

## 📦 技术栈

### 后端
- **框架**: FastAPI 0.110+
- **数据库**: PostgreSQL + SQLAlchemy 2.0 (async)
- **引擎**: 
  - NLP Pipeline: CT/MR/DR/RF/MG
  - 关键词匹配: US/SPECT/PET/OCT/DSA
- **依赖管理**: Poetry

### 前端
- **框架**: React 18 + TypeScript
- **UI 库**: Ant Design 5
- **构建**: Vite 5
- **路由**: React Router 6
- **HTTP**: Axios

## 📁 项目结构

```
match_service/
├── src/match_service/        # 后端源码
│   ├── engine/               # 匹配引擎 (4,772 行)
│   ├── api/                  # API 路由
│   ├── agent/                # AI Agent
│   └── main.py               # 应用入口
├── frontend/                  # React 前端
│   └── src/
│       ├── pages/            # 页面组件
│       ├── components/       # 通用组件
│       └── services/         # API 服务
├── tests/                     # 测试套件 (46 个)
├── scripts/                   # 运维脚本
│   ├── start.sh              # 一键启动
│   ├── stop.sh               # 停止服务
│   ├── test-all.sh           # 完整测试
│   └── init-git.sh           # 初始化独立仓库
└── docs/                      # 文档
```

详细结构见 [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)

## 🔧 开发指南

### 环境要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Poetry
- npm

### 安装依赖

```bash
# 后端
poetry install

# 前端
cd frontend && npm install
```

### 数据库迁移

```bash
poetry run alembic upgrade head
```

### 手动启动

```bash
# 后端 (终端 1)
poetry run uvicorn match_service.main:app --reload --port 9100

# 前端 (终端 2)
cd frontend && npm run dev
```

## 🧪 测试

### 后端测试

```bash
poetry run pytest tests/ -v
```

### 前端测试

```bash
cd frontend
npx tsc --noEmit    # 类型检查
npm run build       # 构建测试
```

### 完整测试套件

```bash
./scripts/test-all.sh
```

测试内容:
1. 后端单元测试 (46 个)
2. 后端 API 测试 (健康检查/匹配/管理/Legacy)
3. 前端构建测试 (TypeScript/ESLint/Build)
4. 集成测试 (前后端联调/CORS)
5. 功能验证 (Phase C-G)

## 📊 数据规模

- **词表总数**: 11,503 条
  - 医学词典: 2,435 条
  - 短语映射: 7,839 条
  - 消歧规则: 1,229 条
- **代码量**: 13,000+ 行
- **质量门禁**: 后端测试、前端类型检查/构建、API 契约和 4,555 项全量评估分别验收

## 🚢 部署

### 开发环境

```bash
./scripts/start.sh
```

### 生产环境 (方案 A: 单机部署)

```bash
# 1. 构建前端
cd frontend && npm run build

# 2. 启动后端 (自动挂载前端)
cd .. && poetry run uvicorn match_service.main:app --host 0.0.0.0 --port 9100
```

### 生产环境 (方案 B: Docker)

```bash
docker-compose up -d
```

### 生产环境 (方案 C: 前后端分离)

- 后端: Docker 容器 (9100)
- 前端: Vercel/Netlify/Nginx (静态部署)

详见 [QUICKSTART.md](./QUICKSTART.md)

## 📖 文档

- [快速启动指南](./QUICKSTART.md)
- [项目结构说明](./PROJECT_STRUCTURE.md)
- [完成报告](./COMPLETION_REPORT.md)
- [AI Agent 设计](./docs/PHASE_F_AGENT.md)
- [多租户设计](./docs/PHASE_G_MULTI_TENANT.md)

## 🎉 完成阶段

- ✅ **Phase 0-4**: 词表裁定 (186/186 条)
- ✅ **Phase A**: 引擎物理独立 (4,772 行迁移)
- ✅ **Phase B**: 新库构建 + Docker
- ✅ **Phase C**: 兼容层 + 灰度部署
- ✅ **Phase D**: 配置层独立化
- ✅ **Phase E**: 管理前端
- ✅ **Phase F**: AI Agent 集成
- ✅ **Phase G**: 多租户设计

## 🔗 与原系统关系

本项目从 `acrac_web_mgmt` 独立出来，替代原系统的匹配服务：

- **原系统后端**: `acrac_backend/app/services/check_item_mgmt/`
- **原系统前端**: `acrac_frontend/src/modules/check-item-mgmt/`
- **兼容性**: Phase C 提供 Legacy API 兼容层
- **灰度切换**: Nginx 10% → 100% 渐进式迁移

## 📝 脚本说明

| 脚本 | 用途 |
|------|------|
| `scripts/start.sh` | 一键启动前后端服务 |
| `scripts/stop.sh` | 停止所有服务 |
| `scripts/test-all.sh` | 运行完整测试套件 |
| `scripts/init-git.sh` | 初始化独立 Git 仓库 |
| `scripts/verify_phases.sh` | 验证 Phase C-G 功能 |
| `scripts/canary_monitor.py` | 灰度监控工具 |

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 👥 作者

从 acrac_web_mgmt 项目独立出来  
提取日期: 2026-07-28

---

**快速命令速查**

```bash
# 开发
./scripts/start.sh          # 启动服务
./scripts/stop.sh           # 停止服务

# 测试
./scripts/test-all.sh       # 完整测试
poetry run pytest tests/    # 后端测试
cd frontend && npm run build  # 前端构建

# 部署
docker-compose up -d        # Docker 部署
bash scripts/verify_phases.sh  # 功能验证

# Git
./scripts/init-git.sh       # 初始化独立仓库
```

# MMS - 医学影像检查项目标准化匹配服务

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue.svg)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 独立的医学影像检查项目标准化匹配服务，提供完整的前后端解决方案

## 🎯 核心功能

- **智能匹配引擎**: 10步 NLP Pipeline + 关键词匹配，支持 9 种影像模态
- **管理后台**: 词库 CRUD、统计看板、版本追溯
- **AI 增强**: 自动分析未匹配项目，提供优化建议
- **灰度部署**: Nginx 流量分流，平滑切换
- **API 兼容**: Legacy API 支持旧服务无缝平替

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
- **测试覆盖**: 46 个测试 (100% 通过率)

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

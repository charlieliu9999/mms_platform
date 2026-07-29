# MMS 标准化匹配服务 - 项目结构

## 概述

MMS (Medical Match Service) 是从 acrac_backend 独立出来的标准化匹配算法服务，提供完整的前后端解决方案。

## 目录结构

```
match_service/
├── README.md                   # 项目说明
├── QUICKSTART.md              # 快速启动指南
├── COMPLETION_REPORT.md       # 项目完成报告
├── pyproject.toml             # Python 依赖管理
├── Dockerfile                 # 后端容器化
├── docker-compose.yml         # 完整栈部署
├── nginx-canary.conf          # 灰度部署配置
│
├── src/match_service/         # 后端源码
│   ├── main.py               # FastAPI 应用入口
│   ├── config.py             # 配置管理
│   ├── db.py                 # 数据库连接
│   │
│   ├── engine/               # 匹配引擎（4,772 行）
│   │   ├── match_engine_v2/  # NLP Pipeline (CT/MR/DR/RF/MG)
│   │   │   ├── orchestrator.py
│   │   │   ├── data_loader.py
│   │   │   ├── disambiguation_service.py
│   │   │   ├── standard_lookup_service.py
│   │   │   └── ...
│   │   └── keyword/          # 关键词引擎 (US/SPECT/PET)
│   │       └── us_spect_pet_matcher.py
│   │
│   ├── api/                  # API 路由
│   │   ├── routes.py         # 新版 API
│   │   ├── legacy.py         # 旧版兼容层（Phase C）
│   │   └── admin.py          # 管理后台 API（Phase E）
│   │
│   ├── agent/                # AI Agent（Phase F）
│   │   ├── reviewer.py       # 匹配审核器
│   │   └── suggestion.py     # 建议数据模型
│   │
│   ├── core/                 # 核心模块
│   │   ├── engine_holder.py  # 引擎单例管理
│   │   └── rule_version.py   # 版本指纹计算
│   │
│   ├── cache/                # 缓存层
│   └── static/               # 旧版管理面板
│       └── admin.html
│
├── frontend/                  # React 前端（新建）
│   ├── package.json          # 前端依赖
│   ├── vite.config.ts        # Vite 配置
│   ├── tsconfig.json         # TypeScript 配置
│   │
│   └── src/
│       ├── main.tsx          # 入口文件
│       ├── App.tsx           # 根组件
│       │
│       ├── components/       # 通用组件
│       │   └── Sidebar.tsx
│       │
│       ├── pages/            # 页面组件
│       │   ├── Dashboard.tsx      # 数据概览
│       │   ├── MatchTest.tsx      # 匹配测试
│       │   └── LexiconMgmt.tsx    # 词库管理
│       │
│       ├── services/         # API 服务
│       │   ├── api.ts             # Axios 配置
│       │   └── matchService.ts    # API 方法
│       │
│       ├── types/            # TypeScript 类型
│       ├── utils/            # 工具函数
│       └── store/            # 状态管理（Zustand）
│
├── tests/                     # 测试套件（46 个测试）
│   ├── engine/
│   │   ├── test_match_engine_v2_pipeline.py
│   │   └── test_match_engine_v2_edge_cases.py
│   └── ...
│
├── migrations/                # 数据库迁移
│   └── versions/
│       └── 20260728_1055_load_finalized_lexicon.py
│
├── scripts/                   # 运维脚本
│   ├── canary_monitor.py     # 灰度监控
│   └── verify_phases.sh      # 阶段验证
│
├── docs/                      # 文档
│   ├── PHASE_F_AGENT.md      # AI Agent 设计
│   └── PHASE_G_MULTI_TENANT.md  # 多租户设计
│
└── phase0-deliverables/       # Phase 0-4 词表定稿
    ├── finalized_medical_dict.csv    # 2,435 条
    ├── finalized_phrase_map.csv      # 7,839 条
    ├── finalized_ambiguity.csv       # 1,229 条
    └── adjudication_report.md
```

## 技术栈

### 后端
- **框架**: FastAPI 0.110+
- **语言**: Python 3.11+
- **数据库**: PostgreSQL (SQLAlchemy 2.0 async)
- **引擎**: NLP Pipeline + 关键词匹配
- **依赖管理**: Poetry

### 前端
- **框架**: React 18
- **语言**: TypeScript
- **UI 库**: Ant Design 5
- **构建工具**: Vite 5
- **路由**: React Router 6
- **HTTP 客户端**: Axios

## 核心功能

### 后端 API (端口 9100)

#### 匹配 API
- `POST /api/match/one` - 单个匹配
- `POST /api/match/batch` - 批量匹配

#### 管理 API (Phase E)
- `GET /api/admin/stats` - 统计数据
- `GET /api/admin/medical-dict` - 词库查询
- `POST /api/admin/medical-dict` - 新增词条
- `PUT /api/admin/medical-dict/{id}` - 更新词条
- `DELETE /api/admin/medical-dict/{id}` - 删除词条
- `GET /api/admin/rule-version/history` - 版本历史

#### Agent API (Phase F)
- `POST /api/agent/analyze` - 分析未匹配项目
- `GET /api/agent/suggestions` - 获取建议列表
- `POST /api/agent/suggestions/{id}/approve` - 审批建议

#### Legacy API (Phase C - 兼容层)
- `POST /algorithm/standardCheck/match` - 旧版匹配接口
- `POST /algorithm/standardCheck/match/batch` - 旧版批量匹配
- ... (其他 4 个旧接口)

### 前端界面 (端口 3100)

1. **概览页** - 数据统计、版本信息
2. **匹配测试** - 单个匹配测试工具
3. **词库管理** - 医学词典 CRUD
4. **AI 建议** - Agent 优化建议审批（开发中）
5. **版本历史** - 规则版本演进记录（开发中）

## 部署方式

### 开发环境
```bash
# 后端
cd match_service
poetry run uvicorn match_service.main:app --reload --port 9100

# 前端
cd match_service/frontend
npm run dev  # 端口 3100，自动代理到 9100
```

### 生产环境

#### 方案 A: 单机部署
```bash
cd frontend && npm run build
cd ..
uvicorn match_service.main:app --host 0.0.0.0 --port 9100
# 访问 http://localhost:9100/ 即可（后端自动服务前端）
```

#### 方案 B: Docker
```bash
docker-compose up -d
```

#### 方案 C: 前后端分离
- 后端: Docker 容器 (9100)
- 前端: Vercel/Netlify/Nginx (静态部署)

## 与原系统的关系

### 原系统 (acrac_web_mgmt)
- **后端**: `acrac_backend/app/services/check_item_mgmt/`
- **前端**: `acrac_frontend/src/modules/check-item-mgmt/`

### 独立系统 (match_service)
- **替代**: 原后端的匹配服务
- **兼容**: Phase C 提供旧 API 兼容层
- **独立**: 完整的前后端独立部署
- **灰度**: Nginx 分流 10% → 100% 渐进切换

## 数据规模

- **医学词典**: 2,435 条
- **短语映射**: 7,839 条
- **消歧规则**: 1,229 条
- **总词表**: 11,503 条
- **代码量**: 7,700+ 行
- **测试**: 46 个（100% 通过率）

## 验证

运行完整验证：
```bash
bash scripts/verify_phases.sh
```

验证内容：
- Phase C: 灰度监控脚本
- Phase E: 管理 API + UI
- Phase F: Agent 模块
- Phase G: 多租户设计文档

## 参考文档

- [快速启动](./QUICKSTART.md)
- [完成报告](./COMPLETION_REPORT.md)
- [AI Agent 设计](./docs/PHASE_F_AGENT.md)
- [多租户设计](./docs/PHASE_G_MULTI_TENANT.md)

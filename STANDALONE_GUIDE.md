# MMS 项目独立化指南

## 背景

`match_service` 是从 `acrac_web_mgmt` 项目中独立出来的标准化匹配服务管理平台，现已完全独立，可以作为单独项目运行。

## 为什么可以移出？

### ✅ 完全技术独立
- **独立后端**: FastAPI + PostgreSQL（不依赖父项目）
- **独立前端**: React + Vite + Tailwind（独立构建）
- **独立数据库**: 自己的 PG 实例和迁移脚本
- **独立容器**: docker-compose.yml 完整定义

### ✅ 代码零耦合
```bash
# 验证无导入依赖
grep -r "from acrac_backend" src/  # 0 个结果
grep -r "from acrac_frontend" frontend/src/  # 0 个结果
```

### ✅ 文档完整
- 8 个 Markdown 文档覆盖架构/部署/测试
- 独立 QUICKSTART.md 可直接启动
- 完整的设计系统文档

---

## 方案一：保留副本（推荐）

**优点**: 保持父项目完整性，新项目独立演进  
**适用**: 需要长期独立维护

### 操作步骤

```bash
# 1. 复制到独立目录
cp -r /Users/charlieliu/git_project_vscode/09_medical/acrac_web_mgmt/match_service \
      /Users/charlieliu/git_project_vscode/09_medical/mms_standalone

# 2. 进入新目录初始化 Git
cd /Users/charlieliu/git_project_vscode/09_medical/mms_standalone
git init
git add .
git commit -m "feat: MMS 独立化 - 从 acrac_web_mgmt 分离"

# 3. 关联远程仓库（可选）
git remote add origin git@github.com:yourusername/mms-platform.git
git push -u origin main

# 4. 验证独立运行
poetry install
poetry run uvicorn src.main:app --port 9100 &
cd frontend && npm install && npm run dev
```

### 清理父项目（可选）

如果父项目不再需要 `match_service`：

```bash
cd /Users/charlieliu/git_project_vscode/09_medical/acrac_web_mgmt
git rm -r match_service
git commit -m "refactor: 移除 match_service（已独立为 mms_standalone）"
```

---

## 方案二：Git Subtree 拆分（高级）

**优点**: 保留完整历史记录  
**适用**: 需要追溯 match_service 的提交历史

```bash
# 1. 在父项目中创建 subtree
cd /Users/charlieliu/git_project_vscode/09_medical/acrac_web_mgmt
git subtree split --prefix=match_service --branch mms-standalone

# 2. 创建新仓库并推送
mkdir /Users/charlieliu/git_project_vscode/09_medical/mms_standalone
cd /Users/charlieliu/git_project_vscode/09_medical/mms_standalone
git init
git pull ../acrac_web_mgmt mms-standalone
git remote add origin <your-new-repo-url>
git push -u origin main

# 3. 从父项目删除（可选）
cd /Users/charlieliu/git_project_vscode/09_medical/acrac_web_mgmt
git rm -r match_service
git commit -m "refactor: match_service 已独立为单独仓库"
```

---

## 方案三：符号链接（临时方案）

**优点**: 不复制文件，节省空间  
**缺点**: 仍依赖父项目

```bash
ln -s /Users/charlieliu/git_project_vscode/09_medical/acrac_web_mgmt/match_service \
      /Users/charlieliu/git_project_vscode/09_medical/mms_link
```

---

## 独立项目配置清单

### 1. 环境变量 `.env`

```bash
# 数据库
DATABASE_URL=postgresql://user:pass@localhost:5432/mms_db

# 后端
API_HOST=0.0.0.0
API_PORT=9100

# 前端
VITE_API_BASE_URL=http://localhost:9100/api
```

### 2. 数据库初始化

```bash
# 创建数据库
createdb mms_db

# 运行迁移
poetry run alembic upgrade head

# 导入词表（如果需要）
psql mms_db < phase0-deliverables/lexicon_baseline.sql
```

### 3. 端口规划

| 服务 | 端口 | 说明 |
|------|------|------|
| 后端 API | 9100 | FastAPI |
| 前端开发服务器 | 3100 | Vite dev server |
| PostgreSQL | 5432 | 数据库 |

### 4. 依赖安装

```bash
# Python 依赖
poetry install

# Node 依赖
cd frontend && npm install
```

---

## 独立后的目录结构

```
mms_standalone/
├── README.md                    # 独立项目说明
├── QUICKSTART.md                # 快速启动
├── PROJECT_STRUCTURE.md         # 架构文档
├── pyproject.toml               # Python 依赖
├── docker-compose.yml           # 容器编排
├── alembic.ini                  # 数据库迁移配置
├── .env.example                 # 环境变量模板
├── src/                         # 后端源码
│   ├── main.py
│   ├── api/
│   ├── models/
│   └── services/
├── frontend/                    # 前端源码
│   ├── package.json
│   ├── vite.config.ts
│   ├── DESIGN.md                # 设计系统
│   └── src/
├── migrations/                  # 数据库迁移
├── tests/                       # 测试
├── scripts/                     # 工具脚本
└── docs/                        # 文档
```

---

## 验证独立性检查清单

- [ ] 后端无导入父项目代码
- [ ] 前端无导入父项目组件
- [ ] 数据库独立（不共享表）
- [ ] 环境变量独立配置
- [ ] Docker 容器独立启动
- [ ] 文档完整可用
- [ ] 测试全部通过

### 验证命令

```bash
# 1. 代码依赖检查
grep -r "from acrac" src/ frontend/src/ || echo "✅ 无父项目依赖"

# 2. 独立启动测试
docker-compose up -d
curl http://localhost:9100/api/health
curl http://localhost:3100

# 3. 测试覆盖率
poetry run pytest tests/ -v
```

---

## 迁移后的维护

### 版本管理

独立后建议使用语义化版本：

```
v1.0.0 - 独立化初始版本
├── Phase 0: 词表对账
├── Phase 1: 标准项目管理  
├── Phase 2: 未匹配工作台
└── Phase 3: 词库治理台
```

### 发布流程

1. **开发** → `dev` 分支
2. **测试** → `test` 分支（可选）
3. **生产** → `main` 分支 + Git Tag

### CI/CD（建议）

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: poetry install
      - run: poetry run pytest
```

---

## 常见问题

### Q1: 移出后父项目还能用吗？
**A**: 如果父项目依赖 match_service，需要先解耦或保留副本。当前检查显示父项目（acrac_backend/acrac_frontend）不依赖 match_service，可以安全移出。

### Q2: 历史提交记录会丢失吗？
**A**: 
- **方案一（复制）**: 会丢失，但可以在 README 中标注来源
- **方案二（subtree）**: 保留完整历史

### Q3: 数据需要迁移吗？
**A**: 如果生产环境使用独立数据库，数据已独立。如果共享数据库，需要：
```bash
# 导出
pg_dump -h old_host -U user -t "nlp_*" -t "da_*" old_db > data.sql
# 导入
psql -h new_host -U user new_db < data.sql
```

### Q4: 配色修订会影响父项目吗？
**A**: 不会。match_service 的前端完全独立，使用独立的 Tailwind 配置和设计系统（DESIGN.md）。

---

## 推荐行动

基于当前状态，**推荐方案一**（保留副本）：

```bash
# 一键独立化
cd /Users/charlieliu/git_project_vscode/09_medical/acrac_web_mgmt/match_service
bash scripts/make_standalone.sh
```

脚本会自动：
1. ✅ 复制到独立目录
2. ✅ 初始化 Git 仓库
3. ✅ 创建独立 README
4. ✅ 生成 .gitignore
5. ✅ 提交初始版本

---

## 参考资料

- [Git Subtree 官方文档](https://git-scm.com/docs/git-subtree)
- [项目结构设计](./PROJECT_STRUCTURE.md)
- [迁移完成报告](./MIGRATION_COMPLETE.md)
- [前端设计系统](./frontend/DESIGN.md)

---

**创建日期**: 2026-07-28  
**状态**: ✅ 可以安全移出  
**建议操作**: 方案一（保留副本）

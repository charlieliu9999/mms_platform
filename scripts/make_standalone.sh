#!/bin/bash
# match_service 独立化脚本

set -e

echo "=== MMS 标准化匹配服务独立化 ==="

# 1. 创建目标目录
TARGET_DIR="/Users/charlieliu/git_project_vscode/09_medical/mms_standalone"
mkdir -p "$TARGET_DIR"

# 2. 复制 match_service 目录
echo "复制 match_service 到独立目录..."
cp -r match_service/* "$TARGET_DIR/"

# 3. 创建独立 Git 仓库
cd "$TARGET_DIR"
git init
git add .
git commit -m "feat: MMS 标准化匹配服务独立化

- 从 acrac_web_mgmt 项目中独立出来
- 完整的前后端代码
- 独立的数据库迁移
- 完整的文档体系
- 统一的配色设计系统

包含功能:
- Phase 0: 词表对账
- Phase 1: 标准项目管理
- Phase 2: 未匹配工作台
- Phase 3: 词库治理台
- Phase A: 匹配引擎 V2"

# 4. 创建 .gitignore
cat > .gitignore << 'EOF'
# Python
.venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info/
dist/
build/

# FastAPI
.env
*.db

# Node
node_modules/
dist/
.DS_Store

# IDE
.vscode/
.idea/

# Logs
logs/*.log
logs/*.pid
!logs/.gitkeep

# Test
.pytest_cache/
.coverage
htmlcov/

# Benchmarks
.benchmarks/
EOF

# 5. 创建独立 README
cat > README.md << 'EOF'
# MMS 标准化匹配服务管理平台

Medical Matching Service - 医学检查项目标准化匹配服务的管理平台

## 项目简介

MMS 是从 ACR AC 项目中独立出来的标准化匹配服务，负责将医院原始医嘱匹配到标准检查项目。

### 核心功能

- **词库治理台**: 管理医学词典、别名映射、消歧规则
- **标准项目管理**: 维护 1882 个标准检查项目
- **未匹配工作台**: 处理匹配失败的案例
- **匹配引擎 V2**: 10步结构化 NLP 匹配算法

### 技术栈

- **后端**: FastAPI + PostgreSQL + SQLAlchemy
- **前端**: React 18 + TypeScript + Tailwind CSS 4 + Ant Design 5
- **部署**: Docker Compose

## 快速启动

详见 [QUICKSTART.md](./QUICKSTART.md)

```bash
# 后端
cd match_service
poetry install
poetry run uvicorn src.main:app --reload --port 9100

# 前端
cd frontend
npm install
npm run dev  # http://localhost:3100
```

## 文档

- [项目结构](./PROJECT_STRUCTURE.md)
- [快速启动](./QUICKSTART.md)
- [迁移完成报告](./MIGRATION_COMPLETE.md)
- [最终测试总结](./FINAL_TEST_SUMMARY.md)
- [前端设计系统](./frontend/DESIGN.md)
- [配色统一修订](./frontend/DESIGN_REVISION.md)

## 部署

### 开发环境
```bash
docker-compose up -d
```

### 生产环境
参见 [PHASE_B_DEPLOYMENT.md](./PHASE_B_DEPLOYMENT.md)

## License

Proprietary - 仅供内部使用
EOF

echo "✅ 独立化完成！"
echo "新项目路径: $TARGET_DIR"
echo ""
echo "后续步骤:"
echo "1. cd $TARGET_DIR"
echo "2. git remote add origin <your-git-repo-url>"
echo "3. git push -u origin main"

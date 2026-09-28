#!/bin/bash
# 将 match_service 初始化为独立 Git 仓库

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}初始化 MMS 独立 Git 仓库${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查是否已经是独立仓库
if [ -d ".git" ]; then
    echo -e "${RED}✗ 当前目录已经是 Git 仓库${NC}"
    echo "如果要重新初始化，请先删除 .git 目录"
    exit 1
fi

# 初始化 Git
echo -e "${GREEN}[1/5] 初始化 Git 仓库...${NC}"
git init
echo ""

# 创建 .gitignore
echo -e "${GREEN}[2/5] 创建 .gitignore...${NC}"
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
env/
venv/
ENV/
build/
dist/
*.egg-info/
.pytest_cache/
.coverage
htmlcov/

# Frontend
frontend/node_modules/
frontend/dist/
frontend/.env.local
frontend/.env.production.local
frontend/npm-debug.log*
frontend/yarn-debug.log*
frontend/yarn-error.log*

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
logs/
*.log

# Database
*.db
*.sqlite

# Environment
.env
.env.local
.env.*.local

# Alembic
alembic.ini.local
EOF
echo "  ✓ .gitignore 已创建"
echo ""

# 添加所有文件
echo -e "${GREEN}[3/5] 添加文件到 Git...${NC}"
git add .
echo "  ✓ 文件已添加"
echo ""

# 首次提交
echo -e "${GREEN}[4/5] 创建首次提交...${NC}"
git commit -m "feat: MMS 标准化匹配服务初始化

技术栈:
- 后端: FastAPI + SQLAlchemy + PostgreSQL
- 前端: React 18 + TypeScript + Ant Design 5 + Vite 5

核心功能:
- 匹配引擎: NLP Pipeline (CT/MR/DR/RF/MG) + 关键词引擎 (US/SPECT/PET)
- 管理 API: 词库 CRUD + 统计数据 + 版本历史
- 前端界面: 概览/匹配测试/词库管理/AI建议/版本历史
- AI Agent: 未匹配分析 + 优化建议审批
- 兼容层: Legacy API 支持旧服务平替
- 灰度部署: Nginx 流量分流配置

项目规模:
- 代码量: 13,000+ 行 (后端 7,700+ | 前端 6,149)
- 测试: 46 个单元测试 (100% 通过率)
- 词表: 11,503 条 (医学词典 2,435 | 短语映射 7,839 | 消歧规则 1,229)

部署:
- 开发: scripts/start.sh (前后端同时启动)
- 测试: scripts/test-all.sh (完整测试套件)
- 生产: Docker / 后端挂载前端 / 前后端分离

文档:
- QUICKSTART.md: 快速启动指南
- PROJECT_STRUCTURE.md: 项目结构说明
- COMPLETION_REPORT.md: 项目完成报告
- docs/PHASE_F_AGENT.md: AI Agent 设计
- docs/PHASE_G_MULTI_TENANT.md: 多租户设计

完成阶段:
✓ Phase 0-4: 词表裁定 (186/186)
✓ Phase A: 引擎物理独立 (4,772 行迁移)
✓ Phase B: 新库构建 + Docker
✓ Phase C: 兼容层 + 灰度部署
✓ Phase D: 配置层独立化
✓ Phase E: 管理前端
✓ Phase F: AI Agent 集成
✓ Phase G: 多租户设计

From: acrac_web_mgmt/match_service
Extracted: 2026-07-28"

echo "  ✓ 首次提交完成"
echo ""

# 显示状态
echo -e "${GREEN}[5/5] 仓库状态...${NC}"
git log --oneline -1
echo ""
COMMIT_COUNT=$(git rev-list --count HEAD)
FILE_COUNT=$(git ls-files | wc -l)
echo "  提交数: $COMMIT_COUNT"
echo "  文件数: $FILE_COUNT"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Git 仓库初始化完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "下一步:"
echo "  1. 添加远程仓库: git remote add origin <your-repo-url>"
echo "  2. 推送到远程: git push -u origin main"
echo ""
echo "或者创建 GitHub 仓库:"
echo "  gh repo create medical-match-service --public --source=. --push"
echo ""

#!/bin/bash
# MMS Platform - 手动部署到 VPS
# 用法: ./scripts/manual_deploy_to_vps.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# VPS 配置
VPS_HOST="220.154.3.166"
VPS_USER="root"
VPS_PASSWORD="${VPS_PASSWORD:-}"
DEPLOY_PATH="/data/mms-platform"
BACKEND_PORT="9100"
FRONTEND_PORT="3100"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          MMS Platform - 手动部署到 VPS                         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# 检查环境变量
if [ -z "$VPS_PASSWORD" ]; then
    echo -e "${RED}错误: 请设置环境变量 VPS_PASSWORD${NC}"
    echo "示例: export VPS_PASSWORD='你的密码'"
    exit 1
fi

# 检查 sshpass
if ! command -v sshpass &> /dev/null; then
    echo -e "${RED}错误: 需要安装 sshpass${NC}"
    echo "安装: brew install hudochenkov/sshpass/sshpass"
    exit 1
fi

# 1. 备份 VPS 上的 .env 文件
echo -e "${YELLOW}[1/6] 备份 VPS 配置文件${NC}"
sshpass -p "${VPS_PASSWORD}" ssh -o StrictHostKeyChecking=no \
  ${VPS_USER}@${VPS_HOST} \
  "cd ${DEPLOY_PATH} && cp .env .env.backup.\$(date +%Y%m%d_%H%M%S) 2>/dev/null || true"
echo -e "${GREEN}✓ 备份完成${NC}"
echo ""

# 2. 同步代码到 VPS
echo -e "${YELLOW}[2/6] 同步代码到 VPS${NC}"
sshpass -p "${VPS_PASSWORD}" rsync -avz --progress \
  --exclude='.git/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.venv/' \
  --exclude='venv/' \
  --exclude='node_modules/' \
  --exclude='.idea/' \
  --exclude='.vscode/' \
  --exclude='.claude/' \
  --exclude='.DS_Store' \
  --exclude='.env' \
  --exclude='.env.local' \
  --exclude='.env.development' \
  --include='.env.production' \
  --exclude='.pytest_cache/' \
  --exclude='scratch/' \
  --exclude='frontend/node_modules/' \
  --exclude='frontend/dist/' \
  -e "ssh -o StrictHostKeyChecking=no" \
  ./ \
  ${VPS_USER}@${VPS_HOST}:${DEPLOY_PATH}/
echo -e "${GREEN}✓ 代码同步完成${NC}"
echo ""

# 3. 在 VPS 上构建前端
echo -e "${YELLOW}[3/6] 在 VPS 上构建前端${NC}"
sshpass -p "${VPS_PASSWORD}" ssh -o StrictHostKeyChecking=no \
  ${VPS_USER}@${VPS_HOST} \
  "cd ${DEPLOY_PATH}/frontend && npm install && npm run build"
echo -e "${GREEN}✓ 前端构建完成${NC}"
echo ""

# 4. 重启后端服务
echo -e "${YELLOW}[4/6] 重启后端服务${NC}"
sshpass -p "${VPS_PASSWORD}" ssh -o StrictHostKeyChecking=no \
  ${VPS_USER}@${VPS_HOST} \
  "cd ${DEPLOY_PATH} && \
   docker compose build backend && \
   docker compose up -d backend && \
   sleep 10"
echo -e "${GREEN}✓ 后端服务已重启${NC}"
echo ""

# 5. 重启前端服务
echo -e "${YELLOW}[5/6] 重启前端服务${NC}"
sshpass -p "${VPS_PASSWORD}" ssh -o StrictHostKeyChecking=no \
  ${VPS_USER}@${VPS_HOST} \
  "cd ${DEPLOY_PATH} && docker compose up -d frontend && sleep 5"
echo -e "${GREEN}✓ 前端服务已重启${NC}"
echo ""

# 6. 健康检查
echo -e "${YELLOW}[6/6] 健康检查${NC}"

# 检查后端
if sshpass -p "${VPS_PASSWORD}" ssh -o StrictHostKeyChecking=no \
  ${VPS_USER}@${VPS_HOST} \
  "curl -sf http://localhost:${BACKEND_PORT}/health" > /dev/null; then
    echo -e "${GREEN}✓ 后端服务健康检查通过${NC}"
else
    echo -e "${RED}✗ 后端服务健康检查失败${NC}"
fi

# 检查前端
if sshpass -p "${VPS_PASSWORD}" ssh -o StrictHostKeyChecking=no \
  ${VPS_USER}@${VPS_HOST} \
  "curl -sf http://localhost:${FRONTEND_PORT}/" > /dev/null; then
    echo -e "${GREEN}✓ 前端服务健康检查通过${NC}"
else
    echo -e "${RED}✗ 前端服务健康检查失败${NC}"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    部署完成                                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ 访问地址:"
echo "  - 后端 API: http://${VPS_HOST}:${BACKEND_PORT}"
echo "  - 前端界面: http://${VPS_HOST}:${FRONTEND_PORT}"
echo ""
echo "📝 验证步骤:"
echo "  1. 检查 PET/CT 和 PET/MR 统计数据是否正确显示"
echo "  2. 测试版本号大小写处理: v3.8.2 vs V3.8.2"
echo "  3. 验证标准项目查询功能"
echo ""

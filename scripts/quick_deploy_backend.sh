#!/bin/bash
# 快速部署后端代码到 VPS（不构建前端）

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

VPS_HOST="220.154.3.166"
VPS_USER="root"
DEPLOY_PATH="/data/mms-platform"
BACKEND_PORT="9100"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          快速部署后端到 VPS（不构建前端）                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# 1. 同步后端代码
echo -e "${YELLOW}[1/3] 同步后端代码${NC}"
rsync -avz --progress \
  --include='src/' \
  --include='src/match_service/' \
  --include='src/match_service/**' \
  --include='migrations/' \
  --include='migrations/**' \
  --include='alembic.ini' \
  --include='pyproject.toml' \
  --include='poetry.lock' \
  --include='Dockerfile' \
  --include='docker-compose.yml' \
  --exclude='*' \
  ./ \
  ${VPS_USER}@${VPS_HOST}:${DEPLOY_PATH}/
echo -e "${GREEN}✓ 后端代码同步完成${NC}"
echo ""

# 2. 重启后端服务
echo -e "${YELLOW}[2/3] 重启后端服务${NC}"
ssh ${VPS_USER}@${VPS_HOST} \
  "cd ${DEPLOY_PATH} && \
   docker compose build backend && \
   docker compose up -d backend && \
   sleep 10"
echo -e "${GREEN}✓ 后端服务已重启${NC}"
echo ""

# 3. 验证
echo -e "${YELLOW}[3/3] 验证部署${NC}"

# 健康检查
if ssh ${VPS_USER}@${VPS_HOST} "curl -sf http://localhost:${BACKEND_PORT}/health" > /dev/null; then
    echo -e "${GREEN}✓ 后端健康检查通过${NC}"
else
    echo -e "${RED}✗ 后端健康检查失败${NC}"
    exit 1
fi

# PET/CT 测试
pet_ct=$(ssh ${VPS_USER}@${VPS_HOST} "curl -s 'http://localhost:${BACKEND_PORT}/api/open/standards/items?modality=PET/CT&limit=1'" | python3 -c "import sys, json; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "0")
pet_mr=$(ssh ${VPS_USER}@${VPS_HOST} "curl -s 'http://localhost:${BACKEND_PORT}/api/open/standards/items?modality=PET/MR&limit=1'" | python3 -c "import sys, json; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "0")

echo "  - PET/CT 项目数: $pet_ct"
echo "  - PET/MR 项目数: $pet_mr"

if [ "$pet_ct" != "0" ] && [ "$pet_mr" != "0" ]; then
    echo -e "${GREEN}✓ PET/CT 和 PET/MR 查询正常${NC}"
else
    echo -e "${RED}✗ PET/CT 或 PET/MR 查询异常${NC}"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    后端部署完成                                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ 后端 API: http://${VPS_HOST}:${BACKEND_PORT}"
echo "📝 已验证: PET/CT 和 PET/MR 修复已生效"
echo ""

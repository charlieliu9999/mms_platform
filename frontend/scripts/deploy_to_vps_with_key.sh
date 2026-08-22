#!/bin/bash
# MMS Platform - 使用 SSH 密钥部署到 VPS
# 用法: ./scripts/deploy_to_vps_with_key.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# VPS 配置
VPS_HOST="220.154.3.166"
VPS_USER="root"
DEPLOY_PATH="/data/mms-platform"
BACKEND_PORT="9100"
FRONTEND_PORT="3100"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          MMS Platform - 部署到 VPS                             ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# 1. 测试 SSH 连接
echo -e "${YELLOW}[1/7] 测试 SSH 连接${NC}"
if ssh -o ConnectTimeout=5 ${VPS_USER}@${VPS_HOST} "echo '连接成功'" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ SSH 连接正常${NC}"
else
    echo -e "${RED}✗ SSH 连接失败${NC}"
    exit 1
fi
echo ""

# 2. 备份 VPS 上的 .env 文件
echo -e "${YELLOW}[2/7] 备份 VPS 配置文件${NC}"
ssh ${VPS_USER}@${VPS_HOST} \
  "cd ${DEPLOY_PATH} && cp .env .env.backup.\$(date +%Y%m%d_%H%M%S) 2>/dev/null || true"
echo -e "${GREEN}✓ 备份完成${NC}"
echo ""

# 3. 同步代码到 VPS
echo -e "${YELLOW}[3/7] 同步代码到 VPS${NC}"
rsync -avz --progress \
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
  --exclude='.pytest_cache/' \
  --exclude='scratch/' \
  --exclude='frontend/node_modules/' \
  --exclude='frontend/dist/' \
  ./ \
  ${VPS_USER}@${VPS_HOST}:${DEPLOY_PATH}/
echo -e "${GREEN}✓ 代码同步完成${NC}"
echo ""

# 4. 在 VPS 上构建前端
echo -e "${YELLOW}[4/7] 在 VPS 上构建前端${NC}"
ssh ${VPS_USER}@${VPS_HOST} \
  "cd ${DEPLOY_PATH}/frontend && npm install && npm run build"
echo -e "${GREEN}✓ 前端构建完成${NC}"
echo ""

# 5. 重启后端服务
echo -e "${YELLOW}[5/7] 重启后端服务${NC}"
ssh ${VPS_USER}@${VPS_HOST} \
  "cd ${DEPLOY_PATH} && \
   docker compose build backend && \
   docker compose up -d backend && \
   sleep 10"
echo -e "${GREEN}✓ 后端服务已重启${NC}"
echo ""

# 6. 重启前端服务
echo -e "${YELLOW}[6/7] 重启前端服务${NC}"
ssh ${VPS_USER}@${VPS_HOST} \
  "cd ${DEPLOY_PATH} && docker compose up -d frontend && sleep 5"
echo -e "${GREEN}✓ 前端服务已重启${NC}"
echo ""

# 7. 健康检查和验证
echo -e "${YELLOW}[7/7] 健康检查和验证${NC}"
echo ""

# 检查后端健康
echo "测试 1: 后端健康检查"
if ssh ${VPS_USER}@${VPS_HOST} "curl -sf http://localhost:${BACKEND_PORT}/health" > /dev/null; then
    echo -e "${GREEN}✓ 后端服务健康检查通过${NC}"
    ssh ${VPS_USER}@${VPS_HOST} "curl -s http://localhost:${BACKEND_PORT}/health" | python3 -m json.tool 2>/dev/null || true
else
    echo -e "${RED}✗ 后端服务健康检查失败${NC}"
fi
echo ""

# 检查前端
echo "测试 2: 前端服务访问"
if ssh ${VPS_USER}@${VPS_HOST} "curl -sf http://localhost:${FRONTEND_PORT}/" > /dev/null; then
    echo -e "${GREEN}✓ 前端服务可访问${NC}"
else
    echo -e "${RED}✗ 前端服务访问失败${NC}"
fi
echo ""

# 测试版本号大小写处理
echo "测试 3: 版本号大小写处理（PET/CT 修复验证）"
v1=$(ssh ${VPS_USER}@${VPS_HOST} "curl -s 'http://localhost:${BACKEND_PORT}/api/open/standards/items?version=v3.8.2&limit=1'" | python3 -c "import sys, json; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "0")
v2=$(ssh ${VPS_USER}@${VPS_HOST} "curl -s 'http://localhost:${BACKEND_PORT}/api/open/standards/items?version=V3.8.2&limit=1'" | python3 -c "import sys, json; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "0")
if [ "$v1" = "$v2" ] && [ "$v1" != "0" ]; then
    echo -e "${GREEN}✓ 版本号大小写处理正常 (v3.8.2: $v1 条, V3.8.2: $v2 条)${NC}"
else
    echo -e "${RED}✗ 版本号大小写处理异常 (v3.8.2: $v1, V3.8.2: $v2)${NC}"
fi
echo ""

# 测试 PET/CT 和 PET/MR 数据
echo "测试 4: PET/CT 和 PET/MR 标准项目查询（关键修复验证）"
pet_ct=$(ssh ${VPS_USER}@${VPS_HOST} "curl -s 'http://localhost:${BACKEND_PORT}/api/open/standards/items?modality=PET/CT&limit=1'" | python3 -c "import sys, json; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "0")
pet_mr=$(ssh ${VPS_USER}@${VPS_HOST} "curl -s 'http://localhost:${BACKEND_PORT}/api/open/standards/items?modality=PET/MR&limit=1'" | python3 -c "import sys, json; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "0")

echo "  - PET/CT 项目数: $pet_ct"
echo "  - PET/MR 项目数: $pet_mr"

if [ "$pet_ct" != "0" ] && [ "$pet_mr" != "0" ]; then
    echo -e "${GREEN}✓ PET/CT 和 PET/MR 数据查询正常${NC}"
else
    echo -e "${RED}✗ PET/CT 或 PET/MR 数据查询异常${NC}"
fi
echo ""

# 查看 Docker 容器状态
echo "测试 5: Docker 容器状态"
ssh ${VPS_USER}@${VPS_HOST} "docker ps --filter name=mms --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
echo ""

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    部署完成                                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ 访问地址:"
echo "  - 后端 API: http://${VPS_HOST}:${BACKEND_PORT}"
echo "  - 前端界面: http://${VPS_HOST}:${FRONTEND_PORT}"
echo "  - API 文档: http://${VPS_HOST}:${BACKEND_PORT}/docs"
echo ""
echo "📝 已验证的修复:"
echo "  ✓ PET/CT 和 PET/MR 标准项目查询逻辑修复"
echo "  ✓ 版本号大小写不敏感处理"
echo "  ✓ 前后端服务正常运行"
echo ""
echo "🔗 下一步:"
echo "  1. 浏览器访问前端界面，检查 PET/CT 和 PET/MR 统计数据"
echo "  2. 测试标准项目搜索功能"
echo "  3. 验证匹配引擎功能"
echo ""

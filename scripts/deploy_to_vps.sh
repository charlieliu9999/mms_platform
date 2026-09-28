#!/bin/bash
# MMS Platform VPS 部署脚本

set -e  # 遇到错误立即退出

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          MMS Platform - VPS 自动部署脚本                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# 1. 检查当前目录
echo -e "${YELLOW}[1/8] 检查当前目录${NC}"
if [ ! -f "src/match_service/main.py" ]; then
    echo -e "${RED}错误: 请在项目根目录运行此脚本${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 当前目录正确${NC}"
echo ""

# 2. 拉取最新代码
echo -e "${YELLOW}[2/8] 拉取最新代码${NC}"
git pull origin main
echo -e "${GREEN}✓ 代码更新完成${NC}"
echo ""

# 3. 显示最新提交
echo -e "${YELLOW}[3/8] 最新提交记录${NC}"
git log -5 --oneline
echo ""

# 4. 重新构建前端
echo -e "${YELLOW}[4/8] 重新构建前端${NC}"
cd frontend
npm run build
echo -e "${GREEN}✓ 前端构建完成${NC}"
cd ..
echo ""

# 5. 检查 Docker 状态
echo -e "${YELLOW}[5/8] 检查 Docker 服务${NC}"
docker ps | grep mms || echo "Docker 容器未运行"
echo ""

# 6. 重启后端服务
echo -e "${YELLOW}[6/8] 重启后端服务${NC}"
echo "选择重启方式:"
echo "  1) docker-compose restart backend (快速重启)"
echo "  2) docker-compose down && docker-compose up -d --build (完全重建)"
echo "  3) 跳过重启"
read -p "请选择 [1-3]: " choice

case $choice in
    1)
        docker-compose restart backend
        echo -e "${GREEN}✓ 后端服务已重启${NC}"
        ;;
    2)
        docker-compose down
        docker-compose up -d --build
        echo -e "${GREEN}✓ 后端服务已重建${NC}"
        ;;
    3)
        echo -e "${YELLOW}跳过重启${NC}"
        ;;
    *)
        echo -e "${RED}无效选择，跳过重启${NC}"
        ;;
esac
echo ""

# 7. 等待服务启动
echo -e "${YELLOW}[7/8] 等待服务启动${NC}"
echo "等待 5 秒..."
sleep 5
echo -e "${GREEN}✓ 服务应该已启动${NC}"
echo ""

# 8. 运行验证测试
echo -e "${YELLOW}[8/8] 运行验证测试${NC}"
echo ""

# 测试健康检查
echo "测试 1: 健康检查端点"
curl -s http://localhost:9100/health | python3 -m json.tool 2>/dev/null || echo "健康检查失败"
echo ""

# 测试 API 信息
echo "测试 2: API 信息端点"
curl -s http://localhost:9100/api | python3 -m json.tool 2>/dev/null || echo "API 信息获取失败"
echo ""

# 测试版本号大小写
echo "测试 3: 版本号大小写处理"
v1=$(curl -s "http://localhost:9100/api/open/standards/items?version=v3.8.2" | python3 -c "import sys, json; print(json.load(sys.stdin)['total'])" 2>/dev/null)
v2=$(curl -s "http://localhost:9100/api/open/standards/items?version=V3.8.2" | python3 -c "import sys, json; print(json.load(sys.stdin)['total'])" 2>/dev/null)
if [ "$v1" = "$v2" ] && [ -n "$v1" ]; then
    echo -e "${GREEN}✓ 版本号大小写处理正常 (v3.8.2: $v1 条, V3.8.2: $v2 条)${NC}"
else
    echo -e "${RED}✗ 版本号大小写处理异常${NC}"
fi
echo ""

# 运行完整测试套件
echo "运行完整测试套件？"
read -p "是否运行完整测试 [y/N]: " run_full_test
if [ "$run_full_test" = "y" ] || [ "$run_full_test" = "Y" ]; then
    if [ -f "scripts/test_vps_api.sh" ]; then
        ./scripts/test_vps_api.sh http://localhost:9100
    else
        echo "测试脚本不存在"
    fi
    
    if [ -f "scripts/test_version_case_insensitive.sh" ]; then
        ./scripts/test_version_case_insensitive.sh http://localhost:9100
    else
        echo "版本号测试脚本不存在"
    fi
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    部署完成                                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ 部署检查清单:"
echo "  - [ ] /health 端点返回健康状态"
echo "  - [ ] /api 端点返回端点列表"
echo "  - [ ] 版本号大小写处理正常"
echo "  - [ ] 前端页面可以访问"
echo "  - [ ] PET/CT 和 PET/MR 统计数据正确"
echo ""
echo "📚 参考文档:"
echo "  - docs/deployment-guide.md"
echo "  - docs/api-endpoints.md"
echo "  - docs/version-case-insensitive.md"
echo ""

#!/bin/bash
# MMS 一键启动脚本
# 用途: 开发环境快速启动前后端服务

set -e

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}MMS 标准化匹配服务 - 一键启动${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查环境
check_requirements() {
    echo -e "${GREEN}[1/5] 检查环境依赖...${NC}"

    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}✗ Python 3 未安装${NC}"
        exit 1
    fi
    echo "  ✓ Python: $(python3 --version)"

    # 检查 Poetry
    if ! command -v poetry &> /dev/null; then
        echo -e "${RED}✗ Poetry 未安装，请运行: pip install poetry${NC}"
        exit 1
    fi
    echo "  ✓ Poetry: $(poetry --version)"

    # 检查 Node.js
    if ! command -v node &> /dev/null; then
        echo -e "${RED}✗ Node.js 未安装${NC}"
        exit 1
    fi
    echo "  ✓ Node.js: $(node --version)"

    # 检查 npm
    if ! command -v npm &> /dev/null; then
        echo -e "${RED}✗ npm 未安装${NC}"
        exit 1
    fi
    echo "  ✓ npm: $(npm --version)"
    echo ""
}

# 安装后端依赖
install_backend() {
    echo -e "${GREEN}[2/5] 安装后端依赖...${NC}"
    if [ ! -d ".venv" ]; then
        poetry install
    else
        echo "  ✓ 后端依赖已安装（跳过）"
    fi
    echo ""
}

# 安装前端依赖
install_frontend() {
    echo -e "${GREEN}[3/5] 安装前端依赖...${NC}"
    cd frontend
    if [ ! -d "node_modules" ]; then
        npm install
    else
        echo "  ✓ 前端依赖已安装（跳过）"
    fi
    cd ..
    echo ""
}

# 检查数据库
check_database() {
    echo -e "${GREEN}[4/5] 检查数据库连接...${NC}"

    # 尝试连接数据库
    poetry run python -c "
from match_service.db import get_engine
import asyncio

async def test():
    engine = get_engine()
    try:
        async with engine.begin() as conn:
            await conn.execute('SELECT 1')
        print('  ✓ 数据库连接成功')
        return True
    except Exception as e:
        print(f'  ⚠ 数据库连接失败（将回退内置规则引擎运行）')
        return False
    finally:
        await engine.dispose()

asyncio.run(test())
" || true
    echo ""
}


# 启动服务
start_services() {
    echo -e "${GREEN}[5/5] 启动服务...${NC}"
    echo ""

    # 创建日志目录
    mkdir -p logs

    # 启动后端
    echo -e "${BLUE}启动后端服务 (端口 9100)...${NC}"
    PYTHONPATH=src poetry run uvicorn match_service.main:app \
        --host 0.0.0.0 \
        --port 9100 \
        --reload \
        > logs/backend.log 2>&1 &
    BACKEND_PID=$!
    echo "  后端 PID: $BACKEND_PID"
    echo "  日志文件: logs/backend.log"
    sleep 3

    # 检查后端是否启动成功（健康检查真实路径为 /api/health，-f 确保 4xx/5xx 判定为失败）
    if curl -sf http://localhost:9100/api/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ 后端启动成功${NC}"
    else
        echo -e "  ${RED}✗ 后端启动失败，请查看日志${NC}"
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi

    # 启动前端
    echo ""
    echo -e "${BLUE}启动前端服务 (端口 3100)...${NC}"
    cd frontend
    npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
    echo "  前端 PID: $FRONTEND_PID"
    echo "  日志文件: logs/frontend.log"
    sleep 5

    # 保存 PID
    echo "$BACKEND_PID" > logs/backend.pid
    echo "$FRONTEND_PID" > logs/frontend.pid

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}服务已启动！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "  后端 API:  http://localhost:9100"
    echo "  API 文档:  http://localhost:9100/docs"
    echo "  前端界面:  http://localhost:3100"
    echo ""
    echo "查看日志:"
    echo "  后端: tail -f logs/backend.log"
    echo "  前端: tail -f logs/frontend.log"
    echo ""
    echo "停止服务:"
    echo "  ./scripts/stop.sh"
    echo ""
}

# 主流程
main() {
    check_requirements
    install_backend
    install_frontend
    check_database
    start_services
}

main

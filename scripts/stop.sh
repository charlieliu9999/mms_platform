#!/bin/bash
# MMS 停止脚本

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "停止 MMS 服务..."

# 读取 PID
if [ -f "logs/backend.pid" ]; then
    BACKEND_PID=$(cat logs/backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID
        echo -e "${GREEN}✓ 后端服务已停止 (PID: $BACKEND_PID)${NC}"
    else
        echo "  后端服务未运行"
    fi
    rm logs/backend.pid
fi

if [ -f "logs/frontend.pid" ]; then
    FRONTEND_PID=$(cat logs/frontend.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID
        echo -e "${GREEN}✓ 前端服务已停止 (PID: $FRONTEND_PID)${NC}"
    else
        echo "  前端服务未运行"
    fi
    rm logs/frontend.pid
fi

# 强制清理可能残留的进程
pkill -f "uvicorn match_service.main:app" 2>/dev/null || true
pkill -f "vite.*--port 3100" 2>/dev/null || true

echo "所有服务已停止"

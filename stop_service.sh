#!/bin/bash
# mms_platform 后端服务停止脚本

PROJECT_DIR="/Users/charlieliu/git_project_vscode/09_medical/mms_platform"
PID_FILE="$PROJECT_DIR/.service.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "❌ 未找到 PID 文件，可能服务未运行"

    # 尝试查找并停止所有相关进程
    PIDS=$(ps aux | grep -E "uvicorn.*match_service" | grep -v grep | awk '{print $2}')
    if [ -n "$PIDS" ]; then
        echo "发现运行中的服务进程，停止中..."
        echo "$PIDS" | xargs kill
        echo "✅ 已停止所有相关进程"
    fi
    exit 0
fi

PID=$(cat "$PID_FILE")

if ps -p $PID > /dev/null 2>&1; then
    echo "🛑 停止服务 (PID: $PID)..."
    kill $PID
    sleep 2

    # 强制停止（如果还在运行）
    if ps -p $PID > /dev/null 2>&1; then
        echo "   强制停止..."
        kill -9 $PID
    fi

    echo "✅ 服务已停止"
else
    echo "⚠️  进程 $PID 不存在"
fi

rm -f "$PID_FILE"

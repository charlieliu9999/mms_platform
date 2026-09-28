#!/bin/bash
# mms_platform 后端服务启动脚本

PROJECT_DIR="/Users/charlieliu/git_project_vscode/09_medical/mms_platform"
LOG_DIR="$PROJECT_DIR/logs"
PID_FILE="$PROJECT_DIR/.service.pid"

# 确保日志目录存在
mkdir -p "$LOG_DIR"

# 检查是否已经在运行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ 服务已在运行 (PID: $PID)"
        exit 0
    else
        echo "⚠️  PID 文件存在但进程不存在，清理中..."
        rm -f "$PID_FILE"
    fi
fi

echo "🚀 启动 mms_platform 后端服务..."
cd "$PROJECT_DIR"

# 使用 poetry 启动服务
nohup poetry run uvicorn match_service.main:app \
    --host 0.0.0.0 \
    --port 9100 \
    --reload \
    > "$LOG_DIR/service.log" 2>&1 &

SERVICE_PID=$!
echo $SERVICE_PID > "$PID_FILE"

echo "✅ 服务已启动"
echo "   PID: $SERVICE_PID"
echo "   日志: $LOG_DIR/service.log"
echo "   API: http://127.0.0.1:9100/docs"

# 等待服务启动
sleep 3

# 验证服务
if curl -s http://127.0.0.1:9100/api/open/standards/versions > /dev/null 2>&1; then
    echo "✅ 服务健康检查通过"
else
    echo "⚠️  服务可能未正常启动，请检查日志"
fi

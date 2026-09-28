# mms_platform 服务管理

## 快速启动

```bash
# 启动服务
./start_service.sh

# 停止服务
./stop_service.sh

# 查看日志
tail -f logs/service.log
```

## 服务信息

- **端口**: 9100
- **API 文档**: http://127.0.0.1:9100/docs
- **健康检查**: http://127.0.0.1:9100/api/open/standards/versions

## 开机自启动（可选）

### macOS (launchd)

创建 plist 文件：

```bash
cat > ~/Library/LaunchAgents/com.rimag.mms-platform.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.rimag.mms-platform</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/charlieliu/git_project_vscode/09_medical/mms_platform/start_service.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/charlieliu/git_project_vscode/09_medical/mms_platform/logs/launchd.out.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/charlieliu/git_project_vscode/09_medical/mms_platform/logs/launchd.err.log</string>
</dict>
</plist>
EOF

# 加载服务
launchctl load ~/Library/LaunchAgents/com.rimag.mms-platform.plist

# 启动服务
launchctl start com.rimag.mms-platform
```

停用自启动：

```bash
launchctl unload ~/Library/LaunchAgents/com.rimag.mms-platform.plist
```

### Docker Compose（推荐）

```yaml
# docker-compose.yml
version: '3.8'

services:
  mms-platform:
    build: .
    ports:
      - "9100:9100"
    environment:
      - MATCH_SVC_DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/acrac_db
      - MATCH_SVC_REDIS_URL=redis://redis:6379/1
    depends_on:
      - db
      - redis
    restart: always

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: acrac_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "15432:5432"

  redis:
    image: redis:7
    ports:
      - "16379:6379"

volumes:
  pgdata:
```

启动：

```bash
docker-compose up -d
```

## 故障排查

### 服务无法启动

1. 检查端口占用：
   ```bash
   lsof -i :9100
   ```

2. 查看日志：
   ```bash
   tail -f logs/service.log
   ```

3. 检查数据库连接：
   ```bash
   cat .env | grep DATABASE_URL
   ```

### 服务运行但无响应

1. 测试 API：
   ```bash
   curl http://127.0.0.1:9100/api/open/standards/versions
   ```

2. 重启服务：
   ```bash
   ./stop_service.sh && ./start_service.sh
   ```

## 监控

查看服务状态：

```bash
# 检查进程
ps aux | grep uvicorn

# 检查 PID 文件
cat .service.pid

# 实时日志
tail -f logs/service.log
```

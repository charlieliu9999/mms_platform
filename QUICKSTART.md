# MMS 项目启动指南

## 架构

```
match_service/
├── backend/              # FastAPI 后端 (端口 9100)
│   ├── src/
│   ├── tests/
│   └── pyproject.toml
└── frontend/             # React 前端 (端口 3100)
    ├── src/
    ├── package.json
    └── vite.config.ts
```

## 快速启动

### 1. 后端启动

```bash
cd match_service
poetry install
poetry run alembic upgrade head
poetry run uvicorn match_service.main:app --host 0.0.0.0 --port 9100 --reload
```

访问: http://localhost:9100/docs (API 文档)

### 2. 前端启动

```bash
cd match_service/frontend
npm install
npm run dev
```

访问: http://localhost:3100 (管理平台)

## 开发模式

前端 Vite 已配置代理，`/api/*` 请求自动转发到后端 9100 端口。

## 生产部署

### 方案 A: 单机部署（后端服务静态文件）

1. 构建前端
```bash
cd frontend
npm run build
# 输出到 frontend/dist/
```

2. 后端挂载静态文件（需修改 main.py）
```python
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
```

3. 启动后端
```bash
uvicorn match_service.main:app --host 0.0.0.0 --port 9100
```

访问: http://localhost:9100/

### 方案 B: 前后端分离部署

**后端**: 
```bash
docker build -t mms-backend .
docker run -p 9100:9100 mms-backend
```

**前端**: 
```bash
cd frontend
npm run build
# 部署 dist/ 到 Nginx/Vercel/Netlify
```

Nginx 配置示例:
```nginx
server {
    listen 80;
    server_name match.example.com;

    # 前端
    location / {
        root /var/www/match-service-frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://localhost:9100/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## 环境变量

### 后端 (.env)
```bash
MATCH_SVC_ENGINE_MODE=local
MATCH_SVC_DB_HOST=localhost
MATCH_SVC_DB_PORT=5432
MATCH_SVC_DB_NAME=acrac
MATCH_SVC_DB_USER=postgres
MATCH_SVC_DB_PASSWORD=your_password
```

### 前端 (.env.local)
```bash
VITE_API_BASE_URL=http://localhost:9100/api
```

生产环境:
```bash
VITE_API_BASE_URL=https://api.match.example.com/api
```

## 功能验证

### 1. 后端健康检查
```bash
curl http://localhost:9100/health
```

### 2. 前端访问
打开浏览器访问 http://localhost:3100

### 3. API 测试
```bash
curl -X POST http://localhost:9100/api/match/one \
  -H 'Content-Type: application/json' \
  -d '{
    "check_item": "胸部CT平扫",
    "modality": "CT"
  }'
```

## 故障排查

### 前端连接后端失败
1. 检查后端是否运行: `curl http://localhost:9100/health`
2. 检查 CORS 配置: main.py 中 CORSMiddleware
3. 检查 Vite 代理配置: frontend/vite.config.ts

### 数据库连接失败
1. 检查 PostgreSQL 是否运行
2. 验证数据库配置: 环境变量或 config.py
3. 运行迁移: `alembic upgrade head`

### 前端构建失败
1. 清理缓存: `rm -rf node_modules && npm install`
2. 检查 Node.js 版本: `node -v` (需要 >= 18)

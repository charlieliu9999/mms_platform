# MMS 前端

独立的 React + TypeScript + Ant Design 前端项目，用于管理 MMS 标准化匹配服务。

## 技术栈

- React 18
- TypeScript
- Vite
- Ant Design 5
- React Router 6
- Axios

## 开发

```bash
# 安装依赖
npm install

# 启动开发服务器 (http://localhost:3100)
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 功能模块

- **概览**: 数据统计、版本信息
- **匹配测试**: 单个匹配测试工具
- **词库管理**: 医学词典增删改查
- **AI 建议**: Agent 优化建议审批（开发中）
- **版本历史**: 规则版本演进记录（开发中）

## 环境变量

创建 `.env.local` 文件配置：

```
VITE_API_BASE_URL=http://localhost:9100/api
```

## 项目结构

```
src/
├── components/       # 通用组件
│   └── Sidebar.tsx
├── pages/           # 页面组件
│   ├── Dashboard.tsx
│   ├── MatchTest.tsx
│   └── LexiconMgmt.tsx
├── services/        # API 服务
│   ├── api.ts
│   └── matchService.ts
├── types/          # TypeScript 类型定义
├── utils/          # 工具函数
├── App.tsx         # 根组件
└── main.tsx        # 入口文件
```

## 部署

### 开发环境
Vite dev server (端口 3100) + 后端代理到 9100

### 生产环境
```bash
npm run build
# dist/ 目录部署到 Nginx/Vercel/Netlify
```

配置 Nginx 反向代理：
```nginx
location /api/ {
    proxy_pass http://localhost:9100/api/;
}

location / {
    root /var/www/match-service-frontend/dist;
    try_files $uri $uri/ /index.html;
}
```

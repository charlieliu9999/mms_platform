# VPS 部署指南 - MMS Platform

> **⚠️ 文档已更新**  
> 本文档包含基础部署验证步骤和监控配置。  
> 
> **完整部署流程请查看新文档：**
> - 📘 [完整部署流程](deployment/code-sync-workflow.md) - 三种部署方法详细步骤
> - 📊 [部署方法对比](deployment/deployment-methods-comparison.md) - 代码同步流程对比
> - 🛠️ Skill: 直接说 "部署到 VPS"，AI 会自动引导
>
> 本文档重点：验证步骤、监控配置、故障排查

---

## 快速部署（简化版）

### 方法选择
- **正式发布** → GitLab CI/CD（自动化）
- **快速迭代** → `./scripts/quick_deploy_backend.sh`
- **紧急修复** → Python 直接运行

详细说明见：[部署方法对比](deployment/deployment-methods-comparison.md)

---

## 历史更新记录

本次推送包含 4 个重要提交：
1. `5cce52a` - 修复 PET/CT 和 PET/MR 统计显示 Bug
2. `b99a997` - 添加健康检查和 API 信息端点
3. `84e8e8f` - 添加 VPS API 测试脚本
4. `0a5d718` - 添加完整的 API 端点文档

## VPS 部署步骤（传统方式）

> **💡 提示：** 这是传统的手动部署方式，适合了解基础流程。  
> 实际使用建议：
> - **自动化部署** → 见 [GitLab CI/CD 流程](deployment/code-sync-workflow.md#方法一gitlab-cicd-自动部署推荐)
> - **快速部署** → 使用 `./scripts/quick_deploy_backend.sh`
> - **AI 辅助** → 直接说 "部署到 VPS"

### 1. 连接到 VPS
```bash
ssh user@your-vps-ip
```

### 2. 进入项目目录
```bash
cd /path/to/mms_platform
```

### 3. 拉取最新代码
```bash
git pull origin main
```

### 4. 检查更新内容
```bash
git log -4 --oneline
# 应该看到:
# 0a5d718 docs: 添加完整的 API 端点文档
# 84e8e8f feat: 添加 VPS API 端点测试脚本
# b99a997 feat: 添加健康检查和 API 信息端点
# 5cce52a fix: 修复 PET/CT 和 PET/MR 统计数据显示逻辑
```

### 5. 重新构建前端（如果使用 Docker）
```bash
cd frontend
npm run build
cd ..
```

### 6. 重启服务

#### 方案 A: Docker 部署
```bash
# 重启后端容器
docker-compose restart backend

# 或者完全重建
docker-compose down
docker-compose up -d --build
```

#### 方案 B: 直接运行
```bash
# 重启后端服务（根据您的进程管理方式）
# systemd
sudo systemctl restart mms-backend

# 或 PM2
pm2 restart mms-backend

# 或手动
pkill -f "uvicorn match_service.main:app"
cd /path/to/mms_platform
poetry run uvicorn match_service.main:app --host 0.0.0.0 --port 9100 &
```

### 7. 验证部署

#### 测试健康检查（新增）
```bash
curl http://localhost:9100/health
# 预期输出:
# {
#   "status": "healthy",
#   "service": "medical-match-service",
#   "version": "1.0.0"
# }
```

#### 测试 API 信息（新增）
```bash
curl http://localhost:9100/api
# 预期输出: 所有可用端点列表
```

#### 运行完整测试套件
```bash
chmod +x scripts/test_vps_api.sh
./scripts/test_vps_api.sh http://localhost:9100
```

### 8. 验证前端修复

访问前端标准项目页面，检查 PET/CT 和 PET/MR 统计数据是否正确显示。

## 关键验证点

### ✅ 必须通过的测试
1. `GET /health` 返回 200
2. `GET /api` 返回端点列表
3. `GET /api/open/standards/items` 返回数据（不是 /list）
4. `GET /api/open/standards/stats` 包含 PET/CT 和 PET/MR 数据
5. 前端统计页面正确显示 PET/CT 和 PET/MR 数量

### ❌ 常见错误
- 测试 `/api/open/standards/list` → 应该是 `/api/open/standards/items`
- 前端显示 PET/CT 和 PET/MR 数量为 0 → 检查是否拉取了最新前端代码

## 端口检查

```bash
# 检查服务是否在监听
netstat -tlnp | grep -E '(9100|3100|5589|3000)'

# 预期输出:
# 9100 - mms_platform 后端
# 3000 - Next.js 前端（如果单独运行）
# 5589 - acrac_web_mgmt
```

## Docker 部署特别说明

### 检查容器状态
```bash
docker ps | grep mms
```

### 查看后端日志
```bash
docker logs -f mms_backend --tail 100
```

### 查看前端构建结果
```bash
ls -la frontend/dist/
# 应该看到构建产物
```

## 回滚方案

如果部署出现问题，可以回滚：

```bash
# 查看之前的版本
git log --oneline -10

# 回滚到之前的提交（例如 5c04c65）
git reset --hard 5c04c65

# 重新部署
docker-compose down && docker-compose up -d --build
```

## 监控配置建议

### 添加健康检查到监控系统

**Prometheus 配置示例:**
```yaml
scrape_configs:
  - job_name: 'mms_platform'
    metrics_path: '/health'
    static_configs:
      - targets: ['your-vps-ip:9100']
```

**Nginx 健康检查配置:**
```nginx
upstream mms_backend {
    server 127.0.0.1:9100 max_fails=3 fail_timeout=30s;
    check interval=3000 rise=2 fall=3 timeout=1000 type=http;
    check_http_send "GET /health HTTP/1.0\r\n\r\n";
    check_http_expect_alive http_2xx;
}
```

## 故障排查

### 问题 1: 后端启动失败
```bash
# 检查日志
docker logs mms_backend
# 或
journalctl -u mms-backend -n 50

# 常见原因:
# - 数据库连接失败
# - 端口被占用
# - 环境变量缺失
```

### 问题 2: API 返回 404
```bash
# 确认路由是否正确
curl http://localhost:9100/api
# 检查 API 列表，确认端点路径

# 参考文档
cat docs/api-endpoints.md
```

### 问题 3: 前端显示数据异常
```bash
# 检查前端是否重新构建
ls -lt frontend/dist/ | head -5

# 检查后端数据
curl http://localhost:9100/api/open/standards/stats | python3 -m json.tool
```

## 部署完成检查清单

- [ ] 代码已拉取到最新版本
- [ ] 前端已重新构建
- [ ] 后端服务已重启
- [ ] `/health` 端点返回 200
- [ ] `/api` 端点返回端点列表
- [ ] 测试脚本全部通过
- [ ] 前端页面 PET/CT 和 PET/MR 数据正确显示
- [ ] Docker 容器状态正常（如果使用）
- [ ] 日志无异常错误

## 联系支持

如果部署遇到问题，请提供：
1. `git log -5 --oneline` 输出
2. `docker ps` 或服务状态输出
3. 错误日志（后端日志最后 50 行）
4. `./scripts/test_vps_api.sh` 输出

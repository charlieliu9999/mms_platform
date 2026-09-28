# MMS Platform 代码同步部署流程

本文档详细说明从本地开发到 VPS 生产环境的完整代码同步部署流程。

## 📋 目录

1. [部署架构概览](#部署架构概览)
2. [方法一：GitLab CI/CD 自动部署（推荐）](#方法一gitlab-cicd-自动部署推荐)
3. [方法二：手动 rsync 部署](#方法二手动-rsync-部署)
4. [方法三：本地脚本快速部署](#方法三本地脚本快速部署)
5. [故障排查](#故障排查)
6. [最佳实践](#最佳实践)

---

## 部署架构概览

```
┌─────────────┐      git push       ┌─────────────┐      GitLab Runner      ┌─────────────┐
│   本地开发   │  ───────────────>  │   GitLab    │  ──────────────────>   │  VPS 生产   │
│  (Mac M1)   │                     │  (内网)     │                         │ 220.154.3.166│
└─────────────┘                     └─────────────┘                         └─────────────┘
      │                                    │                                        │
      │                                    │                                        │
      └────────────── rsync 直接同步 ────────────────────────────────────────────>  │
                     (方法二/三)
```

### 组件说明

| 组件 | 地址 | 说明 |
|------|------|------|
| 本地开发环境 | Mac M1 | 代码编写、测试、提交 |
| GitLab 仓库 | http://192.168.0.155/liuzhaohui/mms_platform.git | 内网代码仓库 |
| GitLab Runner | Mac shell executor | 执行 CI/CD 任务 |
| VPS 生产环境 | 220.154.3.166 | 运行后端（9100）+ 前端（3100） |

---

## 方法一：GitLab CI/CD 自动部署（推荐）

### ✅ 优点
- 全自动化，减少人为错误
- 包含测试、构建、健康检查
- 有日志记录和回滚能力
- 适合团队协作

### 📋 步骤

#### 1. 本地提交代码

```bash
# 在项目根目录
git add .
git commit -m "feat: 添加 PET/CT 和 PET/MR 修复"
git push origin main
```

#### 2. 触发 CI/CD Pipeline

**方式 A：自动触发**
- 推送到 `main` 分支自动触发
- 等待 Pipeline 执行完成

**方式 B：手动触发**
1. 访问 GitLab: http://192.168.0.155/liuzhaohui/mms_platform/-/pipelines
2. 点击 "Run Pipeline"
3. 选择 `main` 分支
4. 点击 "Run Pipeline" 按钮

#### 3. Pipeline 执行流程

```yaml
stages:
  - test          # 运行后端测试 + 前端构建测试
  - deploy        # 部署到 VPS
```

**详细步骤：**

1. **测试阶段** (test)
   - `test_backend`: 运行 pytest 测试
   - `test_frontend`: 构建前端验证

2. **部署阶段** (deploy) - 仅在 main 分支
   - 备份 VPS 上的 `.env` 文件
   - 同步数据目录（双向）
   - rsync 推送代码到 VPS
   - 在 VPS 上构建前端 (`npm run build`)
   - 重启后端服务 (Docker Compose)
   - 重启前端服务 (Docker Compose)
   - 健康检查

#### 4. 查看部署日志

```bash
# 访问 GitLab Pipeline 页面
http://192.168.0.155/liuzhaohui/mms_platform/-/pipelines

# 点击最新的 Pipeline
# 查看 deploy_production 任务日志
```

#### 5. 验证部署

```bash
# 后端健康检查
curl http://220.154.3.166:9100/api

# 前端访问
curl http://220.154.3.166:3100/
```

### 🔧 CI/CD 配置文件

配置文件位于项目根目录：`.gitlab-ci.yml`

**关键配置：**

```yaml
variables:
  DEPLOY_PATH: "/data/mms-platform"
  VPS_HOST: "220.154.3.166"
  VPS_USER: "root"
  VPS_PASSWORD: "${VPS_PASSWORD}"  # GitLab CI/CD 变量
```

### 🔐 配置 GitLab 变量

1. 访问项目设置：http://192.168.0.155/liuzhaohui/mms_platform/-/settings/ci_cd
2. 展开 "Variables" 部分
3. 添加变量：
   - Key: `VPS_PASSWORD`
   - Value: VPS root 密码
   - Masked: ✓（隐藏日志中的值）

---

## 方法二：手动 rsync 部署

### ✅ 优点
- 快速，直接同步
- 适合紧急修复
- 不依赖 GitLab

### ⚠️ 缺点
- 没有自动测试
- 需要手动验证
- 没有部署日志

### 📋 步骤

#### 1. 确保 SSH 密钥配置

```bash
# 测试 SSH 连接
ssh root@220.154.3.166 "echo '连接成功'"
```

如果提示输入密码，需要配置 SSH 密钥：

```bash
# 生成密钥（如果没有）
ssh-keygen -t rsa -b 4096

# 复制公钥到 VPS
ssh-copy-id root@220.154.3.166
```

#### 2. 使用快速部署脚本

```bash
# 在项目根目录
./scripts/quick_deploy_backend.sh
```

**脚本执行内容：**
1. 同步后端代码到 VPS (src/, migrations/, alembic.ini 等)
2. 重启后端服务 (Docker Compose)
3. 验证健康检查
4. 测试 PET/CT 和 PET/MR 查询

#### 3. 完整部署（包含前端）

如果需要同时部署前端：

```bash
./scripts/deploy_to_vps_with_key.sh
```

**注意事项：**
- VPS 上的 Node.js 版本较老，前端构建可能失败
- 建议本地构建前端后再同步：

```bash
# 本地构建前端
cd frontend
npm run build
cd ..

# 同步到 VPS
rsync -avz --progress \
  frontend/dist/ \
  root@220.154.3.166:/data/mms-platform/frontend/dist/
```

---

## 方法三：本地脚本快速部署

### ✅ 适用场景
- 开发期快速迭代
- 调试生产问题
- 验证修复效果

### 📋 Python 直接运行方式（最快）

当 Docker 构建太慢时，使用 Python 虚拟环境直接运行：

#### 1. 同步代码

```bash
rsync -avz --progress \
  --exclude='.git/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.venv/' \
  --exclude='node_modules/' \
  --exclude='frontend/dist/' \
  ./ \
  root@220.154.3.166:/data/mms-platform/
```

#### 2. 重启后端服务

```bash
ssh root@220.154.3.166 "
cd /data/mms-platform

# 停止旧进程
pkill -f 'uvicorn match_service.main'

# 启动新进程
PYTHONPATH=/data/mms-platform/src \
nohup .venv/bin/python -m uvicorn match_service.main:app \
  --host 0.0.0.0 --port 9100 \
  > logs/uvicorn.log 2>&1 &

# 等待启动
sleep 5

# 验证
curl -s http://localhost:9100/api | python3 -m json.tool
"
```

#### 3. 验证部署

```bash
ssh root@220.154.3.166 "
# 检查进程
ps aux | grep 'uvicorn match_service' | grep -v grep

# 测试 API
curl -s 'http://localhost:9100/api/open/standards/items?modality=PET/CT&limit=1' | python3 -m json.tool
"
```

---

## 故障排查

### 问题 1：GitLab Pipeline 卡住

**症状：**
- Pipeline 一直显示 "running"
- deploy_production 任务超时

**解决方案：**

```bash
# 1. 检查 GitLab Runner 状态
ssh root@192.168.0.155
systemctl status gitlab-runner

# 2. 查看 Runner 日志
journalctl -u gitlab-runner -f

# 3. 重启 Runner
systemctl restart gitlab-runner
```

### 问题 2：Docker 构建超时

**症状：**
- VPS 上 Docker 构建 Python 依赖很慢
- 超过 5 分钟仍未完成

**解决方案：**

使用 Python 直接运行（见方法三）

```bash
# 停止 Docker 容器
ssh root@220.154.3.166 "cd /data/mms-platform && docker compose down"

# 使用 Python 虚拟环境运行
ssh root@220.154.3.166 "
cd /data/mms-platform
PYTHONPATH=/data/mms-platform/src \
nohup .venv/bin/python -m uvicorn match_service.main:app \
  --host 0.0.0.0 --port 9100 > logs/uvicorn.log 2>&1 &
"
```

### 问题 3：前端构建失败（glibc 版本问题）

**症状：**
```
Error: Cannot find module @rollup/rollup-linux-x64-gnu
/lib64/libm.so.6: version `GLIBC_2.29' not found
```

**原因：** VPS 是 CentOS 7，glibc 版本太旧

**解决方案：**

在本地构建前端，然后同步到 VPS：

```bash
# 本地构建
cd frontend
npm run build

# 同步到 VPS
rsync -avz --progress \
  dist/ \
  root@220.154.3.166:/data/mms-platform/frontend/dist/
```

### 问题 4：ModuleNotFoundError: No module named 'match_service'

**症状：**
```
ModuleNotFoundError: No module named 'match_service'
```

**原因：** PYTHONPATH 未设置

**解决方案：**

```bash
ssh root@220.154.3.166 "
cd /data/mms-platform

# 启动时设置 PYTHONPATH
PYTHONPATH=/data/mms-platform/src \
.venv/bin/python -m uvicorn match_service.main:app \
  --host 0.0.0.0 --port 9100
"
```

### 问题 5：PET/CT 或 PET/MR 查询返回 0 条

**症状：**
```bash
curl 'http://localhost:9100/api/open/standards/items?modality=PET/CT'
# 返回 "total": 0
```

**排查步骤：**

```bash
# 1. 检查数据库是否有数据
ssh root@220.154.3.166
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db

# 2. 查询标准项目表
SELECT COUNT(*) FROM standard_check_items WHERE modality = 'PET/CT';

# 3. 检查代码是否更新
cd /data/mms-platform
git log --oneline -5

# 4. 确认服务使用的是新代码
ps aux | grep uvicorn
ls -la src/match_service/api/
```

---

## 最佳实践

### 1. 开发流程

```bash
# 本地开发 → 本地测试 → 提交 → 推送 → CI/CD 自动部署

# 步骤 1: 本地开发和测试
cd /path/to/mms_platform
# 修改代码
poetry run pytest tests/ -v

# 步骤 2: 提交代码
git add .
git commit -m "feat: 添加新功能"

# 步骤 3: 推送到 GitLab
git push origin main

# 步骤 4: 等待 CI/CD 完成（自动）
# 访问 GitLab 查看 Pipeline 状态

# 步骤 5: 验证生产环境
curl http://220.154.3.166:9100/api
```

### 2. 紧急修复流程

```bash
# 快速修复 → 快速部署 → 验证 → 补充测试和提交

# 步骤 1: 修改代码
# 修复 bug

# 步骤 2: 快速部署（不等 CI/CD）
./scripts/quick_deploy_backend.sh

# 步骤 3: 验证修复
ssh root@220.154.3.166 "curl http://localhost:9100/api"

# 步骤 4: 补充提交（修复后）
git add .
git commit -m "fix: 修复 PET/CT 查询问题"
git push origin main
```

### 3. 回滚策略

#### 方式 A：回滚代码

```bash
# 1. 本地回滚到上一个提交
git log --oneline -10
git reset --hard <commit-hash>

# 2. 强制推送
git push origin main --force

# 3. 等待 CI/CD 重新部署
```

#### 方式 B：重启旧版本服务

```bash
ssh root@220.154.3.166 "
cd /data/mms-platform

# 查看 git 历史
git log --oneline -10

# 切换到上一个版本
git checkout <commit-hash>

# 重启服务
pkill -f 'uvicorn match_service'
PYTHONPATH=/data/mms-platform/src \
nohup .venv/bin/python -m uvicorn match_service.main:app \
  --host 0.0.0.0 --port 9100 > logs/uvicorn.log 2>&1 &
"
```

### 4. 监控和日志

#### 查看后端日志

```bash
ssh root@220.154.3.166 "tail -f /data/mms-platform/logs/uvicorn.log"
```

#### 查看 Docker 日志

```bash
ssh root@220.154.3.166 "
cd /data/mms-platform
docker compose logs -f backend
"
```

#### 查看服务状态

```bash
ssh root@220.154.3.166 "
# 进程状态
ps aux | grep uvicorn | grep match_service

# 端口占用
netstat -tlnp | grep 9100

# Docker 容器状态
docker ps --filter name=mms
"
```

---

## 部署检查清单

### 部署前检查

- [ ] 本地测试通过 (`pytest tests/ -v`)
- [ ] 前端构建成功 (`cd frontend && npm run build`)
- [ ] 代码已提交到 Git
- [ ] .env 配置文件已备份

### 部署后验证

- [ ] 后端服务运行正常 (`ps aux | grep uvicorn`)
- [ ] 健康检查通过 (`curl http://localhost:9100/api`)
- [ ] PET/CT 查询正常 (`curl 'http://localhost:9100/api/open/standards/items?modality=PET/CT'`)
- [ ] PET/MR 查询正常 (`curl 'http://localhost:9100/api/open/standards/items?modality=PET/MR'`)
- [ ] 前端页面可访问 (`curl http://localhost:3100/`)
- [ ] 查看日志无错误 (`tail logs/uvicorn.log`)

---

## 常用命令速查

### 本地操作

```bash
# 提交代码
git add . && git commit -m "feat: 新功能" && git push origin main

# 本地构建前端
cd frontend && npm run build && cd ..

# 运行本地测试
poetry run pytest tests/ -v

# 快速部署脚本
./scripts/quick_deploy_backend.sh
```

### VPS 操作

```bash
# SSH 连接
ssh root@220.154.3.166

# 重启后端（Python 方式）
pkill -f 'uvicorn match_service' && \
cd /data/mms-platform && \
PYTHONPATH=/data/mms-platform/src nohup .venv/bin/python -m uvicorn match_service.main:app --host 0.0.0.0 --port 9100 > logs/uvicorn.log 2>&1 &

# 重启后端（Docker 方式）
cd /data/mms-platform && docker compose restart backend

# 查看日志
tail -f /data/mms-platform/logs/uvicorn.log

# 查看进程
ps aux | grep uvicorn | grep match_service

# 测试 API
curl http://localhost:9100/api
```

### 故障排查

```bash
# 检查端口占用
netstat -tlnp | grep 9100

# 查看最近日志
tail -100 /data/mms-platform/logs/uvicorn.log

# 检查代码版本
cd /data/mms-platform && git log --oneline -5

# 检查 Python 环境
cd /data/mms-platform && .venv/bin/python --version

# 手动测试数据库连接
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db -c "SELECT COUNT(*) FROM standard_check_items;"
```

---

## 总结

| 方法 | 速度 | 可靠性 | 适用场景 |
|------|------|--------|---------|
| GitLab CI/CD | 中等 | 最高 | 正式发布、团队协作 |
| 手动 rsync | 快 | 中等 | 紧急修复、快速迭代 |
| Python 直接运行 | 最快 | 中等 | 开发调试、Docker 失败时 |

**推荐流程：**
- 🌟 日常开发：使用 GitLab CI/CD 自动部署
- 🔥 紧急修复：使用快速部署脚本
- 🛠️ 调试问题：使用 Python 直接运行

---

## 相关文档

- [VPS 部署指南](../deployment-guide.md)
- [API 端点文档](../api-endpoints.md)
- [故障排查指南](../troubleshooting.md)

---

**最后更新**: 2026-08-21  
**维护者**: MMS Platform 团队

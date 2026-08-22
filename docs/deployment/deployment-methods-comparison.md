# 三种部署方案的代码更新同步对比

## 📊 对比总览表

| 对比维度 | 方法一：GitLab CI/CD | 方法二：rsync 手动同步 | 方法三：Python 直接运行 |
|---------|---------------------|---------------------|---------------------|
| **代码来源** | GitLab 仓库 | 本地工作目录 | 本地工作目录 |
| **同步触发** | Git Push 自动触发 | 手动执行脚本 | 手动 rsync |
| **代码版本** | Git 提交版本 | 本地文件（可能未提交） | 本地文件（可能未提交） |
| **同步速度** | 慢（5-10分钟） | 快（1-2分钟） | 最快（30秒-1分钟） |
| **同步范围** | 完整项目 | 可选择性同步 | 可选择性同步 |
| **版本控制** | ✓ 有 Git 记录 | ✗ 无记录 | ✗ 无记录 |
| **回滚能力** | ✓ 容易（Git） | ⚠️ 困难 | ⚠️ 困难 |
| **依赖处理** | ✓ 自动安装 | ⚠️ 需手动 | ✗ 不处理 |
| **适合场景** | 正式发布 | 快速迭代 | 紧急修复 |

---

## 方法一：GitLab CI/CD 自动部署

### 代码更新流程

```
┌─────────────┐
│  本地修改   │
└──────┬──────┘
       │
       │ git add .
       │ git commit
       │ git push origin main
       ↓
┌─────────────┐
│  GitLab     │ ← 代码存储在 GitLab 仓库
│  仓库       │   版本：Git commit hash
└──────┬──────┘
       │
       │ Webhook 触发
       ↓
┌─────────────┐
│ GitLab      │
│ Runner      │ ← Mac shell executor
│ (本地Mac)   │
└──────┬──────┘
       │
       │ 1. 拉取代码：git clone/pull
       │ 2. 运行测试：pytest
       │ 3. 构建前端：npm run build
       ↓
┌─────────────┐
│   rsync     │ ← 从 Runner 工作目录同步
│   同步      │   到 VPS
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   VPS       │ ← /data/mms-platform/
│ 220.154...  │   代码版本：Git commit
└─────────────┘
```

### 详细步骤

#### 第 1 步：本地提交代码

```bash
# 在项目根目录
cd /Users/charlieliu/git_project_vscode/09_medical/mms_platform

# 修改代码后提交
git add src/match_service/api/routes.py
git commit -m "fix: 修复 PET/CT 查询逻辑"
git push origin main
```

**此时代码位置：**
- ✓ 本地 Git 仓库：已提交
- ✓ GitLab 远程仓库：已推送
- ✗ VPS：还未更新

#### 第 2 步：GitLab Runner 拉取代码

Runner 自动执行（在 Mac 上）：

```bash
# Runner 工作目录
cd /Users/Shared/gitlab-runner/builds/<hash>/mms_platform

# 拉取最新代码
git fetch origin
git checkout main
git pull origin main

# 此时 Runner 拿到的是 GitLab 上的最新版本
```

**此时代码位置：**
- ✓ 本地 Git 仓库：有代码
- ✓ GitLab 远程仓库：有代码
- ✓ Runner 工作目录：已拉取
- ✗ VPS：还未更新

#### 第 3 步：测试和构建

```bash
# Runner 执行测试
poetry run pytest tests/ -v

# 构建前端
cd frontend
npm install
npm run build
```

#### 第 4 步：rsync 同步到 VPS

```bash
# Runner 执行（在 .gitlab-ci.yml 中定义）
sshpass -p "${VPS_PASSWORD}" rsync -avz \
  --exclude='.git/' \
  --exclude='node_modules/' \
  /Users/Shared/gitlab-runner/builds/<hash>/mms_platform/ \
  root@220.154.3.166:/data/mms-platform/
```

**同步的内容：**
- ✓ 所有源代码文件
- ✓ 前端构建产物 (frontend/dist/)
- ✓ 配置文件 (pyproject.toml, docker-compose.yml)
- ✗ .git/ 目录（排除）
- ✗ node_modules/ （排除）

**此时代码位置：**
- ✓ 本地 Git 仓库：有代码
- ✓ GitLab 远程仓库：有代码
- ✓ Runner 工作目录：有代码
- ✓ VPS：已同步

#### 第 5 步：重启服务

```bash
# Runner 通过 SSH 在 VPS 执行
ssh root@220.154.3.166 "
cd /data/mms-platform
docker compose build backend
docker compose up -d backend
"
```

### 代码更新特点

**✅ 优点：**
1. **版本可追溯**：每次部署对应一个 Git commit
2. **自动化**：推送后无需手动操作
3. **有测试保障**：部署前运行测试
4. **完整同步**：确保所有文件都更新

**❌ 缺点：**
1. **必须提交**：未提交的代码无法部署
2. **速度慢**：整个流程 5-10 分钟
3. **依赖 GitLab**：GitLab 或 Runner 故障时无法部署

**适用场景：**
- 正式发布新版本
- 多人协作开发
- 需要代码审查
- 需要完整测试

---

## 方法二：rsync 手动同步

### 代码更新流程

```
┌─────────────┐
│  本地修改   │ ← 直接修改本地文件
└──────┬──────┘   可能未 git commit
       │
       │ ./scripts/quick_deploy_backend.sh
       ↓
┌─────────────┐
│   rsync     │ ← 直接从本地工作目录
│   同步      │   同步到 VPS
└──────┬──────┘   
       │
       ↓
┌─────────────┐
│   VPS       │ ← /data/mms-platform/
│ 220.154...  │   代码版本：本地文件
└─────────────┘
```

### 详细步骤

#### 第 1 步：本地修改代码

```bash
# 直接修改文件
vim src/match_service/api/routes.py

# 不需要 git commit（可以，但不强制）
```

**此时代码位置：**
- ✓ 本地工作目录：有修改
- ? Git 仓库：可能未提交
- ? GitLab：可能未推送
- ✗ VPS：还未更新

#### 第 2 步：执行部署脚本

```bash
./scripts/quick_deploy_backend.sh
```

脚本内部执行：

```bash
# 1. 同步后端代码
rsync -avz --progress \
  --include='src/' \
  --include='src/match_service/' \
  --include='src/match_service/**' \
  --include='migrations/' \
  --include='migrations/**' \
  --include='alembic.ini' \
  --include='pyproject.toml' \
  --include='poetry.lock' \
  --include='Dockerfile' \
  --include='docker-compose.yml' \
  --exclude='*' \
  ./ \
  root@220.154.3.166:/data/mms-platform/
```

**同步的内容（选择性）：**
- ✓ src/match_service/ (后端代码)
- ✓ migrations/ (数据库迁移)
- ✓ pyproject.toml, poetry.lock
- ✓ Dockerfile, docker-compose.yml
- ✗ frontend/ (前端，排除)
- ✗ tests/ (测试，排除)
- ✗ docs/ (文档，排除)

**此时代码位置：**
- ✓ 本地工作目录：有修改
- ? Git 仓库：可能未提交
- ? GitLab：可能未推送
- ✓ VPS：已同步（仅后端）

#### 第 3 步：重启服务

```bash
# 脚本自动执行
ssh root@220.154.3.166 \
  "cd /data/mms-platform && \
   docker compose build backend && \
   docker compose up -d backend"
```

### 代码更新特点

**✅ 优点：**
1. **快速**：1-2 分钟完成
2. **灵活**：可以部署未提交的代码
3. **选择性同步**：只同步需要的文件
4. **独立**：不依赖 GitLab

**❌ 缺点：**
1. **无版本记录**：不知道 VPS 上是哪个版本
2. **容易不一致**：本地、Git、VPS 可能不同步
3. **无测试**：直接部署，可能引入问题
4. **难以回滚**：没有版本历史

**适用场景：**
- 快速验证修复
- 开发期频繁迭代
- 调试生产问题
- GitLab 不可用时

---

## 方法三：Python 直接运行

### 代码更新流程

```
┌─────────────┐
│  本地修改   │ ← 直接修改本地文件
└──────┬──────┘   可能未 git commit
       │
       │ rsync 手动同步
       ↓
┌─────────────┐
│   rsync     │ ← 直接从本地工作目录
│   同步      │   同步到 VPS
└──────┬──────┘   
       │
       ↓
┌─────────────┐
│   VPS       │ ← /data/mms-platform/src/
│   Python    │   使用现有 .venv
│   .venv     │   直接运行代码
└─────────────┘
```

### 详细步骤

#### 第 1 步：本地修改代码

```bash
# 直接修改文件
vim src/match_service/api/routes.py
```

#### 第 2 步：手动 rsync 同步

```bash
# 只同步修改的文件（最快）
rsync -avz \
  src/match_service/api/routes.py \
  root@220.154.3.166:/data/mms-platform/src/match_service/api/

# 或同步整个后端目录
rsync -avz \
  src/ \
  root@220.154.3.166:/data/mms-platform/src/
```

**同步的内容（最小化）：**
- ✓ 只同步修改的 .py 文件
- ✗ 不同步配置文件
- ✗ 不同步依赖
- ✗ 不同步前端

**此时代码位置：**
- ✓ 本地工作目录：有修改
- ? Git 仓库：可能未提交
- ? GitLab：可能未推送
- ✓ VPS：已同步（仅修改的文件）

#### 第 3 步：重启服务

```bash
ssh root@220.154.3.166 "
cd /data/mms-platform

# 停止旧进程
pkill -f 'uvicorn match_service.main'

# 启动新进程（使用现有虚拟环境）
PYTHONPATH=/data/mms-platform/src \
nohup .venv/bin/python -m uvicorn match_service.main:app \
  --host 0.0.0.0 --port 9100 \
  > logs/uvicorn.log 2>&1 &
"
```

**关键点：**
- 使用现有的 `.venv` (不重新安装依赖)
- 直接运行 Python 代码（不用 Docker）
- 代码立即生效（Python 动态加载）

### 代码更新特点

**✅ 优点：**
1. **最快**：30秒-1分钟完成
2. **最灵活**：可以只同步一个文件
3. **无构建**：不需要 Docker 构建
4. **即时生效**：重启服务立即加载新代码

**❌ 缺点：**
1. **最不安全**：无测试、无验证
2. **依赖不更新**：pyproject.toml 变化时问题
3. **容易遗漏**：可能忘记同步某些文件
4. **无版本追踪**：完全无记录

**适用场景：**
- 紧急修复（5分钟内上线）
- 单文件小改动
- 调试问题（反复修改测试）
- Docker 构建失败时

---

## 实战对比案例

### 场景 1：修复 PET/CT 查询 Bug

#### 使用方法一（GitLab CI/CD）

```bash
# 1. 本地修改
vim src/match_service/api/routes.py

# 2. 测试
poetry run pytest tests/test_routes.py -v

# 3. 提交
git add src/match_service/api/routes.py
git commit -m "fix: PET/CT 查询逻辑修复"
git push origin main

# 4. 等待 CI/CD
# 等待 5-10 分钟...

# 5. 验证
curl http://220.154.3.166:9100/api/open/standards/items?modality=PET/CT
```

**总耗时：** 10-15 分钟（包括测试 + CI/CD）

---

#### 使用方法二（rsync 手动）

```bash
# 1. 本地修改
vim src/match_service/api/routes.py

# 2. 快速部署
./scripts/quick_deploy_backend.sh

# 等待 1-2 分钟...

# 3. 验证
curl http://220.154.3.166:9100/api/open/standards/items?modality=PET/CT

# 4. 补充提交（可选）
git add src/match_service/api/routes.py
git commit -m "fix: PET/CT 查询逻辑修复"
git push origin main
```

**总耗时：** 2-3 分钟

---

#### 使用方法三（Python 直接）

```bash
# 1. 本地修改
vim src/match_service/api/routes.py

# 2. 同步单个文件
rsync -avz \
  src/match_service/api/routes.py \
  root@220.154.3.166:/data/mms-platform/src/match_service/api/

# 3. 重启服务
ssh root@220.154.3.166 "
pkill -f 'uvicorn match_service' && \
cd /data/mms-platform && \
PYTHONPATH=/data/mms-platform/src \
nohup .venv/bin/python -m uvicorn match_service.main:app \
  --host 0.0.0.0 --port 9100 > logs/uvicorn.log 2>&1 &
"

# 4. 验证
ssh root@220.154.3.166 "curl http://localhost:9100/api/open/standards/items?modality=PET/CT"

# 5. 补充提交（必须）
git add src/match_service/api/routes.py
git commit -m "fix: PET/CT 查询逻辑修复"
git push origin main
```

**总耗时：** 1 分钟

---

### 场景 2：添加新依赖包

假设需要添加 `pandas` 包：

#### 使用方法一（GitLab CI/CD）

```bash
# 1. 添加依赖
poetry add pandas

# 2. 提交
git add pyproject.toml poetry.lock
git commit -m "feat: 添加 pandas 依赖"
git push origin main

# 3. CI/CD 自动执行
# - poetry install（安装新依赖）
# - docker compose build（重新构建镜像）
# - 部署到 VPS
```

**结果：** ✅ 依赖正确安装

---

#### 使用方法二（rsync 手动）

```bash
# 1. 添加依赖
poetry add pandas

# 2. 部署
./scripts/quick_deploy_backend.sh

# 问题：脚本只同步代码，不安装依赖！
```

**结果：** ❌ VPS 上没有 pandas，运行时报错

**解决方案：** 需要手动 SSH 到 VPS 安装

```bash
ssh root@220.154.3.166 "
cd /data/mms-platform
docker compose build backend  # 重新构建镜像
docker compose up -d backend
"
```

---

#### 使用方法三（Python 直接）

```bash
# 1. 添加依赖
poetry add pandas

# 2. 同步代码
rsync -avz src/ root@220.154.3.166:/data/mms-platform/src/

# 3. 重启服务
ssh root@220.154.3.166 "
pkill -f 'uvicorn match_service'
cd /data/mms-platform
PYTHONPATH=/data/mms-platform/src \
.venv/bin/python -m uvicorn match_service.main:app --host 0.0.0.0 --port 9100
"

# 问题：VPS 上的 .venv 没有 pandas！
```

**结果：** ❌ 运行时 `ImportError: No module named 'pandas'`

**解决方案：** 必须手动安装

```bash
ssh root@220.154.3.166 "
cd /data/mms-platform
.venv/bin/pip install pandas
"
```

---

## 代码同步矩阵对比

| 同步内容 | 方法一：GitLab CI/CD | 方法二：rsync 手动 | 方法三：Python 直接 |
|---------|---------------------|------------------|------------------|
| **Python 源码** | ✓ 全部同步 | ✓ 选择性同步 | ✓ 最小同步 |
| **前端代码** | ✓ 构建后同步 | ⚠️ 需单独处理 | ✗ 不同步 |
| **配置文件** | ✓ 同步 | ✓ 同步 | ⚠️ 可能遗漏 |
| **依赖安装** | ✓ 自动安装 | ⚠️ 需手动触发 | ✗ 不处理 |
| **数据库迁移** | ✓ 自动运行 | ⚠️ 需手动运行 | ✗ 不处理 |
| **测试运行** | ✓ 部署前测试 | ✗ 不测试 | ✗ 不测试 |
| **Git 记录** | ✓ 有版本号 | ⚠️ 可能没有 | ⚠️ 可能没有 |

---

## 推荐使用场景

### 🌟 方法一：GitLab CI/CD（70% 场景）

**适合：**
- ✅ 正式版本发布
- ✅ 功能开发完成
- ✅ 多人协作项目
- ✅ 需要代码审查
- ✅ 有测试覆盖

**工作流：**
```
开发 → 本地测试 → Git 提交 → Push → 自动部署 → 验证
```

**检查清单：**
- [ ] 本地测试通过
- [ ] Git commit message 清晰
- [ ] 已推送到正确分支
- [ ] 等待 Pipeline 完成
- [ ] 验证生产环境

---

### 🔥 方法二：rsync 手动（20% 场景）

**适合：**
- ✅ 快速迭代开发
- ✅ 验证修复效果
- ✅ 后端代码修改
- ✅ GitLab 不可用时

**工作流：**
```
开发 → 快速部署 → 验证 → 补充提交
```

**检查清单：**
- [ ] 确认修改范围
- [ ] 记住修改的文件
- [ ] 部署后验证功能
- [ ] **务必补充 Git 提交**

---

### 🛠️ 方法三：Python 直接（10% 场景）

**适合：**
- ✅ 紧急生产修复
- ✅ 单文件小改动
- ✅ 反复调试测试
- ✅ Docker 构建失败

**工作流：**
```
修改 → 同步单文件 → 重启 → 验证 → 立即提交
```

**检查清单：**
- [ ] 只修改了 .py 文件
- [ ] 没有新增依赖
- [ ] 验证功能正常
- [ ] **立即 Git 提交**（避免丢失）

---

## 最佳实践建议

### 1. 日常开发流程

```bash
# 第1天：功能开发（使用方法二）
vim src/match_service/api/routes.py
./scripts/quick_deploy_backend.sh  # 快速验证
git add .
git commit -m "feat: 添加新接口"

# 第2天：继续迭代（使用方法二）
vim src/match_service/api/routes.py
./scripts/quick_deploy_backend.sh
git add .
git commit -m "feat: 完善接口逻辑"

# 第3天：准备发布（使用方法一）
# 本地完整测试
poetry run pytest tests/ -v

# 推送触发 CI/CD
git push origin main

# 等待自动部署完成
# 验证生产环境
```

### 2. 紧急修复流程

```bash
# 1. 立即修复（使用方法三）
vim src/match_service/api/routes.py
rsync -avz src/match_service/api/routes.py \
  root@220.154.3.166:/data/mms-platform/src/match_service/api/
ssh root@220.154.3.166 "pkill -f uvicorn && ... 重启"

# 2. 验证修复
curl http://220.154.3.166:9100/api/test

# 3. 立即提交（避免丢失）
git add .
git commit -m "hotfix: 紧急修复 XXX 问题"
git push origin main
```

### 3. 代码同步检查表

**每次部署后必查：**
- [ ] VPS 代码版本与本地一致
- [ ] 服务正常运行（ps aux | grep uvicorn）
- [ ] 关键 API 测试通过
- [ ] 日志无错误（tail logs/uvicorn.log）

**定期检查（每周）：**
- [ ] VPS 上的代码有对应的 Git commit
- [ ] 清理未使用的旧代码
- [ ] 检查 .env 配置是否最新

---

## 总结

| 维度 | 方法一 | 方法二 | 方法三 |
|------|--------|--------|--------|
| **速度** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **安全** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| **可追溯** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ |
| **灵活性** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **推荐度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |

**核心原则：**
1. 🌟 **优先使用方法一**（GitLab CI/CD）- 安全可靠
2. 🔥 **开发期用方法二**（rsync 手动）- 快速迭代
3. 🛠️ **紧急时用方法三**（Python 直接）- 分秒必争
4. 📝 **无论哪种，都要 Git 提交** - 保证代码可追溯

---

**文档版本**: v1.0  
**最后更新**: 2026-08-21  
**维护者**: MMS Platform 团队

# 工作流程

> MMS 平台开发、测试、部署、运维工作流程

## 开发工作流

### 1. 环境搭建

```bash
# 克隆项目
cd /path/to/mms_platform

# 后端环境
poetry install
poetry shell

# 前端环境
cd frontend
npm install

# 数据库准备
docker run -d --name mms-postgres \
  -e POSTGRES_DB=acrac_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 15432:5432 \
  postgres:15-alpine

# 运行迁移
poetry run alembic upgrade head
```

### 2. 开发循环

```
┌────────────────────────────────────────────────┐
│ 1. 需求分析                                     │
│    - 理解业务需求                               │
│    - 设计技术方案                               │
│    - 评估影响范围                               │
└────────────┬───────────────────────────────────┘
             ↓
┌────────────────────────────────────────────────┐
│ 2. 编写代码                                     │
│    - 遵循项目规范                               │
│    - 更新相关文档                               │
│    - 编写单元测试                               │
└────────────┬───────────────────────────────────┘
             ↓
┌────────────────────────────────────────────────┐
│ 3. 本地验证                                     │
│    - 运行测试套件                               │
│    - 启动服务检查                               │
│    - 手动功能测试                               │
└────────────┬───────────────────────────────────┘
             ↓
┌────────────────────────────────────────────────┐
│ 4. 提交代码                                     │
│    - Git commit (语义化提交信息)                 │
│    - 推送到远程仓库                             │
│    - 创建 Pull Request                         │
└────────────┬───────────────────────────────────┘
             ↓
┌────────────────────────────────────────────────┐
│ 5. 代码审查                                     │
│    - 同行评审                                   │
│    - 测试覆盖检查                               │
│    - 合并到主分支                               │
└────────────────────────────────────────────────┘
```

### 3. 常见开发任务

#### 添加新词条
```bash
# 1. 连接数据库
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db

# 2. 插入词条
INSERT INTO nlp_medical_dict (word, type, enable) 
VALUES ('肺动脉', 'body_part', 0);

# 3. 重启服务加载词库
./scripts/stop.sh && ./scripts/start.sh

# 4. 验证
curl -X POST http://localhost:9100/api/match \
  -H "Content-Type: application/json" \
  -d '{"text": "肺动脉MRA", "modality": "MR", "version": "V3.8.2"}'
```

#### 添加短语映射
```sql
-- 统一别名表达
INSERT INTO nlp_phrase_map (src_process, dst_process, modality, version)
VALUES ('脑袋', '头部', 'CT', 'V3.8.2');

-- 重启服务
./scripts/stop.sh && ./scripts/start.sh
```

#### 添加消歧规则
```sql
-- 拆分组合检查
INSERT INTO nlp_ambiguity (src_process, dst_process, modality, version)
VALUES ('平扫增强', '平扫 增强', 'CT', 'V3.8.2');
```

#### 修改匹配引擎
```bash
# 1. 修改引擎代码
vim src/match_service/engine/match_engine_v2/orchestrator.py

# 2. 运行引擎测试
poetry run pytest tests/engine/test_match_engine_v2.py -v

# 3. 手动测试
poetry run python -c "
from match_service.engine.match_engine_v2 import MatchEngineOrchestrator
from match_service.db import get_engine
import asyncio

async def test():
    engine = await get_engine()
    orch = MatchEngineOrchestrator(engine)
    await orch.initialize()
    result = orch.match('CT头部平扫', 'CT', 'V3.8.2')
    print(result)
    await engine.dispose()

asyncio.run(test())
"
```

#### 添加 API 端点
```python
# src/match_service/api/routes.py
@router.post("/new-endpoint")
async def new_endpoint(req: NewRequest):
    # 实现逻辑
    return {"result": "success"}
```

```bash
# 验证
curl -X POST http://localhost:9100/api/new-endpoint \
  -H "Content-Type: application/json" \
  -d '{"param": "value"}'
```

#### 数据库迁移
```bash
# 1. 修改模型
vim src/match_service/cache/models.py

# 2. 生成迁移
poetry run alembic revision --autogenerate -m "add new column"

# 3. 检查生成的迁移文件
cat migrations/versions/xxx_add_new_column.py

# 4. 应用迁移
poetry run alembic upgrade head

# 5. 回滚（如有问题）
poetry run alembic downgrade -1
```

---

## 测试工作流

### 1. 测试层级

```
┌────────────────────────────────────────────────┐
│ 单元测试 (Unit Tests)                           │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • 测试单个函数/类                               │
│ • Mock 外部依赖                                │
│ • 快速执行 (< 1 秒)                            │
│                                                │
│ 示例:                                          │
│ - test_preprocess_service.py                   │
│ - test_tokenizer_service.py                    │
│ - test_disambiguation_service.py               │
└────────────────────────────────────────────────┘

┌────────────────────────────────────────────────┐
│ 集成测试 (Integration Tests)                    │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • 测试模块间协作                               │
│ • 使用真实数据库                               │
│ • 中等执行时间 (1-10 秒)                       │
│                                                │
│ 示例:                                          │
│ - test_match_engine_v2.py                      │
│ - test_cache_service.py                        │
│ - test_dispatcher.py                           │
└────────────────────────────────────────────────┘

┌────────────────────────────────────────────────┐
│ 端到端测试 (E2E Tests)                          │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • 测试完整用户场景                             │
│ • 启动真实服务                                 │
│ • 较慢执行 (10+ 秒)                            │
│                                                │
│ 示例:                                          │
│ - test_api_endpoints.py                        │
│ - test_legacy_adapter.py                       │
│ - test_frontend_build.sh                       │
└────────────────────────────────────────────────┘
```

### 2. 运行测试

```bash
# 完整测试套件（推荐）
./scripts/test-all.sh

# 仅后端测试
poetry run pytest tests/ -v

# 仅引擎测试
poetry run pytest tests/engine/ -v

# 单个测试文件
poetry run pytest tests/engine/test_match_engine_v2.py -v

# 单个测试函数
poetry run pytest tests/engine/test_match_engine_v2.py::test_v2_has_results -v

# 带关键词的测试
poetry run pytest tests/ -k "bilateral" -v

# 显示打印输出
poetry run pytest tests/ -v -s

# 生成覆盖率报告
poetry run pytest tests/ --cov=match_service --cov-report=html
```

### 3. 测试驱动开发 (TDD)

```
┌────────────────────────────────────────────────┐
│ 1. 编写失败测试                                 │
│    def test_new_feature():                     │
│        result = my_function()                  │
│        assert result == expected               │
└────────────┬───────────────────────────────────┘
             ↓ (测试失败 - Red)
┌────────────────────────────────────────────────┐
│ 2. 编写最小实现                                 │
│    def my_function():                          │
│        return expected  # 最小实现              │
└────────────┬───────────────────────────────────┘
             ↓ (测试通过 - Green)
┌────────────────────────────────────────────────┐
│ 3. 重构优化                                     │
│    def my_function():                          │
│        # 优化实现，保持测试通过                 │
│        return optimized_result                 │
└────────────┬───────────────────────────────────┘
             ↓ (测试仍通过 - Refactor)
             └─→ 循环到步骤 1
```

### 4. 回归测试

```bash
# Golden 测试（快照测试）
poetry run pytest tests/engine/test_match_engine_v2_performance.py -v

# 更新快照（算法改进后）
poetry run pytest tests/engine/test_match_engine_v2_performance.py --update-golden

# P1/P2 验证测试
poetry run python scripts/validate_p1p2_improvement.py
```

---

## 部署工作流

### 1. 开发环境部署

```bash
# 一键启动
./scripts/start.sh

# 访问服务
open http://localhost:3100  # 前端
open http://localhost:9100/docs  # 后端 API 文档
```

### 2. 生产环境部署

#### 方案 A: 单机部署

```bash
# 1. 构建前端
cd frontend
npm run build
cd ..

# 2. 配置环境变量
cp .env.example .env
vim .env  # 修改生产配置

# 3. 运行数据库迁移
poetry run alembic upgrade head

# 4. 启动服务
poetry run gunicorn match_service.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:9100

# 5. 配置 Systemd（可选）
sudo cat > /etc/systemd/system/mms.service << 'EOF'
[Unit]
Description=MMS Match Service
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/opt/mms_platform
Environment="PATH=/opt/mms_platform/.venv/bin"
ExecStart=/opt/mms_platform/.venv/bin/gunicorn match_service.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:9100

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable mms
sudo systemctl start mms
```

#### 方案 B: Docker 部署

```bash
# 1. 构建镜像
docker build -t mms-service:latest .

# 2. 启动完整栈
docker-compose up -d

# 3. 查看日志
docker-compose logs -f match-service

# 4. 健康检查
curl http://localhost:9100/api/health
```

#### 方案 C: K8s 部署

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mms-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mms-service
  template:
    metadata:
      labels:
        app: mms-service
    spec:
      containers:
      - name: mms
        image: mms-service:latest
        ports:
        - containerPort: 9100
        env:
        - name: MATCH_SVC_DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: mms-secrets
              key: database-url
        readinessProbe:
          httpGet:
            path: /api/health
            port: 9100
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: mms-service
spec:
  selector:
    app: mms-service
  ports:
  - port: 9100
    targetPort: 9100
  type: LoadBalancer
```

```bash
# 部署
kubectl apply -f k8s/

# 查看状态
kubectl get pods -l app=mms-service
kubectl logs -f deployment/mms-service
```

### 3. 灰度部署

```bash
# Nginx 配置
# nginx-canary.conf
upstream mms_old {
    server 127.0.0.1:50000;  # 旧系统
}

upstream mms_new {
    server 127.0.0.1:9100;   # 新系统
}

# 按 IP 哈希分流 10%
split_clients "${remote_addr}" $backend {
    10%     mms_new;
    *       mms_old;
}

server {
    listen 80;
    server_name api.example.com;

    location /algorithm/ {
        proxy_pass http://$backend;
    }
}

# 启动灰度监控
python scripts/canary_monitor.py \
  --old-url http://127.0.0.1:50000 \
  --new-url http://127.0.0.1:9100 \
  --interval 60
```

**灰度步骤**：
1. 10% 流量（观察 24 小时）
2. 30% 流量（观察 48 小时）
3. 50% 流量（观察 72 小时）
4. 100% 流量（完全切换）

**监控指标**：
- 错误率对比
- 响应时间对比
- 匹配准确率对比
- CPU/内存使用对比

---

## 运维工作流

### 1. 日常监控

```bash
# 健康检查
curl http://localhost:9100/api/health

# 查看版本信息
curl http://localhost:9100/api/rules/snapshot

# 查看缓存统计
curl http://localhost:9100/api/cache/stats

# 查看日志
tail -f logs/match_service.log

# 数据库连接检查
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db -c "SELECT 1;"
```

### 2. 性能优化

```bash
# 查询慢查询
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db << 'EOF'
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC
LIMIT 10;
EOF

# 分析缓存命中率
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db << 'EOF'
SELECT 
  COUNT(*) as total,
  SUM(hit_count) as total_hits,
  AVG(confidence) as avg_confidence
FROM match_cache;
EOF

# 清理过期缓存
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db << 'EOF'
DELETE FROM match_cache WHERE ttl < NOW();
EOF
```

### 3. 热重载

```bash
# 重载引擎（不重启服务）
curl -X POST http://localhost:9100/api/reload

# 清空缓存
curl -X POST http://localhost:9100/api/cache/invalidate \
  -H "Content-Type: application/json" \
  -d '{"modality": null}'

# 按模态清空
curl -X POST http://localhost:9100/api/cache/invalidate \
  -H "Content-Type: application/json" \
  -d '{"modality": "CT"}'
```

### 4. 故障排查

#### 服务无法启动
```bash
# 检查端口占用
lsof -i :9100

# 检查数据库连接
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db

# 检查环境变量
env | grep MATCH_SVC_

# 查看启动日志
journalctl -u mms -n 100
```

#### 匹配结果异常
```bash
# 查看引擎版本
curl http://localhost:9100/api/rules/snapshot

# 检查词表数据
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db << 'EOF'
SELECT 
  (SELECT COUNT(*) FROM nlp_medical_dict) as dict_count,
  (SELECT COUNT(*) FROM nlp_phrase_map) as phrase_count,
  (SELECT COUNT(*) FROM nlp_ambiguity) as ambiguity_count;
EOF

# 手动测试匹配
curl -X POST http://localhost:9100/api/match \
  -H "Content-Type: application/json" \
  -d '{"text": "CT头部平扫", "modality": "CT", "version": "V3.8.2"}' \
  | jq .
```

#### 性能下降
```bash
# 检查数据库连接数
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db << 'EOF'
SELECT count(*) FROM pg_stat_activity;
EOF

# 检查缓存大小
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db << 'EOF'
SELECT pg_size_pretty(pg_total_relation_size('match_cache'));
EOF

# 检查进程资源
top -p $(pgrep -f "uvicorn match_service")
```

### 5. 数据备份

```bash
# 备份数据库
pg_dump -h 127.0.0.1 -p 15432 -U postgres -d acrac_db \
  -f backup_$(date +%Y%m%d).sql

# 仅备份词表
pg_dump -h 127.0.0.1 -p 15432 -U postgres -d acrac_db \
  -t nlp_medical_dict \
  -t nlp_phrase_map \
  -t nlp_ambiguity \
  -f lexicon_backup_$(date +%Y%m%d).sql

# 恢复数据库
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db \
  -f backup_20260807.sql
```

### 6. 版本升级

```bash
# 1. 备份数据库
pg_dump -h 127.0.0.1 -p 15432 -U postgres -d acrac_db \
  -f backup_before_upgrade.sql

# 2. 拉取新代码
git pull origin main

# 3. 安装新依赖
poetry install
cd frontend && npm install && cd ..

# 4. 运行数据库迁移
poetry run alembic upgrade head

# 5. 构建前端
cd frontend && npm run build && cd ..

# 6. 重启服务
sudo systemctl restart mms

# 7. 验证
curl http://localhost:9100/api/health
./scripts/test-all.sh
```

---

## Git 工作流

### 1. 分支策略

```
main                    (主分支，生产环境)
  ↓
develop                 (开发分支，集成环境)
  ├─ feature/xxx        (功能分支)
  ├─ bugfix/xxx         (Bug 修复分支)
  └─ hotfix/xxx         (紧急修复分支)
```

### 2. 提交规范

```bash
# 功能开发
git commit -m "feat: 添加血管成像标准项支持"
git commit -m "feat(engine): 实现双侧推断逻辑"

# Bug 修复
git commit -m "fix: 修复方括号修饰语拆分问题"
git commit -m "fix(P1): 修复 Jieba 全局字典热更新"

# 文档更新
git commit -m "docs: 更新 P1+P2 完成报告"
git commit -m "docs: 添加 OpenWiki 快速入门"

# 测试
git commit -m "test: 添加双侧匹配测试用例"

# 重构
git commit -m "refactor: 提取公共部位映射字典"

# 配置
git commit -m "chore: 更新 .gitignore"
```

### 3. Pull Request 流程

```bash
# 1. 创建功能分支
git checkout -b feature/add-vascular-support

# 2. 开发并提交
git add .
git commit -m "feat: 添加血管成像标准项"

# 3. 推送到远程
git push origin feature/add-vascular-support

# 4. 创建 PR
# 在 GitHub/GitLab 创建 Pull Request

# 5. 代码审查
# 等待团队审查和批准

# 6. 合并到 develop
git checkout develop
git merge feature/add-vascular-support

# 7. 删除分支
git branch -d feature/add-vascular-support
git push origin --delete feature/add-vascular-support
```

---

## 相关文档
- [架构设计](architecture.md) - 系统架构
- [测试策略](testing.md) - 测试详解
- [部署方案](deployment.md) - 部署详解
- [故障排查](troubleshooting.md) - 问题诊断

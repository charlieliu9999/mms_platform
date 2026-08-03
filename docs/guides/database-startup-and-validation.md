# 数据库启动与 Phase 2 验证指南

## 当前状态

✅ **Phase 1 & Phase 2 代码和脚本已完成**  
⏳ **待执行：数据库启动 + SQL 脚本执行 + 验证**

---

## 方式 1：使用 Docker Compose（推荐）

### 步骤 1：启动 Docker

```bash
# macOS
open -a Docker

# 或者从应用程序启动 Docker Desktop
```

等待 Docker 启动完成（菜单栏图标不再转动）。

### 步骤 2：启动数据库

```bash
# 启动 PostgreSQL（单独启动，不启动整个服务）
docker-compose up -d postgres

# 检查状态
docker-compose ps
```

预期输出：
```
NAME                COMMAND                  SERVICE             STATUS
mms_platform-postgres-1   "docker-entrypoint.s…"   postgres            running
```

### 步骤 3：验证数据库连接

```bash
# 测试连接
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_prod -c "SELECT 1"

# 如果提示输入密码，密码是：postgres
```

---

## 方式 2：使用本地 PostgreSQL

如果不想使用 Docker，可以使用本地安装的 PostgreSQL。

### 步骤 1：检查本地 PostgreSQL

```bash
# 检查是否已安装
which psql

# 检查版本
psql --version
```

### 步骤 2：启动 PostgreSQL

```bash
# macOS (使用 Homebrew 安装的)
brew services start postgresql@15

# 或手动启动
pg_ctl -D /usr/local/var/postgresql@15 start
```

### 步骤 3：创建数据库

```bash
# 创建数据库（如果不存在）
createdb -h 127.0.0.1 -p 15432 -U postgres acrac_db

# 或使用 psql
psql -h 127.0.0.1 -p 15432 -U postgres -c "CREATE DATABASE acrac_db"
```

### 步骤 4：更新 .env 配置

确保 `.env` 文件中的数据库 URL 正确：

```bash
MATCH_SVC_DATABASE_URL=postgresql+asyncpg://postgres:password@127.0.0.1:15432/acrac_db
```

---

## 执行 Phase 2 补充脚本

数据库启动后，按以下顺序执行：

### 1. 词库映射补充（优先）

```bash
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db \
  -f migrations/manual/phase2_lexicon_补充.sql
```

**预期输出：**
```
INSERT 0 3
INSERT 0 2
INSERT 0 3
INSERT 0 3
INSERT 0 2
INSERT 0 3
```

### 2. 标准库补充

```bash
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db \
  -f migrations/manual/phase2_standard_补充.sql
```

**预期输出：**
```
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
```

### 3. 验证插入结果

```bash
# 查看新增词库
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db -c "
SELECT word, std_name, pos_type
FROM medical_dict
WHERE word IN ('动静脉双期增强', '原发部位', 'UHR模式')
AND version = 'V3.8.2';
"

# 查看新增标准项
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db -c "
SELECT checkitem_code, checkitem_name
FROM nlp_checkitem_standard
WHERE checkitem_code LIKE '%CTA' OR checkitem_code LIKE '%ARTHROGRAPHY'
AND version = 'V3.8.2'
LIMIT 5;
"
```

---

## 运行验证测试

### 测试 1：10 个缺项匹配测试

```bash
poetry run python scripts/test_missing_items.py
```

**预期结果：**
```
整体匹配率: 10/10 (100.0%)

复合增强：3/3 (100%)
血管专项：3/3 (100%)
特殊造影：3/3 (100%)
高级模式：1/1 (100%)
```

### 测试 2：全量匹配分析（可选）

```bash
poetry run python scripts/analyze_match_results.py
```

这会对 4555 项目进行全量匹配分析，生成详细报告。

---

## 故障排查

### 问题 1：Docker 启动失败

**错误：** `Cannot connect to the Docker daemon`

**解决：**
1. 确认 Docker Desktop 已安装
2. 启动 Docker Desktop 应用
3. 等待启动完成（菜单栏图标停止转动）

### 问题 2：端口冲突

**错误：** `port is already allocated`

**解决：**
```bash
# 查找占用端口的进程
lsof -i :15432

# 停止占用的进程
kill -9 <PID>

# 或使用不同的端口
docker-compose down
# 修改 docker-compose.yml 中的端口映射
docker-compose up -d postgres
```

### 问题 3：数据库连接失败

**错误：** `Connection refused`

**检查步骤：**
```bash
# 1. 确认容器正在运行
docker ps | grep postgres

# 2. 查看容器日志
docker logs mms_platform-postgres-1

# 3. 测试端口
nc -zv 127.0.0.1 15432

# 4. 重启容器
docker-compose restart postgres
```

### 问题 4：SQL 脚本执行失败

**错误：** `duplicate key value violates unique constraint`

**原因：** 数据已存在

**解决：** 这是正常的，脚本使用了 `ON CONFLICT DO NOTHING`，重复数据会被忽略

### 问题 5：测试脚本失败

**错误：** 匹配率未提升

**排查：**
```bash
# 1. 确认数据已插入
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db -c "
SELECT COUNT(*) FROM medical_dict WHERE word = '动静脉双期增强';
"

# 2. 清理引擎缓存（重启服务）
pkill -f "uvicorn match_service.main:app"

# 3. 重新运行测试
poetry run python scripts/test_missing_items.py
```

---

## 快速启动（一键执行）

创建一个快速启动脚本：

```bash
#!/bin/bash
# scripts/phase2_validate.sh

set -e

echo "=== Phase 2 验证脚本 ==="
echo

# 1. 启动数据库
echo "1. 启动数据库..."
docker-compose up -d postgres
sleep 5

# 2. 执行词库补充
echo "2. 执行词库补充..."
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db \
  -f migrations/manual/phase2_lexicon_补充.sql

# 3. 执行标准库补充
echo "3. 执行标准库补充..."
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db \
  -f migrations/manual/phase2_standard_补充.sql

# 4. 运行验证测试
echo "4. 运行验证测试..."
poetry run python scripts/test_missing_items.py

echo
echo "=== 验证完成 ==="
```

使用方法：
```bash
chmod +x scripts/phase2_validate.sh
./scripts/phase2_validate.sh
```

---

## 预期结果

完成所有步骤后，应该看到：

✅ 词库新增 17 条记录  
✅ 标准库新增 5 条记录  
✅ 测试匹配率 100% (10/10)  
✅ 全量匹配率提升约 20%  

---

## 下一步

Phase 2 验证通过后，可以选择继续：

- **Phase 3:** 模态整合（IR→DSA, OTHER 细化）
- **Phase 4:** 词库深度优化（降级匹配调优）
- **生产部署:** 将改进应用到生产环境

---

**创建时间：** 2026-08-04  
**最后更新：** 2026-08-04

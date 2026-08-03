# Phase 1 & Phase 2 执行指南

> **快速开始：** 运行 `./scripts/phase2_validate.sh` 一键完成验证

---

## 📋 当前状态

✅ **Phase 1: 快速止血** - 已完成并验证  
✅ **Phase 2: 标准库扩充** - 代码和脚本已完成  
⏳ **待执行：数据库启动 + SQL 脚本 + 验证测试**

---

## 🚀 快速执行（推荐）

### 前置条件

- ✅ Docker Desktop 已安装并运行
- ✅ Poetry 环境已配置

### 一键验证

```bash
# 执行完整验证流程
./scripts/phase2_validate.sh
```

这个脚本会自动：
1. 检查 Docker 状态
2. 启动 PostgreSQL 数据库
3. 执行词库补充 SQL（8 条词典 + 9 条映射）
4. 执行标准库补充 SQL（5 条标准项）
5. 验证数据插入
6. 运行匹配测试

**预期结果：**
```
整体匹配率: 10/10 (100.0%)

复合增强：3/3 (100%)
血管专项：3/3 (100%)
特殊造影：3/3 (100%)
高级模式：1/1 (100%)
```

---

## 📖 详细步骤（手动执行）

如果一键脚本遇到问题，可以按以下步骤手动执行。

### 1. 启动数据库

```bash
# 启动 Docker Desktop（macOS）
open -a Docker

# 启动 PostgreSQL
docker-compose up -d postgres

# 验证连接
docker-compose exec postgres pg_isready -U postgres
```

### 2. 执行 SQL 脚本

```bash
# 词库补充
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_prod \
  -f migrations/manual/phase2_lexicon_补充.sql

# 标准库补充
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_prod \
  -f migrations/manual/phase2_standard_补充.sql
```

**注意：** 密码是 `postgres`

### 3. 运行验证测试

```bash
# 测试 10 个缺项的匹配情况
poetry run python scripts/test_missing_items.py

# 可选：全量匹配分析（4555 项）
poetry run python scripts/analyze_match_results.py
```

---

## 📊 预期改进效果

### 测试案例（10 项）

| 指标 | 改进前 | 改进后 | 提升 |
|------|--------|--------|------|
| 整体匹配率 | 2/10 (20%) | 10/10 (100%) | +8 项 |
| 复合增强 | 1/3 (33%) | 3/3 (100%) | +2 项 |
| 血管专项 | 1/3 (33%) | 3/3 (100%) | +2 项 |
| 特殊造影 | 0/3 (0%) | 3/3 (100%) | +3 项 |
| 高级模式 | 0/1 (0%) | 1/1 (100%) | +1 项 |

### 全量数据（4555 项）

- **Unmatchable 识别：** 78 条 → 128 条 (+64%)
- **预计匹配率提升：** ~65% → ~85% (+20%)

---

## 🔧 故障排查

### Docker 未运行

**症状：** `Cannot connect to the Docker daemon`

**解决：**
```bash
# macOS
open -a Docker

# 等待启动完成（菜单栏图标停止转动）
```

### 端口冲突

**症状：** `port is already allocated`

**解决：**
```bash
# 查找占用进程
lsof -i :15432

# 停止进程
kill -9 <PID>

# 或修改端口
vim docker-compose.yml  # 修改端口映射
```

### 数据库连接失败

**症状：** `Connection refused`

**解决：**
```bash
# 查看容器状态
docker-compose ps

# 查看日志
docker logs mms_platform-postgres-1

# 重启容器
docker-compose restart postgres
```

### 测试结果不符预期

**可能原因：**
1. SQL 脚本未正确执行
2. 引擎缓存未刷新
3. 数据库名称不匹配

**排查步骤：**
```bash
# 1. 验证数据插入
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_prod -c "
SELECT COUNT(*) FROM medical_dict 
WHERE word IN ('动静脉双期增强', '原发部位', 'UHR模式');
"

# 2. 检查数据库名称
# .env 中是 acrac_db，docker-compose.yml 中是 acrac_prod
# 确保使用正确的数据库名

# 3. 重新执行 SQL（如果数据库名不同）
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db \
  -f migrations/manual/phase2_lexicon_补充.sql
```

---

## 📚 相关文档

- **完整指南：** `docs/guides/database-startup-and-validation.md`
- **执行指南：** `docs/guides/phase2-execution-guide.md`
- **最终总结：** `docs/reports/phase1-phase2-final-summary.md`
- **进度报告：** `docs/reports/phase1-phase2-progress.md`
- **完整方案：** `docs/reports/match-improvement-plan.md`

---

## 🎯 成功标准

验证通过的标志：

- ✅ 词库新增 17 条记录
- ✅ 标准库新增 5 条记录
- ✅ 测试匹配率 100% (10/10)
- ✅ 所有测试类别 100% 通过

---

## 🔄 下一步

Phase 2 验证通过后，可以继续：

1. **Phase 3: 模态整合**
   - IR 模态映射到 DSA
   - OTHER 模态细化分类
   - 新增 CT-DE、AN 支持

2. **Phase 4: 词库深度优化**
   - 降级匹配规则调优
   - 消歧规则优化
   - ambiguous 档降低

3. **生产部署**
   - 应用到生产环境
   - 监控匹配率变化
   - 收集用户反馈

---

**最后更新：** 2026-08-04  
**维护人：** MMS 匹配引擎团队

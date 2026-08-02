# MMS平台快速修复指南

## 🚨 关键问题汇总

本项目前端存在 **2个阻断性缺陷**，影响核心功能使用：

1. **匹配算法页面无法显示结果** - 前后端数据格式不匹配
2. **标准项目页面模态筛选失效** - DR/RF/US等模态无法筛选

---

## ⚡ 一键修复（推荐）

```bash
# 执行自动修复脚本
./scripts/fix_critical_issues.sh
```

脚本会自动完成：
- ✅ 数据库模态名称标准化（X线→DR/RF, 超声→US）
- ✅ 前端API数据适配层修复
- ✅ 前端重新构建

---

## 🔧 手动修复步骤

如果自动脚本失败，请手动执行以下步骤：

### 修复1: 标准项目模态映射

```bash
# 连接数据库
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db

# 执行SQL
UPDATE nlp_checkitem_standard
SET modality_name = CASE
  WHEN modality_name = 'X线' AND (scan_name LIKE '%透视%' OR scan_name LIKE '%造影%') THEN 'RF'
  WHEN modality_name = 'X线' THEN 'DR'
  WHEN modality_name = '超声' OR modality_name = '彩超' THEN 'US'
  WHEN modality_name = '乳腺X线摄影' THEN 'MG'
  ELSE modality_name
END;

# 验证结果
SELECT modality_name, COUNT(*) FROM nlp_checkitem_standard GROUP BY modality_name;
```

预期输出：
```
 modality_name | count
---------------+-------
 CT            |  7589
 MR            |  6326
 DR            |  4200  ← 从"X线"转换而来
 RF            |   552  ← 从"X线"转换而来
 US            |   XXX  ← 从"超声"转换而来
 DSA           |    28
```

### 修复2: 前端匹配算法数据适配

编辑 `frontend/src/services/matchService.ts`：

```typescript
// 原代码（第56-58行）
matchOne: (data: MatchRequest): Promise<MatchResult> =>
  apiClient.post('/match', data),

// 修改为
matchOne: (data: MatchRequest): Promise<any> =>
  apiClient.post('/match', data).then((res: any) => ({
    ...res.result,
    matched: res.result.num_standard > 0,
    confidence: res.result.confidence || (res.result.score ? res.result.score / 10 : 0),
    data: res.result.data,
    rule_version: res.rule_version
  })),
```

重新构建前端：

```bash
cd frontend
npm run build
cd ..
```

---

## ✅ 验证修复

### 1. 测试匹配算法页面

```bash
# API测试
curl -X POST http://localhost:9100/api/match \
  -H 'Content-Type: application/json' \
  -d '{"name":"CT头部平扫","modality":"CT"}' | jq '.result.data'

# 预期输出：应该看到标准项目列表
```

### 2. 测试标准项目筛选

```bash
# DR模态（X线检查）
curl 'http://localhost:9100/api/admin/standard-items?modality=DR&page_size=5' | jq '.total'
# 预期输出：应该大于0（约4200条）

# US模态（超声检查）
curl 'http://localhost:9100/api/admin/standard-items?modality=US&page_size=5' | jq '.total'
# 预期输出：应该大于0
```

### 3. 前端界面验证

```bash
# 重启服务
./scripts/stop.sh
./scripts/start.sh

# 打开浏览器
open http://localhost:3100
```

验证项目：
- [ ] 访问"匹配算法"页面，输入"CT头部平扫"，点击"运行单项算法匹配"
- [ ] 应该看到匹配结果，包括信心度、标准项目列表
- [ ] 访问"标准项目库"页面，点击"DR"模态按钮
- [ ] 应该筛选出X线相关的检查项目（约4200条）
- [ ] 点击"US"模态按钮，应该筛选出超声相关项目

---

## 🐛 常见问题

### Q1: 数据库连接失败

**错误**: `psql: could not connect to server`

**解决**:
```bash
# 检查PostgreSQL是否运行
docker ps | grep postgres
# 或
brew services list | grep postgresql

# 启动PostgreSQL
docker start postgres-container
# 或
brew services start postgresql
```

### Q2: 前端构建失败

**错误**: TypeScript编译错误

**解决**:
```bash
cd frontend
npx tsc --noEmit  # 查看详细错误
npm install       # 重新安装依赖
```

### Q3: 修复后仍然无法筛选

**原因**: 浏览器缓存了旧的前端代码

**解决**:
- 硬刷新: `Ctrl+Shift+R` (Windows) 或 `Cmd+Shift+R` (Mac)
- 清除浏览器缓存并重新加载

---

## 📊 修复前后对比

| 功能 | 修复前 | 修复后 |
|------|--------|--------|
| 匹配算法测试 | ❌ 无法显示结果 | ✅ 正常显示匹配项目和信心度 |
| DR模态筛选 | ❌ 0条结果 | ✅ ~4200条X线检查项目 |
| RF模态筛选 | ❌ 0条结果 | ✅ ~552条透视/造影项目 |
| US模态筛选 | ❌ 0条结果 | ✅ 超声检查项目 |

---

## 📝 后续优化建议

修复完成后，建议进一步优化：

1. **评测系统指标修复** - 修复 `accuracy`, `f1_score` 为空的问题
2. **错误处理优化** - 添加友好的错误提示信息
3. **移除硬编码默认值** - Dashboard统计数据改为真实API返回
4. **暗色模式对比度优化** - 提升文字和边框的可读性

详细信息请参考 `docs/reports/2026-08-02-frontend-comprehensive-audit.md`

---

## 🆘 需要帮助？

- 查看完整审查报告: `docs/reports/2026-08-02-frontend-comprehensive-audit.md`
- 查看项目文档: `CLAUDE.md`
- 查看后端API文档: http://localhost:9100/docs

---

**修复准备时间**: < 5分钟  
**预计修复时间**: 2-3分钟（自动脚本） / 10-15分钟（手动修复）  
**影响范围**: 前端页面 + 数据库1个表  
**风险等级**: 低（有备份机制，可回滚）

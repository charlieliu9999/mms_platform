# Phase 2 补充执行指南

## 概述

本指南说明如何执行 Phase 2 的词库和标准库补充，以提升医学影像检查项目的匹配率。

---

## 前置条件

1. **数据库已启动**
   ```bash
   docker ps | grep postgres
   # 或
   pg_isready -h 127.0.0.1 -p 15432
   ```

2. **数据库可访问**
   ```bash
   psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db -c "SELECT 1"
   ```

---

## 执行步骤

### 步骤 1：词库映射补充（优先级高，快速见效）

执行 SQL 脚本：

```bash
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db \
  -f migrations/manual/phase2_lexicon_补充.sql
```

**预期效果：**
- 新增 8 条医学词典（medical_dict）
- 新增 9 条短语映射（phrase_map）
- 提升 3 项匹配：
  - ✅ CT腹部盆腔(平扫+动静脉双期增强)
  - ✅ CT原发部位及区域淋巴结(平扫+增强)
  - ✅ CT颞骨(超高分辨率UHR模式)

**验证方法：**

```bash
# 验证词库新增
poetry run python -c "
import asyncio
from match_service.db import get_engine
from sqlalchemy import text

async def verify():
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text('''
            SELECT COUNT(*) FROM medical_dict 
            WHERE word IN ('动静脉双期增强', '原发部位', 'UHR模式')
            AND version = 'V3.8.2'
        '''))
        count = result.scalar()
        print(f'医学词典新增: {count}/3 条')
    await engine.dispose()

asyncio.run(verify())
"
```

### 步骤 2：标准库补充（需要数据验证）

**重要：执行前先验证部位编码**

```bash
# 查看现有血管部位编码
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db -c "
SELECT DISTINCT two_level_name 
FROM nlp_checkitem_standard 
WHERE modality_code = '2' 
AND two_level_name LIKE '%血管%'
ORDER BY two_level_name;
"

# 查看现有肩关节项目
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db -c "
SELECT checkitem_name, two_level_name, scan_name
FROM nlp_checkitem_standard 
WHERE two_level_name = '肩关节'
LIMIT 5;
"
```

执行补充脚本：

```bash
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db \
  -f migrations/manual/phase2_standard_补充.sql
```

**预期效果：**
- 新增 5 条标准项目（nlp_checkitem_standard）
- 提升 5 项匹配：
  - ✅ CT小肠血管成像(CTA)
  - ✅ CT肝脏血管成像(CTA)
  - ✅ CT脊柱局部(脊髓造影)
  - ✅ CT肩关节(直接造影)
  - ✅ MR肩关节(直接造影)

### 步骤 3：重启匹配引擎（刷新缓存）

```bash
# 如果引擎正在运行，需要重启以加载新数据
pkill -f "uvicorn match_service.main:app" || true
poetry run uvicorn match_service.main:app --reload --port 9100 &
```

### 步骤 4：验证改进效果

运行测试脚本：

```bash
poetry run python scripts/test_missing_items.py
```

**预期结果：**

| 指标 | 补充前 | 补充后 | 提升 |
|------|--------|--------|------|
| 匹配率 | 2/10 (20%) | 10/10 (100%) | +8 项 |
| 复合增强 | 1/3 (33%) | 3/3 (100%) | +2 项 |
| 血管专项 | 1/3 (33%) | 3/3 (100%) | +2 项 |
| 特殊造影 | 0/3 (0%) | 3/3 (100%) | +3 项 |
| 高级模式 | 0/1 (0%) | 1/1 (100%) | +1 项 |

---

## 全量验证（可选）

对 4555 项目全量数据进行匹配，验证整体改进效果：

```bash
poetry run python scripts/analyze_match_results.py
```

**关注指标：**
- 标准库缺项数量减少
- 词库缺项数量减少
- 整体匹配率提升

---

## 回滚方案

如果补充后出现问题，可以回滚：

### 回滚词库映射

```sql
-- 删除新增的医学词典
DELETE FROM medical_dict
WHERE word IN (
    '动静脉双期增强', '脊髓造影', '直接造影',
    '原发部位', '区域淋巴结',
    'UHR模式', '超高分辨率', 'UHR'
)
AND version = 'V3.8.2';

-- 删除新增的短语映射
DELETE FROM phrase_map
WHERE src IN (
    '动静脉双期', '双期增强', '动静脉双期扫描',
    '原发灶', '原发病灶',
    '淋巴结区域', '区域淋巴'
)
AND version = 'V3.8.2';
```

### 回滚标准库

```sql
-- 删除新增的标准项
DELETE FROM nlp_checkitem_standard
WHERE checkitem_code IN (
    'CT_SMALLINTESTINE_CTA',
    'CT_LIVER_CTA',
    'CT_SPINE_LOCAL_MYELOGRAPHY',
    'CT_SHOULDER_DIRECT_ARTHROGRAPHY',
    'MR_SHOULDER_DIRECT_ARTHROGRAPHY'
)
AND version = 'V3.8.2';
```

---

## 故障排查

### 问题 1：SQL 脚本执行失败

**错误：** `duplicate key value violates unique constraint`

**原因：** 词条已存在

**解决：** 检查是否已执行过脚本，使用 `ON CONFLICT DO NOTHING` 忽略重复

### 问题 2：匹配率未提升

**可能原因：**
1. 引擎未重启，缓存未刷新
2. 词库数据未正确加载
3. 部位编码不匹配

**排查步骤：**

```bash
# 1. 确认数据已插入
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db -c "
SELECT COUNT(*) FROM medical_dict WHERE word = '动静脉双期增强';
"

# 2. 检查引擎日志
tail -f /path/to/engine.log | grep "动静脉"

# 3. 运行调试匹配
poetry run python -c "
from match_service.engine.match_engine_v2.orchestrator import MatchEngineOrchestrator
from match_service.db import get_engine
import asyncio

async def debug():
    engine = get_engine()
    match_engine = MatchEngineOrchestrator(engine)
    await match_engine.initialize()
    
    trace = {}
    result = match_engine.match('CT腹部盆腔(平扫+动静脉双期增强)', 'CT', trace=trace)
    print('Trace:', trace.get('3-make_tree'))
    
    await engine.dispose()

asyncio.run(debug())
"
```

### 问题 3：部位编码不一致

**症状：** 标准项已添加，但仍无法匹配

**原因：** `two_level_name` 与引擎解析出的部位不一致

**解决：**

```sql
-- 查看引擎实际解析的部位名
-- （需要从匹配 trace 日志中获取）

-- 更新标准项的部位名
UPDATE nlp_checkitem_standard
SET two_level_name = '实际解析的部位名'
WHERE checkitem_code = 'CT_SMALLINTESTINE_CTA';
```

---

## 下一步

完成 Phase 2 后，继续执行：

1. **Phase 3: 模态整合**（IR→DSA, OTHER 细化）
2. **Phase 4: 词库深度优化**（降级匹配调优）
3. **全量评估**（4555 项目完整报告）

---

## 相关文档

- 完整方案：`docs/reports/match-improvement-plan.md`
- 进度报告：`docs/reports/phase1-phase2-progress.md`
- 测试脚本：`scripts/test_missing_items.py`
- Phase 1 验证：`docs/reports/phase1-validation-*.txt`

---

**创建时间：** 2026-08-04  
**维护人：** MMS 匹配引擎团队

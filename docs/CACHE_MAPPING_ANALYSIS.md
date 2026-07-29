# 生产服务器映射缓存表分析与同步方案

> 基于生产数据库 `da_checkitem_map` 表的分析
> 
> 创建时间：2026-07-29

---

## 一、映射缓存表概述

### 1.1 表结构

**表名**: `da_checkitem_map` (检查项目映射表)

**数据库**: `rimag_data@210.12.11.251:26306`

**字段说明**:

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `id` | int | 主键 | 1 |
| `unique_key` | varchar(255) | MD5唯一键 | `000622cc718ea9a17c1c635fcefe2cac` |
| `original_checkitem` | varchar(190) | **原始检查项目** | `CT平扫(颅脑);胸` |
| `modality` | varchar(255) | **模态** | `CT` |
| `standard_checkitem_code` | varchar(190) | **标准编码** | `2101011000` |
| `standard_checkitem_name` | varchar(190) | **标准名称** | `* CT颅脑（平扫）` |
| `standard_modality` | varchar(255) | 标准模态 | `CT` |
| `compound_num` | int | 复合项目数量 | `2` |
| `standard_version` | varchar(255) | 标准版本 | `V3.0` |
| `operate_user` | varchar(255) | 操作用户 | `admin` |
| `is_valid` | int | **是否有效** | `1` (有效) / `0` (无效) |
| `create_time` | datetime | 创建时间 | `2023-05-09 15:13:40` |
| `update_time` | datetime | 更新时间 | `2023-05-09 15:13:57` |

### 1.2 数据规模

| 维度 | 数量 | 说明 |
|------|------|------|
| **总记录数** | **376 条** | 所有映射记录 |
| **有效记录** | **237 条** | `is_valid=1` |
| **无效记录** | 139 条 | `is_valid=0` (历史版本) |
| **唯一原始项目** | ~200 个 | 去重后的原始检查项目 |

### 1.3 按模态分布

| 模态 | 总记录数 | 有效记录数 | 占比 |
|------|---------|-----------|------|
| **CT** | 296 | 184 | 77.6% |
| **MR** | 78 | 51 | 21.5% |
| **DR** | 1 | 1 | 0.4% |
| **空** | 1 | 1 | 0.4% |

---

## 二、映射缓存的作用

### 2.1 L1 缓存层设计

```
用户请求
    ↓
┌──────────────────────────────────────┐
│ L1: 映射缓存表 (da_checkitem_map)    │  ← O(1) 查表
│  - 已匹配的原始项目 → 标准项目        │
│  - 237 条有效映射                     │
│  - TTL: 永久（人工维护）              │
└──────────────────────────────────────┘
    ↓ 未命中
┌──────────────────────────────────────┐
│ L2: 匹配算法引擎                      │  ← 10步 NLP Pipeline
│  - 词表: 3,716 条                     │
│  - 消歧规则: 51 条                    │
│  - 响应时间: 50-200ms                 │
└──────────────────────────────────────┘
    ↓ 匹配成功
┌──────────────────────────────────────┐
│ L3: 写回缓存 (可选)                   │  ← 人工审核后写入
│  - 高置信度结果                       │
│  - 人工审核通过                       │
└──────────────────────────────────────┘
```

### 2.2 优势

1. **性能优化** ⚡
   - L1 缓存: O(1) 查表，响应时间 < 10ms
   - L2 算法: 10步 Pipeline，响应时间 50-200ms
   - **性能提升**: 10-20 倍

2. **准确率保障** ✅
   - 缓存记录经过人工审核（`operate_user` 字段）
   - 准确率 100%（人工确认）
   - 算法准确率 95%（仍有 5% 误差）

3. **降低算法负载** 📉
   - 常见项目命中缓存
   - 算法仅处理新项目或低频项目

### 2.3 数据示例

#### 示例 1: 简单映射

```csv
原始检查项目: "胸部+右前壁CT"
模态: CT
↓
标准编码: 2104011000
标准名称: * CT胸部（平扫）
```

#### 示例 2: 复合项目映射

```csv
原始检查项目: "右股骨三维重建,右股骨下段CT平扫,胸部CT平扫,下肢血管成像"
模态: CT
compound_num: 3
↓
映射结果1: 2107171010 - * CT右侧股骨（平扫+三维重建）
映射结果2: 2104011000 - * CT胸部（平扫）
映射结果3: 2108182200 - * CT下肢动脉血管造影（CTA）
```

**说明**: 一个原始检查项目可能对应多条标准项目（通过 `unique_key` 关联）

---

## 三、与 MMS Platform 的集成

### 3.1 MMS 的缓存设计

**MMS Platform 已有的 L1 缓存表**: `acr_standard_link`

**字段设计**:
```sql
CREATE TABLE acr_standard_link (
    id SERIAL PRIMARY KEY,
    raw_check_item VARCHAR(512),      -- 原始检查项目
    modality VARCHAR(32),              -- 模态
    version VARCHAR(32),               -- 版本
    standard_code VARCHAR(64),         -- 标准编码
    standard_name VARCHAR(128),        -- 标准名称
    confidence FLOAT,                  -- 置信度 (0.0-1.0)
    source VARCHAR(32),                -- 来源 (algorithm/manual/import)
    create_time TIMESTAMP,
    update_time TIMESTAMP,
    UNIQUE(raw_check_item, modality, version)
);
```

### 3.2 数据同步方案

#### 方案 A: 一次性导入（推荐）

**步骤**:

1. **清洗数据**
```python
# scripts/import_production_cache.py

import pandas as pd

# 读取导出的映射表
df = pd.read_csv('data/cache_mapping/da_checkitem_map.csv')

# 过滤有效记录
df_valid = df[df['is_valid'] == 1]

# 转换为 MMS 格式
df_mms = df_valid[[
    'original_checkitem', 
    'modality',
    'standard_checkitem_code',
    'standard_checkitem_name',
    'standard_version'
]].rename(columns={
    'original_checkitem': 'raw_check_item',
    'standard_checkitem_code': 'standard_code',
    'standard_checkitem_name': 'standard_name',
    'standard_version': 'version'
})

# 添加 MMS 字段
df_mms['confidence'] = 1.0  # 人工审核，置信度 100%
df_mms['source'] = 'import_production'  # 标记来源
df_mms['version'] = df_mms['version'].fillna('V3.8.2')

# 导出
df_mms.to_csv('data/cache_mapping/mms_cache_import.csv', index=False)
```

2. **导入数据库**
```python
# 通过 Alembic 迁移导入
poetry run alembic revision --autogenerate -m "import_production_cache"
poetry run alembic upgrade head
```

3. **验证**
```sql
SELECT 
    COUNT(*) as total,
    source,
    AVG(confidence) as avg_confidence
FROM acr_standard_link
GROUP BY source;
```

**优势**:
- ✅ 一次性导入，简单快速
- ✅ 保留历史数据（`source='import_production'`）
- ✅ 可追溯数据来源

**劣势**:
- ❌ 后续更新需要人工同步

---

#### 方案 B: 定期同步（长期维护）

**架构**:
```
生产数据库 (da_checkitem_map)
    ↓ 每日凌晨 3:00
定时任务 (scripts/sync_production_cache.py)
    ↓ 增量同步
MMS 数据库 (acr_standard_link)
```

**同步策略**:
1. 每日凌晨 3:00 运行同步脚本
2. 根据 `update_time` 字段增量同步
3. 冲突处理：生产数据优先（`ON CONFLICT UPDATE`）

**脚本示例**:
```python
# scripts/sync_production_cache.py

import pymysql
from sqlalchemy import create_engine
import pandas as pd
from datetime import datetime, timedelta

# 1. 连接生产数据库
prod_conn = pymysql.connect(
    host='210.12.11.251',
    port=26306,
    user='data',
    password='rimag123456',
    database='rimag_data',
    charset='utf8mb4'
)

# 2. 查询最近更新的记录（增量）
last_sync_time = get_last_sync_time()  # 从 MMS 配置表读取
query = f"""
SELECT * FROM da_checkitem_map
WHERE is_valid = 1 
  AND update_time > '{last_sync_time}'
ORDER BY update_time
"""

df_new = pd.read_sql(query, prod_conn)
print(f"新增/更新记录: {len(df_new)} 条")

# 3. 转换格式并写入 MMS
if len(df_new) > 0:
    df_mms = transform_to_mms_format(df_new)
    
    # 写入 MMS 数据库
    engine = create_engine('postgresql://...')
    df_mms.to_sql(
        'acr_standard_link', 
        engine, 
        if_exists='append',
        index=False
    )
    
    # 更新同步时间
    update_last_sync_time(datetime.now())
    print(f"✅ 同步完成: {len(df_new)} 条")
```

**优势**:
- ✅ 自动化同步，无需人工干预
- ✅ 增量同步，效率高
- ✅ 与生产环境保持一致

**劣势**:
- ❌ 需要维护同步脚本
- ❌ 依赖生产数据库网络连接

---

#### 方案 C: API 实时同步（未来）

**架构**:
```
MMS Platform
    ↓ 查询 L1 缓存未命中
    ↓ 调用 L2 算法匹配
    ↓ 人工审核通过
    ↓ POST /api/admin/cache/sync
生产数据库 (da_checkitem_map)
    ↓ INSERT 新记录
```

**说明**:
- MMS 的人工审核通过后，通过 API 写回生产数据库
- 实现双向同步
- 需要开发生产数据库的写入 API

**优势**:
- ✅ 实时同步
- ✅ 双向同步（MMS ↔ 生产）

**劣势**:
- ❌ 需要开发生产数据库 API
- ❌ 需要权限管理

---

## 四、推荐实施方案

### 4.1 短期方案（本周）

**执行方案 A: 一次性导入**

**步骤**:
1. ✅ 已完成：导出生产映射表 (`data/cache_mapping/da_checkitem_map.csv`)
2. 🔄 开发导入脚本 (`scripts/import_production_cache.py`)
3. 🔄 生成 Alembic 迁移
4. 🔄 导入 237 条有效映射到 MMS
5. 🔄 验证导入结果

**预计时间**: 2 小时

**交付物**:
- `scripts/import_production_cache.py` - 导入脚本
- `data/cache_mapping/mms_cache_import.csv` - 转换后数据
- `migrations/versions/*_import_production_cache.py` - 迁移脚本
- `docs/CACHE_IMPORT_REPORT.md` - 导入报告

---

### 4.2 中期方案（下周）

**执行方案 B: 定期同步**

**步骤**:
1. 开发增量同步脚本 (`scripts/sync_production_cache.py`)
2. 配置 Cron 任务（每日凌晨 3:00）
3. 监控同步日志
4. 建立同步失败告警

**预计时间**: 1 天

---

### 4.3 长期方案（下月）

**执行方案 C: API 实时同步**

**步骤**:
1. 与生产数据库团队协调 API 开发
2. MMS 增加"写回生产"功能
3. 实现双向同步
4. 权限管理与审批流程

**预计时间**: 1 周

---

## 五、数据质量分析

### 5.1 有效记录分布

| 指标 | 数量 | 占比 |
|------|------|------|
| 有效记录 | 237 | 63.0% |
| 无效记录 | 139 | 37.0% |

**说明**: 无效记录（`is_valid=0`）是历史版本或被覆盖的记录

### 5.2 复合项目统计

```sql
-- 复合项目数量分布
SELECT 
    compound_num,
    COUNT(*) as count
FROM da_checkitem_map
WHERE is_valid = 1
GROUP BY compound_num;
```

**预期结果**:
- `compound_num=1`: 单一映射（约 150 条）
- `compound_num=2-3`: 复合映射（约 70 条）
- `compound_num=NULL`: 未标注（约 17 条）

### 5.3 版本分布

| 版本 | 数量 | 说明 |
|------|------|------|
| `V1` | ~100 | 早期版本 |
| `V3.0` | ~80 | 当前版本 |
| `NULL` | ~57 | 未标注版本 |

**建议**: 导入时统一版本号为 `V3.8.2`

---

## 六、与算法的配合

### 6.1 查询优先级

```python
def match_with_cache(check_item: str, modality: str, version: str):
    # L1: 查询缓存表
    cached = query_cache(check_item, modality, version)
    if cached:
        return {
            'source': 'cache',
            'confidence': 1.0,
            'data': cached
        }
    
    # L2: 调用算法
    result = match_engine.match(check_item, modality, version)
    
    # L3: 高置信度结果可选写回缓存（需人工审核）
    if result['confidence'] >= 0.95:
        # 标记为待审核
        mark_for_review(check_item, result)
    
    return {
        'source': 'algorithm',
        'confidence': result['confidence'],
        'data': result['data']
    }
```

### 6.2 缓存命中率预估

**假设**:
- 生产环境日均匹配请求: 1,000 次
- 常见检查项目占比: 80%
- 缓存覆盖常见项目: 237 条

**预估命中率**: 60-70%

**性能提升**:
- 命中缓存: 1-5ms
- 调用算法: 50-200ms
- **平均响应时间**: 从 100ms → 30ms（提升 70%）

---

## 七、下一步行动

### 立即执行（今天）

1. [ ] 开发导入脚本 `scripts/import_production_cache.py`
2. [ ] 数据格式转换与清洗
3. [ ] 测试导入流程

### 近期计划（本周）

1. [ ] 执行数据导入（237 条有效映射）
2. [ ] 验证导入结果
3. [ ] 生成导入报告

### 长期计划（下周）

1. [ ] 开发定期同步脚本
2. [ ] 配置 Cron 任务
3. [ ] 监控同步状态

---

**文档创建时间**: 2026-07-29
**数据来源**: `rimag_data.da_checkitem_map` (生产数据库)
**导出文件**: `data/cache_mapping/da_checkitem_map.csv` (376 条)
**有效记录**: 237 条

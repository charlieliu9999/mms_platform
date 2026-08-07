# 数据库设计

> MMS 平台数据库表结构与迁移策略

## 表分类

### 词表数据（引擎核心）
- `nlp_medical_dict` - 医学词典
- `nlp_phrase_map` - 短语映射
- `nlp_ambiguity` - 消歧规则

### 标准库数据
- `mms_standard_item` - 标准项目库

### 运行时数据
- `match_cache` - 匹配缓存
- `match_feedback` - 匹配反馈

### 评测数据
- `mms_evaluation_task` - 评测任务
- `mms_evaluation_failure` - 失败记录

### Agent 数据
- `agent_suggestion` - AI 建议

---

## 表结构详解

### 1. nlp_medical_dict (医学词典)

**用途**：Jieba 分词词库

```sql
CREATE TABLE nlp_medical_dict (
    id SERIAL PRIMARY KEY,
    word VARCHAR(200) NOT NULL,        -- 词条
    type VARCHAR(50),                  -- 类型：body_part/process/modifier
    enable INTEGER DEFAULT 0,          -- 启用状态
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_medical_dict_word ON nlp_medical_dict(word);
CREATE INDEX idx_medical_dict_type ON nlp_medical_dict(type);
```

**示例数据**：
```sql
INSERT INTO nlp_medical_dict (word, type, enable) VALUES
('头部', 'body_part', 0),
('腰椎', 'body_part', 0),
('平扫', 'process', 0),
('增强', 'process', 0),
('双侧', 'modifier', 0);
```

**规模**：2,435 条

### 2. nlp_phrase_map (短语映射)

**用途**：别名统一化

```sql
CREATE TABLE nlp_phrase_map (
    id SERIAL PRIMARY KEY,
    src_process VARCHAR(200) NOT NULL,  -- 原始表达
    dst_process VARCHAR(200) NOT NULL,  -- 标准表达
    modality VARCHAR(50),               -- 适用模态
    version VARCHAR(50),                -- 版本号
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_phrase_map_src ON nlp_phrase_map(src_process, modality);
CREATE INDEX idx_phrase_map_modality ON nlp_phrase_map(modality);
```

**示例数据**：
```sql
INSERT INTO nlp_phrase_map (src_process, dst_process, modality, version) VALUES
('脑袋', '头部', 'CT', 'V3.8.2'),
('增强扫描', '增强', 'CT', 'V3.8.2'),
('MRA', '血管成像', 'MR', 'V3.8.2'),
('CTA', '血管成像', 'CT', 'V3.8.2');
```

**规模**：7,839 条

### 3. nlp_ambiguity (消歧规则)

**用途**：解决歧义表达

```sql
CREATE TABLE nlp_ambiguity (
    id SERIAL PRIMARY KEY,
    src_process VARCHAR(200) NOT NULL,  -- 歧义表达
    dst_process VARCHAR(200) NOT NULL,  -- 消歧后表达
    modality VARCHAR(50),               -- 适用模态
    version VARCHAR(50),                -- 版本号
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ambiguity_src ON nlp_ambiguity(src_process, modality);
```

**示例数据**：
```sql
INSERT INTO nlp_ambiguity (src_process, dst_process, modality, version) VALUES
('平扫+增强', '平扫 增强', 'CT', 'V3.8.2'),
('正侧位', '正位 侧位', 'DR', 'V3.8.2'),
('[薄层]', '', 'CT', 'V3.8.2');
```

**规模**：1,229 条

### 4. mms_standard_item (标准项目库)

**用途**：存储规范化检查项目

```sql
CREATE TABLE mms_standard_item (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,         -- 标准名称
    modality VARCHAR(50) NOT NULL,      -- 模态
    body_part VARCHAR(200),             -- 部位
    process VARCHAR(200),               -- 检查过程
    contrast VARCHAR(50),               -- 对比剂：with/without/NA
    laterality VARCHAR(50),             -- 侧别：left/right/bilateral
    position VARCHAR(100),              -- 体位（DR专用）
    acr_code VARCHAR(100),              -- ACR 编码
    version VARCHAR(50) NOT NULL,       -- 版本号
    source VARCHAR(50),                 -- 来源：ACR/internal
    enabled BOOLEAN DEFAULT TRUE,       -- 启用状态
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_standard_modality ON mms_standard_item(modality);
CREATE INDEX idx_standard_version ON mms_standard_item(version);
CREATE INDEX idx_standard_modality_version ON mms_standard_item(modality, version);
CREATE INDEX idx_standard_body_part ON mms_standard_item(body_part);
```

**示例数据**：
```sql
INSERT INTO mms_standard_item 
(name, modality, body_part, process, contrast, version, source) VALUES
('CT头部平扫', 'CT', '头部', '平扫', 'without', 'V3.8.2', 'ACR'),
('CT头部增强', 'CT', '头部', '增强', 'with', 'V3.8.2', 'ACR'),
('MR腰椎平扫', 'MR', '腰椎', '平扫', 'without', 'V3.8.2', 'internal'),
('双膝关节正、侧位', 'DR', '膝关节', '正、侧位', 'NA', 'V3.8.2', 'internal');
```

**规模**：~3,000 条

### 5. match_cache (匹配缓存)

**用途**：L1 缓存层

```sql
CREATE TABLE match_cache (
    id SERIAL PRIMARY KEY,
    text_hash VARCHAR(64) NOT NULL,     -- MD5(text + modality)
    modality VARCHAR(50) NOT NULL,      -- 模态
    original_text VARCHAR(500),         -- 原始文本
    result_json TEXT,                   -- 匹配结果 JSON
    confidence FLOAT,                   -- 置信度
    hit_count INTEGER DEFAULT 0,        -- 命中次数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_hit_at TIMESTAMP,              -- 最后命中时间
    ttl TIMESTAMP,                      -- 过期时间
    UNIQUE (text_hash, modality)
);

CREATE INDEX idx_cache_text_hash ON match_cache(text_hash);
CREATE INDEX idx_cache_ttl ON match_cache(ttl);
CREATE INDEX idx_cache_confidence ON match_cache(confidence);
```

**缓存策略**：
- TTL：30 天
- 最小置信度：0.8
- 自动清理：定期删除过期记录

**规模**：~17 万条

### 6. match_feedback (匹配反馈)

**用途**：收集未匹配项和人工反馈

```sql
CREATE TABLE match_feedback (
    id SERIAL PRIMARY KEY,
    text_hash VARCHAR(64) NOT NULL,     -- MD5(text + modality)
    modality VARCHAR(50) NOT NULL,      -- 模态
    original_text VARCHAR(500),         -- 原始文本
    engine_result_json TEXT,            -- 引擎输出
    engine_tier VARCHAR(50),            -- 匹配层级
    feedback_type VARCHAR(50),          -- 类型：manual_correction/auto_low_confidence
    suggested_fix TEXT,                 -- 建议修复
    status VARCHAR(50) DEFAULT 'pending', -- 状态：pending/resolved/rejected
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (text_hash, modality)
);

CREATE INDEX idx_feedback_status ON match_feedback(status);
CREATE INDEX idx_feedback_modality ON match_feedback(modality);
```

**幂等性**：使用 `(text_hash, modality)` 唯一索引防止重复插入

### 7. mms_evaluation_task (评测任务)

**用途**：批量评测引擎性能

```sql
CREATE TABLE mms_evaluation_task (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,         -- 任务名称
    test_data_json TEXT,                -- 测试数据
    total_count INTEGER,                -- 总数
    matched_count INTEGER,              -- 匹配数
    accuracy FLOAT,                     -- 准确率
    status VARCHAR(50) DEFAULT 'pending', -- pending/running/completed/failed
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_eval_task_status ON mms_evaluation_task(status);
```

### 8. mms_evaluation_failure (评测失败记录)

**用途**：记录评测失败详情

```sql
CREATE TABLE mms_evaluation_failure (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES mms_evaluation_task(id),
    original_text VARCHAR(500),
    modality VARCHAR(50),
    expected_standard VARCHAR(200),
    actual_standard VARCHAR(200),
    failure_type VARCHAR(50),           -- no_match/wrong_match/partial_match
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_eval_failure_task ON mms_evaluation_failure(task_id);
CREATE INDEX idx_eval_failure_type ON mms_evaluation_failure(failure_type);
```

### 9. agent_suggestion (AI 建议)

**用途**：Agent 生成的优化建议

```sql
CREATE TABLE agent_suggestion (
    id SERIAL PRIMARY KEY,
    suggestion_type VARCHAR(50),        -- add_medical_dict/add_phrase_map/...
    modality VARCHAR(50),
    content_json TEXT,                  -- 建议内容
    reason TEXT,                        -- 生成理由
    status VARCHAR(50) DEFAULT 'pending', -- pending/approved/rejected
    approved_by VARCHAR(100),
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_suggestion_status ON agent_suggestion(status);
CREATE INDEX idx_suggestion_type ON agent_suggestion(suggestion_type);
```

---

## 迁移管理

### Alembic 配置

**alembic.ini**：
```ini
[alembic]
script_location = migrations
sqlalchemy.url = postgresql+asyncpg://postgres:password@localhost:15432/acrac_db
```

**migrations/env.py**：
```python
from match_service.cache.models import Base
target_metadata = Base.metadata
```

### 常用迁移命令

```bash
# 查看当前版本
poetry run alembic current

# 查看迁移历史
poetry run alembic history

# 生成迁移（自动检测模型变更）
poetry run alembic revision --autogenerate -m "描述变更"

# 应用所有迁移
poetry run alembic upgrade head

# 回滚一个版本
poetry run alembic downgrade -1

# 回滚到指定版本
poetry run alembic downgrade <revision_id>
```

### 迁移版本历史

```
20260727_1134  baseline_match_service_cache_tables
    ↓
20260729_1735  import_phase1_merged_lexicon
    ↓
20260729_1802  add_evaluation_tables
    ↓
20260729_1804  add_mms_evaluation_tables
    ↓
20260731_0930  import_all_modality_standards
    ↓
20260804_0200  match_feedback_dedupe_unique
    ↓
20260804_1200  unify_standard_tables
    ↓
20260804_1300  retag_nonacr_modality_versions
    ↓
20260804_1400  b19_seed_spect_pet_oct_unmatchable
```

---

## 数据维护

### 词表更新流程

```sql
-- 1. 添加新词条
INSERT INTO nlp_medical_dict (word, type, enable)
VALUES ('肺动脉', 'body_part', 0);

-- 2. 重载引擎
curl -X POST http://localhost:9100/api/reload

-- 3. 清空相关缓存
DELETE FROM match_cache WHERE modality = 'MR';
```

### 缓存清理

```sql
-- 清理过期缓存
DELETE FROM match_cache WHERE ttl < NOW();

-- 清理低置信度缓存
DELETE FROM match_cache WHERE confidence < 0.8;

-- 清理未命中缓存
DELETE FROM match_cache WHERE hit_count = 0 AND created_at < NOW() - INTERVAL '7 days';
```

### 数据备份

```bash
# 完整备份
pg_dump -h 127.0.0.1 -p 15432 -U postgres -d acrac_db \
  -f backup_full_$(date +%Y%m%d).sql

# 仅备份词表
pg_dump -h 127.0.0.1 -p 15432 -U postgres -d acrac_db \
  -t nlp_medical_dict \
  -t nlp_phrase_map \
  -t nlp_ambiguity \
  -f backup_lexicon_$(date +%Y%m%d).sql

# 仅备份标准库
pg_dump -h 127.0.0.1 -p 15432 -U postgres -d acrac_db \
  -t mms_standard_item \
  -f backup_standards_$(date +%Y%m%d).sql
```

### 数据恢复

```bash
# 恢复完整数据库
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db \
  -f backup_full_20260807.sql

# 恢复特定表
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db \
  -c "TRUNCATE nlp_medical_dict CASCADE;"
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db \
  -f backup_lexicon_20260807.sql
```

---

## 性能优化

### 索引优化

```sql
-- 分析查询性能
EXPLAIN ANALYZE
SELECT * FROM match_cache 
WHERE text_hash = 'abc123' AND modality = 'CT';

-- 创建复合索引
CREATE INDEX idx_cache_hash_modality 
ON match_cache(text_hash, modality);

-- 删除未使用索引
DROP INDEX IF EXISTS idx_unused_index;
```

### 分区策略（未来）

```sql
-- 按模态分区（未来扩展）
CREATE TABLE match_cache_ct PARTITION OF match_cache
FOR VALUES IN ('CT');

CREATE TABLE match_cache_mr PARTITION OF match_cache
FOR VALUES IN ('MR');
```

### 定期维护

```sql
-- 更新统计信息
ANALYZE match_cache;
ANALYZE mms_standard_item;

-- 清理死元组
VACUUM match_cache;

-- 重建索引
REINDEX TABLE match_cache;
```

---

## 相关文档
- [架构设计](architecture.md) - 数据流设计
- [领域概念](domain-concepts.md) - 数据模型说明
- [工作流程](workflows.md) - 迁移操作

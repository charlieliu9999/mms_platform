-- ============================================================
-- v4.0.0 数据库结构更新脚本
-- ============================================================
-- 用途: 为 checkitem_standards 表添加 v4.0.0 所需的新字段
-- 执行前: 请先备份数据库
-- ============================================================

-- 1. 添加版本字段
ALTER TABLE checkitem_standards
ADD COLUMN IF NOT EXISTS version VARCHAR(10) DEFAULT 'v3.8.2';

-- 2. 添加医保相关字段
ALTER TABLE checkitem_standards
ADD COLUMN IF NOT EXISTS insurance_code VARCHAR(50),
ADD COLUMN IF NOT EXISTS insurance_ext_code VARCHAR(20),
ADD COLUMN IF NOT EXISTS insurance_name VARCHAR(200),
ADD COLUMN IF NOT EXISTS insurance_item_code VARCHAR(50),
ADD COLUMN IF NOT EXISTS insurance_category VARCHAR(50),
ADD COLUMN IF NOT EXISTS insurance_price DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS province VARCHAR(50) DEFAULT '江西';

-- 3. 添加部位编码字段（如果不存在）
ALTER TABLE checkitem_standards
ADD COLUMN IF NOT EXISTS body_part_code VARCHAR(20);

-- 4. 创建索引以提升查询性能
CREATE INDEX IF NOT EXISTS idx_standards_version
ON checkitem_standards(version);

CREATE INDEX IF NOT EXISTS idx_standards_insurance_code
ON checkitem_standards(insurance_code);

CREATE INDEX IF NOT EXISTS idx_standards_modality_version
ON checkitem_standards(modality, version);

-- 5. 为现有数据标记版本（如果版本字段为空）
UPDATE checkitem_standards
SET version = 'v3.8.2'
WHERE version IS NULL OR version = '';

-- 6. 验证结构
\d checkitem_standards

-- 7. 统计现有数据
SELECT
    version,
    modality,
    COUNT(*) as count
FROM checkitem_standards
GROUP BY version, modality
ORDER BY version, modality;

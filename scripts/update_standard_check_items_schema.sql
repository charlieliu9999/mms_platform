-- ============================================================
-- v4.0.0 标准表结构更新脚本
-- ============================================================
-- 表名: standard_check_items
-- 用途: 添加 v4.0.0 医保版本所需的新字段
-- 执行前: 已备份到 backups/backup_standard_check_items_*.sql
-- ============================================================

-- 1. 添加医保相关字段
ALTER TABLE standard_check_items
ADD COLUMN IF NOT EXISTS insurance_code VARCHAR(50),
ADD COLUMN IF NOT EXISTS insurance_ext_code VARCHAR(20),
ADD COLUMN IF NOT EXISTS insurance_name VARCHAR(200),
ADD COLUMN IF NOT EXISTS insurance_item_code VARCHAR(50),
ADD COLUMN IF NOT EXISTS insurance_category VARCHAR(50),
ADD COLUMN IF NOT EXISTS insurance_price DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS province VARCHAR(50) DEFAULT '江西';

-- 2. 添加部位编码字段
ALTER TABLE standard_check_items
ADD COLUMN IF NOT EXISTS body_part_code VARCHAR(20);

-- 3. 创建索引以提升查询性能
CREATE INDEX IF NOT EXISTS idx_standard_items_version
ON standard_check_items(version);

CREATE INDEX IF NOT EXISTS idx_standard_items_insurance_code
ON standard_check_items(insurance_code);

CREATE INDEX IF NOT EXISTS idx_standard_items_modality_version
ON standard_check_items(modality, version);

-- 4. 验证结构
\d standard_check_items

-- 5. 统计现有数据
SELECT
    version,
    modality,
    COUNT(*) as count,
    COUNT(DISTINCT insurance_code) as with_insurance_code
FROM standard_check_items
WHERE is_active = true
GROUP BY version, modality
ORDER BY version, modality;

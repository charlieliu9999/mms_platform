-- Phase 2: 标准库补充脚本
-- 用途：补充缺失的标准检查项目
-- 执行前提：数据库已启动并可访问

-- ============================================================
-- 缺失项目分析
-- ============================================================

-- 通过测试发现以下项目在标准库中不存在：
--   1. CT小肠血管成像(CTA)
--   2. CT肝脏血管成像(CTA)
--   3. CT脊柱局部(脊髓造影)
--   4. CT肩关节(直接造影)
--   5. MR肩关节(直接造影)

-- ============================================================
-- 1. CT 血管专项成像补充
-- ============================================================

-- 参考现有项目结构（如 CT腹腔血管成像）
-- modality_code='2' (CT), scan_name='动脉血管成像(CTA)'

-- CT小肠血管成像(CTA)
INSERT INTO nlp_checkitem_standard (
    modality_code, modality_name,
    two_level_code, two_level_name,
    scan_code, scan_name,
    checkitem_code, checkitem_name,
    version, is_deleted, create_time, update_time
)
VALUES (
    '2', 'CT',
    NULL, '腹部血管',
    NULL, NULL,
    'CT_SMALLINTESTINE_CTA', '* CT小肠血管成像(CTA)',
    'V3.8.2', 0, NOW(), NOW()
)
ON CONFLICT (checkitem_code, version) DO NOTHING;

-- CT肝脏血管成像(CTA)
INSERT INTO nlp_checkitem_standard (
    modality_code, modality_name,
    two_level_code, two_level_name,
    scan_code, scan_name,
    checkitem_code, checkitem_name,
    version, is_deleted, create_time, update_time
)
VALUES (
    '2', 'CT',
    NULL, '腹部血管',
    NULL, NULL,
    'CT_LIVER_CTA', '* CT肝脏血管成像(CTA)',
    'V3.8.2', 0, NOW(), NOW()
)
ON CONFLICT (checkitem_code, version) DO NOTHING;

-- ============================================================
-- 2. 特殊造影技术补充
-- ============================================================

-- CT脊柱局部(脊髓造影)
-- 需要先确认"脊柱局部"的部位编码
INSERT INTO nlp_checkitem_standard (
    modality_code, modality_name,
    two_level_code, two_level_name,
    scan_code, scan_name,
    checkitem_code, checkitem_name,
    version, is_deleted, create_time, update_time
)
VALUES (
    '2', 'CT',
    NULL, '脊柱',
    NULL, NULL,
    'CT_SPINE_LOCAL_MYELOGRAPHY', '* CT脊柱局部(脊髓造影)',
    'V3.8.2', 0, NOW(), NOW()
)
ON CONFLICT (checkitem_code, version) DO NOTHING;

-- CT肩关节(直接造影)
INSERT INTO nlp_checkitem_standard (
    modality_code, modality_name,
    two_level_code, two_level_name,
    scan_code, scan_name,
    checkitem_code, checkitem_name,
    version, is_deleted, create_time, update_time
)
VALUES (
    '2', 'CT',
    NULL, '肩关节',
    NULL, NULL,
    'CT_SHOULDER_DIRECT_ARTHROGRAPHY', '* CT肩关节(直接造影)',
    'V3.8.2', 0, NOW(), NOW()
)
ON CONFLICT (checkitem_code, version) DO NOTHING;

-- MR肩关节(直接造影)
INSERT INTO nlp_checkitem_standard (
    modality_code, modality_name,
    two_level_code, two_level_name,
    scan_code, scan_name,
    checkitem_code, checkitem_name,
    version, is_deleted, create_time, update_time
)
VALUES (
    '3', 'MR',
    NULL, '肩关节',
    NULL, NULL,
    'MR_SHOULDER_DIRECT_ARTHROGRAPHY', '* MR肩关节(直接造影)',
    'V3.8.2', 0, NOW(), NOW()
)
ON CONFLICT (checkitem_code, version) DO NOTHING;

-- ============================================================
-- 3. 验证插入结果
-- ============================================================

-- 查看新增的标准项
SELECT checkitem_code, checkitem_name, modality_name, two_level_name
FROM nlp_checkitem_standard
WHERE checkitem_code IN (
    'CT_SMALLINTESTINE_CTA',
    'CT_LIVER_CTA',
    'CT_SPINE_LOCAL_MYELOGRAPHY',
    'CT_SHOULDER_DIRECT_ARTHROGRAPHY',
    'MR_SHOULDER_DIRECT_ARTHROGRAPHY'
)
AND version = 'V3.8.2'
ORDER BY modality_code, checkitem_code;

-- ============================================================
-- 4. 数据来源分析（可选执行）
-- ============================================================

-- 如果需要更准确的部位和扫描方式，可以从 procedure_dictionary 提取
-- 以下查询用于分析现有数据：

-- 查找"小肠"相关项目
-- SELECT id, modality, name_zh, body_part
-- FROM procedure_dictionary
-- WHERE name_zh LIKE '%小肠%' AND name_zh LIKE '%血管%'
-- AND is_active = true;

-- 查找"肝脏"相关项目
-- SELECT id, modality, name_zh, body_part
-- FROM procedure_dictionary
-- WHERE name_zh LIKE '%肝脏%' AND name_zh LIKE '%血管%'
-- AND is_active = true;

-- 查找"脊髓造影"相关项目
-- SELECT id, modality, name_zh, body_part
-- FROM procedure_dictionary
-- WHERE name_zh LIKE '%脊髓造影%'
-- AND is_active = true;

-- 查找"直接造影"相关项目
-- SELECT id, modality, name_zh, body_part
-- FROM procedure_dictionary
-- WHERE name_zh LIKE '%直接造影%'
-- AND is_active = true;

-- ============================================================
-- 预期效果
-- ============================================================

-- 补充前未匹配项：5 项
--   1. CT小肠血管成像(CTA)
--   2. CT肝脏血管成像(CTA)
--   3. CT脊柱局部(脊髓造影)
--   4. CT肩关节(直接造影)
--   5. MR肩关节(直接造影)

-- 补充后预期：+5 项匹配
-- 结合词库补充（+3项），总计 +8 项
-- 匹配率：20% → 100%

-- ============================================================
-- 注意事项
-- ============================================================

-- 1. checkitem_code 必须唯一，建议使用规范命名
-- 2. two_level_name（部位）应与现有数据保持一致
-- 3. 标准项名称建议以 "* " 开头，表示系统标准项
-- 4. version 应与当前引擎版本一致（V3.8.2）
-- 5. 执行前建议先查询现有类似项目的结构作为参考

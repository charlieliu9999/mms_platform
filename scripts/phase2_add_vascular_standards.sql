-- Phase 2: 补充CT血管成像标准项
-- 解决问题: 7条未匹配（2 ambiguous + 5 none）
-- 执行前确认: 编码范围 20000000000101-20000000000299 可用

BEGIN;

-- ============================================================================
-- 1. 腹部血管成像标准项（4条）
-- ============================================================================
-- 问题项:
--   ❌ CT小肠血管成像(CTA)
--   ❌ CT肝脏血管成像(CTA)
--   ❌ CT腹部盆腔动脉血管成像(CTA)
--   ❌ CT腹部动静脉血管成像(CTA+CTV)

INSERT INTO standard_check_items (
    item_code, 
    item_name, 
    modality, 
    body_part_l1,
    body_part_l2, 
    scan_method, 
    is_active,
    created_at,
    updated_at
) VALUES
-- 腹部盆腔血管
(
    '20000000000101', 
    'CT腹部盆腔动脉血管成像', 
    'CT', 
    '腹部',
    '腹部盆腔', 
    'CTA', 
    true,
    NOW(),
    NOW()
),

-- 小肠血管
(
    '20000000000102', 
    'CT小肠血管成像', 
    'CT',
    '腹部', 
    '小肠', 
    'CTA', 
    true,
    NOW(),
    NOW()
),

-- 肝脏血管
(
    '20000000000103', 
    'CT肝脏血管成像', 
    'CT',
    '腹部', 
    '肝脏', 
    'CTA', 
    true,
    NOW(),
    NOW()
),

-- 腹部动静脉
(
    '20000000000104', 
    'CT腹部动静脉血管成像', 
    'CT',
    '腹部', 
    '腹部', 
    'CTA+CTV', 
    true,
    NOW(),
    NOW()
);


-- ============================================================================
-- 2. 脊柱脊髓血管成像标准项（3条）
-- ============================================================================
-- 问题项:
--   ❌ CT胸腰段脊髓动脉血管成像(CTA)
--   ❌ CT脊髓动脉血管成像(CTA)

INSERT INTO standard_check_items (
    item_code, 
    item_name, 
    modality,
    body_part_l1, 
    body_part_l2, 
    scan_method, 
    is_active,
    created_at,
    updated_at
) VALUES
-- 胸腰段脊髓动脉
(
    '20000000000201', 
    'CT胸腰段脊髓动脉血管成像', 
    'CT',
    '脊柱', 
    '胸腰段脊髓', 
    'CTA', 
    true,
    NOW(),
    NOW()
),

-- 脊髓动脉（通用）
(
    '20000000000202', 
    'CT脊髓动脉血管成像', 
    'CT',
    '脊柱', 
    '脊髓', 
    'CTA', 
    true,
    NOW(),
    NOW()
),

-- 脊柱局部血管（兼容"脊柱局部"查询）
(
    '20000000000203', 
    'CT脊柱局部血管成像', 
    'CT',
    '脊柱', 
    '脊柱局部', 
    'CTA', 
    true,
    NOW(),
    NOW()
);


-- ============================================================================
-- 3. 特殊造影检查标准项（4条）
-- ============================================================================
-- 问题项:
--   ❌ CT泪囊造影(平扫)
--   ❌ CT泪道造影(平扫+对比剂注射)
--   ❌ CT脊柱局部(脊髓造影)
--   ❌ CT脊柱脊髓造影(平扫+增强)

INSERT INTO standard_check_items (
    item_code, 
    item_name, 
    modality,
    body_part_l1, 
    body_part_l2, 
    scan_method, 
    is_active,
    created_at,
    updated_at
) VALUES
-- 泪道造影
(
    '20000000000301', 
    'CT泪道造影', 
    'CT',
    '头部', 
    '泪道', 
    '造影', 
    true,
    NOW(),
    NOW()
),

-- 泪囊造影（兼容"泪囊"查询）
(
    '20000000000302', 
    'CT泪囊造影', 
    'CT',
    '头部', 
    '泪囊', 
    '造影', 
    true,
    NOW(),
    NOW()
),

-- 脊髓造影
(
    '20000000000401', 
    'CT脊髓造影', 
    'CT',
    '脊柱', 
    '脊髓', 
    '造影', 
    true,
    NOW(),
    NOW()
),

-- 脊柱脊髓造影（覆盖"脊柱脊髓造影"查询）
(
    '20000000000402', 
    'CT脊柱脊髓造影', 
    'CT',
    '脊柱', 
    '脊柱脊髓', 
    '造影', 
    true,
    NOW(),
    NOW()
);


-- ============================================================================
-- 4. 其他专科检查标准项（3条）
-- ============================================================================
-- 问题项:
--   ❌ CT尿路造影(平扫+增强)
--   ❌ CT肩关节(直接造影)
--   ❌ CT乳腺(平扫+增强)

INSERT INTO standard_check_items (
    item_code, 
    item_name, 
    modality,
    body_part_l1, 
    body_part_l2, 
    scan_method, 
    is_active,
    created_at,
    updated_at
) VALUES
-- 尿路造影
(
    '20000000000501', 
    'CT尿路造影', 
    'CT',
    '腹部', 
    '尿路', 
    '造影', 
    true,
    NOW(),
    NOW()
),

-- 肩关节造影
(
    '20000000000601', 
    'CT肩关节造影', 
    'CT',
    '四肢', 
    '肩关节', 
    '造影', 
    true,
    NOW(),
    NOW()
),

-- 乳腺平扫+增强
(
    '20000000000701', 
    'CT乳腺', 
    'CT',
    '胸部', 
    '乳腺', 
    '平扫+增强', 
    true,
    NOW(),
    NOW()
);


-- ============================================================================
-- 5. 验证插入结果
-- ============================================================================

-- 统计新增项
SELECT 
    '新增标准项统计' as info,
    COUNT(*) as total_added,
    COUNT(*) FILTER (WHERE scan_method = 'CTA') as cta_count,
    COUNT(*) FILTER (WHERE scan_method = '造影') as contrast_count,
    COUNT(*) FILTER (WHERE scan_method = 'CTA+CTV') as cta_ctv_count
FROM standard_check_items
WHERE item_code BETWEEN '20000000000101' AND '20000000000799'
AND created_at > NOW() - INTERVAL '1 minute';

-- 按部位分组
SELECT 
    body_part_l1,
    COUNT(*) as count,
    STRING_AGG(item_name, ', ' ORDER BY item_code) as items
FROM standard_check_items
WHERE item_code BETWEEN '20000000000101' AND '20000000000799'
AND created_at > NOW() - INTERVAL '1 minute'
GROUP BY body_part_l1
ORDER BY body_part_l1;

-- 检查编码冲突
SELECT 
    item_code,
    COUNT(*) as duplicate_count,
    STRING_AGG(item_name, ' | ') as names
FROM standard_check_items
WHERE item_code BETWEEN '20000000000101' AND '20000000000799'
GROUP BY item_code
HAVING COUNT(*) > 1;

COMMIT;

-- ============================================================================
-- 执行后验证
-- ============================================================================
-- 1. 确认无编码冲突（上述查询应返回0行）
-- 2. 运行重匹配测试:
--    poetry run python scripts/phase1_quick_fix_ct_unmatch.py --verify-only --full-rematch
-- 3. 检查匹配率提升:
--    poetry run python scripts/analyze_ct_mr_unmatched.py
--
-- 预期效果:
--   - ambiguous 从 10条 降至 8条（血管成像2条解决）
--   - none(standard_lib_gap) 从 15条 降至 5条（补充10条标准项）
--   - 总体匹配率提升: 0% → 38.7% (12/31)

-- ACR 4555 优化 Phase 1: 快速见效
-- 预期收益: 匹配率 +2.5% (85.82% → 88.3%)
-- 执行前备份: pg_dump -U postgres -d acrac_db -t standard_check_items > backup_$(date +%Y%m%d).sql

BEGIN;

-- ============================================================================
-- Part 1: SPECT 核心显像项目补充 (预计 +9 项)
-- ============================================================================

-- 检查编码是否已存在
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM standard_check_items WHERE item_code = '50990001110000') THEN
        INSERT INTO standard_check_items (
            item_code, item_name, modality, modality_code,
            body_part_l1, body_part_l3, scan_method,
            source, version, coverage_status, supplement_status,
            review_status, is_active
        ) VALUES
        (
            '50990001110000', '* SPECT心脏显像',
            'SPECT', '5', '心脏', '心脏', '平扫',
            'acr_4555_optimization_phase1', 'v3.8.2', 'gap_fill', 'proposed',
            'pending_review', true
        );
        RAISE NOTICE '✓ 已添加: SPECT心脏显像';
    ELSE
        RAISE NOTICE '⊘ 已存在: SPECT心脏显像';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM standard_check_items WHERE item_code = '50990002110000') THEN
        INSERT INTO standard_check_items (
            item_code, item_name, modality, modality_code,
            body_part_l1, body_part_l3, scan_method,
            source, version, coverage_status, supplement_status,
            review_status, is_active
        ) VALUES
        (
            '50990002110000', '* SPECT全身显像',
            'SPECT', '5', '全身', '全身', '平扫',
            'acr_4555_optimization_phase1', 'v3.8.2', 'gap_fill', 'proposed',
            'pending_review', true
        );
        RAISE NOTICE '✓ 已添加: SPECT全身显像';
    ELSE
        RAISE NOTICE '⊘ 已存在: SPECT全身显像';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM standard_check_items WHERE item_code = '50990003110000') THEN
        INSERT INTO standard_check_items (
            item_code, item_name, modality, modality_code,
            body_part_l1, body_part_l3, scan_method,
            source, version, coverage_status, supplement_status,
            review_status, is_active
        ) VALUES
        (
            '50990003110000', '* SPECT膀胱显像',
            'SPECT', '5', '膀胱', '膀胱', '平扫',
            'acr_4555_optimization_phase1', 'v3.8.2', 'gap_fill', 'proposed',
            'pending_review', true
        );
        RAISE NOTICE '✓ 已添加: SPECT膀胱显像';
    ELSE
        RAISE NOTICE '⊘ 已存在: SPECT膀胱显像';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM standard_check_items WHERE item_code = '50990004110000') THEN
        INSERT INTO standard_check_items (
            item_code, item_name, modality, modality_code,
            body_part_l1, body_part_l3, scan_method,
            source, version, coverage_status, supplement_status,
            review_status, is_active
        ) VALUES
        (
            '50990004110000', '* SPECT肝脏显像',
            'SPECT', '5', '肝脏', '肝脏', '平扫',
            'acr_4555_optimization_phase1', 'v3.8.2', 'gap_fill', 'proposed',
            'pending_review', true
        );
        RAISE NOTICE '✓ 已添加: SPECT肝脏显像';
    ELSE
        RAISE NOTICE '⊘ 已存在: SPECT肝脏显像';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM standard_check_items WHERE item_code = '50990005110000') THEN
        INSERT INTO standard_check_items (
            item_code, item_name, modality, modality_code,
            body_part_l1, body_part_l3, scan_method,
            source, version, coverage_status, supplement_status,
            review_status, is_active
        ) VALUES
        (
            '50990005110000', '* SPECT肾脏显像',
            'SPECT', '5', '肾脏', '肾脏', '平扫',
            'acr_4555_optimization_phase1', 'v3.8.2', 'gap_fill', 'proposed',
            'pending_review', true
        );
        RAISE NOTICE '✓ 已添加: SPECT肾脏显像';
    ELSE
        RAISE NOTICE '⊘ 已存在: SPECT肾脏显像';
    END IF;

END $$;

-- ============================================================================
-- Part 2: US 高频词汇补充到医学词典 (预计 +15 项)
-- ============================================================================

-- 注意: 词汇补充需要在应用层重新加载引擎后生效
-- 这里先将词汇插入数据库，后续通过热重载加载

INSERT INTO medical_dict (word, pos, weight, source)
VALUES
    ('动静脉内瘘', 'body', 5, 'acr_4555_optimization_phase1'),
    ('肾静脉', 'body', 5, 'acr_4555_optimization_phase1'),
    ('静脉导管', 'body', 5, 'acr_4555_optimization_phase1'),
    ('双胎输血综合征', 'body', 5, 'acr_4555_optimization_phase1'),
    ('全脊柱', 'body', 5, 'acr_4555_optimization_phase1'),
    ('肝静脉', 'body', 5, 'acr_4555_optimization_phase1'),
    ('髂静脉', 'body', 5, 'acr_4555_optimization_phase1'),
    ('腹部动脉', 'body', 5, 'acr_4555_optimization_phase1'),
    ('右心', 'body', 5, 'acr_4555_optimization_phase1')
ON CONFLICT (word, pos) DO UPDATE
SET weight = EXCLUDED.weight,
    source = EXCLUDED.source || ',' || medical_dict.source;

RAISE NOTICE '✓ 已补充 US/DSA 高频词汇到 medical_dict';

-- ============================================================================
-- Part 3: 清理 standard_data_conflict (预计 +17 项)
-- ============================================================================

-- 3.1 标记重复的 SPECT 大动脉显像编码（保留新编码 50100000110000）
UPDATE standard_check_items
SET is_active = false,
    review_status = 'deprecated_duplicate'
WHERE item_code = 'C010A802B0000'
  AND item_name LIKE '%SPECT放射性核素大动脉显像%'
  AND version = 'v2.0';

RAISE NOTICE '✓ 已标记废弃: C010A802B0000 (SPECT放射性核素大动脉显像 v2.0)';

-- 3.2 CT 全脊柱冲突处理（需要临床确认保留哪个编码）
-- 先查询现有编码
DO $$
DECLARE
    conflict_count INT;
BEGIN
    SELECT COUNT(*) INTO conflict_count
    FROM standard_check_items
    WHERE item_name LIKE '* CT全脊柱%'
      AND is_active = true
      AND version = 'v3.8.2'
    GROUP BY item_name
    HAVING COUNT(*) > 1;

    IF conflict_count > 0 THEN
        RAISE NOTICE '⚠ CT全脊柱存在 % 个冲突编码，需要人工审核', conflict_count;
    END IF;
END $$;

-- 3.3 MR 眼眶冲突处理
DO $$
DECLARE
    conflict_count INT;
BEGIN
    SELECT COUNT(*) INTO conflict_count
    FROM standard_check_items
    WHERE item_name LIKE '* MR眼眶%'
      AND is_active = true
      AND version = 'v3.8.2'
    GROUP BY item_name
    HAVING COUNT(*) > 1;

    IF conflict_count > 0 THEN
        RAISE NOTICE '⚠ MR眼眶存在 % 个冲突编码，需要人工审核', conflict_count;
    END IF;
END $$;

-- ============================================================================
-- Part 4: 验证和总结
-- ============================================================================

DO $$
DECLARE
    new_items_count INT;
    new_words_count INT;
BEGIN
    -- 统计新增标准项
    SELECT COUNT(*) INTO new_items_count
    FROM standard_check_items
    WHERE source = 'acr_4555_optimization_phase1';

    -- 统计新增词汇
    SELECT COUNT(*) INTO new_words_count
    FROM medical_dict
    WHERE source LIKE '%acr_4555_optimization_phase1%';

    RAISE NOTICE '';
    RAISE NOTICE '========================================================================';
    RAISE NOTICE 'Phase 1 优化完成';
    RAISE NOTICE '========================================================================';
    RAISE NOTICE '新增标准项: % 条', new_items_count;
    RAISE NOTICE '新增词汇: % 个', new_words_count;
    RAISE NOTICE '';
    RAISE NOTICE '下一步:';
    RAISE NOTICE '  1. 重启匹配引擎加载新词表';
    RAISE NOTICE '  2. 运行 poetry run python scripts/evaluate_acr_4555.py';
    RAISE NOTICE '  3. 对比基线验证匹配率提升';
    RAISE NOTICE '  4. 审核标准项冲突并确认保留编码';
    RAISE NOTICE '';
END $$;

COMMIT;

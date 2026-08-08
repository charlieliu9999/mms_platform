-- 添加复合部位标准项
-- 目标: 解决14个"全脊柱"、"头颈部"等复合检查的匹配问题

-- ============================================================
-- CT 全脊柱
-- ============================================================
INSERT INTO standard_check_items (
    item_code, item_name, modality, 
    body_part_l1, body_part_l2, body_part_l3, 
    scan_method, post_process,
    version, source, is_active, created_at
) VALUES
-- CT全脊柱
('CT_FULL_SPINE_001', '* CT全脊柱(平扫)', 'CT', '脊柱', '全脊柱', '全脊柱', '平扫', '', 'V3.8.2', 'P3补充-复合部位', true, NOW()),
('CT_FULL_SPINE_002', '* CT全脊柱(增强)', 'CT', '脊柱', '全脊柱', '全脊柱', '增强', '', 'V3.8.2', 'P3补充-复合部位', true, NOW()),
('CT_FULL_SPINE_003', '* CT全脊柱(平扫+增强)', 'CT', '脊柱', '全脊柱', '全脊柱', '平扫+增强', '', 'V3.8.2', 'P3补充-复合部位', true, NOW()),

-- CT脊柱（脊髓造影）
('CT_SPINE_MYELO_001', '* CT脊柱(脊髓造影)', 'CT', '脊柱', '脊柱局部', '脊柱', '脊髓造影', '', 'V3.8.2', 'P3补充-复合部位', true, NOW()),
('CT_SPINE_MYELO_002', '* CT脊柱(脊髓造影+增强)', 'CT', '脊柱', '脊柱局部', '脊柱', '脊髓造影', '增强', 'V3.8.2', 'P3补充-复合部位', true, NOW());

-- ============================================================
-- MR 全脊柱
-- ============================================================
INSERT INTO standard_check_items (
    item_code, item_name, modality, 
    body_part_l1, body_part_l2, body_part_l3, 
    scan_method, post_process,
    version, source, is_active, created_at
) VALUES
('MR_FULL_SPINE_001', '* MR全脊柱(平扫)', 'MR', '脊柱', '全脊柱', '全脊柱', '平扫', '', 'V3.8.2', 'P3补充-复合部位', true, NOW()),
('MR_FULL_SPINE_002', '* MR全脊柱(增强)', 'MR', '脊柱', '全脊柱', '全脊柱', '增强', '', 'V3.8.2', 'P3补充-复合部位', true, NOW()),
('MR_FULL_SPINE_003', '* MR全脊柱(平扫+增强)', 'MR', '脊柱', '全脊柱', '全脊柱', '平扫+增强', '', 'V3.8.2', 'P3补充-复合部位', true, NOW());

-- ============================================================
-- MR 头颈部
-- ============================================================
INSERT INTO standard_check_items (
    item_code, item_name, modality, 
    body_part_l1, body_part_l2, body_part_l3, 
    scan_method, post_process,
    version, source, is_active, created_at
) VALUES
('MR_HEAD_NECK_001', '* MR头颈部(平扫)', 'MR', '头颈部', '头颈部', '头颈部', '平扫', '', 'V3.8.2', 'P3补充-复合部位', true, NOW()),
('MR_HEAD_NECK_002', '* MR头颈部(增强)', 'MR', '头颈部', '头颈部', '头颈部', '增强', '', 'V3.8.2', 'P3补充-复合部位', true, NOW()),
('MR_HEAD_NECK_003', '* MR头颈部(平扫+增强)', 'MR', '头颈部', '头颈部', '头颈部', '平扫+增强', '', 'V3.8.2', 'P3补充-复合部位', true, NOW()),
('MR_HEAD_NECK_004', '* MR头颈部动脉血管成像(MRA)', 'MR', '头颈部', '头颈部', '头颈部动脉', '动脉血管成像(MRA)', '', 'V3.8.2', 'P3补充-复合部位', true, NOW()),
('MR_HEAD_NECK_005', '* MR头颈部静脉血管成像(MRV)', 'MR', '头颈部', '头颈部', '头颈部静脉', '静脉血管成像(MRV)', '', 'V3.8.2', 'P3补充-复合部位', true, NOW());

-- ============================================================
-- MR 胸腹部
-- ============================================================
INSERT INTO standard_check_items (
    item_code, item_name, modality, 
    body_part_l1, body_part_l2, body_part_l3, 
    scan_method, post_process,
    version, source, is_active, created_at
) VALUES
('MR_CHEST_ABD_001', '* MR胸腹部(平扫)', 'MR', '胸腹部', '胸腹部', '胸腹部', '平扫', '', 'V3.8.2', 'P3补充-复合部位', true, NOW()),
('MR_CHEST_ABD_002', '* MR胸腹部大血管血管成像', 'MR', '胸腹部', '胸腹部大血管', '胸腹部大血管', '血管成像', '增强', 'V3.8.2', 'P3补充-复合部位', true, NOW());

-- ============================================================
-- MR 全消化道
-- ============================================================
INSERT INTO standard_check_items (
    item_code, item_name, modality, 
    body_part_l1, body_part_l2, body_part_l3, 
    scan_method, post_process,
    version, source, is_active, created_at
) VALUES
('MR_GI_TRACT_001', '* MR全消化道(平扫)', 'MR', '消化道', '全消化道', '全消化道', '平扫', '', 'V3.8.2', 'P3补充-复合部位', true, NOW());

-- ============================================================
-- 添加词库支持
-- ============================================================
INSERT INTO nlp_medical_dict (word, type, enable) VALUES
('全脊柱', 'body_part', 0),
('头颈部', 'body_part', 0),
('胸腹部', 'body_part', 0),
('全消化道', 'body_part', 0)
ON CONFLICT DO NOTHING;

-- 验证
SELECT COUNT(*) as added_count FROM standard_check_items 
WHERE source = 'P3补充-复合部位';

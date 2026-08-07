-- 修复P2补充血管成像标准项的字段
-- 创建时间: 2026-08-07
-- 问题: body_part_l3为空，scan_method格式不标准，导致匹配失败

-- 肺动脉/肺静脉
UPDATE standard_check_items
SET body_part_l3 = '肺动脉', scan_method = '动脉血管成像(MRA)'
WHERE item_code = 'MR_0481';

UPDATE standard_check_items
SET body_part_l3 = '肺静脉', scan_method = '静脉血管成像(MRV)'
WHERE item_code = 'MR_0490';

-- 主动脉
UPDATE standard_check_items
SET body_part_l3 = '主动脉', scan_method = '动脉血管成像(MRA)'
WHERE item_code = 'MR_0485';

-- 肝脏动脉
UPDATE standard_check_items
SET body_part_l3 = '肝脏动脉', scan_method = '动脉血管成像(MRA)'
WHERE item_code = 'MR_0493';

-- 椎-基底动脉
UPDATE standard_check_items
SET body_part_l3 = '椎-基底动脉', scan_method = '动脉血管成像(MRA)'
WHERE item_code = 'MR_0495';

-- 上肢静脉
UPDATE standard_check_items
SET body_part_l3 = '上肢静脉', scan_method = '静脉血管成像(MRV)'
WHERE item_code = 'MR_0486';

-- 头颈部静脉
UPDATE standard_check_items
SET body_part_l3 = '头颈部静脉', scan_method = '静脉血管成像(MRV)'
WHERE item_code = 'MR_0489';

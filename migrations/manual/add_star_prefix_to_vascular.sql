-- 为P2补充的血管成像标准项添加星号前缀
-- 创建时间: 2026-08-07
-- 目标: 使其与ACR标准项保持一致的命名格式

UPDATE standard_check_items
SET item_name = '* ' || item_name
WHERE item_code IN ('MR_0481', 'MR_0486', 'MR_0489', 'MR_0490', 'MR_0493', 'MR_0495', 'MR_0485')
  AND item_name NOT LIKE '* %';

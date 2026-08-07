-- 修正P2补充血管成像标准项的版本号
-- 创建时间: 2026-08-08
-- 问题: P2补充项版本为1.0，而引擎查询V3.8.2，导致未被加载

UPDATE standard_check_items
SET version = 'V3.8.2'
WHERE source = 'P2补充-血管成像'
  AND version = '1.0';

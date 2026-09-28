-- Phase 2: 词库映射补充脚本
-- 用途：补充缺失的医学术语，提升匹配率
-- 执行前提：数据库已启动并可访问

-- ============================================================
-- 1. 医学词典（medical_dict）补充
-- ============================================================

-- 扫描方式相关
INSERT INTO medical_dict (word, std_name, pos_type, version, is_deleted, create_time, update_time)
VALUES
    ('动静脉双期增强', '动静脉双期增强', 'scan', 'V3.8.2', 0, NOW(), NOW()),
    ('脊髓造影', '脊髓造影', 'scan', 'V3.8.2', 0, NOW(), NOW()),
    ('直接造影', '直接造影', 'scan', 'V3.8.2', 0, NOW(), NOW())
ON CONFLICT (word, version) DO NOTHING;

-- 部位相关
INSERT INTO medical_dict (word, std_name, pos_type, version, is_deleted, create_time, update_time)
VALUES
    ('原发部位', '原发部位', 'body', 'V3.8.2', 0, NOW(), NOW()),
    ('区域淋巴结', '区域淋巴结', 'body', 'V3.8.2', 0, NOW(), NOW())
ON CONFLICT (word, version) DO NOTHING;

-- 后处理相关
INSERT INTO medical_dict (word, std_name, pos_type, version, is_deleted, create_time, update_time)
VALUES
    ('UHR模式', '超高分辨率', 'post', 'V3.8.2', 0, NOW(), NOW()),
    ('超高分辨率', '超高分辨率', 'post', 'V3.8.2', 0, NOW(), NOW()),
    ('UHR', '超高分辨率', 'post', 'V3.8.2', 0, NOW(), NOW())
ON CONFLICT (word, version) DO NOTHING;

-- ============================================================
-- 2. 短语映射（phrase_map）补充
-- ============================================================

-- 动静脉双期的变体映射
INSERT INTO phrase_map (src, dst, dst_type, version, is_deleted, create_time, update_time)
VALUES
    ('动静脉双期', '动静脉双期增强', 'scan', 'V3.8.2', 0, NOW(), NOW()),
    ('双期增强', '动静脉双期增强', 'scan', 'V3.8.2', 0, NOW(), NOW()),
    ('动静脉双期扫描', '动静脉双期增强', 'scan', 'V3.8.2', 0, NOW(), NOW())
ON CONFLICT (src, version) DO NOTHING;

-- 原发部位的变体映射
INSERT INTO phrase_map (src, dst, dst_type, version, is_deleted, create_time, update_time)
VALUES
    ('原发灶', '原发部位', 'body', 'V3.8.2', 0, NOW(), NOW()),
    ('原发病灶', '原发部位', 'body', 'V3.8.2', 0, NOW(), NOW())
ON CONFLICT (src, version) DO NOTHING;

-- 淋巴结的变体映射
INSERT INTO phrase_map (src, dst, dst_type, version, is_deleted, create_time, update_time)
VALUES
    ('淋巴结区域', '区域淋巴结', 'body', 'V3.8.2', 0, NOW(), NOW()),
    ('区域淋巴', '区域淋巴结', 'body', 'V3.8.2', 0, NOW(), NOW())
ON CONFLICT (src, version) DO NOTHING;

-- ============================================================
-- 3. 验证插入结果
-- ============================================================

-- 查看新增的医学词典条目
SELECT word, std_name, pos_type
FROM medical_dict
WHERE word IN (
    '动静脉双期增强', '脊髓造影', '直接造影',
    '原发部位', '区域淋巴结',
    'UHR模式', '超高分辨率', 'UHR'
)
AND version = 'V3.8.2'
ORDER BY pos_type, word;

-- 查看新增的短语映射
SELECT src, dst, dst_type
FROM phrase_map
WHERE src IN (
    '动静脉双期', '双期增强', '动静脉双期扫描',
    '原发灶', '原发病灶',
    '淋巴结区域', '区域淋巴'
)
AND version = 'V3.8.2'
ORDER BY dst_type, src;

-- ============================================================
-- 预期效果
-- ============================================================

-- 补充前未匹配项：
--   1. CT腹部盆腔(平扫+动静脉双期增强)
--   2. CT原发部位及区域淋巴结(平扫+增强)
--   3. CT颞骨(超高分辨率UHR模式)

-- 补充后预期：
--   1. 能够解析"动静脉双期增强"为扫描方式
--   2. 能够识别"原发部位"和"区域淋巴结"为部位
--   3. 能够识别"UHR模式/超高分辨率"为后处理方式

-- 预计提升：+3 项匹配，匹配率从 20% → 50%

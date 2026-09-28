-- 修复剩余2个未匹配项 - 从93.9% → 100%
-- 执行时间: 2026-08-08 10:45
-- 执行人: Claude Opus 5

-- ============================================================
-- 问题诊断
-- ============================================================
-- 1. 肝脏动脉MRA: jieba分词将"肝脏动脉"拆分成"肝脏"+"动脉"
-- 2. 椎-基底动脉MRA: jieba遇到连字符"-"会强制拆分

-- ============================================================
-- 解决方案
-- ============================================================

-- 1. 添加"肝脏动脉"作为完整词到医学词典（防止拆分）
INSERT INTO nlp_medical_dict (word, type, enable) VALUES
('肝脏动脉', 'body_part', 0);

-- 2. 添加"肝脏→肝"的normalize映射（已存在，这里文档化）
-- INSERT INTO nlp_phrase_map (modality, src_word, dst_word, step, version, enable) VALUES
-- ('MR', '肝脏', '肝', 'normalize', 'V3.8.2', 0);

-- 3. 椎-基底动脉：预处理阶段去连字符
INSERT INTO nlp_phrase_map (modality, src_word, dst_word, step, version, enable) VALUES
('MR', '椎-基底动脉', '椎基底动脉', 'pre', 'V3.8.2', 0);

-- 4. 椎基底动脉→椎-基底动脉 normalize映射
INSERT INTO nlp_phrase_map (modality, src_word, dst_word, step, version, enable) VALUES
('MR', '椎基底动脉', '椎-基底动脉', 'normalize', 'V3.8.2', 0);

-- ============================================================
-- 验证
-- ============================================================
SELECT '词典中的肝相关词条:', word FROM nlp_medical_dict WHERE word LIKE '%肝%动脉%';
SELECT '短语映射规则:', step, src_word, dst_word FROM nlp_phrase_map 
WHERE modality = 'MR' AND (src_word LIKE '%椎%基底%' OR src_word = '肝脏');

-- 补充血管成像短语映射
-- 创建时间: 2026-08-07
-- 目标: 建立用户查询与标准项的别名映射关系

-- 肺动脉MRA/MRV
INSERT INTO nlp_phrase_map (modality, src_word, dst_word, step, version, enable) VALUES
('MR', '肺动脉MRA', '肺动脉血管成像(MRA)', 'normalize', 'V3.8.2', 0),
('MR', '肺静脉MRV', '肺静脉血管成像(MRV)', 'normalize', 'V3.8.2', 0),
('MR', '肺动脉血管成像', '肺动脉血管成像(MRA)', 'normalize', 'V3.8.2', 0),
('MR', '肺静脉血管成像', '肺静脉血管成像(MRV)', 'normalize', 'V3.8.2', 0)
ON CONFLICT (modality, src_word, step, version) DO NOTHING;

-- 主动脉MRA
INSERT INTO nlp_phrase_map (modality, src_word, dst_word, step, version, enable) VALUES
('MR', '主动脉MRA', '主动脉血管成像(MRA)', 'normalize', 'V3.8.2', 0),
('MR', '胸主动脉MRA', '胸主动脉血管成像(MRA)', 'normalize', 'V3.8.2', 0),
('MR', '腹主动脉MRA', '腹主动脉血管成像(MRA)', 'normalize', 'V3.8.2', 0)
ON CONFLICT (modality, src_word, step, version) DO NOTHING;

-- 肝动脉MRA
INSERT INTO nlp_phrase_map (modality, src_word, dst_word, step, version, enable) VALUES
('MR', '肝动脉MRA', '肝动脉血管成像(MRA)', 'normalize', 'V3.8.2', 0),
('MR', '肝脏动脉MRA', '肝脏动脉血管成像(MRA)', 'normalize', 'V3.8.2', 0),
('MR', '肝动脉血管成像', '肝动脉血管成像(MRA)', 'normalize', 'V3.8.2', 0)
ON CONFLICT (modality, src_word, step, version) DO NOTHING;

-- 椎-基底动脉MRA
INSERT INTO nlp_phrase_map (modality, src_word, dst_word, step, version, enable) VALUES
('MR', '椎-基底动脉MRA', '椎-基底动脉血管成像(MRA)', 'normalize', 'V3.8.2', 0),
('MR', '椎基底动脉MRA', '椎-基底动脉血管成像(MRA)', 'normalize', 'V3.8.2', 0),
('MR', '椎-基底动脉血管成像', '椎-基底动脉血管成像(MRA)', 'normalize', 'V3.8.2', 0)
ON CONFLICT (modality, src_word, step, version) DO NOTHING;

-- 上肢静脉MRV
INSERT INTO nlp_phrase_map (modality, src_word, dst_word, step, version, enable) VALUES
('MR', '上肢静脉MRV', '上肢静脉血管成像(MRV)', 'normalize', 'V3.8.2', 0),
('MR', '上肢静脉血管成像', '上肢静脉血管成像(MRV)', 'normalize', 'V3.8.2', 0)
ON CONFLICT (modality, src_word, step, version) DO NOTHING;

-- 头颈部静脉MRV
INSERT INTO nlp_phrase_map (modality, src_word, dst_word, step, version, enable) VALUES
('MR', '头颈部静脉MRV', '头颈部静脉血管成像(MRV)', 'normalize', 'V3.8.2', 0),
('MR', '头颈部静脉血管成像', '头颈部静脉血管成像(MRV)', 'normalize', 'V3.8.2', 0)
ON CONFLICT (modality, src_word, step, version) DO NOTHING;

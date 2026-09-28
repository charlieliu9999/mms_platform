-- 补充血管相关词条
-- 创建时间: 2026-08-07
-- 目标: 挽回7项血管成像未匹配项目

INSERT INTO nlp_medical_dict (word, type, enable) VALUES
('肺动脉', 'body_part', 0),
('肺静脉', 'body_part', 0),
('肝动脉', 'body_part', 0),
('肝静脉', 'body_part', 0),
('头颈部', 'body_part', 0),
('椎基底动脉', 'body_part', 0),
('椎-基底动脉', 'body_part', 0)
ON CONFLICT (word) DO NOTHING;

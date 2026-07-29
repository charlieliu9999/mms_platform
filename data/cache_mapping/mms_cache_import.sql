-- MMS Platform 生产缓存导入脚本
-- 生成时间: 2026-07-29 16:27:11
-- 记录数: 229

-- 创建临时表
CREATE TEMP TABLE IF NOT EXISTS temp_cache_import (
    raw_check_item VARCHAR(512),
    modality VARCHAR(32),
    standard_code VARCHAR(64),
    standard_name VARCHAR(128),
    version VARCHAR(32),
    confidence FLOAT,
    source VARCHAR(32),
    tier VARCHAR(32),
    compound_num INTEGER,
    unique_key VARCHAR(255)
);

-- 插入数据
INSERT INTO temp_cache_import VALUES ('磁共振平扫（腰椎）,骶尾椎平扫', 'MR', '3003124000.0', '* MR骶尾椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '');
INSERT INTO temp_cache_import VALUES ('右股骨三维重建,右股骨下段CT平扫,胸部CT平扫,下肢血管成像', 'CT', '2107171010.0', '* CT右侧股骨（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '');
INSERT INTO temp_cache_import VALUES ('上腹部CT平扫,胸部CT平扫,头颅CT平扫,颈部（软组织）平扫', 'CT', '2105011000.0', '* CT上腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '');
INSERT INTO temp_cache_import VALUES ('胸部+右前壁CT', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '');
INSERT INTO temp_cache_import VALUES ('磁共振平扫（胸腰椎）,磁共振平扫（颈椎）', 'MR', '3003054000.0', '* MR颈椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '');
INSERT INTO temp_cache_import VALUES ('磁共振平扫（胸腰椎）,磁共振平扫（颈椎）', 'MR', '3003104000.0', '* MR胸腰段（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '');
INSERT INTO temp_cache_import VALUES ('右股骨三维重建,右股骨下段CT平扫,胸部CT平扫,下肢血管成像', 'CT', '2108182200.0', '* CT下肢动脉血管造影（CTA）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '');
INSERT INTO temp_cache_import VALUES ('右股骨三维重建,右股骨下段CT平扫,胸部CT平扫,下肢血管成像', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '');
INSERT INTO temp_cache_import VALUES ('上腹部CT平扫,胸部CT平扫,头颅CT平扫,颈部（软组织）平扫', 'CT', '2102011000.0', '* CT颈部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '');
INSERT INTO temp_cache_import VALUES ('上腹部CT平扫,胸部CT平扫,头颅CT平扫,颈部（软组织）平扫', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '');
INSERT INTO temp_cache_import VALUES ('磁共振平扫（腰椎）,骶尾椎平扫', 'MR', '3003074000.0', '* MR腰椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部);ct平扫（左膝关节）三维重建', 'CT', '2107181010.0', '* CT左侧膝关节（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部);ct平扫（左膝关节）三维重建', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '');
INSERT INTO temp_cache_import VALUES ('头部MRA,头部MRV,头部3DFLAIR', 'MR', '3001014000.0', '* MR颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '');
INSERT INTO temp_cache_import VALUES ('头部MRA,头部MRV,头部3DFLAIR', 'MR', '3008024900.0', '* MR头部静脉血管成像（MRV）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '');
INSERT INTO temp_cache_import VALUES ('头部MRA,头部MRV,头部3DFLAIR', 'MR', '3008014500.0', '* MR头部动脉血管成像（MRA）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '');
INSERT INTO temp_cache_import VALUES ('上腹部CT平扫,胸部CT平扫,头颅CT平扫,颈部（软组织）平扫', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '');
INSERT INTO temp_cache_import VALUES ('磁共振增强扫描（胸椎）', 'MR', '3003064100.0', '* MR胸椎（增强）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01358231f38450180adabb23263f3a7c');
INSERT INTO temp_cache_import VALUES ('DWI(颅脑);', 'MR', '3001015300.0', '* MR颅脑弥散加权成像（DWI）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '02a6f390ce70cf40ac875f57a5fdcbc9');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部),主动脉CTA', 'CT', '2108212200.0', '* CT主动脉血管造影（CTA）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0295aeda05b95acf42d79412ea581c52');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部),主动脉CTA', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0295aeda05b95acf42d79412ea581c52');
INSERT INTO temp_cache_import VALUES ('磁共振平扫(3T及以上);;脑功能成像（颅脑）;', 'MR', '3001015200.0', '* MR颅脑功能性磁共振成像（fMRI）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '024ff94db2adac281ceecd75c6b17a62');
INSERT INTO temp_cache_import VALUES ('磁共振平扫(3T及以上);;脑功能成像（颅脑）;', 'MR', '3001014000.0', '* MR颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '024ff94db2adac281ceecd75c6b17a62');
INSERT INTO temp_cache_import VALUES ('全腹部平扫,CT平扫(颅脑),三维重建(CT)', 'CT', '2101011010.0', '* CT颅脑（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0299558efe43b497bcb06d425798fb3e');
INSERT INTO temp_cache_import VALUES ('全腹部平扫,CT平扫(颅脑),三维重建(CT)', 'CT', '2105121000.0', '* CT全腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0299558efe43b497bcb06d425798fb3e');
INSERT INTO temp_cache_import VALUES ('颈部成像/颈部MRI平扫', 'MR', '3002014000.0', '* MR颈部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0282432f2a464a80aaefef63dd4b956d');
INSERT INTO temp_cache_import VALUES ('肾脏CT平扫,输尿管膀胱CT平扫,胸部CT平扫,肾脏CT平扫', 'CT', '2105041000.0', '* CT双肾（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '027708ec837b0d596ebbf02d1513285d');
INSERT INTO temp_cache_import VALUES ('肾脏CT平扫,输尿管膀胱CT平扫,胸部CT平扫,肾脏CT平扫', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '027708ec837b0d596ebbf02d1513285d');
INSERT INTO temp_cache_import VALUES ('肾脏CT平扫,输尿管膀胱CT平扫,胸部CT平扫,肾脏CT平扫', 'CT', '2105111000.0', '* CT全泌尿系（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '027708ec837b0d596ebbf02d1513285d');
INSERT INTO temp_cache_import VALUES ('头颅CT平扫;颌面部CT平扫;上腹部CT平扫', 'CT', '2105011000.0', '* CT上腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '026fbec7d3e5ccd763597a158b808c50');
INSERT INTO temp_cache_import VALUES ('头颅CT平扫;颌面部CT平扫;上腹部CT平扫', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '026fbec7d3e5ccd763597a158b808c50');
INSERT INTO temp_cache_import VALUES ('头颅CT平扫;颌面部CT平扫;上腹部CT平扫', 'CT', '2101031000.0', '* CT颌面部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '026fbec7d3e5ccd763597a158b808c50');
INSERT INTO temp_cache_import VALUES ('髋关节平扫,CT平扫(颅脑),CT平扫(胸部),CT平扫(腰椎)', 'CT', '2103071000.0', '* CT腰椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '028db1f5a9256c4d08b3e2a03e828475');
INSERT INTO temp_cache_import VALUES ('髋关节平扫,CT平扫(颅脑),CT平扫(胸部),CT平扫(腰椎)', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '028db1f5a9256c4d08b3e2a03e828475');
INSERT INTO temp_cache_import VALUES ('髋关节平扫,CT平扫(颅脑),CT平扫(胸部),CT平扫(腰椎)', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '028db1f5a9256c4d08b3e2a03e828475');
INSERT INTO temp_cache_import VALUES ('髋关节平扫,CT平扫(颅脑),CT平扫(胸部),CT平扫(腰椎)', 'CT', '2107261000.0', '* CT髋关节（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '028db1f5a9256c4d08b3e2a03e828475');
INSERT INTO temp_cache_import VALUES ('胸部CT平扫;上腹部CT平扫;下腹部CT平扫;头颅CT平扫', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '027ec3c186670627f7c892e0e4945fb7');
INSERT INTO temp_cache_import VALUES ('胸部CT平扫;上腹部CT平扫;下腹部CT平扫;头颅CT平扫', 'CT', '2105031000.0', '* CT下腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '027ec3c186670627f7c892e0e4945fb7');
INSERT INTO temp_cache_import VALUES ('胸部CT平扫;上腹部CT平扫;下腹部CT平扫;头颅CT平扫', 'CT', '2105011000.0', '* CT上腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '027ec3c186670627f7c892e0e4945fb7');
INSERT INTO temp_cache_import VALUES ('胸部CT平扫;上腹部CT平扫;下腹部CT平扫;头颅CT平扫', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '027ec3c186670627f7c892e0e4945fb7');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部),肋骨三维,CT平扫(腰椎),CT平扫(上腹部)', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0268c86c70796d14ffb186a84c21793a');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部),肋骨三维,CT平扫(腰椎),CT平扫(上腹部)', 'CT', '2103071000.0', '* CT腰椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0268c86c70796d14ffb186a84c21793a');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部),肋骨三维,CT平扫(腰椎),CT平扫(上腹部)', 'CT', '2104051010.0', '* CT肋骨（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0268c86c70796d14ffb186a84c21793a');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部),肋骨三维,CT平扫(腰椎),CT平扫(上腹部)', 'CT', '2105011000.0', '* CT上腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0268c86c70796d14ffb186a84c21793a');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部),CT平扫(胸椎),三维重建(CT),三维重建(CT),CT平扫(颈椎),椎间隙（四个）,CT平扫(颅脑),三维重建(CT)', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0268e2aece2deba667cb33c898da3916');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部),CT平扫(胸椎),三维重建(CT),三维重建(CT),CT平扫(颈椎),椎间隙（四个）,CT平扫(颅脑),三维重建(CT)', 'CT', '2103051000.0', '* CT颈椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0268e2aece2deba667cb33c898da3916');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部),CT平扫(胸椎),三维重建(CT),三维重建(CT),CT平扫(颈椎),椎间隙（四个）,CT平扫(颅脑),三维重建(CT)', 'CT', '2103061010.0', '* CT胸椎（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0268e2aece2deba667cb33c898da3916');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部),CT平扫(胸椎),三维重建(CT),三维重建(CT),CT平扫(颈椎),椎间隙（四个）,CT平扫(颅脑),三维重建(CT)', 'CT', '2101011010.0', '* CT颅脑（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0268e2aece2deba667cb33c898da3916');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部),CT平扫(胸椎),三维重建(CT),三维重建(CT),CT平扫(颈椎),椎间隙（四个）,CT平扫(颅脑),三维重建(CT)', 'CT', '2103081000.0', '* CT全脊柱（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0268e2aece2deba667cb33c898da3916');
INSERT INTO temp_cache_import VALUES ('骨盆CT平扫;胸部CT平扫;右髋关节三维重建', 'CT', '2107261010.0', '* CT髋关节（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0263f33067a18904ee46de6412173732');
INSERT INTO temp_cache_import VALUES ('骨盆CT平扫;胸部CT平扫;右髋关节三维重建', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0263f33067a18904ee46de6412173732');
INSERT INTO temp_cache_import VALUES ('骨盆CT平扫;胸部CT平扫;右髋关节三维重建', 'CT', '2106011000.0', '* CT骨盆（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0263f33067a18904ee46de6412173732');
INSERT INTO temp_cache_import VALUES ('肝胆脾胰(彩超),上腹部CT平扫,下腹部CT平扫', 'CT', '2105031000.0', '* CT下腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '025811eb43dc29131d95bc74329631a5');
INSERT INTO temp_cache_import VALUES ('肝胆脾胰(彩超),上腹部CT平扫,下腹部CT平扫', 'CT', '2105011000.0', '* CT上腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '025811eb43dc29131d95bc74329631a5');
INSERT INTO temp_cache_import VALUES ('CT平扫(下腹部),CT平扫(胸部),CT平扫(上腹部),CT平扫', 'CT', '2105011000.0', '* CT上腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '025dc02e7631e9786bf6eb52ae4a6adf');
INSERT INTO temp_cache_import VALUES ('CT平扫(下腹部),CT平扫(胸部),CT平扫(上腹部),CT平扫', 'CT', '2105031000.0', '* CT下腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '025dc02e7631e9786bf6eb52ae4a6adf');
INSERT INTO temp_cache_import VALUES ('CT平扫(下腹部),CT平扫(胸部),CT平扫(上腹部),CT平扫', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '025dc02e7631e9786bf6eb52ae4a6adf');
INSERT INTO temp_cache_import VALUES ('CT成套:颅脑(平扫),上腹部(平扫),中腹部(平扫)', 'CT', '2105021000.0', '* CT中腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '025547aafcb891cd9d5fd06ec5222ac7');
INSERT INTO temp_cache_import VALUES ('CT成套:颅脑(平扫),上腹部(平扫),中腹部(平扫)', 'CT', '2105011000.0', '* CT上腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '025547aafcb891cd9d5fd06ec5222ac7');
INSERT INTO temp_cache_import VALUES ('CT成套:颅脑(平扫),上腹部(平扫),中腹部(平扫)', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '025547aafcb891cd9d5fd06ec5222ac7');
INSERT INTO temp_cache_import VALUES ('头颅CT平扫,颈部CT平扫,上腹部CT平扫,下腹部CT平扫,胸部CT平扫', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0254a5bae1ba4ab02898b6bb3530959e');
INSERT INTO temp_cache_import VALUES ('头颅CT平扫,颈部CT平扫,上腹部CT平扫,下腹部CT平扫,胸部CT平扫', 'CT', '2105031000.0', '* CT下腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0254a5bae1ba4ab02898b6bb3530959e');
INSERT INTO temp_cache_import VALUES ('头颅CT平扫,颈部CT平扫,上腹部CT平扫,下腹部CT平扫,胸部CT平扫', 'CT', '2105011000.0', '* CT上腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0254a5bae1ba4ab02898b6bb3530959e');
INSERT INTO temp_cache_import VALUES ('头颅CT平扫,颈部CT平扫,上腹部CT平扫,下腹部CT平扫,胸部CT平扫', 'CT', '2102011000.0', '* CT颈部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0254a5bae1ba4ab02898b6bb3530959e');
INSERT INTO temp_cache_import VALUES ('头颅CT平扫,颈部CT平扫,上腹部CT平扫,下腹部CT平扫,胸部CT平扫', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0254a5bae1ba4ab02898b6bb3530959e');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部),CT平扫(上腹部),CT平扫(腰椎)', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '024b0f9a2e00f55f81d7e7b282c6609a');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部),CT平扫(上腹部),CT平扫(腰椎)', 'CT', '2103071000.0', '* CT腰椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '024b0f9a2e00f55f81d7e7b282c6609a');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部),CT平扫(上腹部),CT平扫(腰椎)', 'CT', '2105011000.0', '* CT上腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '024b0f9a2e00f55f81d7e7b282c6609a');
INSERT INTO temp_cache_import VALUES ('颈椎3-7椎体平扫,头颅', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '021d0f14b587d53893bde0894938f18e');
INSERT INTO temp_cache_import VALUES ('颈椎3-7椎体平扫,头颅', 'CT', '2103051000.0', '* CT颈椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '021d0f14b587d53893bde0894938f18e');
INSERT INTO temp_cache_import VALUES ('胸椎平扫,腰椎平扫', 'MR', '3003074000.0', '* MR腰椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0215134272b20dd80c6e3668244873fa');
INSERT INTO temp_cache_import VALUES ('胸椎平扫,腰椎平扫', 'MR', '3003064000.0', '* MR胸椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0215134272b20dd80c6e3668244873fa');
INSERT INTO temp_cache_import VALUES ('磁共振平扫(颅脑),磁共振增强扫描（颅脑）', 'MR', '3001014000.0', '* MR颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0211ecc9542aae2e0fb4b8e36cd81a7a');
INSERT INTO temp_cache_import VALUES ('磁共振平扫(颅脑),磁共振增强扫描（颅脑）', 'MR', '3001014100.0', '* MR颅脑（增强）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0211ecc9542aae2e0fb4b8e36cd81a7a');
INSERT INTO temp_cache_import VALUES ('胸部CT平扫;肺动脉血管成像', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01ebc76da2487a4266793d7728918a96');
INSERT INTO temp_cache_import VALUES ('胸部CT平扫;肺动脉血管成像', 'CT', '2108132200.0', '* CT肺动脉血管造影（CTA）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01ebc76da2487a4266793d7728918a96');
INSERT INTO temp_cache_import VALUES ('三维重建,;CT平扫(双肾),', 'CT', '2105041010.0', '* CT双肾（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '020a4b91d9acad0b9006022b0ff1725b');
INSERT INTO temp_cache_import VALUES ('CT平扫(颈部),三维重建(CT),三维重建(CT),CT平扫(胸部)', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0204a690969b2b4fc11340c8652beb9a');
INSERT INTO temp_cache_import VALUES ('CT平扫(颈部),三维重建(CT),三维重建(CT),CT平扫(胸部)', 'CT', '2102011010.0', '* CT颈部（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0204a690969b2b4fc11340c8652beb9a');
INSERT INTO temp_cache_import VALUES ('CT平扫(盆腔);;CT平扫(下腹部);', 'CT', '2105031000.0', '* CT下腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '020d70cccac3beb11b98efe0cc7e7c46');
INSERT INTO temp_cache_import VALUES ('CT平扫(盆腔);;CT平扫(下腹部);', 'CT', '2106021000.0', '* CT盆腔（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '020d70cccac3beb11b98efe0cc7e7c46');
INSERT INTO temp_cache_import VALUES ('腰椎三维重建,肋骨三维重建术', 'CT', '2104051010.0', '* CT肋骨（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '02066da381cfeee09812f0fb5d1b102c');
INSERT INTO temp_cache_import VALUES ('腰椎三维重建,肋骨三维重建术', 'CT', '2103071010.0', '* CT腰椎（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '02066da381cfeee09812f0fb5d1b102c');
INSERT INTO temp_cache_import VALUES ('磁共振平扫;（颅脑MRI）', 'MR', '3001014000.0', '* MR颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '020395c7c8097dfe466d4482c424c160');
INSERT INTO temp_cache_import VALUES ('肋骨三维;头颅平扫;', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01efedd8cdfdba3c1514fd8d73b67b02');
INSERT INTO temp_cache_import VALUES ('肋骨三维;头颅平扫;', 'CT', '2104051010.0', '* CT肋骨（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01efedd8cdfdba3c1514fd8d73b67b02');
INSERT INTO temp_cache_import VALUES ('椎间隙（四个）,CT平扫(颅脑),CT平扫(颈椎)', 'CT', '2103051000.0', '* CT颈椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01eb677d4ebe64bdd65123416127b44f');
INSERT INTO temp_cache_import VALUES ('椎间隙（四个）,CT平扫(颅脑),CT平扫(颈椎)', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01eb677d4ebe64bdd65123416127b44f');
INSERT INTO temp_cache_import VALUES ('椎间隙（四个）,CT平扫(颅脑),CT平扫(颈椎)', 'CT', '2103081000.0', '* CT全脊柱（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01eb677d4ebe64bdd65123416127b44f');
INSERT INTO temp_cache_import VALUES ('*MR腰椎（平扫）,去金属伪影序列', 'MR', '3003074000.0', '* MR腰椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01dd443ecd47f35220b7afd3d4521bc4');
INSERT INTO temp_cache_import VALUES ('CT平扫,CT平扫(颈椎),CT平扫(胸部),CT平扫X1', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01dbfae67526e562ad7543a1475d8d2a');
INSERT INTO temp_cache_import VALUES ('CT平扫,CT平扫(颈椎),CT平扫(胸部),CT平扫X1', 'CT', '2103051000.0', '* CT颈椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01dbfae67526e562ad7543a1475d8d2a');
INSERT INTO temp_cache_import VALUES ('中耳', 'CT', '2101041000.0', '* CT乳突薄层（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01da3adceeb3b3dc6783e5cc2214af1e');
INSERT INTO temp_cache_import VALUES ('*CT颅脑（平扫）,*CT三维重建', 'CT', '2101011010.0', '* CT颅脑（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01d552c0983abc414c5511ea6994aa86');
INSERT INTO temp_cache_import VALUES ('CT选一部位,胸部CT平扫,鼻咽部CT平扫', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01d1bc6bf10c2d2d52b6fda9b7a45cd9');
INSERT INTO temp_cache_import VALUES ('CT选一部位,胸部CT平扫,鼻咽部CT平扫', 'CT', '2102051000.0', '* CT鼻咽部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01d1bc6bf10c2d2d52b6fda9b7a45cd9');
INSERT INTO temp_cache_import VALUES ('胸部CT平扫;双髋关节CT平扫;左髋关节三维重建', 'CT', '2107261010.0', '* CT髋关节（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01b36ce5523a46982a19a726b2e2a6a4');
INSERT INTO temp_cache_import VALUES ('胸部CT平扫;双髋关节CT平扫;左髋关节三维重建', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01b36ce5523a46982a19a726b2e2a6a4');
INSERT INTO temp_cache_import VALUES ('CT平扫(下腹部);中腹部', 'CT', '2105021000.0', '* CT中腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01cd017eb0fcc3e2aaa78f56897cf4bd');
INSERT INTO temp_cache_import VALUES ('CT平扫(下腹部);中腹部', 'CT', '2105031000.0', '* CT下腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01cd017eb0fcc3e2aaa78f56897cf4bd');
INSERT INTO temp_cache_import VALUES ('CT成套:体表包块（颈部）(平扫)', 'CT', '2102011000.0', '* CT颈部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01ae1b263082a700d4b477d6fba791d0');
INSERT INTO temp_cache_import VALUES ('CT平扫(颅脑),CT平扫(胸部),CT平扫(上腹部),', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01cb1a39379db86fc5a4864b1fe3e7b0');
INSERT INTO temp_cache_import VALUES ('CT平扫(颅脑),CT平扫(胸部),CT平扫(上腹部),', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01cb1a39379db86fc5a4864b1fe3e7b0');
INSERT INTO temp_cache_import VALUES ('CT平扫(颅脑),CT平扫(胸部),CT平扫(上腹部),', 'CT', '2105011000.0', '* CT上腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01cb1a39379db86fc5a4864b1fe3e7b0');
INSERT INTO temp_cache_import VALUES ('胸部平扫;颅脑平扫(颅脑);', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01acb7b325bd0eab5cc4ca79f98b2c2e');
INSERT INTO temp_cache_import VALUES ('胸部平扫;颅脑平扫(颅脑);', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01acb7b325bd0eab5cc4ca79f98b2c2e');
INSERT INTO temp_cache_import VALUES ('CT平扫(下腹部),CT平扫(上腹部)', 'CT', '2105011000.0', '* CT上腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01a7b9075d72c67ac2fc91db58b8d33b');
INSERT INTO temp_cache_import VALUES ('CT平扫(下腹部),CT平扫(上腹部)', 'CT', '2105031000.0', '* CT下腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01a7b9075d72c67ac2fc91db58b8d33b');
INSERT INTO temp_cache_import VALUES ('胸椎', 'CT', '2103061000.0', '* CT胸椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01913b2f8dfbbe5311d142de772bc960');
INSERT INTO temp_cache_import VALUES ('肝胆胰脾MRI平扫,鼻咽部MRI平扫,肝胆脾胰MRI平扫,鼻咽部MRI平扫', 'MR', '3002054000.0', '* MR鼻咽部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01b3c9edbe011deade9e192506d3b79a');
INSERT INTO temp_cache_import VALUES ('肝胆胰脾MRI平扫,鼻咽部MRI平扫,肝胆脾胰MRI平扫,鼻咽部MRI平扫', 'MR', '3005014000.0', '* MR上腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01b3c9edbe011deade9e192506d3b79a');
INSERT INTO temp_cache_import VALUES ('CT平扫（盆腔）', 'CT', '2106021000.0', '* CT盆腔（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0192b179f2c7017f0dfa02fdc0f241b9');
INSERT INTO temp_cache_import VALUES ('CT平扫(盆腔),CT平扫(上腹部),CT平扫(肾上腺)', 'CT', '2105101000.0', '* CT双肾上腺（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '018f1f0f1dd19a853a84884407be8629');
INSERT INTO temp_cache_import VALUES ('CT平扫(盆腔),CT平扫(上腹部),CT平扫(肾上腺)', 'CT', '2106021000.0', '* CT盆腔（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '018f1f0f1dd19a853a84884407be8629');
INSERT INTO temp_cache_import VALUES ('CT平扫(盆腔),CT平扫(上腹部),CT平扫(肾上腺)', 'CT', '2105011000.0', '* CT上腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '018f1f0f1dd19a853a84884407be8629');
INSERT INTO temp_cache_import VALUES ('鼻咽部平扫+三维,胸部平扫', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0197d00f8cd1afd359c90f80cffd7187');
INSERT INTO temp_cache_import VALUES ('鼻咽部平扫+三维,胸部平扫', 'CT', '2102051010.0', '* CT鼻咽部（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0197d00f8cd1afd359c90f80cffd7187');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部),三维重建', 'CT', '2104011010.0', '* CT胸部（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '012e6a726e0eaaceb10ef37d5f6a43ea');
INSERT INTO temp_cache_import VALUES ('颈部三维重建术,头颅CT平扫,颈部CT平扫,胸部CT平扫', 'CT', '2102011010.0', '* CT颈部（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '011ac5dcc26cc7757cbb4d3a13e7acac');
INSERT INTO temp_cache_import VALUES ('颈部三维重建术,头颅CT平扫,颈部CT平扫,胸部CT平扫', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '011ac5dcc26cc7757cbb4d3a13e7acac');
INSERT INTO temp_cache_import VALUES ('颈部三维重建术,头颅CT平扫,颈部CT平扫,胸部CT平扫', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '011ac5dcc26cc7757cbb4d3a13e7acac');
INSERT INTO temp_cache_import VALUES ('前列腺彩超,头颅CT平扫', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '011258b2167e62e7acb2674100b06d57');
INSERT INTO temp_cache_import VALUES ('颅脑平扫;胸部平扫;', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '010c69ed746d48faad979897c97a05aa');
INSERT INTO temp_cache_import VALUES ('颅脑平扫;胸部平扫;', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '010c69ed746d48faad979897c97a05aa');
INSERT INTO temp_cache_import VALUES ('CT平扫(盆腔),三维重建(CT),CT平扫(腰椎),三维重建(CT)', 'CT', '2103071010.0', '* CT腰椎（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0107631cfb3556ab4fddd7a17ebcb43a');
INSERT INTO temp_cache_import VALUES ('CT平扫(盆腔),三维重建(CT),CT平扫(腰椎),三维重建(CT)', 'CT', '2106021010.0', '* CT盆腔（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0107631cfb3556ab4fddd7a17ebcb43a');
INSERT INTO temp_cache_import VALUES ('CT平扫(鼻副窦);;CT平扫(胸部);', 'CT', '2101101000.0', '* CT副鼻窦（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00faa2a17875bf2cc894a8444691e81f');
INSERT INTO temp_cache_import VALUES ('CT平扫(鼻副窦);;CT平扫(胸部);', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00faa2a17875bf2cc894a8444691e81f');
INSERT INTO temp_cache_import VALUES ('牙缺损区', 'CT', '2101161000.0', '* CT齿科（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00e616ba30dc6c5f6ae7b79cb051f586');
INSERT INTO temp_cache_import VALUES ('前列腺MRI平扫,头颅MRI平扫', 'MR', '3006054000.0', '* MR前列腺（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01dbda4cbc269442f74086181ab39bba');
INSERT INTO temp_cache_import VALUES ('前列腺MRI平扫,头颅MRI平扫', 'MR', '3001014000.0', '* MR颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '01dbda4cbc269442f74086181ab39bba');
INSERT INTO temp_cache_import VALUES ('肾上腺增强', 'CT', '2105102000.0', '* CT双肾上腺（增强）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00f379041a328ab25f824855f1a090a4');
INSERT INTO temp_cache_import VALUES ('左侧膝关节MRI平扫;右侧膝关节MRI平扫', 'MR', '3007194000.0', '* MR右侧膝关节（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00ceb2dda0f2866472568f5659d909f8');
INSERT INTO temp_cache_import VALUES ('左侧膝关节MRI平扫;右侧膝关节MRI平扫', 'MR', '3007184000.0', '* MR左侧膝关节（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00ceb2dda0f2866472568f5659d909f8');
INSERT INTO temp_cache_import VALUES ('颈椎4-7椎间盘平扫,颈椎3-7椎间盘平扫,头颅CT平扫', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00a61fd0b21541bcbe7e0f74647f3e77');
INSERT INTO temp_cache_import VALUES ('颈椎4-7椎间盘平扫,颈椎3-7椎间盘平扫,头颅CT平扫', 'CT', '2103011000.0', '* CT颈椎间盘（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00a61fd0b21541bcbe7e0f74647f3e77');
INSERT INTO temp_cache_import VALUES ('脊柱成像/胸椎MRI平扫,脊柱成像/颈椎MRI平扫', 'MR', '3003054000.0', '* MR颈椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '008b4e545f78227e703da7069c4b5d0c');
INSERT INTO temp_cache_import VALUES ('脊柱成像/胸椎MRI平扫,脊柱成像/颈椎MRI平扫', 'MR', '3003064000.0', '* MR胸椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '008b4e545f78227e703da7069c4b5d0c');
INSERT INTO temp_cache_import VALUES ('胸部平扫;CT平扫(上腹部);', 'CT', '2105011000.0', '* CT上腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '008ea6a64dcc6b3cac246e9850c77532');
INSERT INTO temp_cache_import VALUES ('CT平扫(眼眶),CT平扫(颅脑),CT平扫(胸部),三维重建(CT)(眼眶),三维重建(CT)(颅脑)', 'CT', '2101091010.0', '* CT眼眶（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00c8037b190ca900f4f413b12d058918');
INSERT INTO temp_cache_import VALUES ('胸部平扫;CT平扫(上腹部);', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '008ea6a64dcc6b3cac246e9850c77532');
INSERT INTO temp_cache_import VALUES ('头颅CT平扫,喉部CT平扫', 'CT', '2102041000.0', '* CT喉部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00a083144d82e9a55c319728a4954e5c');
INSERT INTO temp_cache_import VALUES ('头颅CT平扫,喉部CT平扫', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00a083144d82e9a55c319728a4954e5c');
INSERT INTO temp_cache_import VALUES ('CT平扫(眼眶),CT平扫(颅脑),CT平扫(胸部),三维重建(CT)(眼眶),三维重建(CT)(颅脑)', 'CT', '2101011010.0', '* CT颅脑（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00c8037b190ca900f4f413b12d058918');
INSERT INTO temp_cache_import VALUES ('CT平扫(眼眶),CT平扫(颅脑),CT平扫(胸部),三维重建(CT)(眼眶),三维重建(CT)(颅脑)', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00c8037b190ca900f4f413b12d058918');
INSERT INTO temp_cache_import VALUES ('脊柱成像/胸椎MRI增强', 'MR', '3003064100.0', '* MR胸椎（增强）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00a3dd0f1642f01dcaee636806c86cd7');
INSERT INTO temp_cache_import VALUES ('CT平扫(颈椎);;颅脑平扫(颅脑);', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '008e64b09936bf65d333231acb7dddb1');
INSERT INTO temp_cache_import VALUES ('CT平扫(颈椎);;颅脑平扫(颅脑);', 'CT', '2103051000.0', '* CT颈椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '008e64b09936bf65d333231acb7dddb1');
INSERT INTO temp_cache_import VALUES ('右肩关节CT平扫;锁骨三维重建;肋骨三维重建术', 'CT', '2104051010.0', '* CT肋骨（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '012a1158065147faa21ba5f625a92bcb');
INSERT INTO temp_cache_import VALUES ('右肩关节CT平扫;锁骨三维重建;肋骨三维重建术', 'CT', '2104041010.0', '* CT锁骨（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '012a1158065147faa21ba5f625a92bcb');
INSERT INTO temp_cache_import VALUES ('右肩关节CT平扫;锁骨三维重建;肋骨三维重建术', 'CT', '2107021000.0', '* CT右侧肩关节（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '012a1158065147faa21ba5f625a92bcb');
INSERT INTO temp_cache_import VALUES ('上腹部CT增强扫描,胸部CT增强扫描,胸部CT平扫', 'CT', '2105012000.0', '* CT上腹部（增强）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00badc53b56f0623cbb5553672adad1e');
INSERT INTO temp_cache_import VALUES ('上腹部CT增强扫描,胸部CT增强扫描,胸部CT平扫', 'CT', '2104012000.0', '* CT胸部（增强）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00badc53b56f0623cbb5553672adad1e');
INSERT INTO temp_cache_import VALUES ('上腹部CT增强扫描,胸部CT增强扫描,胸部CT平扫', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00badc53b56f0623cbb5553672adad1e');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部);CT平扫(四肢);三维重建(CT);', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00cf00bc85c2ccb61b6202d0ee4fd073');
INSERT INTO temp_cache_import VALUES ('颈部CT平扫', 'CT', '2102011000.0', '* CT颈部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00e62e9e242f54837c1ebc9674a2e59f');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部);CT平扫(四肢);三维重建(CT);', 'CT', '2107571010.0', '* CT双侧下肢（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00cf00bc85c2ccb61b6202d0ee4fd073');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部);CT平扫(四肢);三维重建(CT);', 'CT', '2107561010.0', '* CT双侧上肢（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00cf00bc85c2ccb61b6202d0ee4fd073');
INSERT INTO temp_cache_import VALUES ('颅脑平扫,头部MRA,SWI', 'MR', '3008014500.0', '* MR头部动脉血管成像（MRA）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00ebe928d2ee7ae23dc50328d63413d4');
INSERT INTO temp_cache_import VALUES ('颅脑平扫,头部MRA,SWI', 'MR', '3001015600.0', '* MR颅脑磁敏感加权成像（SWI）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00ebe928d2ee7ae23dc50328d63413d4');
INSERT INTO temp_cache_import VALUES ('颅脑平扫,头部MRA,SWI', 'MR', '3001014000.0', '* MR颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00ebe928d2ee7ae23dc50328d63413d4');
INSERT INTO temp_cache_import VALUES ('颅脑CT平扫;;胸部CT平扫;', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00887229ff68185e6911ceb9db469cff');
INSERT INTO temp_cache_import VALUES ('头颅CT平扫;上腹部CT平扫;颈椎CT平扫', 'CT', '2105011000.0', '* CT上腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0082193ab39a8dacf7961b2f11036b63');
INSERT INTO temp_cache_import VALUES ('CT平扫(鼻副窦);三维重建(CT);CT平扫(中耳);', 'CT', '2101041000.0', '* CT乳突薄层（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '006b4ad56106530a90d543e289545992');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部);颅脑CT平扫', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00770bce19f5a8c9146aa6f2678cf14a');
INSERT INTO temp_cache_import VALUES ('CT平扫(胸部);颅脑CT平扫', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00770bce19f5a8c9146aa6f2678cf14a');
INSERT INTO temp_cache_import VALUES ('下腹部CT增强,颈部CT增强扫描,胸部CT平扫', 'CT', '2105032000.0', '* CT下腹部（增强）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '007ff57bf13f1cc942cc3c79501ff149');
INSERT INTO temp_cache_import VALUES ('下腹部CT增强,颈部CT增强扫描,胸部CT平扫', 'CT', '2102012000.0', '* CT颈部（增强）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '007ff57bf13f1cc942cc3c79501ff149');
INSERT INTO temp_cache_import VALUES ('下腹部CT增强,颈部CT增强扫描,胸部CT平扫', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '007ff57bf13f1cc942cc3c79501ff149');
INSERT INTO temp_cache_import VALUES ('头颅CT平扫;上腹部CT平扫;颈椎CT平扫', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0082193ab39a8dacf7961b2f11036b63');
INSERT INTO temp_cache_import VALUES ('CT平扫(鼻副窦);三维重建(CT);CT平扫(中耳);', 'CT', '2101101010.0', '* CT副鼻窦（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '006b4ad56106530a90d543e289545992');
INSERT INTO temp_cache_import VALUES ('头颅CT平扫;上腹部CT平扫;颈椎CT平扫', 'CT', '2103051000.0', '* CT颈椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0082193ab39a8dacf7961b2f11036b63');
INSERT INTO temp_cache_import VALUES ('颅脑CT平扫;;胸部CT平扫;', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00887229ff68185e6911ceb9db469cff');
INSERT INTO temp_cache_import VALUES ('CT平扫(下腹部),CT平扫(胸部),CT平扫(上腹部),CT平扫(双肾)', 'CT', '2105031000.0', '* CT下腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '008a8ca7b79f20ff0366bf5e997a70e7');
INSERT INTO temp_cache_import VALUES ('CT平扫(下腹部),CT平扫(胸部),CT平扫(上腹部),CT平扫(双肾)', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '008a8ca7b79f20ff0366bf5e997a70e7');
INSERT INTO temp_cache_import VALUES ('CT平扫(下腹部),CT平扫(胸部),CT平扫(上腹部),CT平扫(双肾)', 'CT', '2105011000.0', '* CT上腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '008a8ca7b79f20ff0366bf5e997a70e7');
INSERT INTO temp_cache_import VALUES ('CT平扫(下腹部),CT平扫(胸部),CT平扫(上腹部),CT平扫(双肾)', 'CT', '2105041000.0', '* CT双肾（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '008a8ca7b79f20ff0366bf5e997a70e7');
INSERT INTO temp_cache_import VALUES ('盆腔MRI增强', 'MR', '3006024100.0', '* MR盆腔及盆底结构（增强）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '007da64d41757ee48fff4bdaf10a2625');
INSERT INTO temp_cache_import VALUES ('磁共振平扫（右膝）', 'MR', '3007194000.0', '* MR右侧膝关节（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0063f1a993ff81f983677ea32e9a0e1b');
INSERT INTO temp_cache_import VALUES ('肋骨三维重建术;骨盆三维重建;头颅三维重建', 'CT', '2101011010.0', '* CT颅脑（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '006a5b6a829fb494b158c6deb5ed7b79');
INSERT INTO temp_cache_import VALUES ('肋骨三维重建术;骨盆三维重建;头颅三维重建', 'CT', '2104051010.0', '* CT肋骨（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '006a5b6a829fb494b158c6deb5ed7b79');
INSERT INTO temp_cache_import VALUES ('磁共振平扫（关节）;骶髂关节', 'MR', '3003134000.0', '* MR骶髂关节（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00699a6e6ce2c0fda4a766f22ba1257b');
INSERT INTO temp_cache_import VALUES ('肋骨三维重建术;骨盆三维重建;头颅三维重建', 'CT', '2106011010.0', '* CT骨盆（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '006a5b6a829fb494b158c6deb5ed7b79');
INSERT INTO temp_cache_import VALUES ('胸腰段MRI平扫,右侧膝关节MRI平扫', 'MR', '3003104000.0', '* MR胸腰段（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '007db5e793273ffddcb4ee28a07c7a40');
INSERT INTO temp_cache_import VALUES ('胸腰段MRI平扫,右侧膝关节MRI平扫', 'MR', '3007194000.0', '* MR右侧膝关节（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '007db5e793273ffddcb4ee28a07c7a40');
INSERT INTO temp_cache_import VALUES ('心脏冠脉成像,CT平扫/每部位,CT平扫(胸部)', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0061c1145a17ea2ee9eb0f461c4893b4');
INSERT INTO temp_cache_import VALUES ('心脏冠脉成像,CT平扫/每部位,CT平扫(胸部)', 'CT', '2108152200.0', '* CT冠状动脉血管造影（CTA）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0061c1145a17ea2ee9eb0f461c4893b4');
INSERT INTO temp_cache_import VALUES ('胸部CT平扫;头颅CTA', 'CT', '2108012200.0', '* CT头部动脉血管造影（CTA）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0057920e9e9d1d39ebaa0d362730e8db');
INSERT INTO temp_cache_import VALUES ('左踝关节CT平扫;双髋关节CT平扫;下肢血管成像(静脉);踝关节三维重建术;右髋关节三维重建', 'CT', '2107221010.0', '* CT左侧踝关节（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '005bf4f526e0dad73a06575670a7c943');
INSERT INTO temp_cache_import VALUES ('右腕关节三维重建,右腕关节CT平扫,右腕关节三维重建', 'CT', '2107121010.0', '* CT右侧腕部（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0049bd1bb2749904387c9ab984231505');
INSERT INTO temp_cache_import VALUES ('全腹部平扫,上腹部增强', 'CT', '2105121000.0', '* CT全腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '004b48f2cc7c1bbc28214d448189736c');
INSERT INTO temp_cache_import VALUES ('全腹部平扫,上腹部增强', 'CT', '2105012000.0', '* CT上腹部（增强）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '004b48f2cc7c1bbc28214d448189736c');
INSERT INTO temp_cache_import VALUES ('胸部CT平扫;双髋关节CT平扫;双髋关节三维重建', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0056cd41abf76be255609c9851cd4c92');
INSERT INTO temp_cache_import VALUES ('胸部CT平扫;双髋关节CT平扫;双髋关节三维重建', 'CT', '2107261010.0', '* CT髋关节（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0056cd41abf76be255609c9851cd4c92');
INSERT INTO temp_cache_import VALUES ('胸部CT平扫;头颅CTA', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0057920e9e9d1d39ebaa0d362730e8db');
INSERT INTO temp_cache_import VALUES ('三维重建(CT);CT平扫(颈椎);', 'CT', '2103051010.0', '* CT颈椎（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '005bda5a3422f1c8c3c59dbee3894be8');
INSERT INTO temp_cache_import VALUES ('左踝关节CT平扫;双髋关节CT平扫;下肢血管成像(静脉);踝关节三维重建术;右髋关节三维重建', 'CT', '2107261010.0', '* CT髋关节（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '005bf4f526e0dad73a06575670a7c943');
INSERT INTO temp_cache_import VALUES ('左踝关节CT平扫;双髋关节CT平扫;下肢血管成像(静脉);踝关节三维重建术;右髋关节三维重建', 'CT', '2108192300.0', '* CT下肢静脉血管造影（CTV）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '005bf4f526e0dad73a06575670a7c943');
INSERT INTO temp_cache_import VALUES ('前列腺彩超,下腹部CT平扫', 'CT', '2105031000.0', '* CT下腹部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '005e14aa8f794fe085b8b5739bd5e99d');
INSERT INTO temp_cache_import VALUES ('脑功能成像(FMRI),头部灌注成像,头颅MRI增强,磁共振波谱分析(MRS)', 'MR', '3001015200.0', '* MR颅脑功能性磁共振成像（fMRI）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00540ca2a69f33a2fc1465385369a1b3');
INSERT INTO temp_cache_import VALUES ('脑功能成像(FMRI),头部灌注成像,头颅MRI增强,磁共振波谱分析(MRS)', 'MR', '3001015500.0', '* MR颅脑磁共振灌注成像（PWI）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00540ca2a69f33a2fc1465385369a1b3');
INSERT INTO temp_cache_import VALUES ('脑功能成像(FMRI),头部灌注成像,头颅MRI增强,磁共振波谱分析(MRS)', 'MR', '3001014100.0', '* MR颅脑（增强）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00540ca2a69f33a2fc1465385369a1b3');
INSERT INTO temp_cache_import VALUES ('脑功能成像(FMRI),头部灌注成像,头颅MRI增强,磁共振波谱分析(MRS)', 'MR', '3001015700.0', '* MR颅脑磁共振波谱成像（MRS）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00540ca2a69f33a2fc1465385369a1b3');
INSERT INTO temp_cache_import VALUES ('MRI成套1.5T(含)以上,常规执行:腰椎(平扫)', 'MR', '3003074000.0', '* MR腰椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00553234bbe4fa432af4f5a2693c3ae5');
INSERT INTO temp_cache_import VALUES ('CT平扫(眼眶),三维重建(CT)(眼眶),CT平扫(颅脑)', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '002bd47630361ee3e7b3d6379b603851');
INSERT INTO temp_cache_import VALUES ('CT平扫(颅脑),;CT平扫(胸部),', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00465545ef4778359303555abeb8b3ab');
INSERT INTO temp_cache_import VALUES ('双肾CT平扫', 'CT', '2105041000.0', '* CT双肾（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '002e263c2339476b94dbfe36a41043ab');
INSERT INTO temp_cache_import VALUES ('CT平扫（双肾）', 'CT', '2105041000.0', '* CT双肾（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '002c4d9aea8f9eed4a82f70af3cf7746');
INSERT INTO temp_cache_import VALUES ('左膝关节平扫,右肩关节平扫,磁共振平扫（胸椎）,磁共振平扫（腰椎）', 'MR', '3003074000.0', '* MR腰椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '002de8e855f7df706e5cd6ff1d58a120');
INSERT INTO temp_cache_import VALUES ('CT平扫(眼眶),三维重建(CT)(眼眶),CT平扫(颅脑)', 'CT', '2101091010.0', '* CT眼眶（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '002bd47630361ee3e7b3d6379b603851');
INSERT INTO temp_cache_import VALUES ('头颅CT平扫;左肩关节CT平扫', 'CT', '2107011000.0', '* CT左侧肩关节（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0026b8120c512cd3730f6fde855549fe');
INSERT INTO temp_cache_import VALUES ('头颅CT平扫;左肩关节CT平扫', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0026b8120c512cd3730f6fde855549fe');
INSERT INTO temp_cache_import VALUES ('上腹部CT增强扫描,右肘关节三维重建,右肘关节CT平扫', 'CT', '2105012000.0', '* CT上腹部（增强）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0046a08d9251745680a4a1a26ee2509e');
INSERT INTO temp_cache_import VALUES ('CT平扫(颅脑),;CT平扫(胸部),', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00465545ef4778359303555abeb8b3ab');
INSERT INTO temp_cache_import VALUES ('头部灌注成像,头颅MRI平扫,颈部血管成像,头部灌注成像,颈部血管成像', 'MR', '3001014000.0', '* MR颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00495270bd587ab18745446647253b47');
INSERT INTO temp_cache_import VALUES ('上腹部CT增强扫描,右肘关节三维重建,右肘关节CT平扫', 'CT', '2107061010.0', '* CT右侧肘关节（平扫+三维重建）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0046a08d9251745680a4a1a26ee2509e');
INSERT INTO temp_cache_import VALUES ('左膝关节平扫,右肩关节平扫,磁共振平扫（胸椎）,磁共振平扫（腰椎）', 'MR', '3007184000.0', '* MR左侧膝关节（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '002de8e855f7df706e5cd6ff1d58a120');
INSERT INTO temp_cache_import VALUES ('左膝关节平扫,右肩关节平扫,磁共振平扫（胸椎）,磁共振平扫（腰椎）', 'MR', '3007024000.0', '* MR右侧肩关节（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '002de8e855f7df706e5cd6ff1d58a120');
INSERT INTO temp_cache_import VALUES ('左膝关节平扫,右肩关节平扫,磁共振平扫（胸椎）,磁共振平扫（腰椎）', 'MR', '3003064000.0', '* MR胸椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '002de8e855f7df706e5cd6ff1d58a120');
INSERT INTO temp_cache_import VALUES ('头部灌注成像,头颅MRI平扫,颈部血管成像,头部灌注成像,颈部血管成像', 'MR', '3001015500.0', '* MR颅脑磁共振灌注成像（PWI）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00495270bd587ab18745446647253b47');
INSERT INTO temp_cache_import VALUES ('头部灌注成像,头颅MRI平扫,颈部血管成像,头部灌注成像,颈部血管成像', 'MR', '3008034500.0', '* MR颈部动脉血管成像（MRA）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '00495270bd587ab18745446647253b47');
INSERT INTO temp_cache_import VALUES ('颈椎;腰椎', 'MR', '3003074000.0', '* MR腰椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '002606ed7ce25e22ea1bab76b10bf99a');
INSERT INTO temp_cache_import VALUES ('颈椎;腰椎', 'MR', '3003054000.0', '* MR颈椎（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '002606ed7ce25e22ea1bab76b10bf99a');
INSERT INTO temp_cache_import VALUES ('头颅MRI平扫,颈部血管成像', 'MR', '3008034500.0', '* MR颈部动脉血管成像（MRA）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '001aa0638ee46d66c6a7a1875cc4930f');
INSERT INTO temp_cache_import VALUES ('头颅MRI平扫,颈部血管成像', 'MR', '3001014000.0', '* MR颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '001aa0638ee46d66c6a7a1875cc4930f');
INSERT INTO temp_cache_import VALUES ('上腹部CT平扫,胸部CT平扫,头颅CT平扫,颈部（软组织）平扫', 'CT', '40010102030000.0', '* DR头颅轴位', 'V3.8.2', 1.0, 'import_production', 'exact', 4, '00125e7a1e0cf96c9dc02c306d2281e3');
INSERT INTO temp_cache_import VALUES ('* DR头颅切线位', 'DR', '40010102370000.0', '* DR头颅正、侧位', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '0d4a1a2de7ee40058298def47bb1f448');
INSERT INTO temp_cache_import VALUES ('CT平扫(颅脑);胸', 'CT', '2104011000.0', '* CT胸部（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '');
INSERT INTO temp_cache_import VALUES ('CT平扫(颅脑);胸', 'CT', '2101011000.0', '* CT颅脑（平扫）', 'V3.8.2', 1.0, 'import_production', 'exact', 1, '');

-- 合并到主表（去重）

INSERT INTO acr_standard_link (
    raw_check_item,
    modality,
    standard_code,
    standard_name,
    version,
    confidence,
    source,
    tier,
    created_at,
    updated_at
)
SELECT DISTINCT
    raw_check_item,
    modality,
    standard_code,
    standard_name,
    version,
    confidence,
    source,
    tier,
    NOW(),
    NOW()
FROM temp_cache_import
ON CONFLICT (raw_check_item, modality, version, standard_code)
DO UPDATE SET
    confidence = EXCLUDED.confidence,
    source = EXCLUDED.source,
    updated_at = NOW();


-- 清理临时表
DROP TABLE temp_cache_import;

-- 验证导入
SELECT 
    source,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence
FROM acr_standard_link
WHERE source = 'import_production'
GROUP BY source;
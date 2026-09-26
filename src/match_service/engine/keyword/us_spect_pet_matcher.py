"""
US / SPECT / PET / OCT / DSA 模态匹配引擎。

这些模态不走 examine-standard 的 NLP pipeline（该系统仅覆盖 CT/MR/DR），
而是采用关键词规则匹配 → 直接查 standard_check_items 表的策略。

匹配策略概述：
- US：从医嘱文本提取部位关键词 + 扫描方式 → 匹配 body_part_l2 + scan_method
- SPECT：提取器官 + 显像方式关键词 → 匹配 body_part_l2 + scan_method
- PET：判断 PET/CT vs PET/MR + 全身/局部(部位) → 匹配 body_part_l2
- OCT：提取部位关键词（眼科：视盘/黄斑区/视网膜/眼前节；心血管：冠状动脉/心脏）→ 匹配 body_part_l2
- DSA：排除介入治疗操作，提取部位关键词 → 匹配 body_part_l2（仅诊断造影）
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import text
from ..catalog_policy import CATALOG_POLICY_SQL

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 关键词规则常量（US/SPECT/PET/OCT/DSA）
#
# ⚠️ 单一真相说明（F-D）：运行期匹配以 keyword_match_rules 表为唯一来源
# （见 USSpectPetMatcher._load_rules_from_db）。以下硬编码常量**仅供**
# scripts/seed_keyword_match_rules.py 播种空库，不再作运行期兜底。
# 维护规则请改 DB（词库治理台 / lexicon_api），改这里不影响运行匹配。
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# US 超声匹配规则
# ═══════════════════════════════════════════════════════════════════════════════

# 医嘱关键词 → standard_check_items.body_part_l2 的映射
# 顺序敏感：长词优先匹配，避免"甲状腺"匹配到"甲状旁腺"的情况
US_BODY_KEYWORDS: List[Tuple[List[str], str]] = [
    # ── 通用部位词（新增 - 用于标准化后的 ACR 名称）──
    (['泌尿生殖系统'], '双肾、输尿管、膀胱'),
    (['泌尿系统', '泌尿系'], '双肾、输尿管、膀胱'),

    # ── 浅表小器官 ──
    (['甲状腺及颈部淋巴结', '甲状腺专科', '甲状腺动脉', '甲状腺.*淋巴结'], '甲状腺+颈部淋巴结'),
    (['甲状旁腺'], '甲状旁腺'),
    (['甲状腺'], '甲状腺'),
    (['乳腺.*腋窝', '腋窝.*乳腺', '乳腺专科', '乳腺癌术后'], '乳腺+腋窝淋巴结'),
    (['乳腺', '乳房'], '乳腺'),
    (['腋窝淋巴结', '腋窝'], '腋窝淋巴结'),
    (['颈部淋巴结'], '颈部淋巴结'),
    (['锁骨.*淋巴结', '锁骨下淋巴结'], '锁骨下淋巴结'),
    (['腹股沟淋巴结', '腹股沟'], '腹股沟淋巴结'),
    (['肠系膜淋巴结'], '肠系膜淋巴结'),
    (['淋巴结'], '颈部淋巴结'),
    (['眼球后血管', '眼眶'], '眼眶'),
    (['眼部', '眼球', '双眼'], '眼球'),
    (['阴囊', '睾丸.*附睾'], '阴囊'),
    (['睾丸'], '睾丸'),
    (['附睾'], '附睾'),
    (['精索静脉'], '精索静脉'),
    (['精索'], '精索'),
    (['阴茎'], '阴茎'),
    (['胸壁'], '胸壁'),
    (['腹壁'], '腹壁'),
    (['纵膈', '纵隔'], '纵膈'),
    (['腮腺.*颌下腺', '颌下腺.*腮腺', '涎腺', '唾液腺', '干燥综合征'], '腮腺'),
    (['腮腺'], '腮腺'),
    (['颌下腺'], '颌下腺'),
    (['舌下腺'], '舌下腺'),
    (['颈部'], '颈部'),
    (['男性生殖'], '男性生殖器'),
    # ── 心血管 ──
    (['小儿.*心脏', '儿童.*心脏', '新生儿.*心脏'], '儿童心脏'),
    (['心脏'], '成人心脏'),  # 通用词：心脏 → 成人心脏
    (['超声心动图', '心脏彩', '心脏超声', '心包', '超声心动', '心彩超',
      '右心超声', '左心超声', '心动图'], '成人心脏'),
    # ── 颈部血管 ──
    (['颈脑动脉一体化', '颈动脉.*椎动脉.*锁骨下'], '双侧颈动脉'),
    (['颈动脉.*颈静脉', '颈动静脉'], '双侧颈动脉'),
    (['椎动脉'], '双侧椎动脉'),
    (['锁骨下动脉'], '双侧锁骨下动脉'),
    (['颈总.*颈内外', '颈动脉'], '双侧颈动脉'),
    (['颈静脉'], '双侧颈静脉'),
    # ── 外周血管 ──
    (['四肢动.*静脉', '四肢动静脉'], '双下肢动脉'),
    (['四肢动脉'], '双下肢动脉'),
    (['四肢静脉'], '双下肢静脉'),
    (['双侧上肢动静脉', '上肢动静脉'], '双上肢动脉'),
    (['单侧上肢动脉.*右', '右.*上肢动脉'], '右上肢动脉'),
    (['单侧上肢动脉.*左', '左.*上肢动脉'], '左上肢动脉'),
    (['上肢'], '双上肢动脉'),  # 通用词
    (['上肢动脉'], '双上肢动脉'),
    (['单侧上肢静脉.*右', '右.*上肢静脉'], '右上肢静脉'),
    (['单侧上肢静脉.*左', '左.*上肢静脉'], '左上肢静脉'),
    (['上肢静脉'], '双上肢静脉'),
    (['双侧下肢动静脉', '下肢动静脉'], '双下肢动脉'),
    (['单侧下肢动脉.*右', '右.*下肢动脉'], '右下肢动脉'),
    (['单侧下肢动脉.*左', '左.*下肢动脉'], '左下肢动脉'),
    (['下肢'], '双下肢动脉'),  # 通用词
    (['下肢动脉粥样硬化', '下肢动脉'], '双下肢动脉'),
    (['单侧下肢静脉.*右', '右.*下肢静脉'], '右下肢静脉'),
    (['单侧下肢静脉.*左', '左.*下肢静脉'], '左下肢静脉'),
    (['下肢静脉曲张', '下肢静脉'], '双下肢静脉'),
    (['足背动脉'], '双足背动脉'),
    (['下腔静脉.*髂', '髂静脉受压', '髂静脉'], '下腔静脉'),
    (['下腔静脉'], '下腔静脉'),
    (['门静脉'], '肝胆脾胰'),
    (['髂动脉.*腹主动脉', '腹主动脉.*髂动脉'], '腹主动脉'),
    (['髂动脉'], '髂动脉'),
    (['腹主动脉瘤', '腹主动脉'], '腹主动脉'),
    (['腹腔干.*肠系膜动脉', '腹腔动脉', '肠系膜动脉'], '腹主动脉'),
    (['肾动脉'], '肾动脉'),
    # ── 腹部大血管 ──
    (['腹部.*血管'], '腹部大血管'),
    # ── 颅脑 ──
    (['新生儿.*颅脑', '新生儿.*头颅'], '新生儿颅脑'),
    (['小儿.*颅脑', '小儿.*头颅'], '小儿颅脑'),
    (['头颅', '颅脑', '头部'], '新生儿颅脑'),  # 通用词（默认新生儿，因为成人不做超声）
    (['经颅多普勒', 'TCD', '脑动脉', '脑血流'], '颅脑'),
    # ── 产科 ──
    (['产科', '胎儿', '宫腔'], '胎儿'),
    # ── 妇科 ──
    (['子宫.*附件.*卵巢', '妇科彩超', '妇科.*经腹', '妇科.*经阴', '妇科.*经直肠',
      '子宫及附件', '子宫、卵巢'], '子宫、卵巢、输卵管'),
    (['盆底', '盆腔淤血', '盆腔'], '盆腔'),
    (['卵巢'], '卵巢'),
    (['输卵管'], '输卵管'),
    (['子宫', '宫颈'], '子宫'),
    (['外阴', '阴道', '两性畸形'], '外阴部'),
    # ── 泌尿系统 ──
    (['双肾.*输尿管.*膀胱', '泌尿系彩超', '泌尿系统'], '双肾、输尿管、膀胱'),
    (['肾.*肾上腺', '双肾及肾上腺'], '肾脏'),
    (['肾上腺'], '肾上腺'),
    (['移植肾', '肾脏', '双肾', '肾穿刺', '肾囊肿', '肾周脓肿', '肾活检'], '肾脏'),
    (['膀胱.*残余尿', '膀胱容量', '膀胱'], '膀胱'),
    (['输尿管'], '输尿管'),
    (['前列腺.*精囊腺', '前列腺.*融合', '前列腺'], '前列腺'),
    # ── 消化系统 ──
    (['肝胆脾胰', '腹部普通彩超', '腹部.*泌尿系统.*普通'], '肝胆脾胰'),
    (['腹部', '上腹部', '腹盆'], '肝胆脾胰'),  # 通用词：腹部 → 肝胆脾胰
    (['TIPS', '肝移植', '布加综合征', '慢性肝病', '肝脏', '肝囊肿', '肝脓肿', '肝穿刺'], '肝脏'),
    (['胆囊胆道', '胆囊.*胆道'], '胆囊胆道'),
    (['胆囊', '胆道'], '胆囊'),
    (['胰腺'], '胰腺'),
    (['脾脏'], '脾脏'),
    (['胃.*十二指肠', '十二指肠'], '胃'),
    (['胃肠道', '肠道疾病'], '胃肠道'),
    (['大肠.*造影', '结肠'], '大肠'),
    (['小肠.*造影', '小肠'], '小肠'),
    (['阑尾', '右下腹', '先天性幽门'], '右下腹'),
    (['肠套叠', '肠'], '胃肠道'),
    (['腹腔普通', '腹腔'], '腹腔'),
    (['腹膜后'], '腹膜后'),
    # ── 肌肉骨骼 ──
    (['小儿髋关节', '髋关节发育'], '小儿髋关节'),
    (['髋关节'], '髋关节'),
    (['肩关节'], '肩关节'),
    (['肘关节'], '肘关节'),
    (['腕关节'], '腕关节'),
    (['膝关节'], '膝关节'),
    (['踝关节'], '踝关节'),
    (['手关节', '掌指', '指间'], '掌指关节'),
    (['足关节', '趾间'], '趾间关节'),
    (['关节'], '膝关节'),
    (['胸锁乳突肌', '肌性斜颈'], '胸锁乳突肌'),
    (['臂丛神经'], '臂丛神经'),
    (['正中神经'], '正中神经'),
    (['尺神经'], '尺神经'),
    (['桡神经'], '桡神经'),
    (['坐骨神经'], '坐骨神经'),
    (['股神经'], '股神经'),
    (['胫神经'], '胫神经'),
    (['腓总神经', '腓神经'], '腓总神经'),
    (['周围神经', '神经病变'], '外周神经'),
    (['肌腱'], '肌腱'),
    (['肌肉', '软组织'], '肌肉'),
    (['皮下组织', '皮下'], '皮下组织'),
    (['皮肤', '黑色素瘤', '瘢痕', '硬皮病', '皮肤多模态'], '皮肤'),
    (['浅表'], '皮下组织'),
    (['腘窝'], '腘窝'),
    # ── 补充匹配 ──
    (['肺部', '肺超声', '胸腔', '胸膜'], '胸壁'),
    (['颞浅动脉'], '双侧颈动脉'),
    (['大动脉炎'], '腹主动脉'),
    (['汗腺'], '皮肤'),
    (['肛门', '肛管', '会阴'], '外阴部'),
    (['血管瘤'], '皮下组织'),
    (['视神经'], '眼球'),
    (['局部血管', '血管彩超'], '腹部大血管'),
    (['脏器.*造影'], '肝胆脾胰'),
    (['弹性成像', '彩超弹性'], '肝脏'),
    # ── 通用部位词（新增，用于常见描述）──
    (['胸部', '胸腔'], '胸壁'),
    (['肢体'], '膝关节'),  # 默认膝关节（最常见）
    (['颈椎'], '颈部'),
    (['颌面部'], '腮腺'),
]

# 扫描方式关键词 → scan_method
US_SCAN_KEYWORDS: List[Tuple[List[str], str]] = [
    (['声学造影', '超声造影', '造影超声', '造影综合评估'], '造影'),
    (['介入', '穿刺', '活检', '引流', '引导下', '消融引导'], '介入'),
    (['消融'], '消融'),
    (['弹性成像', '弹性'], '弹性'),
    (['三维体积', '三维'], '三维'),
    (['四维'], '四维'),
    (['床旁', '术中'], '床旁'),
]

# US 特殊用途标识 — 不匹配标准项
US_UNMATCHABLE = (
    '临床操作', 'GCP专用', '科研', '院际会诊',
    '支气管镜', '超声内镜', '内镜检查', '人工智能',
    '请备注部位', '其他脏器',
)


# ═══════════════════════════════════════════════════════════════════════════════
# SPECT 核医学匹配规则
# ═══════════════════════════════════════════════════════════════════════════════

# 医嘱关键词 → body_part_l2
SPECT_BODY_KEYWORDS: List[Tuple[List[str], str]] = [
    # ── 全身 ──
    (['全身骨显像', '全身骨'], '骨'),  # 新增：全身骨
    (['局部骨显像', '局部骨'], '骨'),  # 新增：局部骨
    (['骨关节平面', '关节显像'], '骨关节平面'),
    (['骨髓'], '骨髓'),
    (['三时相骨', '三相骨', '骨三时相'], '骨'),
    (['骨血流'], '骨'),
    (['骨血池'], '骨'),
    (['骨显像', '骨扫描', '骨SPECT'], '骨'),
    (['淋巴显像', '淋巴'], '淋巴'),  # 新增
    (['亲肿瘤', '肿瘤显像'], '全身'),
    # ── 头部 ──
    (['脑脊液'], '脑脊液系统'),
    (['脑池'], '脑池脏器'),
    (['唾液腺', '腮腺显像'], '唾液腺'),
    (['脑血流灌注', '脑灌注', '脑血流'], '脑'),
    (['脑代谢', '脑受体', '脑显像'], '脑'),
    # ── 颈部 ──
    (['甲状旁腺'], '甲状旁腺'),
    (['甲状腺'], '甲状腺'),
    # ── 腹部 ──
    (['肾上腺皮质'], '肾上腺皮质'),
    (['肾上腺髓质'], '肾上腺髓质'),
    (['肾动态', '肾血浆流量', '肾小球滤过'], '肾'),
    (['肾静态', '肾显像'], '肾'),
    (['肝血流', '肝血池'], '肝血流'),
    (['肝胆动态', '肝胆显像'], '肝胆'),  # 修正：标准表是肝胆而非肝脏
    (['肝脏'], '肝脏'),
    (['脾脏', '脾显像'], '脾脏'),
    (['胃黏膜', '异位胃'], '胃黏膜'),
    (['消化道出血', '消化道'], '消化道'),
    # ── 盆腔 ──
    (['阴囊'], '阴囊'),
    # ── 胸部 ──
    (['肺灌注', '肺血流'], '肺'),
    (['肺通气', '肺吸入'], '肺'),
    (['心肌灌注显像', '心肌灌注', '心肌血流'], '心肌'),  # 新增：心肌灌注
    (['负荷心肌', '静息心肌'], '心肌'),  # 新增
    (['心肌显像', '心肌梗死'], '心肌'),
    (['心脏显像', '心脏', '心室', '心功能'], '心脏'),
    # ── 血管 ──
    (['首次通过', '心血池'], '血管'),
    (['大动脉', '动脉显像'], '血管'),
    (['静脉显像'], '血管'),
    (['放射性核素.*白细胞'], '全身'),  # 白细胞显像 → 全身
    # ── 其他 ──
    (['肾'], '肾'),
]

# 显像方式关键词 → scan_method
SPECT_SCAN_KEYWORDS: List[Tuple[List[str], str]] = [
    (['三时相'], '三时相骨显像'),
    (['负荷.*灌注断层', '负荷.*断层'], '灌注断层显像'),  # 新增：负荷+断层
    (['静息.*灌注断层', '静息.*断层'], '灌注断层显像'),  # 新增：静息+断层
    (['灌注断层'], '灌注断层显像'),
    (['负荷.*灌注平面', '负荷.*平面'], '灌注平面显像'),  # 新增：负荷+平面
    (['静息.*灌注平面', '静息.*平面'], '灌注平面显像'),  # 新增：静息+平面
    (['灌注平面'], '灌注平面显像'),
    (['灌注'], '灌注显像'),
    (['动态'], '动态显像'),
    (['静态断层'], '静态断层显像'),
    (['静态平面'], '静态平面显像'),
    (['静态'], '静态显像'),
    (['断层'], '断层显像'),
    (['平面'], '平面显像'),
    (['血流'], '血流显像'),
    (['血池'], '血池显像'),
    (['早期出血', '早期'], '早期扫描'),
    (['延迟出血', '延迟'], '延迟扫描'),
    (['排空'], '排空功能测定'),
    (['亲肿瘤'], '亲肿瘤显像'),
]

# ═══════════════════════════════════════════════════════════════════════════════
# PET 匹配规则
# ═══════════════════════════════════════════════════════════════════════════════

# PET 标准表只有 body_part_l2 和统一的 scan_method="PET常规扫描"
# 关键词 → body_part_l2
PET_BODY_KEYWORDS: List[Tuple[List[str], str]] = [
    (['躯干.*头部.*四肢', '全身.*四肢.*头'], '躯干+头部+四肢'),
    (['躯干.*四肢', '全身.*四肢'], '躯干+四肢'),
    (['躯干.*头部', '躯干+头部', '全身.*头'], '躯干+头部'),
    (['躯干', '全身'], '躯干'),
    (['局部（头部）', '局部.*头部'], '局部（头部）'),
    (['局部（颈部）', '局部.*颈部'], '局部（颈部）'),
    (['局部（胸部）', '局部.*胸部'], '局部（胸部）'),
    (['局部（腹部）', '局部.*腹部'], '局部（腹部）'),
    (['局部（盆腔）', '局部.*盆腔'], '局部（盆腔）'),
    (['局部（心脏）', '局部.*心脏'], '局部（心脏）'),
    (['局部（四肢）', '局部.*四肢'], '局部（四肢）'),
    (['头部', '头颅', '颅脑', '脑'], '局部（头部）'),
    (['颈部', '颈'], '局部（颈部）'),
    (['胸部', '肺', '胸'], '局部（胸部）'),
    (['腹部', '肝', '腹'], '局部（腹部）'),
    (['盆腔', '盆'], '局部（盆腔）'),
    (['心脏', '心'], '局部（心脏）'),
    (['四肢', '肢体'], '局部（四肢）'),
    (['局部'], '局部'),
]


# ═══════════════════════════════════════════════════════════════════════════════
# OCT 匹配规则
# ═══════════════════════════════════════════════════════════════════════════════

# OCT 部位关键词 → body_part_l2（眼科：视盘/黄斑区/视网膜/眼前节；心血管：冠状动脉/心脏）
OCT_BODY_KEYWORDS: List[Tuple[List[str], str]] = [
    # 眼科部位（按特异性排序）
    (['视盘及黄斑区', '视盘.*黄斑', '黄斑.*视盘'], '视盘'),  # 多部位取第一个
    (['AS-OCT', '眼前节'], '眼前节'),
    (['EDI-OCT', '视盘'], '视盘'),
    (['黄斑区', '黄斑'], '黄斑区'),
    (['视网膜'], '视网膜'),
    (['视盘'], '视盘'),
    # 心血管部位
    (['冠状动脉', '冠脉', '腔内成像'], '冠状动脉'),
    (['主干及分叉', '主干', '分叉病变', 'OFR', 'FFR', 'QFR'], '冠状动脉'),  # 冠脉病变/血流计算 → 冠状动脉
    (['心脏'], '心脏'),
]


# ═══════════════════════════════════════════════════════════════════════════════
# DSA 匹配规则
# ═══════════════════════════════════════════════════════════════════════════════

# DSA 介入治疗排除标记（这些是治疗操作，不匹配诊断造影标准项）
DSA_UNMATCHABLE = (
    '栓塞', '取栓', '支架', '球囊', '溶栓', '扩张', '置入', '成形',
    '化疗', '植入', '分流', '血运重建', '导管溶栓', '导管增径', '介入治疗',
)

# DSA 部位关键词 → body_part_l2（按特异性排序，长词在前避免误匹配）
DSA_BODY_KEYWORDS: List[Tuple[List[str], str]] = [
    # 头颈部
    (['全脑'], '全脑'),
    (['头颈部'], '头颈部'),
    (['颈动脉'], '颈动脉'),
    (['椎动脉'], '椎动脉'),
    (['脑血管', '脑'], '脑'),
    # 胸部
    (['冠状动脉', '冠脉'], '冠状动脉'),
    (['胸主动脉'], '胸主动脉'),
    (['肺动脉'], '肺动脉'),
    (['支气管动脉'], '支气管动脉'),
    (['胸腹主动脉'], '胸腹主动脉'),
    # 腹部
    (['腹主动脉'], '腹主动脉'),
    (['肝动脉'], '肝动脉'),
    (['肾动脉'], '肾动脉'),
    (['肠系膜动脉'], '肠系膜动脉'),
    (['腹腔动脉'], '腹腔动脉'),
    (['门静脉'], '门静脉'),
    # 盆腔
    (['盆腔动脉'], '盆腔动脉'),
    (['髂动脉'], '髂动脉'),
    (['盆腔静脉'], '盆腔静脉'),
    (['子宫动脉'], '子宫动脉'),
    # 四肢
    (['上肢动脉'], '上肢动脉'),
    (['上肢静脉'], '上肢静脉'),
    (['下肢动脉'], '下肢动脉'),
    (['下肢静脉'], '下肢静脉'),
    # 全身/其他
    (['主动脉'], '主动脉'),
    (['脊髓'], '脊髓'),
    (['内脏'], '内脏'),
    (['全身'], '全身'),
]


# ═══════════════════════════════════════════════════════════════════════════════
# 匹配引擎
# ═══════════════════════════════════════════════════════════════════════════════

class USSpectPetMatcher:
    """
    US/SPECT/PET/OCT/DSA 匹配引擎。
    从 standard_check_items 表加载标准项到内存，按规则匹配。

    规则以 keyword_match_rules 表为单一真相（见 _load_rules_from_db）。

    DB engine 注入式（P3-1 原位解耦）：构造时传入 AsyncEngine，引擎不再硬依赖
    app.config.database，可被 backend / 独立 match-service 任意入口复用。
    """

    # 扫描方式兼容族：同一技术不同措辞，仅在精确扫描方式查空时按族内顺序回退。
    #
    # '常规' 是 _extract_us_scan 在**没有任何方式关键词命中**时的默认值，
    # 因此它同时代表“标准就是常规”与“输入未指明方式”两种含义。
    # 当 (部位, 常规) 查不到时，回退到多普勒族，以便捕获
    # 「US深静脉多普勒超声检查」→「US深静脉超声检查(scan=多普勒超声)」这类
    # 标准库措辞与医嘱不一致的情况。
    SCAN_FAMILY = {
        '常规': ('常规', '多普勒超声', '彩色多普勒', '频谱多普勒'),
        '彩色多普勒': ('彩色多普勒', '多普勒超声', '频谱多普勒', '常规'),
        '多普勒超声': ('多普勒超声', '彩色多普勒', '频谱多普勒', '常规'),
        '频谱多普勒': ('频谱多普勒', '多普勒超声', '彩色多普勒', '常规'),
    }


    def __init__(self, engine=None):
        # engine 可注入；为空时懒回退到 backend 的 app.config.database.engine，
        # 保持现有进程内调用零改动
        self._engine = engine
        self._initialized = False
        self._us_items: pd.DataFrame = pd.DataFrame()
        self._spect_items: pd.DataFrame = pd.DataFrame()
        self._pet_ct_items: pd.DataFrame = pd.DataFrame()
        self._pet_mr_items: pd.DataFrame = pd.DataFrame()
        self._oct_items: pd.DataFrame = pd.DataFrame()
        self._dsa_items: pd.DataFrame = pd.DataFrame()
        # 规则词表（单一真相：initialize() 时从 keyword_match_rules 加载填充；
        # 硬编码常量仅供 seed 脚本播种，不再作运行期兜底，故此处初始化为空）
        self._us_body_keywords: List[Tuple[List[str], str]] = []
        self._us_scan_keywords: List[Tuple[List[str], str]] = []
        self._us_unmatchable: Tuple[str, ...] = tuple()
        self._spect_body_keywords: List[Tuple[List[str], str]] = []
        self._spect_scan_keywords: List[Tuple[List[str], str]] = []
        self._spect_unmatchable: Tuple[str, ...] = tuple()  # H1: SPECT 排除词
        self._pet_body_keywords: List[Tuple[List[str], str]] = []
        self._pet_unmatchable: Tuple[str, ...] = tuple()    # H1: PET 排除词
        self._oct_body_keywords: List[Tuple[List[str], str]] = []
        self._oct_unmatchable: Tuple[str, ...] = tuple()    # H1: OCT 排除词
        self._dsa_body_keywords: List[Tuple[List[str], str]] = []
        self._dsa_unmatchable: Tuple[str, ...] = tuple()
        # 最近一次匹配的结构化诊断，供 orchestrator 包装统一结果。
        # 保留 match() 的 List[Tuple] 返回值，兼容旧调用方。
        self._last_tier: str = 'exact'
        self._last_reason: str = ''
        self._last_has_entity: Optional[bool] = False
        self._last_unresolved_components: List[str] = []
        self._standard_versions: dict = {}

    async def initialize(self):
        # Phase A: 独立化后 engine 必须外部注入
        if self._engine is None:
            raise ValueError(
                "engine 参数必须提供（Phase A 独立化后无 app.config.database 依赖）"
            )
        async with self._engine.connect() as conn:
            # A fixed catalog per modality restores US/nuclear catalogs without
            # mixing historical versions into the same candidate set.
            result = await conn.execute(text(
                "SELECT item_code, item_name, modality, body_part_l1, body_part_l2, "
                "body_part_l3, scan_method, version "
                "FROM standard_check_items "
                "WHERE modality IN ('US', 'SPECT', 'PET/CT', 'PET/MR', 'OCT', 'DSA') "
                "  AND is_active = true "
                "  AND " + CATALOG_POLICY_SQL + " "
                "ORDER BY modality, item_code"
            ))
            rows = result.fetchall()
            df = pd.DataFrame(rows, columns=[
                'item_code', 'item_name', 'modality', 'body_part_l1',
                'body_part_l2', 'body_part_l3', 'scan_method', 'version'
            ])
            df.fillna('', inplace=True)
            self._standard_versions = {}
            for _, standard in df.iterrows():
                key = (str(standard['item_code']), str(standard['item_name']), standard['modality'])
                self._standard_versions.setdefault(key, set()).add(standard['version'])

            self._us_items = pd.DataFrame(df[df['modality'] == 'US'].values, columns=df.columns)
            self._spect_items = pd.DataFrame(df[df['modality'] == 'SPECT'].values, columns=df.columns)
            self._pet_ct_items = pd.DataFrame(df[df['modality'] == 'PET/CT'].values, columns=df.columns)
            self._pet_mr_items = pd.DataFrame(df[df['modality'] == 'PET/MR'].values, columns=df.columns)
            self._oct_items = pd.DataFrame(df[df['modality'] == 'OCT'].values, columns=df.columns)
            self._dsa_items = pd.DataFrame(df[df['modality'] == 'DSA'].values, columns=df.columns)

            logger.info(
                f"[USSpectPetMatcher] 初始化完成: US={len(self._us_items)}, "
                f"SPECT={len(self._spect_items)}, PET/CT={len(self._pet_ct_items)}, "
                f"PET/MR={len(self._pet_mr_items)}, OCT={len(self._oct_items)}, "
                f"DSA={len(self._dsa_items)}"
            )

            await self._load_rules_from_db(conn)

        self._initialized = True

    async def _load_rules_from_db(self, conn):
        """从 keyword_match_rules 表加载规则词表（单一真相，F-D）。

        运行期以 DB 为唯一来源：DB 有该组则用该组；DB 缺某组视为**配置错误**，
        logger.error 告警并置该组为空（不再静默回退硬编码覆盖）。

        硬编码常量仅供 scripts/seed_keyword_match_rules.py 播种空库，不再作运行兜底。
        DB 完全不可用（表缺失/连接失败）是环境级故障，抛出让上层感知，
        而非静默降级为"看似正常但规则全空"。
        """
        result = await conn.execute(text(
            "SELECT modality, rule_type, keywords, dst_value "
            "FROM keyword_match_rules "
            "WHERE enable = 0 "
            "ORDER BY modality, rule_type, priority"
        ))
        rows = result.fetchall()

        keyword_tables: Dict[Tuple[str, str], List[Tuple[List[str], str]]] = {}
        unmatchable: Dict[str, List[str]] = {}
        for modality, rule_type, keywords, dst_value in rows:
            if rule_type == 'unmatchable':
                unmatchable.setdefault(modality, []).append(keywords)
            else:
                keyword_tables.setdefault((modality, rule_type), []).append(
                    (keywords.split(';'), dst_value or '')
                )

        # 期望的规则组：缺组即告警（提示需运行 seed_keyword_match_rules.py）
        def _group(mod: str, rtype: str):
            key = (mod, rtype)
            grp = keyword_tables.get(key)
            if not grp:
                logger.error(
                    f"[USSpectPetMatcher] keyword_match_rules 缺 {mod}/{rtype} 规则组，"
                    f"该组匹配将全部落空。请运行 scripts/seed_keyword_match_rules.py 播种。"
                )
                # 优雅降级：返回空列表而非崩溃，避免生产环境因配置问题导致服务不可用
                return []
            return grp

        def _unmatch(mod: str):
            grp = unmatchable.get(mod)
            if not grp:
                logger.error(
                    f"[USSpectPetMatcher] keyword_match_rules 缺 {mod}/unmatchable 规则组。"
                )
                return tuple()
            return tuple(grp)

        self._us_body_keywords = _group('US', 'body')
        self._us_scan_keywords = _group('US', 'scan')
        self._us_unmatchable = _unmatch('US')
        self._spect_body_keywords = _group('SPECT', 'body')
        self._spect_scan_keywords = _group('SPECT', 'scan')
        self._spect_unmatchable = _unmatch('SPECT')  # H1
        self._pet_body_keywords = _group('PET', 'body')
        self._pet_unmatchable = _unmatch('PET')      # H1
        self._oct_body_keywords = _group('OCT', 'body')
        self._oct_unmatchable = _unmatch('OCT')      # H1
        self._dsa_body_keywords = _group('DSA', 'body')
        self._dsa_unmatchable = _unmatch('DSA')

        group_counts = {f"{m}/{t}": len(v) for (m, t), v in keyword_tables.items()}
        logger.info(f"[USSpectPetMatcher] 已从 keyword_match_rules 加载规则(单一真相): "
                    f"{group_counts}, unmatchable: { {k: len(v) for k, v in unmatchable.items()} }")

    @property
    def is_ready(self) -> bool:
        return self._initialized

    def standard_version(self, code: str, name: str, modality: str) -> Optional[str]:
        versions = self._standard_versions.get((code, name, modality), set())
        return next(iter(versions)) if len(versions) == 1 and '' not in versions else None

    def match(self, order_name: str, modality: str) -> List[Tuple[str, str]]:
        """匹配单条医嘱，并通过 ``_last_*`` 暴露结构化诊断。

        返回值仍为 ``[(item_code, item_name), ...]``，避免破坏旧版和批量接口。
        """
        self._last_tier = 'exact'
        self._last_reason = ''
        self._last_has_entity = False
        self._last_unresolved_components = []

        if not self._initialized:
            return self._failure('engine_not_ready')

        if modality == 'US':
            result = self._match_us(order_name)
        elif modality == 'SPECT':
            result = self._match_spect(order_name)
        elif modality in ('PET/CT', 'PET/MR'):
            result = self._match_pet(order_name, modality)
        elif modality == 'OCT':
            result = self._match_oct(order_name)
        elif modality == 'DSA':
            result = self._match_dsa(order_name)
        else:
            return self._failure('unsupported_modality')

        if result:
            if (modality == 'US' and re.search(r'血管|动脉|静脉|多普勒', order_name)
                    and not re.search(r'包块|肿块', order_name)):
                safe = [p for p in result if not re.search(r'包块|肿块', p[1])]
                if len(safe) != len(result):
                    self._last_unresolved_components = ['血管/多普勒检查']
                    result = safe
            if modality == 'SPECT' and '灌注' in order_name:
                safe = [p for p in result if '灌注' in p[1]]
                if len(safe) != len(result):
                    self._last_unresolved_components = ['灌注显像']
                    result = safe
            if not result and self._last_unresolved_components:
                return self._failure('standard_semantic_conflict', True)
            if self._last_unresolved_components:
                self._last_tier = 'ambiguous'
                self._last_reason = 'standard_semantic_conflict'
            elif modality == 'SPECT' and len(result) > 1:
                self._last_tier = 'ambiguous'
                self._last_reason = 'multiple_technical_candidates'
            elif (modality == 'SPECT' and '心肌灌注' in order_name
                  and not any(q in order_name for q in ('负荷', '静息', '平面', '断层'))
                  and any(any(q in name for q in ('负荷', '静息', '平面', '断层')) for _, name in result)):
                self._last_tier = 'ambiguous'
                self._last_reason = 'unspecified_technical_qualifier'
            if self._last_tier != 'ambiguous':
                self._last_reason = ''
            self._last_has_entity = True
        elif not self._last_reason:
            self._last_reason = 'lexicon_gap'
        return result

    def _failure(self, reason: str,
                 has_entity: Optional[bool] = None) -> List[Tuple[str, str]]:
        """记录无结果原因，同时保持旧 List 返回协议。"""
        self._last_reason = reason
        self._last_has_entity = has_entity
        return []

    def _query_result(self, pairs: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """标记已识别医学实体后的标准库查询结果。"""
        self._last_has_entity = True
        if not pairs:
            self._last_reason = 'standard_lib_gap'
        return pairs

    # ─── US 匹配 ──────────────────────────────────────────────────────────────

    def _match_us(self, order_name: str) -> List[Tuple[str, str]]:
        # 排除特殊用途。支气管镜等属于非影像自动匹配范围，而不是词库缺失。
        if any(marker in order_name for marker in self._us_unmatchable):
            return self._failure('excluded_non_imaging')
        if re.search(r'动态心电|无影像学|仅临床评估', order_name):
            return self._failure('excluded_non_imaging')

        # 0. 标准化 ACR 项目名，提取核心部位词
        normalized = self._normalize_us_name(order_name)
        text_norm = normalized.upper().replace('（', '(').replace('）', ')')

        # 1. 提取部位（先尝试标准化文本，回退到原始医嘱文本）
        #    回退原因：_normalize_us_name 会剥离"超声"前缀，
        #    对"超声心动"这类标准化后只剩"心动"无法匹配部位规则的输入，
        #    需用原始文本兜底（含"超声心动图"等关键词规则）。
        body_l2 = self._extract_us_body(text_norm, normalized)
        if not body_l2:
            orig_upper = order_name.upper().replace('（', '(').replace('）', ')')
            body_l2 = self._extract_us_body(orig_upper, order_name)
        if not body_l2:
            if re.search(r'穿刺|活检|置管|阻滞|封闭|治疗|引导', order_name):
                return self._failure('excluded_intervention')
            return self._failure('lexicon_gap', False)

        # 2. 提取扫描方式
        scan = self._extract_us_scan(order_name)

        # 3. 查表
        pairs = self._query_us(body_l2, scan)
        # 4. 多候选收敛：US 标准库中"经腹/经阴道/经食管"等路径共用同一 bp2，
        #    会返回多条路径变体（选择式候选）。按输入选最匹配的单个标准项返回
        #    （不做"选择"式多候选，与项目核心原则一致）。
        if len(pairs) > 1:
            pairs = self._select_best_candidate(order_name, pairs)
            # 仅当输入是"完整检查名"（含扫描方式/路径等限定词）时收敛为精确档；
            # 裸词（如"超声心动"）不指定具体检查，保持 degraded 待确认。
            if len(pairs) == 1 and self._has_us_specificity(order_name):
                self._last_tier = 'exact'  # 多候选已收敛为单候选，恢复精确档
        return self._query_result(pairs)

    @staticmethod
    def _has_us_specificity(order_name: str) -> bool:
        """输入是否指定了具体检查（扫描方式/路径/技术限定词）。

        裸词（"超声心动"）无任何限定 → 视为歧义输入，保持 degraded。
        """
        return any(k in order_name for k in (
            '常规', '三维', '四维', '弹性', '造影', '介入', '床旁', '消融',
            '多普勒', '彩色', '高频', '经腹', '经阴道', '经直肠', '经食管',
            '监测', '残余尿', '筛查', 'NT', '负荷', '充盈'))

    @staticmethod
    def _select_best_candidate(order_name: str,
                               pairs: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """从多候选中选择最匹配输入的单个标准项。

        规则：
        1. 输入含 经腹/经阴道/经直肠/经食管/经会阴 等路径词 → 优先对应路径的标准项
        2. 否则按名称与输入的字符重合度选最具体项；重合度相同取较短（更通用）项
        """
        if not pairs or len(pairs) <= 1:
            return pairs
        approach_kws = ('经腹', '经阴道', '经直肠', '经食管', '经会阴', '经肛门')
        for kw in approach_kws:
            if kw in order_name:
                filtered = [p for p in pairs if kw in p[1]]
                if filtered:
                    return filtered[:1]
        input_chars = {c for c in order_name if not c.isspace()}
        # 变体限定词：候选含输入没有的限定词（早孕期/筛查/负荷/充盈等）应降分，
        # 输入含有的限定词命中应加分（如"胎儿系统性筛查（三级）四维"选筛查三级项）
        QUALIFIERS = ('早孕期', 'NT', '筛查', '阶段', '负荷', '充盈', '残余尿', '监测',
                      '经腹', '经阴道', '经直肠', '经食管', '经会阴', '介入', '床旁',
                      '造影', '消融', '弹性', '三维', '四维',
                      # 技术功能测定类限定词（如"经胸超声心动图"不应选"机械运动同步功能"变体）
                      '功能', '定量', '跟踪', '动力学', '室壁', '左心室', '同步',
                      '收缩', '舒张', '测定', '彩色', '应变')
        best = None
        best_score = -1e9
        for p in pairs:
            name = p[1]
            score = len(input_chars & set(name))
            for q in QUALIFIERS:
                in_input = q in order_name
                in_name = q in name
                if in_input and in_name:
                    score += 2
                elif in_name and not in_input:
                    score -= 3
            score -= len(name) * 0.05  # 轻微偏好更短（更通用）项
            if (score > best_score
                    or (score == best_score
                        and (best is None or len(name) < len(best[0][1])))):
                best = [p]
                best_score = score
        return best or pairs[:1]

    def _normalize_us_name(self, name: str) -> str:
        """
        标准化 ACR 项目名，提取核心部位词

        US腹部彩色多普勒超声检查 → 腹部
        US心脏(常规) → 心脏
        US双下肢彩色多普勒超声检查 → 双下肢
        """
        core = name

        # 1. 去除前缀 US
        if core.startswith('US'):
            core = core[2:].strip()

        # 2. 去除扫描方式描述后缀（按长度排序，先匹配长词）
        suffixes = [
            '彩色多普勒超声检查', '常规超声检查', '超声检查',
            '多普勒超声检查', '彩色多普勒', '多普勒',
            '超声', '常规', '检查'
        ]
        for s in suffixes:
            core = core.replace(s, '')

        # 3. 去除括号内容和空格
        core = re.sub(r'[()（）].*$', '', core)
        core = core.strip()

        return core

    def _extract_us_body(self, text_upper: str, original: str) -> Optional[str]:
        for keywords, body_l2 in self._us_body_keywords:
            for kw in keywords:
                if '.*' in kw:
                    if re.search(kw, original):
                        return body_l2
                elif kw in original or kw in text_upper:
                    return body_l2
        return None

    def _extract_us_scan(self, order_name: str) -> str:
        for keywords, scan in self._us_scan_keywords:
            for kw in keywords:
                if kw in order_name:
                    return scan
        return '常规'

    def _query_us(self, body_l2: str, scan_method: str) -> List[Tuple[str, str]]:
        df = self._us_items
        mask = (df['body_part_l2'] == body_l2) & (df['scan_method'] == scan_method)
        result = df[mask]

        if result.empty and scan_method != '常规':
            # C4 修复：扫描方式降级（如造影→常规），标记为 degraded
            # 避免 orchestrator 以 exact/1.0 置信度缓存错误结果
            mask = (df['body_part_l2'] == body_l2) & (df['scan_method'] == '常规')
            result = df[mask]
            if not result.empty:
                self._last_tier = 'degraded'
                logger.info(f"[US] 扫描方式降级: {scan_method}→常规 (body={body_l2})")

        # 扫描方式同族回退：彩色多普勒/多普勒超声/频谱多普勒 描述的是同一类
        # 多普勒技术。标准库与医嘱对同一检查的措辞常常不一致（标准写
        # “多普勒超声”、医嘱写“彩色多普勒”），应在同族内先回退，而不是直接
        # 降到“常规”——否则会漏掉权威项，甚至错误命中“常规”下的无关项
        # （例：深静脉医嘱被降级后错配到双上肢动脉常规超声）。
        if result.empty:
            for alt in self.SCAN_FAMILY.get(scan_method, ()):
                if alt == scan_method:
                    continue
                mask = (df['body_part_l2'] == body_l2) & (df['scan_method'] == alt)
                alt_result = df[mask]
                if not alt_result.empty:
                    result = alt_result
                    self._last_tier = 'degraded'
                    logger.info(
                        f"[US] 扫描方式同族回退: {scan_method}→{alt} (body={body_l2})"
                    )
                    break

        # 多候选不能标记 exact；候选收敛由 _match_us 的 _select_best_candidate
        # 统一处理（按输入精确选择单个标准项），此处返回全部候选。
        if len(result) > 1:
            self._last_tier = 'degraded'

        return [(str(r['item_code']), str(r['item_name'])) for _, r in result.iterrows()]

    # ─── SPECT 匹配 ───────────────────────────────────────────────────────────

    def _match_spect(self, order_name: str) -> List[Tuple[str, str]]:
        # H1 修复：排除介入/科研类医嘱（与 US/DSA 保持一致）
        if any(marker in order_name for marker in self._spect_unmatchable):
            return self._failure('excluded_non_imaging')

        # SPECT 标准表项目名直接包含了描述信息
        # 策略：提取器官关键词 + 显像方式 → 查 body_part_l2 + scan_method
        body_l2 = self._extract_spect_body(order_name)
        scan = self._extract_spect_scan(order_name)

        if not body_l2:
            return self._failure('lexicon_gap', False)

        return self._query_result(self._query_spect(body_l2, scan))

    def _extract_spect_body(self, order_name: str) -> Optional[str]:
        for keywords, body_l2 in self._spect_body_keywords:
            for kw in keywords:
                if kw in order_name:
                    return body_l2
        return None

    def _extract_spect_scan(self, order_name: str) -> Optional[str]:
        for keywords, scan in self._spect_scan_keywords:
            for kw in keywords:
                if kw in order_name:
                    return scan
        return None

    def _query_spect(self, body_l2: str, scan_method: Optional[str]) -> List[Tuple[str, str]]:
        df = self._spect_items
        if scan_method:
            mask = (df['body_part_l2'] == body_l2) & (df['scan_method'] == scan_method)
            result = df[mask]
            if not result.empty:
                return [(str(r['item_code']), str(r['item_name'])) for _, r in result.iterrows()]

        mask = (df['body_part_l2'] == body_l2)
        result = df[mask]
        if result.empty:
            return []
        # H4 修复：返回所有匹配结果，不再静默丢弃
        # 多结果时标记 degraded，提示上层需人工确认
        if len(result) > 1:
            self._last_tier = 'degraded'
            logger.info(f"[SPECT] 多结果({len(result)}条): body={body_l2}, scan={scan_method}")
        return [(str(r['item_code']), str(r['item_name'])) for _, r in result.iterrows()]

    # ─── PET 匹配 ─────────────────────────────────────────────────────────────

    def _match_pet(self, order_name: str, modality: str) -> List[Tuple[str, str]]:
        # H1 修复：排除科研/介入类医嘱
        if any(marker in order_name for marker in self._pet_unmatchable):
            return self._failure('excluded_non_imaging')

        df = self._pet_ct_items if modality == 'PET/CT' else self._pet_mr_items
        body_l2 = self._extract_pet_body(order_name)

        if not body_l2:
            return self._failure('lexicon_gap', False)

        mask = df['body_part_l2'] == body_l2
        result = df[mask]
        pairs = [(str(r['item_code']), str(r['item_name'])) for _, r in result.iterrows()]
        return self._query_result(pairs)

    def _extract_pet_body(self, order_name: str) -> Optional[str]:
        # 去除前缀
        name = order_name
        if name.startswith('PET/CT'):
            name = name[6:].strip()
        elif name.startswith('PET/MR'):
            name = name[6:].strip()

        for keywords, body_l2 in self._pet_body_keywords:
            for kw in keywords:
                if '.*' in kw:
                    if re.search(kw, name):
                        return body_l2
                # 精确匹配或包含匹配
                elif kw == name or kw in name:
                    return body_l2

        # H2 修复：不再默认回退 '躯干'（会产生假阳性）
        # 无法识别部位的 PET 医嘱应返回 None，由上层标记为 none/0.0
        return None

    # ─── OCT 匹配 ─────────────────────────────────────────────────────────────

    def _match_oct(self, order_name: str) -> List[Tuple[str, str]]:
        """OCT 匹配：提取部位关键词 → 查 body_part_l2"""
        # H1 修复：排除介入/科研类医嘱
        if any(marker in order_name for marker in self._oct_unmatchable):
            return self._failure('excluded_non_imaging')

        body_l2 = self._extract_oct_body(order_name)
        if not body_l2:
            return self._failure('lexicon_gap', False)
        return self._query_result(self._query_oct(body_l2))

    def _extract_oct_body(self, order_name: str) -> Optional[str]:
        """从医嘱名提取 OCT 部位"""
        for keywords, body_l2 in self._oct_body_keywords:
            for kw in keywords:
                if '.*' in kw:
                    if re.search(kw, order_name):
                        return body_l2
                elif kw in order_name:
                    return body_l2
        return None

    def _query_oct(self, body_l2: str) -> List[Tuple[str, str]]:
        """查询 OCT 标准表"""
        df = self._oct_items
        mask = (df['body_part_l2'] == body_l2)
        result = df[mask]
        return [(str(r['item_code']), str(r['item_name'])) for _, r in result.iterrows()]

    # ─── DSA 匹配 ─────────────────────────────────────────────────────────────

    def _match_dsa(self, order_name: str) -> List[Tuple[str, str]]:
        """DSA 匹配：排除介入治疗，提取部位关键词 → 查 body_part_l2"""
        if any(marker in order_name for marker in self._dsa_unmatchable):
            return self._failure('excluded_intervention')

        body_l2 = self._extract_dsa_body(order_name)
        if not body_l2:
            return self._failure('lexicon_gap', False)
        return self._query_result(self._query_dsa(body_l2))

    def _extract_dsa_body(self, order_name: str) -> Optional[str]:
        """从医嘱名提取 DSA 部位"""
        for keywords, body_l2 in self._dsa_body_keywords:
            for kw in keywords:
                if '.*' in kw:
                    if re.search(kw, order_name):
                        return body_l2
                elif kw in order_name:
                    return body_l2
        return None

    def _query_dsa(self, body_l2: str) -> List[Tuple[str, str]]:
        """查询 DSA 标准表"""
        df = self._dsa_items
        mask = (df['body_part_l2'] == body_l2)
        result = df[mask]
        return [(str(r['item_code']), str(r['item_name'])) for _, r in result.iterrows()]

    # ─── 批量接口 ──────────────────────────────────────────────────────────────

    def batch_match(self, items: List[Dict[str, str]]) -> Dict[str, List[Tuple[str, str]]]:
        """
        批量匹配。

        Args:
            items: [{"key": id, "modality": "US", "name": "甲状腺彩超"}, ...]

        Returns:
            {key: [(item_code, item_name), ...]}
        """
        result: Dict[str, List[Tuple[str, str]]] = {}
        for item in items:
            key = item['key']
            modality = item.get('modality', '')
            name = item.get('name', '')

            if not name or modality not in ('US', 'SPECT', 'PET/CT', 'PET/MR', 'OCT', 'DSA'):
                result[key] = []
                continue

            try:
                result[key] = self.match(name, modality)
            except Exception as e:
                logger.warning(f"US/SPECT/PET 匹配失败 [{key}] {name}: {e}")
                result[key] = []

        return result


# ─── 全局单例 ──────────────────────────────────────────────────────────────────────

_matcher_instance: Optional[USSpectPetMatcher] = None


async def get_us_spect_pet_matcher(engine=None) -> USSpectPetMatcher:
    """获取全局 US/SPECT/PET/OCT/DSA 匹配器实例（懒初始化）。

    engine 可注入（独立 match-service 传自建 engine）；未传则用 backend app engine。
    """
    global _matcher_instance
    if _matcher_instance is None or not _matcher_instance.is_ready:
        _matcher_instance = USSpectPetMatcher(engine=engine)
        await _matcher_instance.initialize()
    return _matcher_instance

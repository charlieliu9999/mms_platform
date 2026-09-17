"""Make current-version (v3.8.2) keyword-modality standards reachable.

Revision ID: 20260911_0200
Revises: 20260911_0100
Create Date: 2026-09-11 02:00:00

背景（见 analysis/20260911/REPORT.md 缺陷②）：
关键词引擎（US/SPECT/PET/OCT/DSA）用 ``(body_part_l2, scan_method)`` 查表，
但以下 v3.8.2 权威标准项的 ``body_part_l2`` 为 NULL，导致**永远查不到**：

  - DSA 28 条：全部血管造影项（bp1 有值，且与 keyword_match_rules 的
    dst_value 完全一致 → 直接 bp2 ← bp1）
  - US  10 条：静脉导管/腹直肌/指(趾)甲/眼前节/全脊柱/双胎/跟骨/锁骨下静脉/
    颈内静脉/深静脉（bp1 粒度太粗，必须按项显式指定）
  - SPECT 12 条：本次不处理（与 C010A 系列存在并行/重复关系，
    处置方式需数据治理决策，见 REPORT.md §5）

  - SPECT 11 条：SPECT/CT 系列与器官显像（bp2 取值全部复用已有
    SPECT body 规则的 dst_value）。**不包含** ``50100000110000
    SPECT放射性核素大动脉显像``——它与 ``C010A802B0000`` 同名重复，
    由 L0 编码优先级选定，不动。

同时补齐缺失的 US 部位/扫描方式规则（部位词表原本没有 跟骨/深静脉/
锁骨下静脉/颈内静脉，且 ``静脉导管`` 被错误映射到不存在的
``胎儿静脉导管``）。修正后 ``DSA`` 匹配不再依赖历史 ``v2.0`` 行的内部编码。

配套代码改动：``USSpectPetMatcher.initialize`` 增加 v3.8.2 版本过滤，
落实「标准只用 v3.8.2」。
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260911_0200"
down_revision: Union[str, None] = "20260911_0100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# DSA：bp1 与 keyword_match_rules.dst_value 一致，可直接回填
DSA_BP2 = """VALUES
    ('DSA001001'), ('DSA001002'), ('DSA001003'), ('DSA001004'), ('DSA001005'),
    ('DSA002001'), ('DSA002002'), ('DSA002003'), ('DSA002004'), ('DSA002005'),
    ('DSA003001'), ('DSA003002'), ('DSA003003'), ('DSA003004'), ('DSA003005'),
    ('DSA003006'),
    ('DSA004001'), ('DSA004002'), ('DSA004003'), ('DSA004004'),
    ('DSA005001'), ('DSA005002'), ('DSA005003'), ('DSA005004'),
    ('DSA006001'), ('DSA006002'), ('DSA006003'), ('DSA006004')
"""

# US：按项显式指定 bp2，取值必须与 keyword_match_rules.dst_value 对齐
US_BP2 = [
    ("50U990001C0000", "静脉导管"),
    ("50U990002C0000", "双胎及胎盘"),
    ("50U990003C0000", "全脊柱"),
    ("50U990004C0000", "腹直肌"),
    ("50U990005C0000", "指(趾)甲"),
    ("50U990006C0000", "眼前节"),
    ("50U990007C0000", "跟骨"),
    ("50U990008C0000", "双侧锁骨下静脉"),
    ("50U990009C0000", "颈内静脉"),
    ("50U990010C0000", "深静脉"),
]

# SPECT：bp2 取值全部复用已有 SPECT body 规则的 dst_value。
# 50100000110000 是 C010A802B0000 的同名重复项，不在本迁移内处理。
SPECT_BP2 = [
    ("50990001110000", "心脏"),
    ("50990002110000", "全身"),
    ("50990003110000", "膀胱"),
    ("50990004110000", "肝脏"),
    ("50990005110000", "肾"),
    ("50990006110000", "颅底"),
    ("50990007110000", "颈部及纵隔"),
    ("50990008110000", "颈部及纵隔"),
    ("50990009110000", "颈部及纵隔"),
    ("50990010110000", "全身"),
    ("50990011110000", "全身"),
]

# 新增/修正的 keyword_match_rules（US）。
#
# 注意优先级：现有 US scan 规则占用 priority 0..6（造影/介入/消融/弹性/
# 三维/四维/床旁）。新增的 scan 规则必须排在它们**之后**（priority ≥ 50），
# 否则会把“弹性/三维/床旁/造影”等更具体的方式覆盖掉：
#   例 "US乳腺常规超声检查(彩色多普勒联合弹性成像)" 若 彩色多普勒 先命中，
#   就会从 `乳腺弹性超声检查` 退化为 `乳腺常规超声检查`（精度损失）。
# body 规则仍用负数高优先（与现有 -100..-90 约定一致）。
US_RULES = [
    # rule_type, keywords, dst_value, priority, remark
    ("body", "静脉导管", "静脉导管", -96,
     "通用静脉导管；原规则指向不存在的 dst=胎儿静脉导管"),
    ("body", "深静脉", "深静脉", -94, "深静脉血栓/下肢静脉彩超"),
    ("body", "跟骨;骨密度;QUS", "跟骨", -89, "跟骨骨密度超声"),
    ("body", "锁骨下静脉", "双侧锁骨下静脉", -88, "锁骨下静脉（静脉，勿与动脉混淆）"),
    ("body", "颈内静脉", "颈内静脉", -87, "颈内静脉"),
    # ── scan 规则：必须排在现有 0..6 之后，作为“无其他方式关键词时”的兼底
    ("scan", "高频", "高频超声", 50, "高频超声（低于 弹性/三维/床旁 等优先级）"),
    ("scan", "骨密度;QUS", "骨密度超声", 51, "骨密度超声"),
    ("scan", "生物显微镜;UBM", "超声生物显微镜", 52, "超声生物显微镜(UBM)"),
    ("scan", "彩色及频谱多普勒;彩色多普勒", "彩色多普勒", 53,
     "彩色多普勒；低于 弹性/三维/床旁/造影/介入"),
]


def upgrade() -> None:
    # 0) 清理历史版本迁移可能残留的同名规则（含早期把 scan 规则误置于 -10..-6
    #    的版本），保证 upgrade 幂等。
    op.execute("""
        DELETE FROM keyword_match_rules
        WHERE modality = 'US'
          AND priority IN (-96, -94, -89, -88, -87, -10, -9, -8, -7, -6,
                           50, 51, 52, 53, 60)
          AND dst_value IN ('静脉导管', '深静脉', '跟骨', '双侧锁骨下静脉',
                            '颈内静脉', '高频超声', '骨密度超声',
                            '超声生物显微镜', '彩色多普勒', '多普勒超声')
    """)

    # 1) DSA：bp2 ← bp1（两者与规则 dst_value 一致，已逐条核对）
    op.execute(f"""
        UPDATE standard_check_items AS s
        SET body_part_l2 = s.body_part_l1
        FROM ({DSA_BP2}) AS v(item_code)
        WHERE s.item_code = v.item_code
          AND s.modality = 'DSA'
          AND UPPER(TRIM(s.version)) = 'V3.8.2'
          AND (s.body_part_l2 IS NULL OR s.body_part_l2 = '')
    """)

    # 2) US：按项显式回填 bp2
    for code, bp2 in US_BP2:
        op.execute(f"""
            UPDATE standard_check_items
            SET body_part_l2 = '{bp2}'
            WHERE item_code = '{code}'
              AND modality = 'US'
              AND UPPER(TRIM(version)) = 'V3.8.2'
              AND (body_part_l2 IS NULL OR body_part_l2 = '')
        """)

    # 2b) SPECT：按项显式回填 bp2
    for code, bp2 in SPECT_BP2:
        op.execute(f"""
            UPDATE standard_check_items
            SET body_part_l2 = '{bp2}'
            WHERE item_code = '{code}'
              AND modality = 'SPECT'
              AND UPPER(TRIM(version)) = 'V3.8.2'
              AND (body_part_l2 IS NULL OR body_part_l2 = '')
        """)

    # 3) 补齐/修正 US 规则（幂等：先按 (modality, rule_type, keywords) 删除旧行再插入，
    #    避免历史版本迁移残留了不同 priority 的同名规则而互相干扰）
    for rule_type, keywords, dst, priority, remark in US_RULES:
        op.execute(f"""
            DELETE FROM keyword_match_rules
            WHERE modality = 'US' AND rule_type = '{rule_type}'
              AND keywords = '{keywords}'
        """)
        op.execute(f"""
            INSERT INTO keyword_match_rules
                (modality, rule_type, keywords, dst_value, priority, enable, remark)
            VALUES ('US', '{rule_type}', '{keywords}', '{dst}', {priority}, 0, '{remark}')
        """)

    # 4) 修正 p=-95 的坏规则：静脉导管 → 胎儿静脉导管（dst 不存在，死路）
    #    收窄为仅胎儿语境命中，通用「静脉导管」交给新增的 p=-96 规则。
    op.execute("""
        UPDATE keyword_match_rules
        SET keywords = '胎儿.*静脉导管;胎儿静脉导管',
            remark = '收窄为胎儿语境；通用静脉导管见 p=-96 规则'
        WHERE modality = 'US' AND rule_type = 'body' AND priority = -95
          AND dst_value = '胎儿静脉导管'
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM keyword_match_rules
        WHERE modality = 'US'
          AND priority IN (-96, -94, -89, -88, -87, -10, -9, -8, -7, -6,
                           50, 51, 52, 53, 60)
          AND dst_value IN ('静脉导管', '深静脉', '跟骨', '双侧锁骨下静脉',
                            '颈内静脉', '高频超声', '骨密度超声',
                            '超声生物显微镜', '彩色多普勒', '多普勒超声')
    """)
    op.execute("""
        UPDATE keyword_match_rules
        SET keywords = '静脉导管'
        WHERE modality = 'US' AND rule_type = 'body' AND priority = -95
          AND dst_value = '胎儿静脉导管'
    """)
    op.execute("""
        UPDATE standard_check_items
        SET body_part_l2 = NULL
        WHERE modality = 'US'
          AND item_code IN ('50U990001C0000','50U990002C0000','50U990003C0000',
                            '50U990004C0000','50U990005C0000','50U990006C0000',
                            '50U990007C0000','50U990008C0000','50U990009C0000',
                            '50U990010C0000')
    """)
    op.execute("""
        UPDATE standard_check_items
        SET body_part_l2 = NULL
        WHERE modality = 'SPECT'
          AND item_code IN ('50990001110000','50990002110000','50990003110000',
                            '50990004110000','50990005110000','50990006110000',
                            '50990007110000','50990008110000','50990009110000',
                            '50990010110000','50990011110000')
    """)
    op.execute("""
        UPDATE standard_check_items
        SET body_part_l2 = NULL
        WHERE modality = 'DSA' AND UPPER(TRIM(version)) = 'V3.8.2'
    """)

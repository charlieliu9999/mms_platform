# MMS 独立化进度总结

**更新时间**: 2026-07-28 10:24  
**最新提交**: 1988389a

---

## ✅ 已完成阶段

### Phase 0-4: 词表差异裁定（完成并验收）
- **提交**: da09b4ef
- **成果**:
  * 186 条差异全部裁定（KEEP 168, DROP 18）
  * 定稿词表 11,503 条
  * 裁定报告和验收文档
- **验收**: ✅ 通过所有标准

### Phase D: 配置层独立化（部分完成）
- **提交**: da09b4ef (rule_version) + 1988389a (ENGINE_MODE)
- **完成项**:
  * ✅ rule_version.py - MMS 自有规则版本计算
  * ✅ test_rule_version_parity.py - 版本号对齐测试（PASSED）
  * ✅ ENGINE_MODE 配置 - 支持 local/shared 两种模式
  * ✅ engine_holder 改造 - 模式切换逻辑
  * ✅ Dockerfile 改进 - 多阶段构建 + 健康检查
- **剩余项**:
  * ⏳ Phase A 引擎代码迁移（ENGINE_MODE=local 的前置条件）
  * ⏳ 测试 Docker 构建完整性

---

## ⚠️ 当前阻塞项

### Phase 0-5/0-6: 生产基线采集
**阻塞原因**: SSH 封禁（210.12.11.251）  
**影响**: 无法采集生产服务匹配结果作为验证标尺

**替代方案**: 本地基线策略
1. 用定稿词表更新本地数据库
2. 对现有医嘱跑本地引擎，建立"当前状态基线"
3. Phase A 验证改为"迁移前后自我对比"
4. Phase D 双跑时补生产对比

**前置条件**: 需要可访问的数据库（当前不可用）

---

## 📋 下一步行动

### 优先级 1: Phase A - 引擎物理独立

**目标**: 将 match_engine_v2 代码迁入 match_service，消除 acrac_backend 依赖

**任务清单**:
1. 创建 `match_service/src/match_service/engine/` 目录结构
2. 复制 `acrac_backend/app/services/check_item_mgmt/match_engine_v2/` 全部代码
3. 复制 `acrac_backend/app/services/check_item_mgmt/us_spect_pet_matcher.py`
4. 调整 import 路径（`from app.services...` → `from match_service.engine...`）
5. 迁移现有测试（97 个用例）
6. engine_holder 改用内置引擎（ENGINE_MODE=local）
7. 验证：全量测试通过

**验收标准**:
- `grep -r "from app\." match_service/src` 零结果
- pytest match_service/tests 全绿
- Docker 构建成功（无需 COPY acrac_backend）

### 优先级 2: Phase 0-5 本地基线（数据库可用时）

**任务**:
1. 用定稿词表更新数据库（3 表 upsert）
2. 查询现有医嘱清单（支持的模态）
3. 批量匹配并存档结果
4. 作为 Phase A 验证的对比基线

### 优先级 3: Phase B/C/D/E/F/G（顺序推进）

按设计文档 §9 的顺序逐阶段完成。

---

## 🎯 关键路径

```
Phase A 引擎独立 → Phase 0-5 本地基线 → Phase A 验证 → Phase B-G
      ↓
  消除 app.* 依赖
      ↓
  ENGINE_MODE=local 可用
      ↓
  Docker 独立构建
```

**当前瓶颈**: Phase A 尚未开始，这是后续所有阶段的前置条件

---

## 📊 整体进度

| Phase | 状态 | 进度 | 阻塞 |
|---|---|---|---|
| 0-4 | ✅ 完成 | 100% | - |
| 0-5 | ⚠️ 阻塞 | 0% | SSH + DB |
| 0-6 | ⚠️ 阻塞 | 0% | SSH + DB |
| A | ⏳ 待开始 | 0% | - |
| B | ⏳ 待开始 | 0% | Phase A |
| C | ⏳ 待开始 | 0% | Phase B |
| D | 🟡 部分完成 | 40% | Phase A |
| E | ⏳ 待开始 | 0% | Phase D |
| F | ⏳ 待开始 | 0% | Phase E |
| G | ⏳ 待开始 | 0% | 有第二接入方时 |

**总体完成度**: ~15% (Phase 0-4 + Phase D 部分)

---

## 🚀 立即可执行

**Phase A 第一步**: 创建目录结构并复制引擎代码

```bash
# 1. 创建目录
mkdir -p match_service/src/match_service/engine/match_engine_v2
mkdir -p match_service/src/match_service/engine/keyword

# 2. 复制代码
cp -r acrac_backend/app/services/check_item_mgmt/match_engine_v2/* \
      match_service/src/match_service/engine/match_engine_v2/

cp acrac_backend/app/services/check_item_mgmt/us_spect_pet_matcher.py \
   match_service/src/match_service/engine/keyword/

# 3. 调整 import（批量替换）
find match_service/src/match_service/engine -name "*.py" -exec \
  sed -i '' 's/from app\.services\.check_item_mgmt/from match_service.engine/g' {} \;
```

这一步不依赖任何外部资源，可以立即执行。

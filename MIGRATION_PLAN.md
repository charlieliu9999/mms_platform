# MMS 前端完整迁移计划

## 当前状态

### 已完成（简化版）
- ✅ Dashboard.tsx - 数据概览（新建，原系统无）
- ✅ MatchTest.tsx - 匹配测试工具（新建，原系统无）
- ⚠️ LexiconMgmt.tsx - 词库管理（仅简单 CRUD，原系统是完整的 5 表治理台）

### 未迁移（原系统核心页面）
- ❌ StandardItems.tsx - 标准项目管理（12KB，约 350 行）
- ❌ CoverageMgmt.tsx - 推荐项目标准匹配（31KB，约 900 行）
- ❌ CoverageAnalysis.tsx - ACR 覆盖分析（24KB，约 700 行）
- ❌ HospitalMapping.tsx - 医院项目映射（18KB，约 550 行）
- ❌ UnmatchedWorkbench.tsx - 未匹配工作台（10KB，约 300 行）
- ❌ ReviewMgmt.tsx - 审核管理（13KB，约 400 行）
- ❌ SpecialItemReview.tsx - 特殊项目审核（10KB，约 300 行）

### 未迁移（子组件）
- ❌ MedicalDictView.tsx - 医学词典视图
- ❌ PhraseMapView.tsx - 短语映射视图
- ❌ AmbiguityView.tsx - 消歧规则视图
- ❌ KeywordRuleView.tsx - 关键词规则视图
- ❌ CheckitemStandardView.tsx - 标准项目视图
- ❌ LexiconVersionBar.tsx - 词库版本条
- ❌ BatchReviewPanel.tsx - 批量审核面板
- ❌ BatchProgressPanel.tsx - 批量进度面板
- ❌ DeepResearchModal.tsx - 深度研究弹窗

---

## 迁移统计

| 类别 | 原系统 | 已迁移 | 待迁移 |
|------|--------|--------|--------|
| 主页面 | 9 个 (127KB) | 1 个 (简化) | 8 个 |
| 子组件 | 8 个 (约 50KB) | 0 个 | 8 个 |
| 总代码量 | ~4,295 行 | ~300 行 | ~3,995 行 |
| 完成度 | 100% | 7% | 93% |

---

## 迁移策略

### 方案 A: 完整迁移（推荐）
**优点**: 功能完整，与原系统一致  
**工作量**: 3-5 天  
**步骤**:
1. 迁移 LexiconMgmt（替换简化版，迁移 5 个子组件）
2. 迁移 StandardItems + UnmatchedWorkbench
3. 迁移 CoverageMgmt + CoverageAnalysis
4. 迁移 HospitalMapping + ReviewMgmt
5. 迁移 SpecialItemReview

### 方案 B: 分阶段迁移
**阶段 1（核心）**: LexiconMgmt + StandardItems + UnmatchedWorkbench  
**阶段 2（扩展）**: CoverageMgmt + HospitalMapping  
**阶段 3（高级）**: CoverageAnalysis + ReviewMgmt + SpecialItemReview

### 方案 C: 保持当前简化版
**优点**: 快速启动，满足基本需求  
**缺点**: 功能不完整，无法替代原系统  
**适用**: 原型验证、演示

---

## 技术债务

### 已知问题
1. **前端 API 不匹配**: 
   - 新前端使用 `check_item` 字段
   - 后端 API 使用 `name` 字段
   - 需要统一字段命名

2. **数据库依赖**:
   - 原系统依赖 5 张 NLP 规则表
   - 新系统尚未完整迁移数据库 schema

3. **状态管理缺失**:
   - 原系统可能使用 Redux/Context
   - 新系统未实现全局状态管理

4. **类型定义不完整**:
   - 需要从原系统迁移完整的 TypeScript 类型定义

---

## 推荐行动

### 立即执行
1. **统一 API 字段命名**
   - 前端 matchService.ts 中将 `check_item` 改为 `name`
   - 或后端 schemas.py 中将 `name` 改为 `check_item`

2. **完整迁移 LexiconMgmt**
   - 这是最核心的页面（词库治理）
   - 包含 5 个子组件（医学词典/短语映射/消歧规则/关键词/标准项目）
   - 从 2,633 行扩展到原系统的完整实现

### 后续计划
3. **迁移核心业务页面**（按优先级）
   - P0: StandardItems（标准项目管理）
   - P0: UnmatchedWorkbench（未匹配工作台）
   - P1: HospitalMapping（医院项目映射）
   - P2: CoverageMgmt（推荐项目匹配）
   - P3: CoverageAnalysis（覆盖分析）

---

## 工作量估算

| 页面 | 代码量 | 复杂度 | 预计时间 |
|------|--------|--------|----------|
| LexiconMgmt（完整版）| 31KB | 高 | 8-12 小时 |
| StandardItems | 12KB | 中 | 4-6 小时 |
| UnmatchedWorkbench | 10KB | 中 | 4-6 小时 |
| HospitalMapping | 18KB | 中 | 6-8 小时 |
| CoverageMgmt | 31KB | 高 | 8-12 小时 |
| CoverageAnalysis | 24KB | 高 | 6-10 小时 |
| ReviewMgmt | 13KB | 中 | 4-6 小时 |
| SpecialItemReview | 10KB | 中 | 4-6 小时 |
| **总计** | **~150KB** | - | **44-66 小时** |

---

## 决策

**问题**: 是否需要完整迁移原系统的所有页面？

**选项**:
1. ✅ **完整迁移** - 替代原系统，3-5 天工作量
2. ⚠️ **核心迁移** - 仅迁移 LexiconMgmt + StandardItems，1-2 天
3. ❌ **保持现状** - 仅作为演示/原型，功能不完整

**建议**: 选择方案 1（完整迁移），确保功能对等，可完全替代原系统。

# 24.6 万条全量匹配与 L1 映射库构建 — 设计文档

**日期**: 2026-07-29
**状态**: 待评审
**作者**: Claude Code

## 1. 背景与目标

MMS 采用三层匹配架构（L1 映射库 → L2 算法引擎 → L3 AI Agent）。当前 `match_cache`（L1）仅有 59 条记录（`agent_confirmed` 22 条、`llm_semantic` 37 条），命中率极低，绝大多数请求穿透到 L2 算法引擎。

项目已有 24.6 万条带标准答案的基准数据集 `tests/benchmark/16zzy_combined_246k.csv`，尚未用于全量评测，也未沉淀为 L1 映射数据。

**目标**：
1. 对 24.6 万条数据执行全量匹配，量化引擎当前性能
2. 产出结构化分析报告，定位优化方向
3. 将高质量匹配结果沉淀为 L1 映射库，提升线上查表命中率

## 2. 数据现状

### 2.1 输入数据集

`tests/benchmark/16zzy_combined_246k.csv`，246,113 行（不含表头）。

| 字段 | 说明 |
|------|------|
| `check_item` | 原始检查项目文本 |
| `modality` | 模态（CT / DR / MR） |
| `version` | 标准版本，全部为 `V3.8.2` |
| `expected_standard_code` | 期望标准编码 |
| `expected_standard_name` | 期望标准名称 |

**分布**：CT 115,983 / DR 93,325 / MR 36,805。

**数据质量**：
- `expected_standard_code` 与 `expected_standard_name` 无空值
- `check_item` 唯一值 245,018，`(check_item, modality)` 组合唯一值 246,113 —— 即组合层面完全无重复，但同一 `check_item` 文本可能跨模态出现
- `expected_standard_code` 为浮点字符串格式（如 `20041100010000.0`），需去除 `.0` 后缀

### 2.2 目标表结构

复用现有表，无需新建：

- **`mms_eval_tasks`** — 评测任务元数据（状态、进度、指标）
- **`mms_eval_details`** — 每条记录的匹配明细
- **`match_cache`** — L1 映射库
- **`match_feedback`** — 冲突与异常记录

`match_cache` 关键字段：

```
text_hash    SHA-256(normalize(text) + "|" + MODALITY)，唯一索引 (text_hash, modality)
modality     大写模态
original_text 原始文本
result_json  完整匹配结果 JSON
confidence   置信度
source       来源标识
expires_at   过期时间
```

`MatchCache.compute_hash` 的归一化规则：`text.strip().lower().replace(" ", "")`。

## 3. 已知缺陷（必须先修复）

### 3.1 `evaluation/runner.py` 将 `score` 误用为 `confidence`

`src/match_service/evaluation/runner.py:190`：

```python
confidence = match_result.get('score', 0.0)
```

引擎返回的 `score` 由 `orchestrator.py:304` 计算：`match_info['score'] = 10 - score`，取值范围约 0–10。而真正的置信度是独立字段 `confidence`，由 tier 映射得出：

```python
TIER_CONFIDENCE = {
    'exact': 1.0, 'partial': 0.8, 'degraded': 0.6,
    'ambiguous': 0.4, 'none': 0.0, 'error': 0.0,
}
```

已入库的缓存记录可证实两者并存且不同：`{"score": 10, ..., "confidence": 1.0}`。

**影响**：若沿用此逻辑，筛选 `confidence >= 0.8` 会退化为筛选 `score >= 0.8`，几乎放行所有匹配结果，L1 库将被低质量映射污染。

**修复**：改用 `match_result.get('confidence', 0.0)`。本次实现新脚本时直接采用正确字段；`runner.py` 的同类修复归入本设计范围（见 6.1）。

### 3.2 置信度阈值与三层架构的一致性

`confidence >= 0.8` 恰好等价于 `tier in {exact, partial}`，与 `core/dispatcher.py` 的 `AUTO_CACHE_TIERS` 及 `AUTO_CACHE_MIN_CONFIDENCE = 0.8` 完全一致。导入策略因此与线上回写策略同源，不引入新口径。

## 4. 方案设计

### 4.1 整体流程

```
Phase 1  全量匹配      CSV(246k) → 匹配引擎 → mms_eval_tasks + mms_eval_details
Phase 2  结果分析      mms_eval_details → Markdown 报告
Phase 3  L1 导入       筛选高质量记录 → match_cache（冲突记录 → match_feedback）
Phase 4  导入验证      数量统计 + 抽样核对 + 缓存命中测试
```

### 4.2 Phase 1：全量匹配

**脚本**：`scripts/bulk_match_and_import.py`

**执行方式**：直接调用引擎单例（`EngineHolder`），不经 HTTP，避免网络开销。

**关键设计**：

| 项 | 决策 | 理由 |
|----|------|------|
| 批大小 | 每 100 条提交一次 DB | 控制事务体积与内存占用 |
| 断点续跑 | 以 DB 中 `mms_eval_details` 的已有记录数为准 | 比 .progress.json 更可靠，与 DB 提交原子性一致 |
| 进度反馈 | 终端日志 + `mms_eval_tasks.progress` 字段 | 兼顾人工观察与 API 查询 |
| 正确性判定 | 复用 `runner.py` 的 exact + fuzzy 双重判定 | 与既有评测口径一致 |
| 置信度取值 | `match_result.get('confidence') or TIER_CONFIDENCE.get(match_result.get('tier', 'none'), 0.0)` | 优先取直接字段，fallback 到 tier 映射 |
| 异常处理 | 单条异常也写入 `mms_eval_details`，标记 `failure_reason='algorithm'` | 确保每批 100 条事务完整，失败记录也可追溯 |

**运行模式**：

```bash
# 冒烟测试：1000 条
python scripts/bulk_match_and_import.py --sample 1000

# 全量
python scripts/bulk_match_and_import.py --full
```

**明细字段**（写入 `mms_eval_details`）：`check_item`、`modality`、`expected_code`、`expected_name`、`actual_code`、`actual_name`、`confidence`、`response_time`、`is_matched`、`is_correct`、`match_type`、`failure_reason`、`failure_detail`。

### 4.3 Phase 2：结果分析

**脚本**：`scripts/analyze_benchmark_results.py --task-id <id>`

**输出**：`docs/reports/2026-07-29-bulk-match-246k-report.md`

报告章节：

1. **总体指标** — 总数、匹配率、准确率、Precision / Recall / F1、平均置信度
2. **按模态统计** — CT / DR / MR 各自的匹配率、准确率、F1
3. **失败原因分类** — `missing_word` / `ambiguity` / `complex` / `algorithm` / `wrong_match` 的数量与占比
4. **Top 20 高频失败案例** — 按 `check_item` 聚合失败次数排序
5. **置信度分布** — 五档区间 [0,0.2) … [0.8,1.0] 的记录数
6. **响应时间分析** — 平均值、P50、P95、最慢 10 条

所有统计通过 SQL 聚合完成，不将 24.6 万条明细载入内存。

### 4.4 Phase 3：L1 映射库导入

**脚本**：`scripts/import_to_l1_cache.py --task-id <id>`

**筛选条件**（三者同时满足）：

```sql
is_correct = true          -- 与期望标准一致（exact 或 fuzzy 命中）
AND confidence >= 0.8      -- 等价于 tier ∈ {exact, partial}
AND actual_code IS NOT NULL
```

**冲突处理**：已存在的**有效**记录一律保留旧值；过期记录可更新。

```
计算 text_hash = compute_hash(check_item, modality)
查询 match_cache WHERE text_hash = ? AND modality = ?

情况 1: 记录不存在
  → 插入 match_cache:
       source     = 'benchmark'
       confidence = 明细中的 confidence
       expires_at = now + MATCH_CACHE_TTL(30 天)

情况 2: 记录存在且未过期 (expires_at IS NULL OR expires_at > now())
  → 保留旧记录，写一条 match_feedback:
       feedback_type     = 'cache_conflict'
       status           = 'pending'
       original_text    = check_item
       engine_result_json = 新结果（benchmark匹配结果）
       suggested_fix    = JSON 说明：旧source={old.source}, 旧conf={old.confidence}

情况 3: 记录存在但已过期 (expires_at <= now())
  → 更新记录:
       result_json  = 新结果
       confidence   = 新 confidence
       source       = 'benchmark'
       confirmed_at = now()
       expires_at   = now + MATCH_CACHE_TTL(30 天)
       hit_count    = 保持不变（历史命中次数）
```

**结果 JSON 结构**：直接序列化引擎返回的完整结果（已剥离 `_cache_*` 等内部字段），确保 `CacheService.lookup` 返回的对象与 L2 直出结果同构。

```python
# 从 mms_eval_details 重构 result_json
result_json = {
    "check_item": detail.check_item,
    "num_standard": 1 if detail.actual_code else 0,
    "data": [{
        "raw": detail.check_item,
        "standard": [{
            "code": detail.actual_code,
            "name": detail.actual_name
        }]
    }] if detail.actual_code else [],
    "score": 10,  # 高置信度固定为满分
    "tier": detail.match_type if detail.match_type in ['exact', 'partial'] else 'exact',
    "confidence": float(detail.confidence),
    "reason": "",
    "has_entity": True
}
```

**去重与碰撞检测**：源数据 `(check_item, modality)` 组合已完全唯一，无需额外去重；但仍以 `text_hash` 唯一索引作为最终防线，因归一化（去空格、转小写）可能使不同原文碰撞到同一 hash。

碰撞处理：
- 在冒烟测试（1000条）阶段统计碰撞率
- 如果碰撞率 > 0.1%，则在 `match_feedback` 的 `suggested_fix` 字段记录被丢弃的原文，供人工审核
- 碰撞案例示例记录到分析报告的独立章节

**输出**：`data/bulk_match/import_summary.json`，记录符合条件数、成功插入数、冲突跳过数（未过期）、更新数（过期）、feedback 写入数、hash 碰撞数。

### 4.5 Phase 4：导入验证

**脚本**：`scripts/verify_l1_import.py --task-id <id>`

**验证项**：

1. **数量核对** — `match_cache` 按 `source` 分组计数，确认 `benchmark` 条数与 `import_summary.json` 的 `inserted + updated` 一致
2. **抽样核对** — 从各模态随机抽取 1%（~2460 条），按失败原因分层采样，逐条比对：
   - `original_text`、`modality` 与 `mms_eval_details` 一致
   - `result_json.data[0].standard[0].code` 与 `expected_code` 一致
   - `confidence >= 0.8`
3. **冲突记录核对** — `match_feedback` 中 `feedback_type='cache_conflict'` 的记录数等于 `import_summary.json` 的 `skipped`
4. **过期时间有效性** — 随机取 10 条 `source='benchmark'` 记录，验证 `expires_at` 在 `[now, now+30天]` 区间
5. **缓存命中测试** — 从导入记录中取 20 条，经 `MatchDispatcher.match` 调用，断言返回 `_cache_hit = True` 且 `_cache_source = 'benchmark'`
6. **hash 碰撞检测** — 如果 `import_summary.json` 的 `hash_collisions > 0`，输出碰撞案例列表供人工审核

## 5. 错误处理与性能监控

### 5.1 异常处理

| 场景 | 处理 |
|------|------|
| 单条匹配抛异常 | 捕获具体异常，构造 `EvalDetail` 记录：`is_matched=false`, `failure_reason='algorithm'`, `failure_detail=str(e)[:200]`，继续下一条 |
| 引擎未就绪 | 启动时校验 `engine.is_ready`，未就绪则中止并报错 |
| DB 提交失败 | 回滚当前批次，记录错误日志后退出。续跑时从 `mms_eval_details` 的已有记录数继续 |
| 导入阶段唯一约束冲突 | SQLAlchemy IntegrityError 视为并发写入，按冲突分支处理，不中断 |

`expected_standard_code` 的 `.0` 后缀在读取时统一剥离（`runner.py` 已有此逻辑，复用）。

### 5.2 性能监控

**Phase 1 匹配阶段**：
- 每 1000 条输出统计：当前总数、平均响应时间、P95 响应时间
- 如果 P95 > 200ms，输出告警日志（不中断，仅记录）
- 最终报告最慢的 10 条 case（`check_item` + `response_time`）

**DB 连接池配置验证**：
- 启动时检查 `pool_size` 和 `max_overflow` 配置
- 预期 `pool_size >= 5` 且 `max_overflow >= 10`
- 不满足则输出警告

### 5.3 冒烟测试验收标准

运行 `--sample 1000` 后，必须满足以下条件才能执行全量：

1. **准确率 ≥ 85%** — `correct / matched >= 0.85`
2. **匹配率 ≥ 90%** — `matched / total >= 0.90`
3. **平均响应时间 < 100ms**
4. **无系统级异常** — DB 连接失败、引擎崩溃、内存溢出等
5. **hash 碰撞率 < 0.1%** — `collisions / total < 0.001`

## 6. 变更清单

### 6.1 修改

- `src/match_service/evaluation/runner.py:190` — `score` → `confidence`

### 6.2 新增

- `scripts/bulk_match_and_import.py` — Phase 1 全量匹配
- `scripts/analyze_benchmark_results.py` — Phase 2 分析报告
- `scripts/import_to_l1_cache.py` — Phase 3 L1 导入
- `scripts/verify_l1_import.py` — Phase 4 验证

### 6.3 产出物

- `docs/reports/2026-07-29-bulk-match-246k-report.md` — 分析报告
- `data/bulk_match/import_summary.json` — 导入摘要

无数据库 schema 变更，无需 Alembic 迁移。

## 7. 回滚方案

如导入后发现批量数据有问题，执行以下 SQL 快速回滚：

```sql
-- 1. 记录回滚前的数量（用于验证）
SELECT COUNT(*) FROM match_cache WHERE source = 'benchmark';
SELECT COUNT(*) FROM match_feedback WHERE feedback_type = 'cache_conflict';

-- 2. 回滚 match_cache
DELETE FROM match_cache WHERE source = 'benchmark';

-- 3. 回滚 match_feedback（按时间范围，<导入开始时间> 需替换）
DELETE FROM match_feedback 
WHERE feedback_type = 'cache_conflict' 
  AND created_at >= '<导入开始时间>';

-- 4. 验证回滚结果
SELECT source, COUNT(*) FROM match_cache GROUP BY source;
```

**注意**：回滚会丢失导入期间的 `hit_count` 增量，如果已有线上流量命中，建议先评估影响。

## 8. 验收标准

1. **冒烟测试通过** — 1000 条样本满足 5.3 节的全部条件
2. **全量处理完毕** — 24.6 万条全部处理，`mms_eval_details` 记录数等于 246,113
3. **分析报告完整** — 包含全部六个章节，数据可复算，hash 碰撞率 < 0.1%
4. **导入数量一致** — `match_cache` 中 `source='benchmark'` 的记录数 = `import_summary.json` 的 `inserted + updated`
5. **抽样验证通过** — 2460 条抽样（1%）全部核对通过
6. **冲突记录一致** — `match_feedback` 中 `cache_conflict` 记录数 = `import_summary.json` 的 `skipped`
7. **缓存命中测试通过** — 20 条测试全部返回 `_cache_hit = True`
8. **既有测试不受影响** — `runner.py` 的 confidence 修复后，`pytest tests/ -q` 全绿

## 9. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 全量耗时超预期 | 单条 50ms 估算下约 3.4 小时 | 先跑 1000 条冒烟测试测得真实速率；断点续跑机制确保可中断恢复 |
| 基准数据本身标注有误 | 准确率被低估，且错误映射进入 L1 | 抽样 1%（2460 条）按失败原因分层采样人工复核；Phase 2 分析识别"高频被判错的标准编码" |
| 归一化 hash 碰撞 | 不同原文映射到同一缓存项 | 冒烟测试统计碰撞率；冲突一律保留旧值并记 feedback 供审计 |
| 一次性导入大量记录 | L1 命中率提升但可能固化当前算法的错误 | `source='benchmark'` 可独立标识，必要时按 source 批量失效；提供回滚方案 |
| 引擎性能退化 | 长时间运行可能导致内存泄漏或性能下降 | 每 1000 条监控响应时间，P95 > 200ms 时告警；必要时分批执行 |
| 并发写入冲突 | 导入期间线上系统写入新数据被误判为冲突 | 冲突处理检查 `expires_at`；只保留未过期的旧记录 |
| DB 连接池耗尽 | 2461 次提交可能超出连接池上限 | 预先验证 `pool_size >= 5` 且 `max_overflow >= 10` |

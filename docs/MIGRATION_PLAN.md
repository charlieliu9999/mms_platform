# MMS Platform 优化迁移计划

> 基于 16_zzy 项目的对比分析，制定分阶段的优化迁移计划
> 
> 创建时间：2026-07-29
> 
> 目标：将 16_zzy 的测试数据和实战经验整合到 MMS Platform

---

## 总体目标

将 MMS Platform 的工程优势与 16_zzy 的实战数据结合，打造生产级匹配服务：

1. ✅ **保持 MMS 的架构优势**（双引擎、异步、管理后台）
2. ✅ **补充 16_zzy 的测试数据**（6.3 万条实战样本）
3. ✅ **吸收 16_zzy 的边界经验**（400+ 行迭代日志）
4. ✅ **验证准确率提升**（目标 F1 > 0.95）

---

## 阶段划分

### Phase 1: 数据差异分析与词表合并（预计 2 天）
### Phase 2: 测试数据导入与 Benchmark 建立（预计 3 天）
### Phase 3: 边界 Case 提取与测试补充（预计 3 天）
### Phase 4: 准确率验证与调优（预计 5 天）
### Phase 5: 生产部署与监控（预计 2 天）

**总工期**：15 天

---

## Phase 1: 数据差异分析与词表合并（2天）

### 1.1 目标

- 识别 16_zzy 特有的医学词汇
- 合并到 MMS 词表中
- 保持 MMS 的数据结构（词性、版本、设备字段）

### 1.2 任务清单

#### Task 1.1: 医学词典差异分析（0.5天）

```bash
# 脚本：scripts/phase1_analyze_dict_diff.py
```

**输出**：
- `reports/dict_diff_analysis.csv` - 差异词汇清单（约 200 条）
- `reports/dict_overlap_analysis.csv` - 重叠词汇对比

**验收标准**：
- ✅ 识别出 16_zzy 特有的词汇数量
- ✅ 标注词性（body/scan/post/position）
- ✅ 标注适用设备（CT/MR/DR/ALL）

#### Task 1.2: 短语映射差异分析（0.5天）

```bash
# 脚本：scripts/phase1_analyze_phrase_diff.py
```

**输出**：
- `reports/phrase_diff_analysis.csv` - 差异短语清单（约 100 条）

**验收标准**：
- ✅ 识别 16_zzy 特有的短语映射
- ✅ 检查是否与 MMS 现有规则冲突

#### Task 1.3: 词表合并与验证（1天）

```bash
# 脚本：scripts/phase1_merge_lexicon.py
```

**执行步骤**：
1. 合并医学词典（去重、补充词性）
2. 合并短语映射（去重、补充版本）
3. 消歧规则对比（16_zzy 仅 51 条，MMS 1,229 条，无需合并）
4. 生成新版词表文件

**输出**：
- `phase1-deliverables/merged_medical_dict.csv` - 合并后的医学词典（约 2,600 条）
- `phase1-deliverables/merged_phrase_map.csv` - 合并后的短语映射（约 7,900 条）
- `phase1-deliverables/merge_report.md` - 合并报告

**验收标准**：
- ✅ 新词表通过 schema 验证
- ✅ 无重复词条
- ✅ 保持 MMS 的数据结构

### 1.3 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 词性标注不准确 | 中 | 人工复核前 50 条，建立标注规则 |
| 短语映射冲突 | 高 | 冲突时优先保留 MMS 规则（已验证） |
| 数据格式不兼容 | 低 | 先转换为 MMS 格式，再合并 |

---

## Phase 2: 测试数据导入与 Benchmark 建立（3天）

### 2.1 目标

- 导入 16_zzy 的 6.3 万条测试数据
- 建立 benchmark 测试集
- 与 MMS 现有 46 个测试对齐

### 2.2 任务清单

#### Task 2.1: 测试数据清洗与转换（1天）

```bash
# 脚本：scripts/phase2_import_test_data.py
```

**输入**：
- `16_zzy/data/20221219.xlsx` - 6.3 万条原始数据
  - CT: 27,772 条
  - DR: 25,970 条
  - MR: 9,804 条

**输出**：
- `tests/benchmark/16zzy_ct_27k.csv`
- `tests/benchmark/16zzy_dr_26k.csv`
- `tests/benchmark/16zzy_mr_10k.csv`
- `tests/benchmark/16zzy_combined_63k.csv`

**数据格式转换**：
```python
# 16_zzy 格式
{
  "原始检查项目": "胸部CT平扫",
  "模态": "CT",
  "标准项目": "胸部平扫"
}

# MMS 格式
{
  "check_item": "胸部CT平扫",
  "modality": "CT",
  "version": "V3.8.2",
  "expected_standards": [
    {"code": "CT_001", "name": "胸部平扫"}
  ]
}
```

**验收标准**：
- ✅ 数据格式符合 MMS 测试框架
- ✅ 去除无效记录（空值、格式错误）
- ✅ 统计数据质量报告

#### Task 2.2: Benchmark 测试框架开发（1天）

```bash
# 测试文件：tests/benchmark/test_16zzy_benchmark.py
```

**功能**：
```python
def test_ct_27k_benchmark():
    """测试 16_zzy 的 27,772 条 CT 数据"""
    results = run_benchmark('16zzy_ct_27k.csv')
    
    assert results['precision'] >= 0.95
    assert results['recall'] >= 0.92
    assert results['f1'] >= 0.93
    
    # 生成详细报告
    generate_report(results, 'reports/ct_benchmark_report.md')
```

**验收标准**：
- ✅ 支持批量测试（6.3 万条）
- ✅ 计算准确率指标（Precision/Recall/F1）
- ✅ 生成详细报告（误匹配分析）

#### Task 2.3: 基线准确率测试（1天）

```bash
# 运行 benchmark
poetry run pytest tests/benchmark/test_16zzy_benchmark.py -v
```

**输出**：
- `reports/baseline_accuracy_report.md` - 基线准确率报告
  - CT: Precision/Recall/F1
  - DR: Precision/Recall/F1
  - MR: Precision/Recall/F1
  - Overall: Precision/Recall/F1

**验收标准**：
- ✅ 完成 6.3 万条数据测试
- ✅ 准确率达到或超过 16_zzy（F1 >= 0.95）
- ✅ 识别 Top 100 误匹配 case

### 2.3 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 数据格式不一致 | 高 | 先转换 100 条验证，再批量处理 |
| 测试时间过长 | 中 | 并行测试 + 采样验证（先测 1 万条） |
| 准确率低于预期 | 高 | 分析误匹配原因，Phase 4 调优 |

---

## Phase 3: 边界 Case 提取与测试补充（3天）

### 3.1 目标

- 从 16_zzy 的 README（400+ 行迭代日志）中提取边界 case
- 补充到 MMS 测试集
- 确保覆盖历史难点

### 3.2 任务清单

#### Task 3.1: README 日志分析（1天）

```bash
# 脚本：scripts/phase3_extract_edge_cases.py
```

**输入**：
- `16_zzy/examine-standard/README.md` - 597 行日志

**提取维度**：
1. **部位歧义**（如"膝关节"→左/右）
2. **术语映射**（如"骨成像"→"三维重建"）
3. **复合项目**（如"颅脑胸部腰椎（三维重建）"）
4. **错别字**（如"右前壁"→"右前臂"）
5. **特殊序列**（如"ESWAN"、"ASL"）

**输出**：
- `reports/edge_cases_catalog.md` - 边界 case 分类目录（约 200 条）

**验收标准**：
- ✅ 提取 200+ 条有代表性的边界 case
- ✅ 按类型分类（部位歧义/术语映射/复合项目等）

#### Task 3.2: 边界 Case 测试开发（1天）

```bash
# 测试文件：tests/edge_cases/test_16zzy_edge_cases.py
```

**测试结构**：
```python
class Test16zzyEdgeCases:
    def test_body_ambiguity(self):
        """部位歧义测试（50条）"""
        cases = load_cases('edge_cases/body_ambiguity.csv')
        for case in cases:
            result = match(case['input'], case['modality'])
            assert case['expected'] in result['standards']
    
    def test_term_mapping(self):
        """术语映射测试（50条）"""
        ...
    
    def test_composite_items(self):
        """复合项目测试（50条）"""
        ...
```

**验收标准**：
- ✅ 200+ 条边界 case 全部通过测试
- ✅ 失败 case 记录到 `reports/edge_case_failures.md`

#### Task 3.3: 测试覆盖率分析（1天）

```bash
# 运行覆盖率测试
poetry run pytest tests/ --cov=match_service --cov-report=html
```

**输出**：
- `htmlcov/index.html` - 覆盖率报告
- `reports/coverage_report.md` - 覆盖率分析

**验收标准**：
- ✅ 引擎核心代码覆盖率 >= 85%
- ✅ 识别未覆盖的代码路径

### 3.3 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 边界 case 提取不全 | 中 | 人工复核 README，补充遗漏 |
| 测试用例编写耗时 | 中 | 使用模板批量生成测试 |
| 部分 case 无法通过 | 高 | 记录到 backlog，Phase 4 解决 |

---

## Phase 4: 准确率验证与调优（5天）

### 4.1 目标

- 分析 benchmark 测试结果
- 优化词表和规则
- 将准确率提升到 F1 > 0.95

### 4.2 任务清单

#### Task 4.1: 误匹配分析（2天）

```bash
# 脚本：scripts/phase4_analyze_mismatches.py
```

**输入**：
- `reports/baseline_accuracy_report.md` - 基线准确率报告
- `reports/edge_case_failures.md` - 边界 case 失败清单

**分析维度**：
1. **误匹配类型分布**
   - 未匹配（False Negative）
   - 误匹配（False Positive）
   - 部分匹配（置信度低）

2. **误匹配原因分类**
   - 词表缺失
   - 消歧规则缺失
   - 短语映射缺失
   - 算法逻辑问题

**输出**：
- `reports/mismatch_analysis.md` - 误匹配分析报告
- `reports/optimization_priorities.md` - 优化优先级清单

**验收标准**：
- ✅ 识别 Top 50 高频误匹配模式
- ✅ 按影响范围排序优化优先级

#### Task 4.2: 词表与规则优化（2天）

**优化方向**：

1. **补充缺失词汇**（约 50-100 条）
```python
# 示例：补充 16_zzy 特有词汇
new_words = [
    {'word': '茎突', 'type': 'body', 'device': 'CT', 'version': 'V3.8.2'},
    {'word': '髁关节', 'type': 'body', 'device': 'DR', 'version': 'V3.8.2'},
]
```

2. **补充短语映射**（约 20-50 条）
```python
# 示例：补充术语映射
new_phrases = [
    {'src_word': '骨成像', 'dst_word': '三维重建', 'step': 'normalize'},
    {'src_word': '中耳', 'dst_word': '乳突薄层', 'step': 'normalize'},
]
```

3. **补充消歧规则**（约 10-20 条）
```python
# 示例：补充特定场景消歧
new_rules = [
    {
        'device': 'CT',
        'src_body': '膝关节',
        'src_process': '',
        'dst_body': '单侧膝关节',
        'dst_process': '平扫'
    }
]
```

**验收标准**：
- ✅ 补充的词表和规则通过 schema 验证
- ✅ 补充后准确率提升 >= 2%

#### Task 4.3: 回归测试与验证（1天）

```bash
# 运行完整测试套件
./scripts/test-all.sh

# 运行 benchmark
poetry run pytest tests/benchmark/ -v

# 运行边界 case
poetry run pytest tests/edge_cases/ -v
```

**验收标准**：
- ✅ 所有原有测试（46 个）通过
- ✅ Benchmark F1 >= 0.95
- ✅ 边界 case 通过率 >= 95%

### 4.3 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 优化引入新问题 | 高 | 每次优化后立即回归测试 |
| 准确率提升不明显 | 中 | 分析根本原因，调整算法逻辑 |
| 优化时间超预期 | 中 | 聚焦 Top 20 高频问题，其余记录 backlog |

---

## Phase 5: 生产部署与监控（2天）

### 5.1 目标

- 部署优化后的服务
- 建立监控体系
- 灰度切换策略

### 5.2 任务清单

#### Task 5.1: 数据库迁移（0.5天）

```bash
# 生成迁移脚本
poetry run alembic revision --autogenerate -m "merge_16zzy_lexicon"

# 应用迁移
poetry run alembic upgrade head
```

**验收标准**：
- ✅ 词表数据成功导入数据库
- ✅ 版本指纹更新

#### Task 5.2: 生产部署（0.5天）

```bash
# 构建前端
cd frontend && npm run build

# 启动服务
docker-compose up -d
```

**验收标准**：
- ✅ 服务启动正常
- ✅ API 健康检查通过
- ✅ 前端管理界面可访问

#### Task 5.3: 监控与日志（1天）

**监控指标**：
1. **匹配准确率监控**
   - 每日匹配数
   - 置信度分布（exact/partial/degraded/ambiguous）
   - 未匹配率

2. **性能监控**
   - API 响应时间（P50/P95/P99）
   - 数据库查询时间
   - 缓存命中率

3. **错误监控**
   - 异常日志
   - 引擎错误率

**工具**：
- 日志：`logs/match_service.log`
- 监控脚本：`scripts/monitor_production.py`

**验收标准**：
- ✅ 监控指标正常采集
- ✅ 告警规则配置完成

---

## 交付物清单

### Phase 1 交付物
- [ ] `reports/dict_diff_analysis.csv` - 词典差异分析
- [ ] `reports/phrase_diff_analysis.csv` - 短语差异分析
- [ ] `phase1-deliverables/merged_medical_dict.csv` - 合并后医学词典
- [ ] `phase1-deliverables/merged_phrase_map.csv` - 合并后短语映射
- [ ] `phase1-deliverables/merge_report.md` - 合并报告

### Phase 2 交付物
- [ ] `tests/benchmark/16zzy_ct_27k.csv` - CT 测试数据
- [ ] `tests/benchmark/16zzy_dr_26k.csv` - DR 测试数据
- [ ] `tests/benchmark/16zzy_mr_10k.csv` - MR 测试数据
- [ ] `tests/benchmark/test_16zzy_benchmark.py` - Benchmark 测试框架
- [ ] `reports/baseline_accuracy_report.md` - 基线准确率报告

### Phase 3 交付物
- [ ] `reports/edge_cases_catalog.md` - 边界 case 目录
- [ ] `tests/edge_cases/test_16zzy_edge_cases.py` - 边界 case 测试
- [ ] `reports/coverage_report.md` - 测试覆盖率报告

### Phase 4 交付物
- [ ] `reports/mismatch_analysis.md` - 误匹配分析报告
- [ ] `reports/optimization_priorities.md` - 优化优先级清单
- [ ] `reports/final_accuracy_report.md` - 最终准确率报告

### Phase 5 交付物
- [ ] `migrations/versions/*_merge_16zzy_lexicon.py` - 数据库迁移脚本
- [ ] `docs/DEPLOYMENT_GUIDE.md` - 部署指南
- [ ] `scripts/monitor_production.py` - 监控脚本
- [ ] `reports/production_readiness_checklist.md` - 生产就绪检查清单

---

## 脚本开发清单

### Phase 1 脚本
- [ ] `scripts/phase1_analyze_dict_diff.py` - 词典差异分析
- [ ] `scripts/phase1_analyze_phrase_diff.py` - 短语差异分析
- [ ] `scripts/phase1_merge_lexicon.py` - 词表合并

### Phase 2 脚本
- [ ] `scripts/phase2_import_test_data.py` - 测试数据导入
- [ ] `scripts/phase2_run_benchmark.py` - 运行 benchmark

### Phase 3 脚本
- [ ] `scripts/phase3_extract_edge_cases.py` - 边界 case 提取
- [ ] `scripts/phase3_generate_tests.py` - 测试用例生成

### Phase 4 脚本
- [ ] `scripts/phase4_analyze_mismatches.py` - 误匹配分析
- [ ] `scripts/phase4_optimize_lexicon.py` - 词表优化

### Phase 5 脚本
- [ ] `scripts/phase5_deploy_production.sh` - 生产部署
- [ ] `scripts/monitor_production.py` - 生产监控

---

## 关键里程碑

| 里程碑 | 预计完成时间 | 验收标准 |
|--------|-------------|----------|
| **M1: 词表合并完成** | Day 2 | 词表规模达到 2,600+ 条 |
| **M2: Benchmark 建立** | Day 5 | 6.3 万条测试数据可运行 |
| **M3: 边界 Case 覆盖** | Day 8 | 200+ 条边界 case 测试通过 |
| **M4: 准确率达标** | Day 13 | F1 >= 0.95 |
| **M5: 生产就绪** | Day 15 | 服务部署完成，监控正常 |

---

## 资源需求

### 人力资源
- **算法工程师** 1 人（全职，15 天）
- **测试工程师** 1 人（支持，Phase 2-4，8 天）
- **运维工程师** 1 人（支持，Phase 5，2 天）

### 计算资源
- **开发环境**：16GB 内存，4 核 CPU
- **测试环境**：32GB 内存，8 核 CPU（运行 6.3 万条测试）
- **生产环境**：64GB 内存，16 核 CPU（按现有配置）

### 时间资源
- **总工期**：15 个工作日
- **并行任务**：Phase 1-2 可部分并行
- **缓冲时间**：预留 3 天缓冲

---

## 风险管理

### 高风险项

| 风险项 | 影响 | 概率 | 缓解措施 | 应急预案 |
|--------|------|------|----------|----------|
| 准确率低于预期 | 高 | 中 | Phase 4 预留 5 天调优 | 延长 Phase 4 到 7 天 |
| 数据格式不兼容 | 高 | 低 | Phase 2 先转换验证 | 人工清洗数据 |
| 优化引入回归 | 中 | 中 | 每次优化后回归测试 | 回滚到上一版本 |

### 中风险项

| 风险项 | 影响 | 概率 | 缓解措施 | 应急预案 |
|--------|------|------|----------|----------|
| 边界 case 提取不全 | 中 | 中 | 人工复核 README | 优先处理高频问题 |
| 测试时间过长 | 中 | 高 | 并行测试 + 采样 | 先测 10% 数据 |
| 部署问题 | 中 | 低 | 灰度发布 | 回滚到旧版本 |

---

## 成功标准

### 必要条件（Must Have）
- ✅ 词表规模达到 2,600+ 条（医学词典）
- ✅ Benchmark F1 >= 0.95
- ✅ 所有原有测试（46 个）通过
- ✅ 边界 case 通过率 >= 95%
- ✅ 服务部署成功，监控正常

### 期望条件（Should Have）
- ✅ 词表规模达到 8,000+ 条（短语映射）
- ✅ Benchmark F1 >= 0.96
- ✅ 测试覆盖率 >= 85%
- ✅ API 响应时间 P95 < 200ms

### 可选条件（Nice to Have）
- ✅ 前端管理界面支持词表在线编辑
- ✅ AI Agent 自动分析未匹配项
- ✅ 多租户支持

---

## 下一步行动

### 立即执行（本周）
1. [ ] 创建项目目录结构（`reports/`, `phase1-deliverables/`）
2. [ ] 开发 `scripts/phase1_analyze_dict_diff.py`
3. [ ] 运行词典差异分析

### 近期计划（下周）
1. [ ] 完成 Phase 1 词表合并
2. [ ] 开始 Phase 2 测试数据导入

### 长期计划（两周后）
1. [ ] 完成 Phase 2-4 准确率验证
2. [ ] 完成 Phase 5 生产部署

---

**计划制定时间**：2026-07-29
**计划负责人**：AI 算法团队
**计划审批人**：待定

---

## 附录：相关文档

- [算法对比分析报告](./ALGORITHM_COMPARISON.md)
- [项目结构说明](../PROJECT_STRUCTURE.md)
- [快速启动指南](../QUICKSTART.md)
- [CLAUDE.md 开发指南](../CLAUDE.md)

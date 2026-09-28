# ACR 4555 评价集契约

## 结论

ACR 核心评价集不是 `procedure_dictionary` 的全部 active 记录。权威集合定义为：

```sql
is_active = true AND semantic_id ~ '^PR[0-9]+$'
```

2026-08-30 核验结果为 4555 条、4555 个唯一 `semantic_id`。同表另有 1124 条 active
扩展项目，使用 `PS`、`PRG` 等前缀，不进入 ACR 4555 核心 KPI。

## 冻结资产

- `data/evaluation/acr_4555_manifest.csv`：按 `semantic_id` 排序，冻结 ID、中文名、原始模态。
- `data/evaluation/acr_4555_manifest.meta.json`：记录数据集版本、来源过滤条件、数据库迁移版本和文件 SHA-256。
- `scripts/evaluate_acr_4555.py`：默认读取冻结清单，并将实时数据库与清单逐项比对。数量、ID、名称或模态发生漂移时退出码为 2，不产生伪基线。

## 标准运行

```bash
poetry run python scripts/evaluate_acr_4555.py --snapshot /tmp/acr-4555-base.json
poetry run python scripts/evaluate_acr_4555.py --compare /tmp/acr-4555-base.json
```

快照固定记录数据集哈希、4555 总数、Git 提交和脏状态、规则指纹、Alembic 数据库版本、
总匹配结果及分模态结果。对比时数据集或结果 ID 集不一致会失败；出现任何
`matched -> unmatched` 回退时退出码为 1。

## 重新冻结治理

只有在权威评价集变更经过评审后，才运行：

```bash
poetry run python scripts/freeze_acr_4555_manifest.py --force
```

重新冻结后必须提交清单和元数据，并建立新的基线快照；不得用 `LIMIT 4555`、数据库物理 ID
范围或“当前 active 总数”替代权威 ID 集。

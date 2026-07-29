# Phase B 部署指南：match-service 数据层独立化

**前置条件**：Phase A 已完成（match_engine_v2 依赖注入解耦）

---

## B1. 独立 DB 连接池✅

**目标**：match-service 不再依赖 acrac_backend 的 `app.config.database`，拥有独立连接池配置。

**实现**：
- `src/match_service/db.py`：全局单例 `get_engine()` / `get_session_factory()`
- `src/match_service/config.py`：`DATABASE_URL` 从环境变量 `MATCH_SVC_DATABASE_URL` 读取
- 连接池参数：`pool_size=10, max_overflow=20, pool_pre_ping=True`（生产可调优）

**验证**：
```bash
cd match_service
export MATCH_SVC_DATABASE_URL="postgresql+asyncpg://postgres:password@127.0.0.1:15432/acrac_db"
python -c "from src.match_service.db import get_engine; print(get_engine().url)"
```

---

## B2. Alembic 迁移体系✅

**目标**：schema 演进可追踪、可回滚，避免 `create_all` 的静默跳过风险。

### 配置文件

- `alembic.ini`：script_location、日志、模板配置
- `migrations/env.py`：
  - `DATABASE_URL` 从 `match_service.config.get_settings()` 读取（单一来源）
  - `target_metadata = cache.models.Base.metadata`
  - `include_object` 白名单过滤（只管理 `match_cache` / `match_feedback` / `lexicon_suggestion`）
  - 支持 async engine（asyncpg）

### 关键：共用数据库的表过滤

match-service 与 acrac_backend 共用 `acrac_db`，各管理各的表：
- **backend**：`standard_check_items`、`keyword_match_rules`、`acr_standard_links` 等（~40 张）
- **match-service**：`match_cache` 三张表

`env.py` 中 `include_object` 白名单确保 autogenerate 只关心 cache 表，避免误报「removed table」或生成危险的 DROP 操作。

### 使用流程

```bash
# 首次部署：应用 baseline（空操作，只是初始化 alembic_version 表）
alembic upgrade head

# schema 变更：修改 models.py 后生成迁移
alembic revision --autogenerate -m "add match_cache.retry_count column"
# 审阅 migrations/versions/*.py，确认 DDL 符合预期
alembic upgrade head

# 回滚（开发环境）
alembic downgrade -1
```

**验证**：
```bash
# 测试 autogenerate 侦测能力（已验证通过）
# 1. 给 match_cache 加列 → 生成 op.add_column
# 2. 改 String(20) → String(50) → 生成 op.alter_column
# 3. 删列 → 生成 op.drop_column
```

---

## B3. 移除启动时 `create_all`✅

**变更前**：`main.py` lifespan 调用 `Base.metadata.create_all`（只能建新表，无法演进已有表）

**变更后**：移除 `create_all`，启动前需手动执行 `alembic upgrade head`

**理由**：
- `create_all` 对已有表的 schema 变更静默跳过（加列/改类型/加索引都不执行）
- 生产环境 schema 演进必须可追踪、可审计、可回滚，Alembic 是行业标准

**部署检查清单**：
1. 环境变量 `MATCH_SVC_DATABASE_URL` 已设置
2. 执行 `alembic upgrade head`（首次 = baseline，后续 = 应用增量迁移）
3. 启动服务：`uvicorn match_service.main:app --host 0.0.0.0 --port 9100`

---

## B4. 模态名归一 — 经核查无需改动 ❎

设计文档原假设「代码混用 petct / PET-CT / PET/CT 三种拼写需归一」，实测后该假设不成立。

**实际分布**：

| 写法 | 出现位置 | 是否模态值 |
|---|---|---|
| `_pet_ct_items` / `_pet_mr_items` | `us_spect_pet_matcher.py` Python 变量名 | ❌ 仅变量名，比较时用 `'PET/CT'` |
| `PET-CT` | LLM prompt 文本、Excel sheet 名 | ❌ 自然语言 / 外部文件契约 |
| `PET-CT` | `acr_matching_service.py:118-120` | ✅ 有意的兼容归一（同时接受两种写法）|
| `PET/CT` `PET/MR` | DB `standard_check_items.modality` | ✅ 权威值 |

**跨表差异（有意设计，非 bug）**：
- `standard_check_items.modality`：`PET/CT`、`PET/MR` 分开（各 12 项）
- `keyword_match_rules.modality`：只有 `PET`（19 条部位规则两模态共享）
- `_match_pet()` 按 `PET` 加载共享规则，按 `PET/CT`/`PET/MR` 分别筛标准项 — 正确

**行为等价性验证**（6 组对照，两种写法结果完全一致）：

| 输入 | 结果 |
|---|---|
| `PET-CT全身显像` / `PET/CT全身显像` | 均 → `* PET/CT躯干` |
| `PET-CT脑显像` / `PET/CT脑显像` | 均 → `* PET/CT局部（头部）` |
| `PET-CT心肌代谢显像` / `PET/CT心肌代谢显像` | 均 → `* PET/CT局部（心脏）` |
| `PET-MR全身` / `PET/MR全身` | 均 → `* PET/MR躯干` |

原因：`_extract_pet_body()` 用包含匹配（`kw in name`），前缀剥离是否成功都不影响部位关键词命中。

**结论**：不做改动。改 Excel sheet 名会导致读不到文件，改 prompt 文本无意义，
改变量名是纯噪声 diff。真正的模态值已统一为 `PET/CT`/`PET/MR`。

---

## B5. 词表清洗（待实施）

**Phase 0-3 发现的真实脏数据**：
1. 4 条引号损坏（`\"T\"`、`\"T管\"`）→ 按生产值修正
2. 1 条词尾 TAB 撞键（`phrase_map` 两行 `source` 相同但尾部有 `\t`）→ 去重

---

## 依赖安装

```bash
cd match_service
poetry add alembic
poetry install
```

---

## 测试验证

```bash
# 编译检查
python -m py_compile src/match_service/**/*.py

# 迁移测试（开发库）
export MATCH_SVC_DATABASE_URL="postgresql+asyncpg://postgres:password@127.0.0.1:15432/acrac_db"
alembic upgrade head
alembic downgrade base

# 服务启动（需先执行 alembic upgrade head）
uvicorn match_service.main:app --reload
curl http://127.0.0.1:9100/health
```

---

**Phase B 状态**：B1-B3 ✅，B4-B5 待用户裁定后实施

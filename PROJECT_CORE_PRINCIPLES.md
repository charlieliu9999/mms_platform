# MMS Platform 核心原则

## 唯一业务目标

把医院原始影像检查项目稳定地转换为可追溯、可版本化的标准检查项目，供
`acrac_web_mgmt` 等业务系统通过 HTTP API 调用。核心评价集是 4,555 个 ACR
检查项目；每次规则或算法优化都必须降低未匹配数量，并且不得让既有正确结果回退。

## 强制门禁

1. 修改匹配引擎、词表或标准库前后，都要在同一数据、同一版本和同一配置下运行全量 4,555 项评估。
2. 交付必须同时满足：未匹配数量不增加、各模态无回退、必需测试零失败、API 契约测试通过。
3. 评估必须记录代码提交、规则指纹、数据库迁移版本、输入数量、匹配数、未匹配数和分模态结果。
4. 生产数据库变更只能通过经过备份、演练和回滚验证的 Alembic 迁移；禁止直接修改 `alembic_version`。
5. `acrac_web_mgmt` 只消费 MMS HTTP 契约，不复制或加载 MMS 进程内匹配引擎。

## 标准调用契约

- 业务就绪：`GET /api/health`
- 规则指纹：`GET /api/rules/snapshot`
- 批量标准化：`POST /api/batch-match`
- 规则热重载：`POST /api/reload`

批量输入使用 `items[].key/name/modality`；`modality` 可以为空字符串，由 MMS 根据文本推断。
批量输出使用 `results[key].data[].standard[{code,name}]`，并携带 `confidence`、`tier`、
`effective_modality` 和顶层 `rule_version`。消费者不得把进程探针 `GET /health` 当成业务就绪证明。

## 验证命令

```bash
poetry run pytest
poetry run python scripts/evaluate_acr_4555.py
cd frontend && npx tsc --noEmit && npm run build
```

若评估脚本、4,555 项权威输入或隔离数据库不可用，任务必须标记为阻塞，不得宣称匹配优化完成。

# Phase 3 部署检查清单

## 代码变更

### 1. 分析脚本修改（不影响生产）
- ✅ `scripts/analyze_ct_mr_dr_matching.py` - 添加了模态纠正调用

### 2. 引擎预处理优化（影响生产）
- ✅ `src/match_service/engine/match_engine_v2/preprocess_service.py`
  - 添加了功能序列清理：DWI、STIR、弥散加权成像、扩散加权成像

### 3. 数据库变更（已生效）
- ✅ `nlp_phrase_map` 表 ID=672
  - 添加映射：前后位 → 正位
  - step: pre
  - version: V3.8
  - enable: 0 (启用)
  - modality: ALL

## 部署步骤

### Step 1: 验证数据库变更
```bash
poetry run python -c "
import asyncio
from match_service.db import get_engine, AsyncSession
from sqlalchemy import text

async def check():
    engine = get_engine()
    async with AsyncSession(engine) as session:
        result = await session.execute(text('''
            SELECT id, src_word, dst_word, step, version, enable
            FROM nlp_phrase_map
            WHERE id = 672
        '''))
        row = result.fetchone()
        print(f'映射配置: {row[1]} → {row[2]} | step:{row[3]} | version:{row[4]} | enable:{row[5]}')
    await engine.dispose()

asyncio.run(check())
"
```

### Step 2: 停止当前服务
```bash
./scripts/stop.sh
```

### Step 3: 启动新服务
```bash
./scripts/start.sh
```

### Step 4: 健康检查
```bash
curl http://localhost:9100/health
```

### Step 5: 运行测试套件
```bash
# 后端单元测试
poetry run pytest tests/ -v

# API功能测试
curl -X POST http://localhost:9100/api/match/one \
  -H "Content-Type: application/json" \
  -d '{"name": "X线肘关节(前后位)", "modality": "DR"}'

# 前端构建测试
cd frontend && npm run build
```

## 验证点

### 1. 体位映射验证（Phase 3B）
- [x] X线肘关节(前后位) → 应匹配成功
- [x] X线胸部(前后位，平扫) → 应匹配成功
- [x] X线腰椎(前后位) → 应匹配成功

### 2. 功能序列清理验证（Phase 3C）
- [x] MR盆腔扩散加权成像(DWI) → 应匹配成功
- [x] MR直肠(弥散加权成像) → 应匹配成功
- [x] MR眼眶(扩散加权成像DWI) → 应匹配成功

### 3. 回归测试
- [ ] 原有匹配项不应受影响
- [ ] 引擎版本指纹应更新

## 回滚计划

如果部署失败：

1. 恢复代码：
```bash
git checkout src/match_service/engine/match_engine_v2/preprocess_service.py
```

2. 禁用映射：
```sql
UPDATE nlp_phrase_map SET enable = 1 WHERE id = 672;
```

3. 重启服务：
```bash
./scripts/stop.sh && ./scripts/start.sh
```

## 预期效果

- DR匹配率：80.1% → 89.0% (+8.9%)
- MR匹配率：94.4% → 95.2% (+0.8%)
- 总匹配率：92.8% → 94.3% (+1.5%)
- 减少未匹配项：43项


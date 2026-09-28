# MMS Platform - 问题清单与修复指南

**生成时间**: 2026-08-23  
**审计基础**: rimag-official-web/docs/architecture-audit-2026-08-23.md  
**项目路径**: `/Users/charlieliu/git_project_vscode/09_medical/mms_platform`

本文档列出 MMS Platform（医学影像检查项目标准化匹配服务）中需要修复的安全、数据和部署问题。

---

## 立即修复（P0 Critical）

### C-04: 管理、缓存、重载、Agent 审批和评测接口未见认证

**当前状态**:  
`src/match_service/api/routes.py`、`admin.py`、`evaluation.py` 中的管理接口未实施认证。

**风险**:  
- 若 9100 端口可被非受信网络访问，可直接修改匹配缓存
- 可以改变规则运行状态或治理结果
- 可以触发系统重载或评测任务
- 匿名访问敏感的匹配统计和日志

**影响范围**:
- `/api/admin/*` - 管理接口
- `/api/cache/*` - 缓存管理
- `/api/evaluation/*` - 评测接口
- `/api/agent/*` - Agent 审批接口

**需要修改的文件**:
1. `src/match_service/api/routes.py` - 主路由注册
2. `src/match_service/api/admin.py` - 管理接口
3. `src/match_service/api/evaluation.py` - 评测接口
4. `src/match_service/agent/reviewer.py` - Agent 审批
5. `src/match_service/main.py` - 添加认证中间件

**修复方案**:

```python
# ✅ 方案 1: 添加 FastAPI 依赖注入认证
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_admin_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:
    """验证管理员 Token"""
    token = credentials.credentials
    # 实现 Token 验证逻辑（JWT/API Key）
    if not is_valid_admin_token(token):
        raise HTTPException(status_code=403, detail="Unauthorized")
    return {"user": "admin", "role": "admin"}

# 在所有管理接口添加依赖
@router.post("/api/admin/reload")
async def reload_engine(
    auth: dict = Depends(verify_admin_token)
):
    # 实现逻辑
    pass

# ✅ 方案 2: 基于 IP 白名单（临时方案）
ALLOWED_ADMIN_IPS = ["127.0.0.1", "::1", "内网IP段"]

@app.middleware("http")
async def admin_ip_filter(request: Request, call_next):
    if request.url.path.startswith("/api/admin"):
        client_ip = request.client.host
        if client_ip not in ALLOWED_ADMIN_IPS:
            return JSONResponse(
                status_code=403,
                content={"error": "Access denied"}
            )
    return await call_next(request)
```

**环境变量配置**:
```bash
# .env
MATCH_SVC_ADMIN_TOKEN=your-secure-random-token-here
MATCH_SVC_ALLOWED_ADMIN_IPS=127.0.0.1,::1,192.168.1.0/24

# 或使用 JWT
MATCH_SVC_JWT_SECRET=your-jwt-secret
MATCH_SVC_JWT_ALGORITHM=HS256
```

**验收标准**:
- [ ] 未认证调用所有 `/api/admin/*` 返回 401/403
- [ ] 未认证调用所有 `/api/cache/*` 写操作返回 401/403
- [ ] 未认证调用 `/api/evaluation/*` 返回 401/403
- [ ] Agent 审批接口要求认证
- [ ] 生产环境不使用默认 Token
- [ ] 添加认证相关日志和审计

**优先级**: P0 - 立即修复，如果 9100 端口暴露到非受信网络

---

## 高优先级修复（P1 High）

### H-02: 迁移链不能从空库可靠重建

**当前问题**:  
Alembic 迁移链存在问题：
1. 部分迁移依赖外部数据文件，缺失时"成功跳过"
2. 迁移可能不是幂等的
3. 从空数据库无法完整重建到 head

**风险**:  
- 部署/灾备可能得到已到 head 但缺表、缺列或缺数据的环境
- 新环境部署不可重复
- 数据迁移失败被掩盖

**影响文件**:
- `migrations/versions/*_load_finalized_lexicon.py`
- `migrations/versions/*_initial.py`
- `migrations/env.py`

**修复方案**:

```python
# ✅ 改进迁移脚本
def upgrade():
    # 1. 检查前置条件
    conn = op.get_bind()
    
    # 2. 原子性操作
    with conn.begin():
        # 创建表
        op.create_table(...)
        
        # 加载数据（嵌入或明确依赖）
        data_file = Path(__file__).parent / "data" / "lexicon.json"
        if not data_file.exists():
            raise FileNotFoundError(
                f"Required data file not found: {data_file}\n"
                f"Migration cannot proceed without lexicon data."
            )
        
        # 导入数据
        load_lexicon_data(conn, data_file)
    
    # 3. 验证结果
    result = conn.execute(text("SELECT COUNT(*) FROM medical_dict"))
    count = result.scalar()
    expected = 2435
    if count != expected:
        raise ValueError(
            f"Lexicon data incomplete: expected {expected}, got {count}"
        )

def downgrade():
    # 必须实现 downgrade
    op.drop_table("medical_dict")
```

**数据文件管理**:
```bash
# ✅ 将关键数据文件纳入版本控制
migrations/
├── versions/
│   ├── 001_initial.py
│   ├── 002_load_lexicon.py
│   └── data/
│       ├── medical_dict.json
│       ├── phrase_map.json
│       └── ambiguity_rule.json
```

**迁移验证脚本**:
```bash
#!/bin/bash
# scripts/validate-migrations.sh

set -e

echo "Testing migration chain from empty database..."

# 1. 创建临时数据库
TEST_DB="test_migration_$$"
psql -c "CREATE DATABASE $TEST_DB;"

# 2. 运行迁移
DATABASE_URL="postgresql://postgres:postgres@localhost:15432/$TEST_DB" \
  poetry run alembic upgrade head

# 3. 验证数据
poetry run python -c "
from sqlalchemy import create_engine, text
engine = create_engine('$DATABASE_URL')
with engine.connect() as conn:
    # 检查表存在
    tables = ['medical_dict', 'phrase_map', 'ambiguity_rule', 'standard_item']
    for table in tables:
        result = conn.execute(text(f'SELECT COUNT(*) FROM {table}'))
        count = result.scalar()
        print(f'{table}: {count} rows')
    
    # 检查数据完整性
    expected = {'medical_dict': 2435, 'phrase_map': 7839, 'ambiguity_rule': 1229}
    for table, count in expected.items():
        result = conn.execute(text(f'SELECT COUNT(*) FROM {table}'))
        actual = result.scalar()
        assert actual == count, f'{table}: expected {count}, got {actual}'
"

# 4. 清理
psql -c "DROP DATABASE $TEST_DB;"

echo "Migration validation passed!"
```

**验收标准**:
- [ ] 空数据库运行 `alembic upgrade head` 成功
- [ ] 所有必需表和数据正确创建
- [ ] 词表数量符合预期：medical_dict (2,435), phrase_map (7,839), ambiguity_rule (1,229)
- [ ] 标准数据正确导入（v3.8.2 + v4.0.0）
- [ ] 迁移验证脚本加入 CI
- [ ] 所有迁移实现 downgrade

---

### H-11: v4 手工导入不是幂等、原子、受迁移管理的流程

**当前问题**:  
v4.0.0 医保版标准（1,336 条）通过手工脚本导入，不受 Alembic 管理。

**风险**:  
- 重复执行或部分失败时无法保证得到准确 1,336 条版本快照
- 不同环境的 v4 数据可能不一致
- 无法回滚或验证完整性

**数据源文件**:
- `/Users/charlieliu/Desktop/01标准/09 医保版-标准/影像检查项目名称和编码V4.0.xlsx`

**需要创建的文件**:
1. 迁移脚本：`migrations/versions/xxx_load_v4_standards.py`
2. 数据文件：`migrations/versions/data/v4_standards.json`
3. 导入工具：`scripts/import-v4-standards.py`

**修复方案**:

```python
# ✅ 创建正式迁移
# migrations/versions/xxx_load_v4_standards.py

"""Load v4.0.0 standards

Revision ID: xxx
Revises: yyy
Create Date: 2026-08-23
"""

from alembic import op
import sqlalchemy as sa
from pathlib import Path
import json

def upgrade():
    conn = op.get_bind()
    
    # 1. 检查 v4 数据是否已存在
    result = conn.execute(
        sa.text("SELECT COUNT(*) FROM standard_item WHERE version = 'v4.0.0'")
    )
    existing_count = result.scalar()
    
    if existing_count > 0:
        print(f"v4.0.0 data already exists ({existing_count} items), skipping import")
        return
    
    # 2. 加载数据文件
    data_file = Path(__file__).parent / "data" / "v4_standards.json"
    if not data_file.exists():
        raise FileNotFoundError(
            f"v4 standards data not found: {data_file}\n"
            f"Please run: python scripts/import-v4-standards.py --prepare"
        )
    
    with open(data_file, 'r', encoding='utf-8') as f:
        standards = json.load(f)
    
    # 3. 原子性批量插入
    with conn.begin():
        for item in standards:
            conn.execute(
                sa.text("""
                    INSERT INTO standard_item 
                    (code, name, modality, body_part, version, created_at)
                    VALUES 
                    (:code, :name, :modality, :body_part, :version, NOW())
                """),
                {
                    'code': item['code'],
                    'name': item['name'],
                    'modality': item.get('modality'),
                    'body_part': item.get('body_part'),
                    'version': 'v4.0.0'
                }
            )
    
    # 4. 验证结果
    result = conn.execute(
        sa.text("SELECT COUNT(*) FROM standard_item WHERE version = 'v4.0.0'")
    )
    count = result.scalar()
    expected = 1336
    
    if count != expected:
        raise ValueError(
            f"v4 import incomplete: expected {expected}, got {count}"
        )
    
    print(f"Successfully imported {count} v4.0.0 standards")

def downgrade():
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM standard_item WHERE version = 'v4.0.0'")
    )
```

**数据准备脚本**:
```python
# scripts/import-v4-standards.py

import pandas as pd
import json
from pathlib import Path

def prepare_v4_data():
    """从 Excel 提取 v4 数据并生成 JSON"""
    
    excel_path = Path("/Users/charlieliu/Desktop/01标准/09 医保版-标准/影像检查项目名称和编码V4.0.xlsx")
    output_path = Path("migrations/versions/data/v4_standards.json")
    
    if not excel_path.exists():
        raise FileNotFoundError(f"Source file not found: {excel_path}")
    
    # 读取 Excel
    df = pd.read_excel(excel_path, sheet_name=0)
    
    # 数据清洗和转换
    standards = []
    for _, row in df.iterrows():
        standards.append({
            'code': str(row['编码']).strip(),
            'name': str(row['名称']).strip(),
            'modality': str(row.get('检查类别', '')).strip() or None,
            'body_part': str(row.get('检查部位', '')).strip() or None,
        })
    
    # 验证数量
    if len(standards) != 1336:
        raise ValueError(f"Expected 1336 items, got {len(standards)}")
    
    # 保存 JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(standards, f, ensure_ascii=False, indent=2)
    
    print(f"Generated {output_path} with {len(standards)} items")

if __name__ == "__main__":
    prepare_v4_data()
```

**执行流程**:
```bash
# 1. 准备数据（开发时一次性执行）
poetry run python scripts/import-v4-standards.py

# 2. 运行迁移（每次部署执行）
poetry run alembic upgrade head

# 3. 验证结果
psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db -c \
  "SELECT version, COUNT(*) FROM standard_item GROUP BY version;"
```

**验收标准**:
- [ ] v4 数据通过 Alembic 迁移管理
- [ ] 数据文件纳入版本控制
- [ ] 导入是幂等的（重复执行结果一致）
- [ ] 导入失败会回滚
- [ ] 验证导入数量为 1,336 条
- [ ] 实现 downgrade 可以完全移除 v4 数据
- [ ] 文档说明数据来源和版本

---

### H-13: 匹配 API 未拒绝不支持版本，L1 cache key 不包含请求标准版本

**当前问题**:  
1. 匹配 API 接受任意版本参数，不明确拒绝不支持的版本
2. L1 缓存键不包含标准版本，可能导致跨版本缓存污染

**风险**:  
- 未来多版本匹配可产生跨版本缓存污染
- 用户无法明确知道哪些版本可用
- v4 匹配结果可能错误地缓存为 v3

**需要修改的文件**:
1. `src/match_service/api/routes.py` - 匹配接口
2. `src/match_service/cache/` - 缓存键生成
3. `src/match_service/engine/match_engine_v2/orchestrator.py` - 版本验证

**修复方案**:

```python
# ✅ 1. 定义支持的版本
# src/match_service/config.py
SUPPORTED_STANDARD_VERSIONS = ['v3.8.2', 'v4.0.0']

def normalize_version(version: str) -> str:
    """规范化版本字符串"""
    normalized = version.lower().strip()
    if normalized in ['v3', 'v3.8.2']:
        return 'v3.8.2'
    if normalized in ['v4', 'v4.0', 'v4.0.0']:
        return 'v4.0.0'
    raise ValueError(f"Unsupported version: {version}")

# ✅ 2. 在匹配接口验证版本
# src/match_service/api/routes.py
from fastapi import HTTPException
from ..config import normalize_version, SUPPORTED_STANDARD_VERSIONS

@router.post("/api/match/one")
async def match_single(request: MatchRequest):
    try:
        version = normalize_version(request.standard_version)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": str(e),
                "supported_versions": SUPPORTED_STANDARD_VERSIONS
            }
        )
    
    # 检查版本能力
    if version == 'v4.0.0' and not is_v4_matching_enabled():
        raise HTTPException(
            status_code=501,
            detail={
                "error": "v4.0.0 matching not yet available",
                "message": "v4 standards loaded but L2 NLP engine not trained",
                "available_versions": ["v3.8.2"]
            }
        )
    
    # 继续匹配流程...

# ✅ 3. 修复缓存键生成
# src/match_service/cache/cache_manager.py
def generate_cache_key(
    input_text: str, 
    standard_version: str,
    modality: Optional[str] = None
) -> str:
    """生成包含版本的缓存键"""
    from ..config import normalize_version
    
    version = normalize_version(standard_version)
    
    components = [
        f"match",
        version,  # ✅ 包含版本
        hashlib.md5(input_text.encode()).hexdigest(),
    ]
    
    if modality:
        components.append(modality)
    
    return ":".join(components)

# ✅ 4. 添加版本能力 API
@router.get("/api/capabilities")
async def get_capabilities():
    """返回系统能力"""
    return {
        "supported_versions": SUPPORTED_STANDARD_VERSIONS,
        "matching_capabilities": {
            "v3.8.2": {
                "available": True,
                "engines": ["L1_cache", "L2_nlp", "L2_keyword", "L3_agent"]
            },
            "v4.0.0": {
                "available": False,
                "reason": "NLP engine training in progress",
                "engines": ["L1_cache", "L3_semantic_candidate"],
                "eta": "2026-09-01"
            }
        }
    }
```

**数据库索引优化**:
```sql
-- 确保缓存表包含版本字段和索引
ALTER TABLE match_cache ADD COLUMN IF NOT EXISTS standard_version VARCHAR(20);

-- 复合索引包含版本
CREATE INDEX IF NOT EXISTS idx_match_cache_version 
ON match_cache(input_text_hash, standard_version, modality);
```

**验收标准**:
- [ ] 不支持的版本返回 400 + 支持的版本列表
- [ ] v4 匹配未就绪时返回 501 + 明确说明
- [ ] 缓存键包含 `standard_version`
- [ ] 添加 `/api/capabilities` 端点
- [ ] v3 和 v4 缓存完全隔离
- [ ] 前端可以查询哪些版本可匹配

---

## 中等优先级修复（P2 Medium）

### M-08: v3 页面存在最多 3,000 条的静默截断

**当前问题**:  
`/api/open/standards/items` 可能返回截断的结果，不通知客户端。

**影响**:  
- 数据增长后列表和计数不完整
- 前端无法分页访问全部数据

**需要修改的文件**:
1. `src/match_service/api/open_portal.py`

**修复方案**:

```python
# ✅ 实现真实分页
@router.get("/api/open/standards/items")
async def list_standards(
    version: str = "v3.8.2",
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    modality: Optional[str] = None,
    body_part: Optional[str] = None,
):
    """分页查询标准项目"""
    
    # 构建查询
    query = select(StandardItem).where(
        StandardItem.version == version
    )
    
    if modality:
        query = query.where(StandardItem.modality == modality)
    if body_part:
        query = query.where(StandardItem.body_part.contains(body_part))
    
    # 计算总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # 分页查询
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
            "has_next": page * page_size < total,
            "has_prev": page > 1
        }
    }
```

**验收标准**:
- [ ] 返回真实的 `total` 计数
- [ ] 支持 `page` 和 `page_size` 参数
- [ ] 返回分页元数据（total_pages、has_next 等）
- [ ] 移除 3,000 条硬编码限制
- [ ] 更新 API 文档

---

### M-10: CORS 配置过宽

**当前问题**:  
`src/match_service/main.py` CORS 允许所有来源。

**风险**:  
- 与匿名写接口结合扩大浏览器攻击面
- 允许任意域名调用 API

**需要修改的文件**:
1. `src/match_service/main.py`

**修复方案**:

```python
# ✅ 限制 CORS 来源
from fastapi.middleware.cors import CORSMiddleware
from .config import settings

# 从环境变量读取允许的来源
ALLOWED_ORIGINS = settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS else [
    "http://localhost:3000",
    "http://localhost:3100",
    "https://rimag.example.com",  # 生产域名
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # ✅ 明确的白名单
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

**环境变量**:
```bash
# .env
MATCH_SVC_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3100,https://rimag.example.com
```

**验收标准**:
- [ ] CORS 来源从环境变量配置
- [ ] 生产环境只允许官方域名
- [ ] 开发环境允许 localhost
- [ ] 文档说明 CORS 配置方法

---

## 架构改进建议

### 数据库 Schema 所有权明确

**当前问题**:  
MMS 与 ACRAC 共享数据库，表的所有权不清晰。

**建议方案**:

```sql
-- ✅ 方案 1: 独立数据库
CREATE DATABASE mms_platform;
CREATE DATABASE acrac;

-- MMS 负责标准数据
-- ACRAC 负责规则数据

-- ✅ 方案 2: Schema 隔离
CREATE SCHEMA mms;
CREATE SCHEMA acrac;

-- MMS 表在 mms schema
CREATE TABLE mms.standard_item (...);
CREATE TABLE mms.match_cache (...);

-- ACRAC 表在 acrac schema
CREATE TABLE acrac.clinical_recommendation (...);
CREATE TABLE acrac.panel (...);
```

**迁移策略**:
1. 建立独立迁移链
2. MMS 迁移只能修改 `mms.*` 表
3. ACRAC 迁移只能修改 `acrac.*` 表
4. 跨 schema 访问通过视图或 API

---

### 匹配能力版本化

**建议新增**:
- `GET /api/capabilities` - 返回支持的版本和能力
- `GET /api/versions` - 返回所有标准版本及其状态
- `GET /api/engines/status` - 返回引擎加载状态

**响应示例**:
```json
{
  "versions": {
    "v3.8.2": {
      "status": "production",
      "item_count": 3847,
      "matching": {
        "nlp_pipeline": true,
        "keyword_matching": true,
        "l1_cache": true,
        "l3_agent": true
      },
      "modalities": ["CT", "MR", "DR", "US", "RF", ...]
    },
    "v4.0.0": {
      "status": "loaded_not_trained",
      "item_count": 1336,
      "matching": {
        "nlp_pipeline": false,
        "keyword_matching": false,
        "l1_cache": true,
        "l3_agent": true
      },
      "message": "Standards loaded, NLP training in progress"
    }
  }
}
```

---

## 修复优先级建议

### 第 1-2 天（立即）
1. C-04: 保护管理接口（如果 9100 暴露）
2. H-13: 修复缓存键版本污染

### 第 3-5 天
1. H-02: 修复迁移链可重建性
2. H-11: v4 数据导入迁移化

### 第 2 周
1. M-08: 实现真实分页
2. M-10: 限制 CORS 配置
3. 添加 `/api/capabilities` 端点

### 长期改进
1. 数据库 Schema 所有权明确
2. 匹配能力版本化 API
3. 完整的 API 契约测试

---

## 验收总清单

### 安全验收
- [ ] 未认证访问 `/api/admin/*` 返回 401/403
- [ ] 未认证访问 `/api/cache/*` 写操作返回 401/403
- [ ] 未认证访问 `/api/evaluation/*` 返回 401/403
- [ ] Agent 审批接口要求认证
- [ ] CORS 限制到明确的域名列表
- [ ] 生产环境不使用默认凭据

### 数据完整性验收
- [ ] 空库可通过 `alembic upgrade head` 完整重建
- [ ] 词表数量正确：medical_dict (2,435), phrase_map (7,839), ambiguity_rule (1,229)
- [ ] v3.8.2 标准正确导入
- [ ] v4.0.0 标准导入 1,336 条
- [ ] 所有迁移有对应的 downgrade
- [ ] 迁移验证脚本加入 CI

### 匹配能力验收
- [ ] 不支持的版本返回 400
- [ ] v4 匹配未就绪时返回 501
- [ ] 缓存键包含版本，v3/v4 完全隔离
- [ ] `/api/capabilities` 返回正确的能力信息
- [ ] 前端可以查询支持的版本

### 部署验收
- [ ] 迁移验证脚本通过
- [ ] 生产部署文档更新
- [ ] 环境变量配置说明完整

---

## 与其他项目协作

### 需要官网配合
- 官网调用 `/api/capabilities` 判断版本支持（而不是猜测）
- 标准列表请求包含 `page` 和 `page_size` 参数
- 处理 400/501 错误并显示明确提示

### 需要 ACRAC 配合
- 明确数据库 Schema 所有权
- 共享表的迁移责任分配
- 统一认证机制（JWT/Bridge Token）

---

**文档维护**: 每修复一个问题，在此文档中标记 ✅ 并记录提交 hash 和部署时间。

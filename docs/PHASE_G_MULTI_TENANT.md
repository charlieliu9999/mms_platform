# Phase G: 多租户支持（未来扩展）

## 概述

当有第二家医院/机构接入时启动。提供租户隔离、租户级词库定制、独立计费统计。

## 触发条件

- 第二家接入方确认
- 需要独立词库定制
- 需要独立计费/审计

**当前状态**: 单租户（ACRAC 内部使用），Phase G 为预留设计

---

## 架构设计

### 1. 租户模型

```sql
-- 租户表
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    tenant_code VARCHAR(32) UNIQUE NOT NULL,  -- 租户标识（如 acrac, hospital_a）
    tenant_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- 租户配置
CREATE TABLE tenant_configs (
    id SERIAL PRIMARY KEY,
    tenant_id INT REFERENCES tenants(id),
    config_key VARCHAR(50) NOT NULL,
    config_value TEXT,
    UNIQUE(tenant_id, config_key)
);
```

### 2. 词库隔离方案

**方案 A: 共享词库 + 租户补充**
- 基础词库：所有租户共享（nlp_medical_dict）
- 租户词库：tenant_medical_dict（tenant_id 外键）
- 查询时合并：`SELECT ... FROM nlp_medical_dict UNION SELECT ... FROM tenant_medical_dict WHERE tenant_id=?`

**方案 B: 完全隔离词库**
- 每个租户独立词库副本
- 存储空间大，但隔离彻底
- 适用于强监管场景

**推荐**: 方案 A（90% 词库可共享，10% 定制）

### 3. 引擎实例管理

**方案 A: 共享引擎 + 动态词库**
- 单个 MatchEngineOrchestrator 实例
- match() 时传入 tenant_id，动态加载租户词库
- 优点：资源高效
- 缺点：租户间有性能影响

**方案 B: 租户独立引擎**
- 每个租户一个 MatchEngineOrchestrator 实例
- 启动时预加载租户词库
- 优点：完全隔离，性能稳定
- 缺点：内存占用大

**推荐**: 方案 B（2-5 个租户时可行；>10 个租户改用方案 A）

### 4. API 鉴权

```python
# Header 传递租户标识
X-Tenant-ID: acrac
X-API-Key: tenant_secret_key

# 或 JWT Token
Authorization: Bearer eyJhbGc...
# Payload: {"tenant_id": "acrac", "tenant_name": "..."}
```

中间件验证：
1. 提取 tenant_id
2. 校验 API Key / JWT
3. 注入到请求上下文
4. 后续逻辑使用 tenant_id 过滤数据

---

## 实现计划

### Phase G1: 基础租户模型
- [ ] 创建 tenants / tenant_configs 表
- [ ] 实现租户注册/管理 API
- [ ] 租户级配置存储

### Phase G2: 词库隔离
- [ ] tenant_medical_dict / tenant_phrase_map / tenant_ambiguity 表
- [ ] 引擎加载逻辑改造（支持租户参数）
- [ ] 租户词库管理 UI

### Phase G3: API 鉴权
- [ ] API Key 生成与验证
- [ ] JWT 鉴权中间件
- [ ] 租户上下文注入

### Phase G4: 计费与审计
- [ ] 请求日志记录（tenant_id, request_count, timestamp）
- [ ] 按租户统计调用量
- [ ] 租户级审计日志

### Phase G5: 租户独立引擎
- [ ] EnginePool 管理器（tenant_id → MatchEngineOrchestrator）
- [ ] 租户引擎懒加载
- [ ] 内存限制与 LRU 淘汰

---

## 数据隔离示例

### 词库查询（租户 A）
```python
# 基础词库
base_dict = session.query(MedicalDict).filter(MedicalDict.enable == 0)

# 租户补充词库
tenant_dict = session.query(TenantMedicalDict).filter(
    TenantMedicalDict.tenant_id == tenant_id,
    TenantMedicalDict.enable == 0
)

# 合并
all_dict = base_dict.union(tenant_dict)
```

### 匹配请求（租户隔离）
```python
@router.post("/match")
async def match_one(req: MatchRequest, tenant_id: str = Depends(get_tenant_id)):
    # 获取租户专用引擎
    engine = engine_pool.get(tenant_id)
    
    # 匹配时使用租户词库
    result = engine.match(req.check_item, req.modality, tenant_id=tenant_id)
    
    # 记录租户调用日志
    await log_tenant_request(tenant_id, req)
    
    return result
```

---

## 计费模型

### 按调用量计费
- 基础版: ¥0.01/次（共享词库）
- 定制版: ¥0.05/次（租户词库 + 独立引擎）
- 月结算，按实际调用量

### 按租户订阅
- 基础版: ¥1,000/月（10 万次/月）
- 专业版: ¥5,000/月（50 万次/月 + 词库定制）
- 企业版: ¥20,000/月（不限次数 + 独立引擎 + 专属支持）

---

## 监控指标（租户维度）

- 调用量（QPS、日/月总量）
- 匹配率（matched / total）
- 响应时间（P50/P95/P99）
- 错误率
- 词库规模（租户补充词数）

---

## 安全与合规

### 数据隔离
- 租户 A 不能访问租户 B 的词库
- 租户 A 的匹配日志对租户 B 不可见
- API Key / JWT 严格绑定租户

### 审计日志
- 所有租户操作记录（词库修改、API 调用）
- 保留 90 天，支持查询与导出
- 符合医疗数据合规要求（HIPAA / 等保三级）

---

## 迁移路径（单租户 → 多租户）

1. **Phase G0: 预留设计**（当前阶段）
   - 文档设计
   - 数据库 schema 预留

2. **Phase G1: 软切换**（第二家接入时）
   - 创建 tenants 表，默认租户 `acrac`
   - 现有数据标记为 `tenant_id=1 (acrac)`
   - API 向后兼容（未传 tenant_id 默认 acrac）

3. **Phase G2: 租户词库**
   - 新增租户专用词表
   - 引擎支持租户参数
   - 管理 UI 租户切换

4. **Phase G3: 完全隔离**
   - 强制 API 鉴权
   - 租户独立引擎实例
   - 计费系统上线

---

## 成本估算（5 个租户场景）

### 资源需求
- 引擎内存: 500MB × 5 = 2.5GB
- 数据库存储: 基础词库 50MB + 租户补充 10MB × 5 = 100MB
- API 服务器: 8 核 16GB × 2（主备）

### 运维成本
- 云服务器: ¥2,000/月
- 数据库: ¥500/月
- 带宽: ¥300/月
- **总计**: ¥2,800/月

### 收入预期（5 个租户，专业版）
- ¥5,000/月 × 5 = ¥25,000/月
- 毛利率: (25,000 - 2,800) / 25,000 = 88.8%

---

**当前决策**: Phase G 暂不实施，待第二家接入方确认后启动。文档已就绪。

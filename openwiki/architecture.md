# 架构设计

> MMS 平台三层匹配架构与模块职责

## 总体架构

### 系统定位
MMS (Medical Match Service) 是从 `acrac_web_mgmt` 独立出来的医学影像检查项目标准化匹配服务，提供：
- **独立部署**：完整的前后端解决方案
- **三层匹配**：缓存 → 算法 → AI，逐层降级
- **API 兼容**：支持旧系统平滑迁移
- **可扩展性**：模块化设计，支持新模态和算法升级

### 三层匹配架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户请求                              │
│              "CT头部平扫" + 模态=CT                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│ L1: 映射库缓存 (match_cache)                             │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • Hash 查询: O(1)                                        │
│ • TTL: 30 天                                            │
│ • 置信度阈值: 0.8                                        │
│ • 命中率: ~70%                                          │
└────────────────────┬────────────────────────────────────┘
                     │ 未命中
                     ↓
┌─────────────────────────────────────────────────────────┐
│ L2: 算法引擎                                             │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                          │
│ ┌──────────────────────┐  ┌──────────────────────┐     │
│ │ NLP Pipeline         │  │ 关键词引擎            │     │
│ │ ──────────────────── │  │ ──────────────────── │     │
│ │ CT/MR/DR/RF/MG      │  │ US/SPECT/PET/OCT/DSA │     │
│ │                      │  │                      │     │
│ │ 1. 预处理            │  │ 1. 模态关键词提取     │     │
│ │ 2. Jieba 分词        │  │ 2. 部位关键词提取     │     │
│ │ 3. 消歧规则          │  │ 3. 组合匹配          │     │
│ │ 4. 标准查找          │  │ 4. 置信度评分        │     │
│ └──────────────────────┘  └──────────────────────┘     │
│                                                          │
│ 词表规模: 11,503 条                                      │
│ • 医学词典: 2,435                                        │
│ • 短语映射: 7,839                                        │
│ • 消歧规则: 1,229                                        │
└────────────────────┬────────────────────────────────────┘
                     │ 置信度 < 0.8
                     ↓
┌─────────────────────────────────────────────────────────┐
│ L3: AI Agent                                             │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • LLM 语义匹配 (semantic_matcher.py)                     │
│ • 未匹配项分析 (reviewer.py)                             │
│ • 词库优化建议 → 人工审批 → 词库进化                      │
│ • 异步执行，不阻塞主流程                                  │
└─────────────────────────────────────────────────────────┘
```

---

## 后端架构

### 模块分层

```
┌─────────────────────────────────────────────────────────┐
│ API Layer (FastAPI)                                      │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • /api/match           - 新版匹配 API                    │
│ • /algorithm/*         - Legacy 兼容 API                 │
│ • /api/admin/*         - 管理后台 API                    │
│ • /api/evaluation/*    - 评测系统 API                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│ Core Layer                                               │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • dispatcher.py        - 匹配调度器                      │
│ • engine_holder.py     - 引擎单例管理                    │
│ • rule_version.py      - 版本指纹计算                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│ Engine Layer                                             │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • match_engine_v2/     - NLP Pipeline (10 步处理)        │
│ • keyword/             - 关键词匹配引擎                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│ Data Layer                                               │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • PostgreSQL           - 主数据库 (词表/标准库/缓存)      │
│ • Redis (可选)         - 分布式缓存                      │
│ • SQLAlchemy 2.0       - 异步 ORM                        │
└─────────────────────────────────────────────────────────┘
```

### 关键设计模式

#### 1. 单例模式 (EngineHolder)
```python
# src/match_service/core/engine_holder.py
class EngineHolder:
    """引擎单例：应用启动时加载词表，全局共享"""
    _instance = None
    
    def __init__(self):
        self.v2_engine = None      # NLP Pipeline
        self.kw_engine = None      # 关键词引擎
        self.rule_version = None   # 版本指纹
        self.is_ready = False
    
    async def initialize(self):
        """从数据库加载词表，计算版本指纹"""
        # 加载 medical_dict, phrase_map, ambiguity
        # 计 SHA-256 指纹
        self.rule_version = compute_version(...)
        self.is_ready = True
```

**用途**：
- 避免每次请求都加载词表（2-3 秒开销）
- 全局共享，内存占用 ~50 MB
- 支持热重载：`POST /api/reload`

#### 2. 策略模式 (Dispatcher)
```python
# src/match_service/core/dispatcher.py
class MatchDispatcher:
    """匹配调度器：根据模态选择引擎"""
    
    async def match(self, text, modality, version):
        # 1. 尝试 L1 缓存
        cached = await self.cache.get(text, modality)
        if cached and cached.confidence >= 0.8:
            return cached.result
        
        # 2. 选择引擎
        if modality in ['CT', 'MR', 'DR', 'RF', 'MG']:
            result = self.v2_engine.match(text, modality, version)
        else:  # US/SPECT/PET/OCT/DSA
            result = self.kw_engine.match(text, modality)
        
        # 3. 缓存结果
        if result.confidence >= 0.8:
            await self.cache.store(text, modality, result)
        
        return result
```

**用途**：
- 统一匹配入口
- 自动选择 NLP vs 关键词引擎
- 缓存透明管理

#### 3. 责任链模式 (NLP Pipeline)
```python
# src/match_service/engine/match_engine_v2/orchestrator.py
class MatchEngineOrchestrator:
    """NLP Pipeline 编排器：10 步处理链"""
    
    def match(self, text, modality, version):
        # Step 1: 预处理（全角转半角、去空格）
        text = self.preprocess_service.preprocess(text)
        
        # Step 2: Jieba 分词（医学词典）
        tokens = self.tokenizer_service.tokenize(text)
        
        # Step 3: 消歧规则（phrase_map → ambiguity）
        resolved = self.disambiguation_service.resolve(tokens)
        
        # Step 4: 标准查找（process + body + contrast + ...）
        standards = self.lookup_service.find(resolved, modality)
        
        # Step 5-10: 扫描分类、部位提取、双侧推断、...
        return self.post_process(standards)
```

**用途**：
- 复杂逻辑分解为独立步骤
- 每步可独立测试和优化
- 支持中间状态调试

---

## 前端架构

### 组件层次

```
App.tsx (路由根节点)
│
├─ Sidebar.tsx (全局导航)
│
└─ <Routes>
   ├─ Dashboard.tsx           - 数据概览
   │  └─ StatCard, LineChart
   │
   ├─ MatchTest.tsx           - 匹配测试
   │  └─ Form, ResultTable
   │
   ├─ StandardItems.tsx       - 标准项目
   │  └─ Table, Pagination, Modal
   │
   ├─ LexiconMgmt.tsx         - 词库管理
   │  └─ Tabs, Table, EditModal
   │
   └─ UnmatchedWorkbench.tsx  - AI 建议审批
      └─ List, SuggestionCard, ApproveButton
```

### 数据流

```
┌─────────────────────────────────────────────────────────┐
│ React 组件                                               │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • useState / useEffect                                   │
│ • Ant Design 组件                                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│ Services Layer (frontend/src/services/)                  │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • matchService.ts  - 匹配 API 封装                       │
│ • adminService.ts  - 管理 API 封装                       │
│ • api.ts           - Axios 实例 (统一拦截器)             │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP Request
                     ↓
┌─────────────────────────────────────────────────────────┐
│ Backend API (localhost:9100)                             │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • /api/match                                             │
│ • /api/admin/*                                           │
└─────────────────────────────────────────────────────────┘
```

**开发代理**：
```typescript
// frontend/vite.config.ts
export default {
  server: {
    proxy: {
      '/api': 'http://localhost:9100',
      '/algorithm': 'http://localhost:9100'
    }
  }
}
```

**生产部署**：
- FastAPI 自动挂载 `frontend/dist/` 静态文件
- 访问 `http://localhost:9100/` 即可（无需独立前端服务器）

---

## 数据库架构

### 核心表关系

```
┌─────────────────────┐
│ nlp_medical_dict    │  医学词典（Jieba 分词）
│ ─────────────────── │
│ • word              │  词条
│ • type              │  类型（部位/过程/修饰）
│ • enable            │  启用状态
└─────────────────────┘
          │
          │ 1:N
          ↓
┌─────────────────────┐
│ nlp_phrase_map      │  短语映射（别名统一）
│ ─────────────────── │
│ • src_process       │  原始表达
│ • dst_process       │  标准表达
│ • modality          │  模态
└─────────────────────┘
          │
          │ 1:N
          ↓
┌─────────────────────┐
│ nlp_ambiguity       │  消歧规则（歧义消除）
│ ─────────────────── │
│ • src_process       │  歧义表达
│ • dst_process       │  消歧后表达
│ • modality          │  模态
└─────────────────────┘
          │
          ↓ 查询
┌─────────────────────┐
│ mms_standard_item   │  标准项目库
│ ─────────────────── │
│ • name              │  标准名称
│ • modality          │  模态
│ • process           │  检查过程
│ • body_part         │  部位
│ • contrast          │  对比剂
│ • version           │  版本号
└─────────────────────┘
          │
          ↓ 缓存
┌─────────────────────┐
│ match_cache         │  匹配缓存（L1）
│ ─────────────────── │
│ • text_hash         │  输入哈希
│ • modality          │  模态
│ • result_json       │  匹配结果
│ • confidence        │  置信度
│ • ttl               │  过期时间
└─────────────────────┘
          │
          ↓ 反馈
┌─────────────────────┐
│ match_feedback      │  匹配反馈（未匹配项）
│ ─────────────────── │
│ • text_hash         │  输入哈希
│ • original_text     │  原始文本
│ • status            │  状态（pending/resolved）
│ • suggested_fix     │  建议修复
└─────────────────────┘
```

### 索引策略

| 表 | 索引 | 用途 |
|---|---|---|
| `match_cache` | `(text_hash, modality)` UNIQUE | 快速查询 + 防重 |
| `match_cache` | `confidence` | 高置信度筛选 |
| `match_feedback` | `(text_hash, modality)` UNIQUE | 幂等 upsert |
| `mms_standard_item` | `(modality, version)` | 版本过滤 |
| `nlp_phrase_map` | `(src_process, modality)` | 别名查询 |

---

## 部署架构

### 开发模式
```
┌──────────────┐      ┌──────────────┐
│ Vite Dev     │      │ Uvicorn      │
│ localhost    │ ───→ │ --reload     │
│ :3100        │      │ :9100        │
└──────────────┘      └──────────────┘
                            │
                            ↓
                      ┌──────────────┐
                      │ PostgreSQL   │
                      │ Docker       │
                      │ :15432       │
                      └──────────────┘
```

### 生产模式（单机）
```
┌─────────────────────────────────────┐
│ FastAPI (Gunicorn)                  │
│ ──────────────────────────────────  │
│ • 挂载 frontend/dist/ 静态文件       │
│ • 提供 API 服务                      │
│ • 端口 9100                         │
└────────────────┬────────────────────┘
                 │
                 ↓
           ┌──────────────┐
           │ PostgreSQL   │
           │ :5432        │
           └──────────────┘
```

### 生产模式（Docker Compose）
```
┌──────────────┐
│ match-service│ (后端 + 前端)
│ :9100        │
└──────┬───────┘
       │
       ├─→ ┌──────────────┐
       │   │ postgres     │
       │   │ :5432        │
       │   └──────────────┘
       │
       └─→ ┌──────────────┐
           │ redis        │
           │ :6379        │
           └──────────────┘
```

### 灰度部署（Nginx）
```
                   ┌──────────────┐
                   │ Nginx        │
                   │ :80          │
                   └──────┬───────┘
                          │
              ┌───────────┴───────────┐
              ↓                       ↓
    ┌──────────────┐        ┌──────────────┐
    │ 旧系统       │  90%   │ MMS 新系统   │  10%
    │ :50000       │ ←────  │ :9100        │ ─────→
    └──────────────┘        └──────────────┘
    
    灰度策略:
    - 按用户 IP 哈希分流
    - 逐步调整比例: 10% → 50% → 100%
    - 监控错误率和响应时间
```

---

## 性能特征

### 匹配性能
| 场景 | 响应时间 | 吞吐量 |
|---|---|---|
| L1 缓存命中 | < 10 ms | 1000 req/s |
| L2 NLP Pipeline | 50-200 ms | 100 req/s |
| L2 关键词引擎 | 20-50 ms | 300 req/s |
| L3 Agent (异步) | 2-5 s | 不阻塞主流程 |

### 缓存命中率
- 生产环境: ~70%
- 新部署: 初期 0%，1周后达 60%+
- 缓存大小: ~17 万条，占用 ~500 MB

### 词表加载
- 首次加载: 2-3 秒
- 热重载: 2-3 秒 (阻塞所有请求)
- 内存占用: ~50 MB

---

## 扩展性

### 新增模态
1. 更新 `constants.py` 添加模态定义
2. 在 `dispatcher.py` 配置引擎路由
3. 如需 NLP：扩展 `match_engine_v2`
4. 如需关键词：扩展 `keyword/` 引擎
5. 添加词表数据（medical_dict, phrase_map）
6. 编写测试用例

### 新增 AI 能力
1. 在 `agent/` 目录添加新模块
2. 实现 `BaseMatcher` 接口
3. 在 `routes.py` 添加 API 端点
4. 配置 LLM 连接（环境变量）

### 横向扩展
- 无状态设计：可部署多实例
- 缓存共享：使用 Redis 替代 PostgreSQL 缓存
- 负载均衡：Nginx / K8s Service
- 数据库：PostgreSQL 主从复制

---

## 设计原则

1. **分层解耦**：API → Core → Engine → Data，每层可独立替换
2. **配置外置**：所有环境变量前缀 `MATCH_SVC_`，支持 `.env` 文件
3. **版本管理**：规则版本指纹确保灰度部署一致性
4. **优雅降级**：L3 Agent 失败不影响 L2 匹配
5. **可观测性**：结构化日志、健康检查、版本快照
6. **向后兼容**：Legacy API 保持旧系统接口不变

---

## 相关文档
- [工作流程](workflows.md) - 开发测试部署流程
- [匹配引擎实现](engine-implementation.md) - NLP Pipeline 详解
- [数据库设计](database-schema.md) - 表结构与迁移
- [部署方案](deployment.md) - 生产部署指南

# MMS Platform API 端点说明

## 问题分析

### VPS 测试的端点
❌ `/api/open/standards/list` - **不存在**

### 实际可用的端点

## 1. 开放门户 API (Open Portal)
**路由前缀:** `/api/open`
**文件:** `src/match_service/api/open_portal.py`

### 标准项目相关
- `GET /api/open/standards/items` - 获取标准项目列表 ✅
- `GET /api/open/standards/items/{item_id}` - 获取单个标准项目详情
- `GET /api/open/standards/stats` - 获取标准项目统计
- `GET /api/open/standards/versions` - 获取可用版本列表
- `GET /api/open/standards/filter-options` - 获取筛选选项
- `GET /api/open/standards/versions/compare` - 版本对比

### 其他端点
- `GET /api/open/stats` - 全局统计
- `GET /api/open/panels` - 获取面板数据
- `GET /api/open/topics` - 获取主题列表
- `GET /api/open/topics/{topic_id}` - 获取单个主题
- `GET /api/open/search` - 搜索
- `GET /api/open/recommendations/{semantic_id}/provenance` - 推荐溯源

## 2. 匹配 API
**路由前缀:** `/api`
**文件:** `src/match_service/api/routes.py`

- `POST /api/match/one` - 单项目匹配
- `POST /api/match/batch` - 批量匹配

## 3. 管理后台 API
**路由前缀:** `/api/admin`
**文件:** `src/match_service/api/admin.py`

- `GET /api/admin/standard-items` - 标准项目查询（带分页）
- `GET /api/admin/standard-item-stats` - 标准项目统计
- 更多管理端点...

## 4. 旧版兼容 API
**路由前缀:** `/algorithm`
**文件:** `src/match_service/api/legacy.py`

- `POST /algorithm/standardCheck/match` - 旧版匹配接口

## 5. 评测系统 API
**路由前缀:** `/api/evaluation`
**文件:** `src/match_service/api/evaluation.py`

## 缺失的端点

### ❌ 健康检查端点
当前 **不存在** 以下端点:
- `/health`
- `/api/health`
- `/healthz`

**建议:** 添加健康检查端点用于监控

## VPS 测试建议

### 测试 1: 开放门户 - 标准项目列表
```bash
curl http://localhost:9100/api/open/standards/items
```

### 测试 2: 开放门户 - 统计数据
```bash
curl http://localhost:9100/api/open/standards/stats
```

### 测试 3: 匹配接口
```bash
curl -X POST http://localhost:9100/api/match/one \
  -H "Content-Type: application/json" \
  -d '{
    "item_name": "胸部CT平扫",
    "modality": "CT"
  }'
```

### 测试 4: API 文档
```bash
# 访问 FastAPI 自动生成的文档
curl http://localhost:9100/docs
```

## 修复建议

### 1. 添加健康检查端点

在 `src/match_service/main.py` 中添加:

```python
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }
```

### 2. 添加根路径 API 信息

```python
@app.get("/api")
async def api_info():
    """API 信息"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "endpoints": {
            "docs": "/docs",
            "openapi": "/openapi.json",
            "health": "/health",
            "match": "/api/match/*",
            "admin": "/api/admin/*",
            "open": "/api/open/*"
        }
    }
```

## 路由挂载顺序

```python
# main.py 中的路由挂载顺序
1. app.include_router(router, prefix="/api")              # /api/match/*
2. app.include_router(legacy_router)                      # /algorithm/*
3. app.include_router(admin_router)                       # /api/admin/*
4. app.include_router(evaluation_router)                  # /api/evaluation/*
5. app.include_router(open_portal_router, prefix="/api")  # /api/open/*
6. app.mount("/", StaticFiles(...))                       # 前端静态文件
```

## 端口说明

- **9100** - mms_platform 后端服务
- **3100** - mms_platform 前端开发服务器（开发模式）
- **5589** - acrac_web_mgmt AI 推荐服务
- **3000** - Next.js 前端应用

## 总结

**问题原因:** 测试的端点 `/api/open/standards/list` 不存在
**正确端点:** `/api/open/standards/items`
**建议:** 添加 `/health` 端点用于监控

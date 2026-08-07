# API 参考

> MMS 平台 REST API 完整参考

## 基础信息

**Base URL**：`http://localhost:9100`

**认证**：当前版本无需认证（内网部署）

**请求头**：
```
Content-Type: application/json
Accept: application/json
```

**响应格式**：JSON

---

## 新版 API (/api/*)

### 1. 单项匹配

```http
POST /api/match
```

**请求体**：
```json
{
  "text": "CT头部平扫",
  "modality": "CT",
  "version": "V3.8.2"
}
```

**响应**：
```json
{
  "result": {
    "num_standard": 1,
    "data": [
      {
        "process": "平扫",
        "body": "头部",
        "standard": [
          {
            "id": 123,
            "name": "CT头部平扫",
            "modality": "CT",
            "acr_code": "70450"
          }
        ]
      }
    ],
    "tier": "exact",
    "confidence": 1.0
  },
  "rule_version": "v13755-761ba9a916fa"
}
```

### 2. 批量匹配

```http
POST /api/batch-match
```

**请求体**：
```json
{
  "items": [
    {"key": "1", "name": "CT头部平扫", "modality": "CT"},
    {"key": "2", "name": "MR腰椎平扫+增强", "modality": "MR"}
  ],
  "version": "V3.8.2"
}
```

**响应**：
```json
{
  "total": 2,
  "results": [
    {
      "key": "1",
      "text": "CT头部平扫",
      "modality": "CT",
      "matched": true,
      "standards": [...]
    },
    {
      "key": "2",
      "text": "MR腰椎平扫+增强",
      "modality": "MR",
      "matched": true,
      "standards": [...]
    }
  ]
}
```

### 3. 健康检查

```http
GET /api/health
```

**响应**：
```json
{
  "status": "ok",
  "rule_version": "v13755-761ba9a916fa",
  "engine_ready": true,
  "cache_stats": {
    "total_entries": 172725,
    "high_confidence_entries": 152002,
    "total_hits": 24726
  }
}
```

### 4. 规则快照

```http
GET /api/rules/snapshot
```

**响应**：
```json
{
  "rule_version": "v13755-761ba9a916fa",
  "ready": true
}
```

### 5. 热重载

```http
POST /api/reload
```

**响应**：
```json
{
  "status": "reloaded",
  "rule_version": "v13756-abc123def",
  "cache_cleared": true
}
```

### 6. 缓存统计

```http
GET /api/cache/stats
```

**响应**：
```json
{
  "total_entries": 172725,
  "high_confidence_entries": 152002,
  "total_hits": 24726,
  "hit_rate": 0.70
}
```

### 7. 清空缓存

```http
POST /api/cache/invalidate
```

**请求体**：
```json
{
  "modality": "CT"  // null 表示清空全部
}
```

**响应**：
```json
{
  "status": "invalidated",
  "count": 1234
}
```

### 8. 提交反馈

```http
POST /api/feedback
```

**请求体**：
```json
{
  "text": "头部核磁共振血管扫描",
  "modality": "MR",
  "comment": "应该匹配到 MR头部血管成像",
  "correct_result": {
    "standard_id": 456,
    "name": "MR头部血管成像"
  }
}
```

**响应**：
```json
{
  "status": "recorded"
}
```

---

## 管理后台 API (/api/admin/*)

### 1. 获取统计数据

```http
GET /api/admin/stats
```

**响应**：
```json
{
  "lexicon": {
    "medical_dict": 2435,
    "phrase_map": 7839,
    "ambiguity": 1229
  },
  "standards": {
    "total": 3000,
    "by_modality": {
      "CT": 500,
      "MR": 450,
      "DR": 800,
      "US": 600
    }
  },
  "cache": {
    "total": 172725,
    "hit_rate": 0.70
  },
  "feedback": {
    "pending": 45,
    "resolved": 120
  }
}
```

### 2. 词库查询

```http
GET /api/admin/medical-dict?page=1&page_size=20&word=头部
```

**响应**：
```json
{
  "total": 2435,
  "items": [
    {
      "id": 1,
      "word": "头部",
      "type": "body_part",
      "enable": 0
    }
  ]
}
```

### 3. 新增词条

```http
POST /api/admin/medical-dict
```

**请求体**：
```json
{
  "word": "肺动脉",
  "type": "body_part",
  "enable": 0
}
```

### 4. 更新词条

```http
PUT /api/admin/medical-dict/123
```

**请求体**：
```json
{
  "word": "肺动脉",
  "type": "body_part",
  "enable": 1
}
```

### 5. 删除词条

```http
DELETE /api/admin/medical-dict/123
```

### 6. 标准项目查询

```http
GET /api/admin/standard-items?modality=CT&page=1&page_size=20
```

**响应**：
```json
{
  "total": 500,
  "items": [
    {
      "id": 123,
      "name": "CT头部平扫",
      "modality": "CT",
      "body_part": "头部",
      "process": "平扫",
      "contrast": "without",
      "acr_code": "70450",
      "version": "V3.8.2"
    }
  ]
}
```

### 7. 未匹配项列表

```http
GET /api/admin/unmatched/list?status=pending&page=1&page_size=20
```

**响应**：
```json
{
  "total": 45,
  "items": [
    {
      "id": 1,
      "original_text": "头部核磁共振血管扫描",
      "modality": "MR",
      "status": "pending",
      "suggested_fix": null,
      "created_at": "2026-08-07T10:00:00"
    }
  ]
}
```

---

## Agent API (/api/agent/*)

### 1. 语义匹配

```http
POST /api/semantic-match
```

**请求体**：
```json
[
  {
    "text": "头部核磁共振血管扫描",
    "modality": "MR"
  }
]
```

**响应**：
```json
{
  "results": [
    {
      "text": "头部核磁共振血管扫描",
      "matched_standard": "MR头部血管成像",
      "confidence": 0.95,
      "reasoning": "根据语义理解，核磁共振血管扫描对应 MRA"
    }
  ]
}
```

### 2. 触发 Agent 审核

```http
POST /api/agent/review?limit=50
```

**响应**：
```json
{
  "analyzed": 45,
  "suggestions_generated": 12,
  "types": {
    "add_medical_dict": 5,
    "add_phrase_map": 4,
    "add_standard_item": 3
  }
}
```

### 3. 获取建议列表

```http
GET /api/agent/suggestions?limit=100
```

**响应**：
```json
{
  "total": 12,
  "suggestions": [
    {
      "id": 1,
      "type": "add_medical_dict",
      "modality": "MR",
      "content": {
        "word": "肺动脉",
        "type": "body_part"
      },
      "reason": "5个未匹配项包含此词",
      "status": "pending",
      "created_at": "2026-08-07T10:00:00"
    }
  ]
}
```

### 4. 审批建议

```http
POST /api/agent/suggestions/1/approve
```

**响应**：
```json
{
  "status": "approved",
  "applied": true,
  "message": "已添加词条：肺动脉"
}
```

---

## 评测系统 API (/api/evaluation/*)

### 1. 创建评测任务

```http
POST /api/evaluation/tasks
```

**请求体**：
```json
{
  "name": "P1+P2验证",
  "test_data": [
    {
      "text": "CT头部平扫",
      "modality": "CT",
      "expected_standard": "CT头部平扫"
    }
  ]
}
```

**响应**：
```json
{
  "id": 1,
  "name": "P1+P2验证",
  "status": "pending",
  "total_count": 100,
  "created_at": "2026-08-07T10:00:00"
}
```

### 2. 启动评测任务

```http
POST /api/evaluation/tasks/1/start
```

**响应**：
```json
{
  "status": "running",
  "started_at": "2026-08-07T10:05:00"
}
```

### 3. 获取任务详情

```http
GET /api/evaluation/tasks/1
```

**响应**：
```json
{
  "id": 1,
  "name": "P1+P2验证",
  "status": "completed",
  "total_count": 100,
  "matched_count": 85,
  "accuracy": 0.85,
  "started_at": "2026-08-07T10:05:00",
  "completed_at": "2026-08-07T10:10:00"
}
```

### 4. 获取失败列表

```http
GET /api/evaluation/tasks/1/failures?page=1&page_size=20
```

**响应**：
```json
{
  "total": 15,
  "items": [
    {
      "original_text": "膝关节正、侧位",
      "modality": "DR",
      "expected_standard": "双膝关节正、侧位",
      "actual_standard": null,
      "failure_type": "no_match",
      "confidence": 0.0
    }
  ]
}
```

### 5. 失败统计

```http
GET /api/evaluation/tasks/1/failures/stats
```

**响应**：
```json
{
  "total_failures": 15,
  "by_type": {
    "no_match": 10,
    "wrong_match": 3,
    "partial_match": 2
  },
  "by_modality": {
    "DR": 6,
    "CT": 5,
    "MR": 4
  }
}
```

---

## Legacy API (/algorithm/*)

### 1. 单项匹配（兼容旧系统）

```http
POST /algorithm/standardCheck/match
```

**请求体**：
```json
{
  "name": "CT头部平扫",
  "modality": "CT",
  "version": "V3.8.2"
}
```

**响应**（旧格式）：
```json
{
  "code": 200,
  "data": {
    "num_standard": 1,
    "rows": [
      {
        "process": "平扫",
        "body": "头部",
        "standard": [
          {
            "id": 123,
            "standard_name": "CT头部平扫",
            "modality": "CT",
            "acr_code": "70450"
          }
        ]
      }
    ]
  },
  "message": "success"
}
```

### 2. 批量匹配（兼容旧系统）

```http
POST /algorithm/standardCheck/match/batch
```

**请求体**：
```json
{
  "items": [
    {"key": "1", "name": "CT头部平扫", "modality": "CT"}
  ],
  "version": "V3.8.2"
}
```

---

## 错误响应

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "modality"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 503 Service Unavailable
```json
{
  "detail": "引擎未就绪"
}
```

### 500 Internal Server Error
```json
{
  "detail": "内部服务器错误: ..."
}
```

---

## 相关文档
- [快速入门](quickstart.md) - API 使用示例
- [架构设计](architecture.md) - API 层设计
- [源码索引](source-map.md) - API 实现位置

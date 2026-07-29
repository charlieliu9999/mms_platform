# Phase F: AI Agent 集成

## 概述

AI Agent 自动分析未匹配项目，提出词库/规则优化建议。

## 架构

```
未匹配项目 → Agent 分析 → 建议生成 → 人工审批 → 自动应用
```

## Agent 能力

### 1. 词库缺口识别
- 分析未匹配项目中的高频词
- 识别新的医学术语
- 建议添加到 nlp_medical_dict

### 2. 消歧规则优化
- 检测模糊匹配场景
- 分析上下文歧义
- 建议新增 nlp_ambiguity 规则

### 3. 短语映射增强
- 识别同义词/缩写
- 发现新的映射关系
- 建议更新 nlp_phrase_map

## 实现状态

### ✅ 已完成（Phase C1/C2）
- `agent/reviewer.py`: 基础 Agent 框架
- `agent/suggestion.py`: 建议数据模型
- API 端点:
  * POST /api/agent/analyze: 分析未匹配项目
  * GET /api/agent/suggestions: 获取待审批建议
  * POST /api/agent/suggestions/{id}/approve: 审批通过

### ⏳ 待完善
- Agent 智能分析算法（当前为规则模板）
- LLM 集成（GPT-4 / Claude）
- 批量建议审批
- 建议效果追踪

## 使用流程

### 1. 自动分析
```bash
# 定期任务：分析近 7 天未匹配项目
curl -X POST http://localhost:9100/api/agent/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "since_days": 7,
    "min_frequency": 3,
    "modality": "CT"
  }'
```

### 2. 查看建议
```bash
curl http://localhost:9100/api/agent/suggestions?status=pending
```

响应：
```json
{
  "total": 5,
  "suggestions": [
    {
      "id": 1,
      "type": "add_medical_dict",
      "modality": "CT",
      "content": {"word": "CBCT", "type": "body"},
      "reason": "高频未匹配词（出现 15 次）",
      "status": "pending"
    }
  ]
}
```

### 3. 审批通过
```bash
curl -X POST http://localhost:9100/api/agent/suggestions/1/approve
```

自动执行：
1. 插入 nlp_medical_dict
2. 更新建议状态为 approved
3. 触发引擎热重载

## Agent 配置

### 分析阈值
```python
AGENT_CONFIG = {
    "min_frequency": 3,        # 最小出现次数
    "lookback_days": 7,        # 回溯天数
    "confidence_threshold": 0.7,  # 建议置信度阈值
}
```

### LLM 集成（可选）
```python
# 环境变量
OPENAI_API_KEY=sk-...
AGENT_LLM_MODEL=gpt-4

# 启用后，Agent 会调用 LLM 生成更智能的建议
```

## 监控指标

- **建议生成率**: 每日新建议数
- **审批通过率**: approved / (approved + rejected)
- **建议有效性**: 应用后匹配率提升
- **响应时间**: 从发现缺口到审批通过的时长

## 安全性

- 所有建议需人工审批（防止自动污染词库）
- 审批操作记录日志
- 支持回滚（标记 enable=0）

## 未来扩展

### Phase F2: 高级 Agent
- 基于 LLM 的智能分析
- 多轮对话式规则优化
- A/B 测试自动评估

### Phase F3: 自动化闭环
- 低风险建议自动审批
- 效果追踪与自动回滚
- 持续学习与迭代

---

**当前状态**: Phase F 基础框架完成，待集成 LLM 智能分析

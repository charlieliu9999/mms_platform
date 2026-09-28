# Phase 7: 智能排序优化方案

## 当前问题

所有匹配结果按字母序排序（在 `standard_lookup_service.py` 的 285、317、323、329 行），导致：
- 常用项目可能排在后面
- 用户体验不佳（需要在长列表中查找）
- 无法体现实际使用偏好

## 优化目标

将排序逻辑从：
```
按字母序排序
```

优化为：
```
1. 按匹配置信度降序（exact > degraded > partial）
2. 同等置信度按使用频率降序（热门项优先）
3. 最后按字母序（保证稳定性）
```

## 技术方案

### 方案 A: 基于缓存表的隐式频率统计（推荐）

**优点**：
- 无需新增表结构
- 利用现有 `match_cache` 表的 `hit_count` 字段
- 实现简单，性能开销小

**实现步骤**：

1. **统计频率**：从 `match_cache` 表聚合使用频率
   ```sql
   SELECT result_code, SUM(hit_count) as usage_count
   FROM match_cache
   WHERE modality = :modality
   GROUP BY result_code
   ```

2. **排序逻辑**：
   ```python
   def smart_sort(results: List[Tuple[str, str]], usage_stats: Dict[str, int]) -> List[Tuple[str, str]]:
       """
       智能排序：使用频率降序 → 字母序
       
       Args:
           results: [(code, name), ...]
           usage_stats: {code: usage_count, ...}
       """
       return sorted(results, key=lambda x: (-usage_stats.get(x[0], 0), x[1]))
   ```

3. **修改位置**：
   - `standard_lookup_service.py:285` - bodies 排序
   - `standard_lookup_service.py:317` - process_vals 排序
   - `standard_lookup_service.py:323` - post_vals 排序
   - `match_node.py:273-276` - 最终结果排序（关键）

### 方案 B: 新增使用统计表（更精确但复杂）

**表结构**：
```sql
CREATE TABLE standard_item_usage (
    id SERIAL PRIMARY KEY,
    checkitem_code VARCHAR(50) NOT NULL,
    modality VARCHAR(10) NOT NULL,
    usage_count INTEGER DEFAULT 1,
    last_used TIMESTAMP DEFAULT NOW(),
    UNIQUE(checkitem_code, modality)
);
```

**优点**：
- 精确统计每个标准项的使用频率
- 可按时间窗口统计（最近7天、30天等）

**缺点**：
- 需要数据库迁移
- 需要在每次匹配后更新统计
- 性能开销较大

## 实施计划

采用 **方案 A**：

1. ✅ 分析问题（已完成）
2. ⏳ 实现智能排序函数
3. ⏳ 修改 `match_node.py` 的 `standard()` 方法
4. ⏳ 从缓存表加载使用统计
5. ⏳ 测试验证

## 预期效果

- **用户体验提升**：常用项目优先展示
- **降低选择成本**：减少在长列表中查找的时间
- **体现真实偏好**：反映实际临床使用习惯

## 备注

- 初期使用统计数据可能不足，逐步积累后效果更明显
- 保留字母序作为最后排序依据，保证稳定性
- 未来可考虑引入地域/医院维度的个性化排序

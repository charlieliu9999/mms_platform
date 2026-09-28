# 版本号大小写不敏感处理

## 问题背景

### 原始问题
用户在前端选择版本号时，可能会传入不同大小写格式：
- 前端传入大写: `V3.8.2`, `V4.0.0`
- 前端传入小写: `v3.8.2`, `v4.0.0`

而数据库中存储的版本号格式是固定的小写：
```sql
SELECT DISTINCT version FROM standard_check_items;
-- 结果:
-- v1.0-imported
-- v2.0
-- v3.8.2
-- v4.0.0
```

### 导致的问题
当前端传入大写版本号（如 `V3.8.2`）时：
- SQL 查询: `WHERE version = 'V3.8.2'`
- 数据库实际值: `v3.8.2`
- 结果: **无法匹配，返回空结果**

## 解决方案：后端统一标准化

### 方案选择
采用**方案 1：后端 API 统一处理（推荐）⭐⭐⭐⭐⭐**

在所有 API 端点中统一将版本号转换为小写，确保与数据库格式一致。

### 实现细节

#### 1. 标准化函数

在 `open_portal.py` 和 `admin.py` 中添加统一的版本号标准化函数：

```python
def _normalize_version(version: Optional[str]) -> Optional[str]:
    """统一版本号格式为小写

    将前端传入的版本号统一转为小写，解决数据库大小写不一致问题。
    数据库中存储的版本号是小写格式（v3.8.2, v4.0.0）

    例如: V3.8.2 -> v3.8.2, V4.0.0 -> v4.0.0

    Args:
        version: 原始版本号（可能为 None 或任意大小写）

    Returns:
        小写版本号或 None
    """
    if version and version.strip():
        return version.lower()
    return None
```

#### 2. 应用到所有相关端点

**开放门户 API (`open_portal.py`):**
- `GET /api/open/standards/items` - 标准项目列表
- `GET /api/open/standards/filter-options` - 筛选选项

**管理后台 API (`admin.py`):**
- `GET /api/admin/standard-items` - 标准项目查询
- `GET /api/admin/standard-items/stats` - 统计数据

**使用方式:**
```python
async def get_standard_items(
    version: Optional[str] = None,
    # ... 其他参数
):
    # 统一版本号格式为小写
    version = _normalize_version(version)
    
    # 然后执行查询
    if version:
        where_clauses.append("version = :version")
        params["version"] = version
```

## 测试验证

### 单元测试

```python
from match_service.api.open_portal import _normalize_version

# 测试用例
assert _normalize_version("v3.8.2") == "v3.8.2"  # 小写保持不变
assert _normalize_version("V3.8.2") == "v3.8.2"  # 大写转小写
assert _normalize_version("V4.0.0") == "v4.0.0"  # 大写转小写
assert _normalize_version(None) == None           # None 保持不变
assert _normalize_version("") == None             # 空字符串转 None
assert _normalize_version("  ") == None           # 空白转 None
```

### 集成测试

使用测试脚本 `scripts/test_version_case_insensitive.sh`:

```bash
# 本地测试
./scripts/test_version_case_insensitive.sh

# VPS 测试
./scripts/test_version_case_insensitive.sh http://your-vps:9100
```

### 测试结果

| 端点 | v3.8.2 (小写) | V3.8.2 (大写) | 结果 |
|------|---------------|---------------|------|
| `/api/open/standards/items` | 1984 条 | 1984 条 | ✅ 一致 |
| `/api/open/standards/stats` | 3352 条 | 3352 条 | ✅ 一致 |
| `/api/admin/standard-items` | 1984 条 | 1984 条 | ✅ 一致 |
| `/api/admin/standard-items/stats` | 1984 条 | 1984 条 | ✅ 一致 |

## 方案对比

### ✅ 方案 1：后端 API 统一处理（已采用）

**优点:**
- ✅ 前端无需修改
- ✅ 所有客户端（Web、移动端、第三方）都自动受益
- ✅ 根本解决问题，不会遗漏
- ✅ 统一规范化逻辑
- ✅ 易于维护和测试

**缺点:**
- 需要修改多个后端端点（已完成）

**代码改动:**
- 2 个文件
- 约 60 行新增代码
- 4 个端点应用

### ❌ 方案 2：前端处理

**优点:**
- 后端无需修改

**缺点:**
- ❌ 需要修改所有调用版本号参数的前端代码
- ❌ 容易遗漏某些调用点
- ❌ 移动端、第三方客户端也需要同步修改
- ❌ 问题分散，难以统一管理

### ❌ 方案 3：数据库 SQL 大小写不敏感查询

使用 `LOWER(version) = LOWER(:version)` 或 `ILIKE`

**优点:**
- 查询时不区分大小写

**缺点:**
- ❌ 每个查询都需要修改
- ❌ 无法使用索引，性能下降
- ❌ 代码分散，难以维护

### ❌ 方案 4：修改数据库版本号为大写

**优点:**
- 数据统一为大写

**缺点:**
- ❌ 需要数据迁移
- ❌ 可能影响现有的其他系统
- ❌ 历史数据需要更新
- ❌ 风险较大

## 实施影响

### 前端影响
- ✅ **无需任何修改**
- ✅ 现有代码继续正常工作
- ✅ 传入大写或小写都能正确查询

### 后端影响
- ✅ 逻辑集中在标准化函数
- ✅ 易于测试和维护
- ✅ 性能无影响（字符串转小写是 O(n) 操作，n 为版本号长度）

### 数据库影响
- ✅ **无需任何修改**
- ✅ 继续使用现有索引
- ✅ 查询性能不变

## 最佳实践建议

### 1. 新增端点规范
以后新增使用 `version` 参数的端点时，记得应用标准化：

```python
async def new_endpoint(
    version: Optional[str] = None,
    # ...
):
    # 第一步：标准化版本号
    version = _normalize_version(version)
    
    # 第二步：构建查询
    if version:
        # ...
```

### 2. 代码审查检查点
在代码审查时，检查所有使用 `version` 参数的端点是否应用了标准化。

### 3. 测试覆盖
为所有版本号相关的端点添加大小写测试用例。

### 4. 文档说明
在 API 文档中明确说明：
> 版本号参数大小写不敏感，推荐使用小写格式（如 v3.8.2）

## 故障排查

### 问题：版本号查询仍然返回空结果

**排查步骤:**

1. **确认数据库中的版本号格式**
   ```sql
   SELECT DISTINCT version FROM standard_check_items;
   ```

2. **确认 API 是否应用了标准化**
   ```python
   # 在端点入口添加日志
   logger.info(f"原始 version: {version}")
   version = _normalize_version(version)
   logger.info(f"标准化后 version: {version}")
   ```

3. **测试标准化函数**
   ```bash
   cd src
   python -c "from match_service.api.open_portal import _normalize_version; print(_normalize_version('V3.8.2'))"
   # 应该输出: v3.8.2
   ```

4. **验证 SQL 查询**
   ```sql
   -- 手动测试查询
   SELECT COUNT(*) FROM standard_check_items WHERE version = 'v3.8.2';
   ```

## 总结

通过在后端 API 统一标准化版本号格式：
- ✅ 彻底解决了版本号大小写问题
- ✅ 前端无需任何修改
- ✅ 所有客户端自动受益
- ✅ 代码集中易维护
- ✅ 性能无影响

这是最佳的解决方案，推荐在其他类似场景中也采用这种模式。

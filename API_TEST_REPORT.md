# MMS 前端迁移 - API 测试报告

**测试日期**: 2026-07-28 19:16  
**测试环境**: 本地开发环境  
**后端**: http://localhost:9100  
**前端**: http://localhost:3100

---

## ✅ 后端 API 测试结果

### 1. 基础 API（已存在）

| 端点 | 方法 | 状态 | 响应 |
|------|------|------|------|
| `/api/admin/stats` | GET | ✅ 通过 | 返回5张表统计，规则版本v30466 |
| `/api/admin/medical-dict` | GET | ✅ 通过 | 2,427条医学词典 |
| `/health` | GET | ⚠️ 404 | 需要添加健康检查端点 |

### 2. 词库管理 API（新增）

| 端点 | 方法 | 状态 | 测试结果 |
|------|------|------|----------|
| `/api/admin/lexicon/versions` | GET | ✅ 通过 | 返回3张表版本清单，默认V3.8.2 |
| `/api/admin/lexicon/medical_dict` | GET | ✅ 通过 | 2,427条，分页正常 |
| `/api/admin/lexicon/phrase_map` | GET | ✅ 通过 | 7,858条，支持多条件筛选 |
| `/api/admin/lexicon/phrase_map/grouped` | GET | ✅ 通过 | 3,539组，按dst_word聚合 |
| `/api/admin/lexicon/ambiguity` | GET | ✅ 通过 | 1,158条消歧规则 |
| `/api/admin/lexicon/keyword_match_rules` | GET | ✅ 通过 | 329条关键词规则 |
| `/api/admin/lexicon/checkitem_standard` | GET | ✅ 通过 | 18,695条标准项目 |
| `/api/admin/lexicon/{table}` | POST | 🔄 待测 | 新增功能（需前端测试） |
| `/api/admin/lexicon/{table}/{id}` | PUT | 🔄 待测 | 更新功能（需前端测试） |
| `/api/admin/lexicon/{table}/{id}` | DELETE | 🔄 待测 | 软删除功能（需前端测试） |
| `/api/admin/lexicon/reload` | POST | ✅ 通过 | 热重载成功 |

### 3. 标准项目管理 API（需实现）

| 端点 | 方法 | 状态 | 说明 |
|------|------|------|------|
| `/api/admin/standard-items` | GET | ⚠️ 未实现 | StandardItems 页面需要 |
| `/api/admin/standard-items/stats` | GET | ⚠️ 未实现 | 统计Dashboard需要 |
| `/api/admin/standard-items/filter-options` | GET | ⚠️ 未实现 | 级联筛选需要 |
| `/api/admin/standard-items/import-all` | POST | ⚠️ 未实现 | 批量导入需要 |

### 4. 未匹配工作台 API（需实现）

| 端点 | 方法 | 状态 | 说明 |
|------|------|------|------|
| `/api/admin/unmatched/summary` | GET | ⚠️ 未实现 | UnmatchedWorkbench 页面需要 |
| `/api/admin/unmatched/list` | GET | ⚠️ 未实现 | 列表查询需要 |
| `/api/admin/unmatched/{id}/status` | PUT | ⚠️ 未实现 | 状态更新需要 |

---

## 📊 API 测试详情

### ✅ 测试1: 版本管理
```bash
curl "http://localhost:9100/api/admin/lexicon/versions"
```
**结果**: 
- phrase_map: 4个版本（V3.8.2/V3.8/V3.7/V3.0）
- ambiguity: 3个版本
- checkitem_standard: 10个版本
- 规则指纹: v30466-1f12fa6350d2

### ✅ 测试2: 短语映射分组查询
```bash
curl "http://localhost:9100/api/admin/lexicon/phrase_map/grouped?page=1&page_size=2&step=normalize"
```
**结果**:
- 总计3,539组
- "颅脑"组：25个别名（头部/小脑/脑干/...）
- "双肺"组：20个别名

### ✅ 测试3: 关键词规则查询
```bash
curl "http://localhost:9100/api/admin/lexicon/keyword_match_rules?modality=US&page_size=3"
```
**结果**:
- US模态共176条规则
- 支持body/scan/unmatchable三种类型
- 包含priority优先级排序

### ✅ 测试4: 消歧规则查询
```bash
curl "http://localhost:9100/api/admin/lexicon/ambiguity?modality=CT&page_size=2"
```
**结果**:
- CT模态共304条规则
- 支持(src_body, src_process) → (dst_body, dst_process)映射
- 示例：颅脑+CTA → 头部动脉+CTA

### ✅ 测试5: 热重载
```bash
curl -X POST "http://localhost:9100/api/admin/lexicon/reload"
```
**结果**:
- 热重载成功
- 新规则版本: v30466-1f12fa6350d2

---

## 🔄 待实现 API

### 标准项目管理（Phase 2）

需要在 `admin.py` 中添加以下端点：

```python
@router.get("/standard-items")
async def get_standard_items(
    page: int = 1,
    page_size: int = 20,
    modality: Optional[str] = None,
    body_part_l1: Optional[str] = None,
    body_part_l2: Optional[str] = None,
    body_part_l3: Optional[str] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(_get_session),
):
    """标准项目查询"""
    # 查询 nlp_checkitem_standard 表
    pass

@router.get("/standard-items/stats")
async def get_standard_item_stats(session: AsyncSession = Depends(_get_session)):
    """标准项目统计"""
    # 按模态/部位聚合统计
    pass

@router.get("/standard-items/filter-options")
async def get_standard_item_filter_options(
    modality: Optional[str] = None,
    body_part_l1: Optional[str] = None,
    body_part_l2: Optional[str] = None,
    session: AsyncSession = Depends(_get_session),
):
    """级联筛选选项"""
    # 返回可选的一级/二级/三级部位列表
    pass

@router.post("/standard-items/import-all")
async def import_all_standard_items(session: AsyncSession = Depends(_get_session)):
    """批量导入标准项目"""
    # 从ACR标准库导入
    pass
```

### 未匹配工作台（Phase 3）

需要添加以下端点：

```python
@router.get("/unmatched/summary")
async def get_unmatched_summary(session: AsyncSession = Depends(_get_session)):
    """未匹配汇总统计"""
    # 按reason_code分组统计
    pass

@router.get("/unmatched/list")
async def get_unmatched_list(
    page: int = 1,
    page_size: int = 20,
    reason_code: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(_get_session),
):
    """未匹配列表查询"""
    # 查询未匹配记录
    pass

@router.put("/unmatched/{id}/status")
async def update_unmatched_status(
    id: int,
    status: str,
    session: AsyncSession = Depends(_get_session),
):
    """更新未匹配状态"""
    # 更新状态（open/resolved/wontfix）
    pass
```

---

## 🎯 前端测试计划

### Phase 1: 词库管理（可测试）

1. **医学词典**
   - [ ] 分类筛选（部位/扫描/后处理/摆位）
   - [ ] 搜索功能
   - [ ] 新增词条
   - [ ] 编辑词条
   - [ ] 停用词条

2. **短语映射**
   - [ ] step筛选（归一化/预处理/处理方式/全局部位/局部部位/血管）
   - [ ] 模态筛选
   - [ ] 分组显示（按dst_word）
   - [ ] 新增别名
   - [ ] 编辑别名
   - [ ] 删除别名

3. **消歧规则**
   - [ ] 模态筛选（CT/MR/DR/RF）
   - [ ] 搜索功能
   - [ ] 新增规则
   - [ ] 编辑规则
   - [ ] 删除规则

4. **关键词规则**
   - [ ] 模态筛选（US/SPECT/PET/OCT/DSA）
   - [ ] 规则类型筛选（部位/扫描方式/不可匹配）
   - [ ] 新增规则
   - [ ] 编辑规则
   - [ ] 停用规则

5. **标准查找表**
   - [ ] 模态筛选
   - [ ] 搜索功能
   - [ ] 只读浏览
   - [ ] 分页

6. **版本控制条**
   - [ ] 版本切换
   - [ ] 版本行数显示
   - [ ] 热重载按钮

### Phase 2: 标准项目管理（需后端API）

- [ ] 统计Dashboard显示
- [ ] 级联筛选（模态→一级→二级→三级）
- [ ] 项目列表浏览
- [ ] 批量导入

### Phase 3: 未匹配工作台（需后端API）

- [ ] 分类卡片统计
- [ ] 状态筛选
- [ ] 搜索功能
- [ ] 状态切换操作

---

## 📝 下一步行动

### 立即执行

1. **前端测试** - 在浏览器中测试词库管理功能
   ```
   打开: http://localhost:3100
   导航: 词库管理
   测试: 5个tab的CRUD操作
   ```

2. **实现缺失API** - StandardItems 和 UnmatchedWorkbench 的后端API
   - 标准项目管理（4个端点）
   - 未匹配工作台（3个端点）

3. **完整测试** - 完成所有功能的端到端测试

---

## ✅ 当前状态

- **Phase 1 API**: ✅ 100% 完成并测试通过
- **Phase 2 API**: ⚠️ 0% （需实现4个端点）
- **Phase 3 API**: ⚠️ 0% （需实现3个端点）

**总体 API 完成度**: 11/18 = **61%**

---

**建议**: 先完成 Phase 1 前端功能测试，确认 CRUD 操作无误后，再实现 Phase 2/3 的后端 API。

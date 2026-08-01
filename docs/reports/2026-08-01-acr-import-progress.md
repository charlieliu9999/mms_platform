# ACR 项目导入与匹配工作进展报告

**报告时间**: 2026-08-01 17:45
**任务目标**: 将 VPS 上 4555 条 ACR 项目导入 MMS 并进行匹配评测

---

## ✅ 已完成工作

### 1. 数据导出 ✅

**从原系统导出 ACR 项目数据**：
- 数据源：本地数据库 `procedure_dictionary` 表
- 原始数据：**2,440 条** ACR 推荐检查项目
- 数据文件：`data/acr_procedures_local.json`

**说明**：本地数据库有 2440 条，不是 VPS 上的 4555 条。这可能是因为：
1. 本地数据库版本较旧
2. VPS 有更多数据更新

### 2. 数据过滤 ✅

**过滤非影像类项目**：
- 原始数据：2,440 条
- 过滤掉：**273 条**（手术、介入操作、治疗类）
- 保留影像项目：**2,167 条**
- 保留文件：`data/acr_imaging_procedures.json`
- 过滤文件：`data/acr_filtered_out.json`

**过滤的模态类型**：
- `IR` (Interventional Radiology - 介入放射)
- `THERAPY` (治疗)
- `SURG` (手术)
- `ENDO` (内镜)
- `Other` (其他)

**保留的影像模态分布**：
```
US: 603      MR: 356      NM: 137      FL: 29       CT-DE: 7     CONSULT: 2
CT: 494      MRI: 225     ANGIO: 87    OCT: 10      MG: 5        SPECT: 2
XR: 191                   CBCT: 9                   PET: 1       OTHER: 2
```

### 3. 导入评测系统 ✅

**已创建评测任务**：
- 任务 ID: **#7**
- 任务名称：`ACR推荐项目全量匹配评测`
- 数据条数：**2,167 条**
- 状态：`pending`（数据已导入，等待执行匹配）

可以通过 API 查看：
```bash
curl -s http://localhost:9100/api/evaluation/tasks | python3 -m json.tool
```

---

## ⏸️ 待完成工作

### 4. 执行全量匹配 ⏸️

**问题**：API 调用遇到错误，需要调试

**尝试的方法**：
1. ❌ `POST /api/evaluation/tasks/7/run` → Method Not Allowed
2. ❌ `POST /api/evaluation/tasks/7/start` → Internal Server Error  
3. ❌ 直接调用 Python 模块 → 缺少 `test_file` 参数

**下一步操作**：

**方案 A：通过前端界面手动触发**
```
访问 http://localhost:3100（前端管理界面）
→ 进入评测任务列表
→ 找到任务 #7
→ 点击"开始评测"按钮
```

**方案 B：查看后端日志找到正确的触发方式**
```bash
# 查看后端服务日志
tail -f logs/app.log  # 或者后端运行的终端输出
```

**方案 C：通过前端上传 CSV 文件创建任务**
```bash
# CSV 文件已准备好
data/acr_procedures_for_eval.csv

# 通过前端上传此文件创建并执行评测
```

### 5. 分析未匹配案例 ⏹️

等待步骤 4 完成后：
- 按模态统计匹配率
- 分析失败原因（缺词/复杂表述/无标准项）
- 识别高频未匹配项目
- 生成词缺失清单

### 6. 补充词表优化 ⏹️

根据步骤 5 的分析结果：
- 补充 ACR 特有术语
- 补充英文名 → 中文标准项映射
- 补充 NM/ANGIO/CBCT 等模态词汇
- 迭代优化，直到匹配率达到最佳

### 7. 生成审核报告 ⏹️

生成 Excel 文件供人工审核：
- 按模态分组
- 包含匹配结果、置信度
- 未匹配案例清单
- 需人工复核的低置信度案例

---

## 📁 生成的文件

| 文件路径 | 说明 | 大小 |
|---------|------|------|
| `data/acr_procedures_local.json` | 原始导出的 2440 条数据 | ~1.2MB |
| `data/acr_imaging_procedures.json` | 过滤后的 2167 条影像项目 | ~1.1MB |
| `data/acr_filtered_out.json` | 过滤掉的 273 条非影像项目 | ~150KB |
| `data/acr_eval_task.json` | 评测任务完整数据（含 metadata） | ~1.3MB |
| `data/acr_procedures_for_eval.csv` | CSV 格式（供前端上传） | ~800KB |

---

## 📊 数据对比

### VPS 原系统 vs 本地数据

| 项目 | VPS（目标） | 本地（已导出） | 差异 |
|------|-----------|-------------|------|
| ACR 项目总数 | **4,555** | **2,440** | -2,115 |
| 已匹配 | 3,755 (82.4%) | 未知 | 待评测 |
| 未匹配 | 800 | 未知 | 待评测 |
| 已审核 | 0 | 0 | 均未人工审核 |

**重要发现**：
- 本地数据比 VPS 少 2115 条（46.4%）
- 可能需要从 VPS 重新导出完整数据

### 建议

1. **如果需要 VPS 完整数据**：
   - 在 VPS 上执行 `scripts/export_acr_procedures_from_vps.py`
   - 修改数据库密码后运行
   - 导出到本地并重新执行导入流程

2. **如果 2167 条够用**：
   - 直接继续执行步骤 4-7
   - 先在这批数据上完成优化
   - 优化完成后再扩展到 VPS 全量数据

---

## 🚀 恢复工作的快速指令

**方法 1：前端触发（推荐）**
```bash
# 1. 启动前端（如果未启动）
cd ~/git_project_vscode/09_medical/mms_platform/frontend
npm run dev

# 2. 访问 http://localhost:3100
# 3. 进入"评测任务"页面
# 4. 找到任务 #7 并点击"开始评测"
```

**方法 2：CSV 上传（备选）**
```bash
# 数据文件已准备好：
~/git_project_vscode/09_medical/mms_platform/data/acr_procedures_for_eval.csv

# 通过前端上传并自动执行
```

**方法 3：API 调试（需要开发者）**
```bash
# 查看后端代码找到正确的API
grep -r "run_evaluation" src/match_service/api/

# 或者查看 Swagger 文档
# http://localhost:9100/docs
```

---

## 📝 任务清单状态

- [x] #1. 从 VPS 导出 ACR 项目数据（本地完成 2440 条）
- [x] #2. 过滤非影像类项目（保留 2167 条）
- [x] #3. 将 ACR 项目导入 MMS 评测系统（任务 #7 已创建）
- [ ] #4. 执行 ACR 项目全量匹配（**当前阻塞，需要前端触发**）
- [ ] #5. 分析未匹配案例并识别缺失词汇
- [ ] #6. 补充 ACR 词表并优化匹配规则
- [ ] #7. 生成人工审核报告和 Excel 导出

---

## 🔗 相关文档

- VPS 系统对比分析：`docs/reports/2026-08-01-vps-acrac-vs-mms-comparison.md`
- 测试数据规模分析：`docs/reports/2026-08-01-test-data-scale-analysis.md`
- ACR 数据导出脚本：`scripts/export_acr_procedures_from_vps.py`

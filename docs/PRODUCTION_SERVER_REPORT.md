# 生产服务器检查项目匹配算法部署情况报告

> 服务器: 10.101.1.178:22
> 
> 用户: rimagai
> 
> 调研时间: 2026-07-29
> 
> 服务名称: examine-standard (16_zzy 项目)

---

## 一、服务概况

### 1.1 基本信息

| 项目 | 信息 |
|------|------|
| **服务路径** | `/home/rimagai/zzy/examine-standard/` |
| **服务进程** | `python match_service.py --env online --port 50000` |
| **进程ID** | 155921 |
| **启动时间** | 2026-04-24 |
| **运行时长** | 96天01小时14分钟 ✅ |
| **监听端口** | 50000 (TCP, 0.0.0.0) |
| **框架** | Flask + Tornado (WSGI) |
| **Python环境** | pyenv venv-prod (Python 3.10.13) |
| **启动方式** | nohup 后台运行 |

### 1.2 服务状态

```bash
# 进程运行正常
rimagai   155921  1.3  0.1 1796060 259932 ?  Sl  Apr24 1853:29 python match_service.py

# 端口监听正常
tcp  0.0.0.0:50000  LISTEN  155921/python
tcp6 :::50000       LISTEN  155921/python
```

**结论**: ✅ 服务运行稳定（已连续运行 96 天）

---

## 二、API 端点

### 2.1 主要 API

| 端点 | 方法 | 功能 | 路径 |
|------|------|------|------|
| `/algorithm/standardCheck/match` | POST | **匹配检查项目** | match_service.py:24 |
| `/algorithm/standardCheck/update_table` | POST | 更新词表 | match_service.py:62 |
| `/algorithm/standardCheck/query_rule` | POST/GET | 查询规则 | match_service.py:91 |
| `/algorithm/standardCheck/modify_phrase_map` | POST/GET | 修改短语映射 | match_service.py:124 |
| `/algorithm/standardCheck/modify_rule_map` | POST/GET | 修改消歧规则 | match_service.py:174 |
| `/algorithm/standardCheck/run_batch` | POST | 批量匹配 | match_service.py:227 |
| `/audio-message` | POST | 音频消息（？） | match_service.py:330 |

### 2.2 API 测试

**测试请求**:
```bash
curl -X POST http://10.101.1.178:50000/algorithm/standardCheck/match \
  -H 'Content-Type: application/json' \
  -d '{
    "request_id": "test_001",
    "version": "V3.8",
    "data": [{
      "modality": "CT",
      "check_item": "胸部CT平扫",
      "md5": "test"
    }]
  }'
```

**测试结果**:
```json
{
  "code": 0,
  "msg": "success",
  "data": [{
    "data": [{
      "subitem": "胸部CT平扫",
      "standard": [{
        "modality": "CT",
        "std_check_name": "* CT胸部(平扫)",
        "std_check_code": "20040100110000",
        "version": "V3.8"
      }]
    }],
    "debug": {
      "op": [],
      "1-preprocess": "胸部CT平扫",
      "2-split": ["CT_胸部CT平扫"],
      "3-make_tree": ["胸部CT平扫: 胸部_CT_平扫, body_other_scan, 胸部_CT_平扫"],
      "5-merge_no_body": ["胸部CT平扫: 胸部_CT_平扫, body_other_scan, 胸部_CT_平扫"]
    },
    "md5": "test",
    "modality": "CT"
  }]
}
```

**结论**: ✅ API 响应正常，匹配功能工作正常

---

## 三、数据配置

### 3.1 词表规模

| 词表类型 | 文件路径 | 数量 | 对比 MMS |
|---------|----------|------|----------|
| **医学词典** | `data/tbl_medical_dict.csv` | **2,071 条** | MMS: 2,435 条 (+17.6%) |
| **短语映射** | `data/tbl_phrase_map.csv` | **1,594 条** | MMS: 7,839 条 (+391%) |
| **消歧规则** | `data/tbl_ambiguity.csv` | **51 条** | MMS: 1,229 条 (+2309%) |
| **总计** | - | **3,716 条** | MMS: 11,503 条 (+209%) |

**结论**: ⚠️ 服务器词表规模显著小于 MMS Platform（仅为 MMS 的 32%）

### 3.2 数据库配置

**环境**: `online`

```python
'online': {
    'db': 'mysql+pymysql://data:rimag123456@210.12.11.251:26306/rimag_data',
    'port': 50000,
    'commit_batch_result_api': 'http://datacenter.rimag.com.cn:80/adm.php/...'
}
```

**数据库表**:
- `s_standard_exam_rule_nlp` - 匹配结果表
- `s_standard_exam_rule_nlp_back` - 备份表
- `dim_standard_exam` - 标准检查项目维度表

---

## 四、算法架构

### 4.1 支持的模态

通过查看 `core/` 目录，服务支持以下模态：

| 模态 | 引擎文件 | 说明 |
|------|----------|------|
| **CT** | `match_ct.py` | CT 匹配引擎 |
| **MR** | `match_mr.py` | MR 匹配引擎 |
| **DR** | `match_dr.py` | DR 匹配引擎 |
| **RF** | `match_rf.py` | RF（透视）引擎 |
| **MG** | `match_mg.py` | MG（乳腺摄影）引擎 |
| **US** | `match_us.py` | US（超声）引擎 |
| **PET/CT** | `match_petct.py` | PET/CT 引擎 |
| **PET/MR** | `match_petmr.py` | PET/MR 引擎 |
| **SPECT** | `match_spect.py` | SPECT 引擎 |

**总计**: 支持 **9 种模态**

### 4.2 算法版本

- **代码版本**: V2.4（`core/match_base.py:25`）
- **API 支持版本**: V3.8（通过参数指定）
- **匹配引擎**: 10 步 NLP Pipeline

### 4.3 匹配流程

根据 API 响应的 debug 信息，匹配流程包括：

1. **预处理** (`1-preprocess`) - 字符规范化
2. **拆分** (`2-split`) - 按模态分组
3. **构建树** (`3-make_tree`) - 分词 + 词性识别
4. **合并节点** (`5-merge_no_body`) - 无部位节点合并
5. **消歧** - 根据消歧规则重映射
6. **查表** - 从标准表查询匹配结果

---

## 五、日志与监控

### 5.1 日志文件

| 日志文件 | 大小 | 最后更新 |
|---------|------|----------|
| `match_service_new.log` | 21 MB | 2026-07-29 11:11 |
| `match_task.log` | 2.1 MB | 2026-07-29 08:00 |
| `match_task_v2.log` | 2.4 MB | 2026-07-29 08:30 |
| `nohup.out` | 48 MB | 2025-12-27 |

### 5.2 日志内容

最新日志内容：
```
特色项目 []
特色项目 []
...（重复输出）
```

**问题**: ⚠️ 日志输出重复，可能存在特殊项目处理逻辑

---

## 六、与 MMS Platform 对比

### 6.1 架构对比

| 维度 | 生产服务器 (16_zzy) | MMS Platform | 优势方 |
|------|---------------------|--------------|--------|
| **框架** | Flask + Tornado | FastAPI | **MMS** ✅ |
| **异步支持** | ❌ 同步 WSGI | ✅ async/await | **MMS** ✅ |
| **词表规模** | 3,716 条 | 11,503 条 | **MMS** ✅ |
| **支持模态** | 9 种 | 11 种 (+ OCT/DSA) | **MMS** ✅ |
| **管理界面** | ❌ 无 | ✅ React + Ant Design | **MMS** ✅ |
| **测试覆盖** | ❌ 无 | ✅ 46 个测试 | **MMS** ✅ |
| **部署方式** | nohup | Docker Compose | **MMS** ✅ |
| **运行时长** | ✅ 96 天稳定 | 未知 | **生产** ✅ |
| **生产验证** | ✅ 已验证 | 待验证 | **生产** ✅ |

### 6.2 词表对比

| 词表类型 | 生产服务器 | MMS Platform | 差距 |
|---------|-----------|--------------|------|
| 医学词典 | 2,071 | 2,435 | +364 条 (+17.6%) |
| 短语映射 | 1,594 | 7,839 | +6,245 条 (+391%) |
| 消歧规则 | 51 | 1,229 | +1,178 条 (+2309%) |
| **总计** | **3,716** | **11,503** | **+7,787 条 (+209%)** |

**结论**: MMS Platform 词表规模是生产服务器的 **3.1 倍**

---

## 七、问题与风险

### 7.1 已识别问题

1. **词表规模小** ⚠️
   - 生产服务器词表仅 3,716 条
   - MMS Platform 有 11,503 条（3.1 倍）
   - 可能影响匹配准确率和覆盖率

2. **日志输出异常** ⚠️
   - `特色项目 []` 重复输出
   - 日志文件较大（21 MB）
   - 可能影响性能

3. **技术栈老旧** ⚠️
   - Flask + Tornado (同步 WSGI)
   - 不支持异步处理
   - 无法充分利用现代硬件

4. **无管理界面** ⚠️
   - 词表修改需要直接操作数据库
   - 无法可视化查看匹配结果
   - 运维成本高

5. **无自动化测试** ⚠️
   - 缺少单元测试
   - 无法保证代码质量
   - 回归风险高

### 7.2 稳定性优势

1. **长期稳定运行** ✅
   - 连续运行 96 天无故障
   - 证明代码稳定性

2. **生产验证** ✅
   - 已在生产环境使用
   - 经过实战检验

---

## 八、迁移建议

### 8.1 迁移策略

**推荐方案**: 灰度迁移到 MMS Platform

**理由**:
1. ✅ MMS 词表规模是生产的 3.1 倍
2. ✅ MMS 技术栈更现代（FastAPI + async）
3. ✅ MMS 有完整的管理界面和测试
4. ✅ 生产服务器已稳定运行 96 天，可作为灰度对照

### 8.2 灰度方案

```
                     Nginx 流量分流
                          │
                ┌─────────┴─────────┐
                │                   │
           10% 流量             90% 流量
                │                   │
                ▼                   ▼
        MMS Platform        生产服务器 (16_zzy)
       (10.101.1.178:9100)  (10.101.1.178:50000)
                │                   │
                └─────────┬─────────┘
                          │
                    对比准确率
```

**步骤**:
1. 在同一服务器部署 MMS Platform (端口 9100)
2. Nginx 配置 10% 流量到 MMS，90% 到旧服务
3. 监控准确率和性能指标
4. 逐步提升 MMS 流量占比（10% → 30% → 50% → 100%）
5. 验证稳定后下线旧服务

### 8.3 迁移前置任务

根据 `MIGRATION_PLAN.md`：

1. **Phase 1**: 词表合并（2天）
   - 合并生产服务器的 3,716 条词表到 MMS
   - 保留 MMS 的 11,503 条词表
   - 去重后预计 12,000+ 条

2. **Phase 2**: 测试数据导入（3天）
   - 从生产服务器导出历史匹配数据
   - 建立 benchmark 测试集
   - 验证准确率

3. **Phase 3-5**: 准确率验证与部署（10天）
   - 边界 case 测试
   - 准确率调优（目标 F1 >= 0.95）
   - 生产部署与监控

**总工期**: 15 天

---

## 九、总结

### 9.1 核心发现

1. **生产服务运行稳定** ✅
   - 96 天连续运行无故障
   - API 响应正常
   - 支持 9 种模态

2. **词表规模不足** ⚠️
   - 仅 3,716 条（MMS 的 32%）
   - 短语映射和消歧规则严重不足
   - 影响匹配准确率和覆盖率

3. **技术栈老旧** ⚠️
   - Flask + Tornado（同步）
   - 无管理界面
   - 无自动化测试

### 9.2 推荐行动

**立即执行**:
1. ✅ 启动 Phase 1-2（词表合并 + 测试数据导入）
2. ✅ 建立 benchmark 对比准确率

**近期计划**（2周内）:
1. 完成 Phase 3-5（准确率验证 + 灰度部署）
2. 在同一服务器部署 MMS Platform
3. Nginx 配置 10% 流量灰度

**长期规划**（1个月内）:
1. 验证 MMS 准确率 >= 生产服务器
2. 逐步提升流量占比到 100%
3. 下线旧服务

---

**报告生成时间**: 2026-07-29
**报告人**: AI 算法团队
**下一步**: 执行 Phase 1 词表合并任务

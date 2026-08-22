# 部署文档导航

MMS Platform 部署相关文档的总入口。

---

## 🚀 快速开始

### 我应该看哪个文档？

| 你想做什么 | 推荐文档 |
|-----------|---------|
| 🆕 第一次部署 | [完整部署流程](#完整部署流程) |
| 🤔 不知道用哪种方法 | [部署方法对比](#部署方法对比) |
| ⚡ 快速部署（已熟悉流程） | 直接说 "部署到 VPS" 触发 skill |
| 🔍 验证部署 | [部署指南 - 验证步骤](#基础部署指南) |
| 🐛 部署遇到问题 | [故障排查](#故障排查) |
| 📊 配置监控 | [部署指南 - 监控配置](#基础部署指南) |

---

## 📚 文档清单

### 完整部署流程

**文件：** `deployment/code-sync-workflow.md`

**内容：**
- 部署架构概览（本地→GitLab→VPS）
- 方法一：GitLab CI/CD 自动部署（推荐）
- 方法二：rsync 手动同步
- 方法三：Python 直接运行（最快）
- 故障排查（Docker 超时、glibc 问题）
- 常用命令速查

**何时阅读：**
- ✅ 第一次部署项目
- ✅ 需要了解完整流程
- ✅ 配置 GitLab CI/CD
- ✅ 遇到 Docker 构建问题

**链接：** [查看文档](deployment/code-sync-workflow.md)

---

### 部署方法对比

**文件：** `deployment/deployment-methods-comparison.md`

**内容：**
- 三种方法的代码同步流程详细对比
- 实战案例分析（PET/CT 修复、添加依赖包）
- 代码更新矩阵对比
- 最佳实践建议
- 推荐使用场景（70%/20%/10% 法则）

**何时阅读：**
- ✅ 不确定该用哪种部署方法
- ✅ 想了解每种方法的优缺点
- ✅ 需要处理依赖变更、前端构建等特殊情况
- ✅ 想学习最佳实践

**链接：** [查看文档](deployment/deployment-methods-comparison.md)

---

### 基础部署指南

**文件：** `deployment-guide.md`

**内容：**
- 传统手动部署步骤（git pull 方式）
- 部署验证清单
- 健康检查和 API 测试
- 监控配置（Prometheus、Nginx）
- 回滚方案
- 故障排查

**何时阅读：**
- ✅ 需要验证部署结果
- ✅ 配置监控系统
- ✅ 学习基础验证流程
- ✅ 需要回滚操作

**链接：** [查看文档](deployment-guide.md)

---

## 🛠️ 快速工具

### Skill: vps-deploy

**触发词：**
- "部署到 VPS"
- "同步代码到 VPS"
- "更新生产环境"
- "紧急修复上线"

**功能：**
- ✅ 自动问诊（部署类型、Git 状态、变更范围）
- ✅ 智能选择部署方法
- ✅ 执行完整部署流程
- ✅ 自动验证和测试
- ✅ 强制 Git 提交提醒
- ✅ 生成部署报告

**使用方式：**
```
用户: "部署到 VPS"
AI: [自动加载 skill，开始问诊流程]
```

---

### 部署脚本

| 脚本 | 用途 | 耗时 |
|------|------|------|
| `scripts/quick_deploy_backend.sh` | 快速部署后端（rsync） | 1-2分钟 |
| `scripts/deploy_to_vps_with_key.sh` | 完整部署（前后端） | 5-10分钟 |
| `scripts/test_vps_api.sh` | API 功能测试 | 30秒 |

---

## 📖 知识库

### 记忆系统

**文件：** `.claude/projects/.../memory/vps-deployment-workflow.md`

**内容：**
- 三种部署方法的核心原则
- 决策树（何时用哪种方法）
- 关键注意事项和限制
- PYTHONPATH 设置说明
- 故障排查要点

**作用：** AI 助手的长期记忆，确保每次对话都能正确指导部署

---

## 🎯 三种部署方法速查

### 方法一：GitLab CI/CD（70% 场景）

```bash
git add .
git commit -m "feat: 功能描述"
git push origin main
# 等待 Pipeline 自动完成（5-10分钟）
```

**特点：** 
- ✅ 自动化、有测试、可追溯
- ⏱️ 耗时较长

**适合：** 正式发布、功能开发完成

---

### 方法二：rsync 手动（20% 场景）

```bash
./scripts/quick_deploy_backend.sh
# 验证后补充 Git 提交
git add . && git commit -m "fix: 描述" && git push
```

**特点：**
- ⚡ 快速（1-2分钟）
- ⚠️ 需手动补充 Git 提交

**适合：** 快速迭代、验证修复

---

### 方法三：Python 直接运行（10% 场景）

```bash
# 1. 同步代码
rsync -avz src/ root@220.154.3.166:/data/mms-platform/src/

# 2. 重启服务
ssh root@220.154.3.166 "
pkill -f 'uvicorn match_service'
cd /data/mms-platform
PYTHONPATH=/data/mms-platform/src \
nohup .venv/bin/python -m uvicorn match_service.main:app \
  --host 0.0.0.0 --port 9100 > logs/uvicorn.log 2>&1 &
"

# 3. 立即提交
git add . && git commit -m "hotfix: 描述" && git push
```

**特点：**
- 🚀 最快（30秒-1分钟）
- ⚠️ 无测试、必须立即提交

**适合：** 紧急修复、Docker 失败时

---

## 🆘 故障排查

### 常见问题速查

| 问题 | 原因 | 解决方案 | 文档位置 |
|------|------|---------|---------|
| Docker 构建超时 | VPS glibc 版本过低 | 使用方法三（Python 直接运行） | [完整流程 - 故障排查](deployment/code-sync-workflow.md#问题-2docker-构建超时) |
| ModuleNotFoundError | PYTHONPATH 未设置 | 添加 `PYTHONPATH=/data/mms-platform/src` | [完整流程 - 故障排查](deployment/code-sync-workflow.md#问题-4modulenotfounderror-no-module-named-match_service) |
| 前端构建失败 | Node.js glibc 不兼容 | 本地构建后 rsync | [方法对比 - 问题3](deployment/deployment-methods-comparison.md#问题-3前端构建失败glibc-版本问题) |
| PET/CT 返回 0 条 | 代码未更新 | 检查服务进程和代码版本 | [基础指南 - 故障排查](deployment-guide.md#问题-3-前端显示数据异常) |
| GitLab Pipeline 卡住 | Runner 故障 | 重启 GitLab Runner | [完整流程 - 故障排查](deployment/code-sync-workflow.md#问题-1gitlab-pipeline-卡住) |

---

## ✅ 部署检查清单

### 部署前
- [ ] 确认修改的文件范围
- [ ] 确认是否需要依赖安装
- [ ] 确认是否需要数据库迁移
- [ ] 确认是否需要前端构建
- [ ] 确认 Git 提交状态

### 部署后
- [ ] 服务进程运行正常
- [ ] 后端 API 响应正常
- [ ] PET/CT 查询返回正确数据
- [ ] PET/MR 查询返回正确数据
- [ ] 日志无错误
- [ ] Git 提交已完成（方法二、三必须）

---

## 📞 寻求帮助

### AI 辅助部署
直接说：
```
"部署到 VPS"
```
AI 会自动加载 skill 并引导你完成整个流程。

### 查看示例
参考文档中的实战案例：
- [方法对比 - 场景1：修复 PET/CT Bug](deployment/deployment-methods-comparison.md#场景-1修复-petct-查询-bug)
- [方法对比 - 场景2：添加新依赖](deployment/deployment-methods-comparison.md#场景-2添加新依赖包)

---

## 📝 文档维护

**最后更新：** 2026-08-21  
**维护者：** MMS Platform 团队

**版本历史：**
- 2026-08-21: 创建部署文档导航，整合三份文档
- 2026-08-21: 添加 vps-deploy skill 和记忆系统
- 2026-08-01: 创建基础部署指南

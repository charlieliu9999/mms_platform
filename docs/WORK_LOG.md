# MMS Platform 工作日志

## 2026-08-17
- 文档清理：删除90+个历史报告文件
  - 根目录：70+个历史PHASE/FIX/CT/MR分析报告
  - docs/reports：7/8月早期报告
  - 保留：核心分析(unmatched-1391)、最新bug修复、进度追踪、必备文档
  - 剩余：根目录6个 + docs/reports 17个 + openwiki完整保留
- 清理临时json/log文件：删除2.8MB历史数据
  - 根目录：7个评测/测试日志
  - logs/：8个历史日志（保留当前backend.log/frontend.log）
  - data/：5个ACR导入json（已入库）
  - scripts/：3个临时结果文件
  - src/：2个评测输出日志
  - 剩余：10个必需配置/资产文件
- 目录清理：data/ 1.8MB→1.5MB，docs/ 500KB→224KB
  - data/：删除空目录、已导入临时数据（eval_tasks/、lexicon/import*）
  - docs/：删除20+个历史分析文档（7/8月早期）
  - 保留：词表源头数据（phase0/phase1）、核心分析、最新报告
  - 剩余：docs仅3个md + 3个子目录，data保留6项必需数据
- 制定文件生产规则：防止文档泛滥
  - 原因：曾有150+个md（代码仅165个py），AI每次生成独立报告
  - 规则：禁止随意创建新文件，强制使用WORK_LOG.md记录
  - 允许：5类指定文件（工作日志、bug追踪、技术文档、openwiki）
  - 详见：docs/FILE_PRODUCTION_RULES.md
  - 已写入记忆系统

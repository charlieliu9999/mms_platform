#!/bin/bash
# MMS平台关键问题修复脚本
# 修复日期: 2026-08-02
# 修复内容:
#   1. 标准项目页面模态映射问题
#   2. 前端匹配算法数据适配问题

set -e

echo "=========================================="
echo "MMS平台关键问题修复脚本"
echo "=========================================="
echo ""

# 检查数据库连接
echo "[1/3] 检查数据库连接..."
if ! psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db -c "SELECT 1" > /dev/null 2>&1; then
    echo "❌ 数据库连接失败，请检查PostgreSQL是否运行在15432端口"
    exit 1
fi
echo "✓ 数据库连接正常"
echo ""

# 修复标准项目模态映射
echo "[2/3] 修复标准项目模态映射..."
echo "  执行SQL: 将中文模态名统一为国际标准代码"

psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db << 'EOF'
-- 备份当前数据（可选）
-- CREATE TABLE nlp_checkitem_standard_backup AS SELECT * FROM nlp_checkitem_standard;

-- 统一模态名称为国际标准代码
UPDATE nlp_checkitem_standard
SET modality_name = CASE
  -- X线分为DR和RF
  WHEN modality_name = 'X线' AND (
    scan_name LIKE '%透视%' OR
    scan_name LIKE '%造影%' OR
    scan_name LIKE '%食管%' OR
    scan_name LIKE '%胃肠%'
  ) THEN 'RF'
  WHEN modality_name = 'X线' THEN 'DR'

  -- 超声类
  WHEN modality_name = '超声' OR modality_name = '彩超' THEN 'US'

  -- 乳腺X线
  WHEN modality_name = '乳腺X线摄影' OR modality_name = '乳腺X线' THEN 'MG'

  -- 保持原有标准代码
  ELSE modality_name
END;

-- 验证修复结果
SELECT
  modality_name,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM nlp_checkitem_standard
GROUP BY modality_name
ORDER BY COUNT(*) DESC;
EOF

echo "✓ 模态映射修复完成"
echo ""

# 修复前端匹配算法数据适配
echo "[3/3] 修复前端匹配算法数据适配..."

# 备份原文件
cp frontend/src/services/matchService.ts frontend/src/services/matchService.ts.bak

# 应用修复补丁
cat > /tmp/match_service_fix.patch << 'EOF'
--- a/frontend/src/services/matchService.ts
+++ b/frontend/src/services/matchService.ts
@@ -54,8 +54,14 @@ export interface StatsData {
 // 匹配相关 API
 export const matchAPI = {
   // 单个匹配
-  matchOne: (data: MatchRequest): Promise<MatchResult> =>
-    apiClient.post('/match', data),
+  matchOne: (data: MatchRequest): Promise<any> =>
+    apiClient.post('/match', data).then((res: any) => ({
+      ...res.result,
+      matched: res.result.num_standard > 0,
+      confidence: res.result.confidence || (res.result.score ? res.result.score / 10 : 0),
+      data: res.result.data,
+      rule_version: res.rule_version
+    })),

   // 批量匹配
   matchBatch: (items: MatchRequest[]): Promise<MatchResult[]> =>
EOF

# 应用补丁
if patch -p1 < /tmp/match_service_fix.patch; then
    echo "✓ 前端数据适配修复完成"
else
    echo "⚠ 补丁应用失败，请手动修复 frontend/src/services/matchService.ts"
    echo "  参考备份文件: frontend/src/services/matchService.ts.bak"
fi

rm -f /tmp/match_service_fix.patch
echo ""

# 重建前端
echo "[4/4] 重建前端..."
cd frontend
npm run build > /dev/null 2>&1 && echo "✓ 前端构建成功" || echo "⚠ 前端构建失败，请检查TypeScript错误"
cd ..
echo ""

echo "=========================================="
echo "修复完成！请执行以下验证："
echo "=========================================="
echo ""
echo "1. 测试匹配算法页面:"
echo "   curl -X POST http://localhost:9100/api/match \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"name\":\"CT头部平扫\",\"modality\":\"CT\"}' | jq"
echo ""
echo "2. 测试标准项目筛选:"
echo "   curl 'http://localhost:9100/api/admin/standard-items?modality=DR&page_size=5' | jq '.total'"
echo "   curl 'http://localhost:9100/api/admin/standard-items?modality=US&page_size=5' | jq '.total'"
echo ""
echo "3. 重启服务并访问前端:"
echo "   ./scripts/stop.sh && ./scripts/start.sh"
echo "   打开浏览器: http://localhost:3100"
echo ""
echo "=========================================="

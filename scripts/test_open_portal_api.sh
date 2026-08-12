#!/bin/bash
set -e

BASE_URL="http://127.0.0.1:9100/api/open"

echo "======================================"
echo "测试 mms_platform Open Portal API"
echo "======================================"
echo ""

# 检查服务是否运行
echo "0. 检查服务状态..."
if ! curl -s -f "$BASE_URL/../health" > /dev/null 2>&1; then
    echo "❌ 服务未启动，请先运行: cd /Users/charlieliu/git_project_vscode/09_medical/mms_platform && poetry run uvicorn match_service.main:app --port 9100"
    exit 1
fi
echo "✅ 服务运行中"
echo ""

# 1. 统计信息
echo "1. GET /stats - 推荐系统统计"
echo "---"
curl -s "$BASE_URL/stats" | python3 -m json.tool
echo ""
echo ""

# 2. 标准统计
echo "2. GET /standards/stats - 标准统计信息"
echo "---"
curl -s "$BASE_URL/standards/stats" | python3 -m json.tool
echo ""
echo ""

# 3. 版本列表
echo "3. GET /standards/versions - 标准版本列表"
echo "---"
curl -s "$BASE_URL/standards/versions" | python3 -m json.tool
echo ""
echo ""

# 4. 筛选选项
echo "4. GET /standards/filter-options - 筛选选项"
echo "---"
curl -s "$BASE_URL/standards/filter-options" | python3 -m json.tool | head -30
echo "..."
echo ""

# 5. 标准项目列表（第1页）
echo "5. GET /standards/items?page=1&page_size=5 - 标准项目列表"
echo "---"
curl -s "$BASE_URL/standards/items?page=1&page_size=5" | python3 -m json.tool | head -40
echo "..."
echo ""

# 6. 按模态筛选
echo "6. GET /standards/items?modality=CT&page_size=3 - CT模态筛选"
echo "---"
curl -s "$BASE_URL/standards/items?modality=CT&page_size=3" | python3 -m json.tool | head -40
echo "..."
echo ""

# 7. 按版本筛选
echo "7. GET /standards/items?version=V3.8.2&page_size=3 - V3.8.2版本筛选"
echo "---"
curl -s "$BASE_URL/standards/items?version=V3.8.2&page_size=3" | python3 -m json.tool | head -40
echo "..."
echo ""

# 8. 关键词搜索
echo "8. GET /standards/items?keyword=头颅&page_size=3 - 关键词搜索"
echo "---"
curl -s "$BASE_URL/standards/items?keyword=头颅&page_size=3" | python3 -m json.tool | head -40
echo "..."
echo ""

# 9. 标准项目详情
echo "9. GET /standards/items/1 - 标准项目详情"
echo "---"
curl -s "$BASE_URL/standards/items/1" | python3 -m json.tool
echo ""
echo ""

# 10. 版本对比
echo "10. GET /standards/versions/compare?v1=V3.8.2&v2=V4.0 - 版本对比"
echo "---"
curl -s "$BASE_URL/standards/versions/compare?v1=V3.8.2&v2=V4.0" | python3 -m json.tool 2>/dev/null || echo "V4.0数据未导入"
echo ""
echo ""

# 11. 推荐面板（占位）
echo "11. GET /panels - 推荐面板列表（占位）"
echo "---"
curl -s "$BASE_URL/panels" | python3 -m json.tool
echo ""
echo ""

echo "======================================"
echo "✅ API 测试完成"
echo "======================================"

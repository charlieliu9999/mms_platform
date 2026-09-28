#!/bin/bash
# VPS API 端点测试脚本

BASE_URL="${1:-http://localhost:9100}"

echo "================================"
echo "MMS Platform API 测试"
echo "BASE_URL: $BASE_URL"
echo "================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local desc=$4
    
    echo -e "${YELLOW}测试: ${desc}${NC}"
    echo "  ${method} ${endpoint}"
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "${BASE_URL}${endpoint}")
    else
        response=$(curl -s -w "\n%{http_code}" -X ${method} "${BASE_URL}${endpoint}" \
            -H "Content-Type: application/json" \
            -d "${data}")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo -e "  ${GREEN}✓ 成功 (HTTP $http_code)${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null | head -20 || echo "$body" | head -20
    else
        echo -e "  ${RED}✗ 失败 (HTTP $http_code)${NC}"
        echo "$body" | head -10
    fi
    echo ""
}

# 1. 健康检查
test_endpoint "GET" "/health" "" "健康检查"

# 2. API 信息
test_endpoint "GET" "/api" "" "API 信息"

# 3. API 文档 (仅检查是否可访问)
echo -e "${YELLOW}测试: API 文档${NC}"
echo "  GET /docs"
http_code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/docs")
if [ "$http_code" = "200" ]; then
    echo -e "  ${GREEN}✓ 成功 (HTTP $http_code)${NC}"
    echo "  访问: ${BASE_URL}/docs"
else
    echo -e "  ${RED}✗ 失败 (HTTP $http_code)${NC}"
fi
echo ""

# 4. 开放门户 - 统计数据
test_endpoint "GET" "/api/open/standards/stats" "" "开放门户 - 标准项目统计"

# 5. 开放门户 - 标准项目列表 (前5条)
test_endpoint "GET" "/api/open/standards/items?page=1&page_size=5" "" "开放门户 - 标准项目列表"

# 6. 开放门户 - 版本列表
test_endpoint "GET" "/api/open/standards/versions" "" "开放门户 - 版本列表"

# 7. 匹配接口测试
test_endpoint "POST" "/api/match/one" '{"item_name":"胸部CT平扫","modality":"CT"}' "匹配接口 - 单项目匹配"

# 8. 管理后台 - 标准项目统计
test_endpoint "GET" "/api/admin/standard-item-stats" "" "管理后台 - 标准项目统计"

echo "================================"
echo "测试完成"
echo "================================"

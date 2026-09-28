#!/bin/bash
# 测试 API 版本号大小写处理

BASE_URL="${1:-http://localhost:9100}"

echo "================================"
echo "API 版本号大小写处理测试"
echo "BASE_URL: $BASE_URL"
echo "================================"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

test_version() {
    local version=$1
    local endpoint=$2
    local desc=$3
    
    echo -e "${YELLOW}测试: ${desc}${NC}"
    echo "  版本号: ${version}"
    echo "  端点: ${endpoint}"
    
    response=$(curl -s "${BASE_URL}${endpoint}?version=${version}")
    count=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('total', 0))" 2>/dev/null || echo "0")
    
    if [ "$count" -gt 0 ]; then
        echo -e "  ${GREEN}✓ 成功 - 返回 ${count} 条记录${NC}"
    else
        echo "  ⚠️  返回 0 条记录（可能该版本无数据）"
    fi
    echo ""
}

# 测试开放门户 API
echo "1️⃣  测试开放门户 - 标准项目列表"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_version "v3.8.2" "/api/open/standards/items" "小写版本号"
test_version "V3.8.2" "/api/open/standards/items" "大写版本号"
test_version "v4.0.0" "/api/open/standards/items" "小写版本号 v4.0.0"
test_version "V4.0.0" "/api/open/standards/items" "大写版本号 V4.0.0"

echo "2️⃣  测试开放门户 - 统计数据"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_version "v3.8.2" "/api/open/standards/stats" "小写版本号统计"
test_version "V3.8.2" "/api/open/standards/stats" "大写版本号统计"

echo "3️⃣  测试管理后台 - 标准项目查询"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_version "v3.8.2" "/api/admin/standard-items" "小写版本号"
test_version "V3.8.2" "/api/admin/standard-items" "大写版本号"

echo "4️⃣  测试管理后台 - 统计数据"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_version "v3.8.2" "/api/admin/standard-item-stats" "小写版本号统计"
test_version "V3.8.2" "/api/admin/standard-item-stats" "大写版本号统计"

echo "================================"
echo "测试完成"
echo ""
echo "预期结果:"
echo "  - 小写版本号 (v3.8.2) 和大写版本号 (V3.8.2) 应该返回相同的数据"
echo "  - 所有端点都应该正确处理版本号大小写"
echo "================================"

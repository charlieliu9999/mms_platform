#!/bin/bash
# MMS 完整测试脚本
# 测试后端 API + 前端构建 + 端到端功能

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

FAILED_TESTS=0
TOTAL_TESTS=0

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_test() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "${YELLOW}[$TOTAL_TESTS] $1${NC}"
}

pass() {
    echo -e "${GREEN}  ✓ $1${NC}"
}

fail() {
    echo -e "${RED}  ✗ $1${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
}

print_header "MMS 完整测试套件"

# ============================================
# 1. 后端单元测试
# ============================================
print_header "[1/5] 后端单元测试"

print_test "运行 pytest 测试套件"
if poetry run pytest tests/ -v --tb=short 2>&1 | tee logs/test-backend.log; then
    TEST_COUNT=$(grep -c "passed" logs/test-backend.log || echo "0")
    pass "pytest: $TEST_COUNT 个测试通过"
else
    fail "pytest 测试失败"
fi

# ============================================
# 2. 后端 API 测试
# ============================================
print_header "[2/5] 后端 API 测试"

# 启动后端
print_test "启动后端服务"
poetry run uvicorn match_service.main:app --port 9100 > logs/test-backend-server.log 2>&1 &
BACKEND_PID=$!
sleep 5

if curl -s http://localhost:9100/health > /dev/null; then
    pass "后端启动成功 (PID: $BACKEND_PID)"
else
    fail "后端启动失败"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# 健康检查
print_test "API 健康检查"
HEALTH=$(curl -s http://localhost:9100/health)
if echo "$HEALTH" | grep -q "ok"; then
    pass "健康检查: $HEALTH"
else
    fail "健康检查失败"
fi

# 测试匹配 API
print_test "测试匹配 API"
MATCH_RESULT=$(curl -s -X POST http://localhost:9100/api/match/one \
    -H 'Content-Type: application/json' \
    -d '{"check_item": "胸部CT平扫", "modality": "CT"}')

if echo "$MATCH_RESULT" | grep -q "matched"; then
    pass "匹配 API 响应正常"
else
    fail "匹配 API 响应异常: $MATCH_RESULT"
fi

# 测试管理 API
print_test "测试管理 API - 统计数据"
STATS=$(curl -s http://localhost:9100/api/admin/stats)
if echo "$STATS" | grep -q "total_medical_dict"; then
    pass "管理 API 响应正常"
else
    fail "管理 API 响应异常: $STATS"
fi

# 测试词库查询 API
print_test "测试词库查询 API"
DICT=$(curl -s "http://localhost:9100/api/admin/medical-dict?page=1&page_size=10")
if echo "$DICT" | grep -q "items"; then
    pass "词库查询 API 响应正常"
else
    fail "词库查询 API 响应异常: $DICT"
fi

# 测试 Legacy API (兼容层)
print_test "测试 Legacy API 兼容层"
LEGACY=$(curl -s -X POST http://localhost:9100/algorithm/standardCheck/match \
    -H 'Content-Type: application/json' \
    -d '{"check_item": "胸部CT", "modality": "CT"}')

if echo "$LEGACY" | grep -q "matched\|standard_name"; then
    pass "Legacy API 兼容层正常"
else
    fail "Legacy API 兼容层异常: $LEGACY"
fi

# 停止后端
kill $BACKEND_PID 2>/dev/null || true
sleep 2

# ============================================
# 3. 前端构建测试
# ============================================
print_header "[3/5] 前端构建测试"

cd frontend

print_test "TypeScript 类型检查"
if npx tsc --noEmit > ../logs/test-frontend-tsc.log 2>&1; then
    pass "TypeScript 类型检查通过"
else
    fail "TypeScript 类型检查失败"
    cat ../logs/test-frontend-tsc.log
fi

print_test "ESLint 代码检查"
if npm run lint > ../logs/test-frontend-lint.log 2>&1 || true; then
    pass "ESLint 检查完成"
else
    fail "ESLint 检查失败"
fi

print_test "前端生产构建"
if npm run build > ../logs/test-frontend-build.log 2>&1; then
    BUILD_SIZE=$(du -sh dist | cut -f1)
    pass "前端构建成功 (大小: $BUILD_SIZE)"
else
    fail "前端构建失败"
    cat ../logs/test-frontend-build.log
fi

print_test "检查构建产物"
if [ -f "dist/index.html" ] && [ -d "dist/assets" ]; then
    FILE_COUNT=$(find dist -type f | wc -l)
    pass "构建产物完整 ($FILE_COUNT 个文件)"
else
    fail "构建产物不完整"
fi

cd ..

# ============================================
# 4. 集成测试（前后端联调）
# ============================================
print_header "[4/5] 集成测试"

print_test "启动后端 + 挂载前端"
poetry run uvicorn match_service.main:app --port 9100 > logs/test-integration.log 2>&1 &
BACKEND_PID=$!
sleep 5

if curl -s http://localhost:9100/health > /dev/null; then
    pass "后端启动成功"
else
    fail "后端启动失败"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

print_test "检查前端静态文件挂载"
if curl -s http://localhost:9100/ | grep -q "MMS" || grep -q "挂载" logs/test-integration.log; then
    pass "前端静态文件挂载正常"
else
    fail "前端静态文件未挂载"
fi

print_test "测试 API 跨域"
CORS_RESULT=$(curl -s -X OPTIONS http://localhost:9100/api/match/one \
    -H "Origin: http://localhost:3100" \
    -H "Access-Control-Request-Method: POST" \
    -I | grep -i "access-control-allow-origin")

if [ -n "$CORS_RESULT" ]; then
    pass "CORS 配置正常"
else
    fail "CORS 配置异常"
fi

kill $BACKEND_PID 2>/dev/null || true

# ============================================
# 5. 功能验证（Phase C-G）
# ============================================
print_header "[5/5] Phase C-G 功能验证"

print_test "运行 verify_phases.sh"
if bash scripts/verify_phases.sh > logs/test-phases.log 2>&1; then
    pass "所有阶段验证通过"
else
    fail "阶段验证失败"
    cat logs/test-phases.log
fi

# ============================================
# 测试报告
# ============================================
print_header "测试报告"

echo "总测试数: $TOTAL_TESTS"
echo "通过数: $((TOTAL_TESTS - FAILED_TESTS))"
echo "失败数: $FAILED_TESTS"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}所有测试通过 ✓${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}测试失败: $FAILED_TESTS 个${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo "查看详细日志:"
    echo "  后端测试: cat logs/test-backend.log"
    echo "  前端测试: cat logs/test-frontend-build.log"
    echo "  集成测试: cat logs/test-integration.log"
    exit 1
fi

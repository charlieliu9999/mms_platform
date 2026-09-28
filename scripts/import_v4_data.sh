#!/bin/bash
# ============================================================
# v4.0.0 数据导入脚本
# ============================================================
# 用途: 将转换后的 CSV 数据导入到 PostgreSQL
# 前提:
#   1. Docker 容器已启动
#   2. 数据库结构已更新
#   3. CSV 文件已生成
# ============================================================

set -e  # 遇到错误立即退出

# 配置
DB_CONTAINER="mms_platform-postgres-1"
DB_NAME="acrac_prod"
DB_USER="postgres"
CSV_FILE=$(ls -t data/v4.0.0_standards_*.csv 2>/dev/null | head -1)

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "============================================================"
echo "v4.0.0 数据导入脚本"
echo "============================================================"

# 1. 检查 CSV 文件
if [ -z "$CSV_FILE" ]; then
    echo -e "${RED}❌ 未找到 CSV 文件${NC}"
    echo "请先运行: python3 scripts/convert_v4_to_csv.py"
    exit 1
fi

echo -e "${GREEN}✓${NC} 找到 CSV 文件: $CSV_FILE"

# 2. 检查 Docker 容器
if ! docker ps | grep -q "$DB_CONTAINER"; then
    echo -e "${RED}❌ PostgreSQL 容器未运行${NC}"
    echo "请先启动: docker-compose up -d postgres"
    exit 1
fi

echo -e "${GREEN}✓${NC} PostgreSQL 容器运行中"

# 3. 备份现有数据
BACKUP_FILE="backups/backup_$(date +%Y%m%d_%H%M%S).sql"
echo ""
echo -e "${YELLOW}📦 备份现有数据...${NC}"

docker-compose exec -T postgres pg_dump \
    -U $DB_USER \
    -d $DB_NAME \
    -t checkitem_standards \
    > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} 备份成功: $BACKUP_FILE"
else
    echo -e "${RED}❌ 备份失败${NC}"
    exit 1
fi

# 4. 更新数据库结构
echo ""
echo -e "${YELLOW}🔧 更新数据库结构...${NC}"

docker-compose exec -T postgres psql \
    -U $DB_USER \
    -d $DB_NAME \
    < scripts/init_v4_schema.sql

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} 结构更新成功"
else
    echo -e "${RED}❌ 结构更新失败${NC}"
    exit 1
fi

# 5. 复制 CSV 到容器
echo ""
echo -e "${YELLOW}📤 复制 CSV 到容器...${NC}"

docker cp "$CSV_FILE" "${DB_CONTAINER}:/tmp/v4_data.csv"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} 文件已复制到容器"
else
    echo -e "${RED}❌ 文件复制失败${NC}"
    exit 1
fi

# 6. 导入数据
echo ""
echo -e "${YELLOW}💾 导入数据到数据库...${NC}"

docker-compose exec -T postgres psql \
    -U $DB_USER \
    -d $DB_NAME \
    -c "\COPY checkitem_standards (modality, checkitem_code, checkitem_name, body_part_l1_code, body_part_l1, body_part_l2_code, body_part_l2, body_part_l3_code, body_part_l3, body_part_code, scan_method, insurance_code, insurance_ext_code, version, province, insurance_name, insurance_item_code) FROM '/tmp/v4_data.csv' DELIMITER ',' CSV HEADER;"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} 数据导入成功"
else
    echo -e "${RED}❌ 数据导入失败${NC}"
    echo ""
    echo "恢复备份:"
    echo "  docker-compose exec -T postgres psql -U $DB_USER -d $DB_NAME < $BACKUP_FILE"
    exit 1
fi

# 7. 验证导入结果
echo ""
echo -e "${YELLOW}🔍 验证导入结果...${NC}"

docker-compose exec -T postgres psql \
    -U $DB_USER \
    -d $DB_NAME \
    -c "SELECT version, modality, COUNT(*) as count, COUNT(DISTINCT insurance_code) as unique_insurance_codes FROM checkitem_standards GROUP BY version, modality ORDER BY version, modality;"

echo ""
echo "============================================================"
echo -e "${GREEN}✅ 导入完成！${NC}"
echo "============================================================"
echo ""
echo "备份文件: $BACKUP_FILE"
echo ""
echo "下一步:"
echo "  1. 验证数据正确性"
echo "  2. 测试 API 接口"
echo "  3. 更新前端页面"
echo ""

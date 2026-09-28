#!/bin/bash
# ============================================================
# v4.0.0 数据导入脚本（standard_check_items 表）
# ============================================================
# 用途: 将转换后的 CSV 数据导入到 standard_check_items 表
# 前提:
#   1. 数据库已备份
#   2. 表结构已更新
#   3. CSV 文件已生成
# ============================================================

set -e  # 遇到错误立即退出

# 配置
DB_CONTAINER="acrac_web_mgmt_postgres_prod"
DB_NAME="acrac_db"
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
echo "   文件大小: $(du -h "$CSV_FILE" | cut -f1)"
echo "   总行数: $(wc -l < "$CSV_FILE") (含表头)"

# 2. 检查 Docker 容器
if ! docker ps | grep -q "$DB_CONTAINER"; then
    echo -e "${RED}❌ PostgreSQL 容器未运行${NC}"
    echo "容器名: $DB_CONTAINER"
    exit 1
fi

echo -e "${GREEN}✓${NC} PostgreSQL 容器运行中"

# 3. 验证备份存在
LATEST_BACKUP=$(ls -t backups/backup_standard_check_items_*.sql 2>/dev/null | head -1)
if [ -z "$LATEST_BACKUP" ]; then
    echo -e "${RED}❌ 未找到备份文件${NC}"
    echo "请先备份: docker exec $DB_CONTAINER pg_dump -U $DB_USER -d $DB_NAME -t standard_check_items > backups/backup_\$(date +%Y%m%d_%H%M%S).sql"
    exit 1
fi

echo -e "${GREEN}✓${NC} 最新备份: $LATEST_BACKUP ($(du -h "$LATEST_BACKUP" | cut -f1))"

# 4. 转换 CSV 为兼容格式（添加必需字段）
echo ""
echo -e "${YELLOW}🔄 转换 CSV 格式...${NC}"

python3 << 'EOF'
import pandas as pd
import sys

try:
    # 读取 CSV
    csv_file = sorted([f for f in __import__('pathlib').Path('data').glob('v4.0.0_standards_*.csv')],
                      key=lambda x: x.stat().st_mtime, reverse=True)[0]
    df = pd.read_csv(csv_file)

    print(f"  原始数据: {len(df)} 行, {len(df.columns)} 列")

    # 字段映射（CSV -> 数据库）
    column_mapping = {
        'checkitem_code': 'item_code',
        'checkitem_name': 'item_name',
        'modality': 'modality',
        'body_part_l1_code': 'body_part_l1_code',
        'body_part_l1': 'body_part_l1',
        'body_part_l2_code': 'body_part_l2_code',
        'body_part_l2': 'body_part_l2',
        'body_part_l3_code': 'body_part_l3_code',
        'body_part_l3': 'body_part_l3',
        'body_part_code': 'body_part_code',
        'scan_method': 'scan_method',
        'insurance_code': 'insurance_code',
        'insurance_ext_code': 'insurance_ext_code',
        'insurance_name': 'insurance_name',
        'insurance_item_code': 'insurance_item_code',
        'province': 'province',
        'version': 'version',
    }

    # 映射列名
    df_mapped = df.rename(columns=column_mapping)

    # 添加必需字段
    df_mapped['coverage_status'] = 'standard'
    df_mapped['supplement_status'] = 'complete'
    df_mapped['is_active'] = True
    df_mapped['source'] = 'v4.0.0-import'

    # 只保留数据库需要的列
    db_columns = ['item_code', 'item_name', 'modality', 'body_part_l1_code', 'body_part_l1',
                  'body_part_l2_code', 'body_part_l2', 'body_part_l3_code', 'body_part_l3',
                  'body_part_code', 'scan_method', 'insurance_code', 'insurance_ext_code',
                  'insurance_name', 'insurance_item_code', 'province', 'version',
                  'coverage_status', 'supplement_status', 'is_active', 'source']

    df_final = df_mapped[db_columns]

    # 导出
    output_file = 'data/v4.0.0_for_import.csv'
    df_final.to_csv(output_file, index=False, encoding='utf-8-sig')

    print(f"  转换完成: {len(df_final)} 行, {len(df_final.columns)} 列")
    print(f"  输出文件: {output_file}")

except Exception as e:
    print(f"❌ 转换失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ CSV 转换失败${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} CSV 格式转换成功"

# 5. 复制 CSV 到容器
echo ""
echo -e "${YELLOW}📤 复制 CSV 到容器...${NC}"

docker cp data/v4.0.0_for_import.csv "${DB_CONTAINER}:/tmp/v4_data.csv"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} 文件已复制到容器"
else
    echo -e "${RED}❌ 文件复制失败${NC}"
    exit 1
fi

# 6. 导入数据
echo ""
echo -e "${YELLOW}💾 导入数据到数据库...${NC}"

docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME << 'EOSQL'
-- 开始事务
BEGIN;

-- 导入数据
\COPY standard_check_items (item_code, item_name, modality, body_part_l1_code, body_part_l1, body_part_l2_code, body_part_l2, body_part_l3_code, body_part_l3, body_part_code, scan_method, insurance_code, insurance_ext_code, insurance_name, insurance_item_code, province, version, coverage_status, supplement_status, is_active, source) FROM '/tmp/v4_data.csv' DELIMITER ',' CSV HEADER;

-- 提交事务
COMMIT;

-- 清理临时文件
\! rm -f /tmp/v4_data.csv

EOSQL

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} 数据导入成功"
else
    echo -e "${RED}❌ 数据导入失败${NC}"
    echo ""
    echo "恢复备份:"
    echo "  docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME < $LATEST_BACKUP"
    exit 1
fi

# 7. 验证导入结果
echo ""
echo -e "${YELLOW}🔍 验证导入结果...${NC}"

docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "
SELECT
    version,
    modality,
    COUNT(*) as count,
    COUNT(DISTINCT insurance_code) as unique_insurance_codes,
    COUNT(CASE WHEN insurance_code IS NOT NULL THEN 1 END) as with_insurance_code
FROM standard_check_items
WHERE is_active = true
GROUP BY version, modality
ORDER BY version, modality;
"

echo ""
echo "============================================================"
echo -e "${GREEN}✅ 导入完成！${NC}"
echo "============================================================"
echo ""
echo "📊 数据统计:"
docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -t -c "
SELECT
    '  v4.0.0: ' || COUNT(*) || ' 条记录'
FROM standard_check_items
WHERE version = 'v4.0.0' AND is_active = true;
"

echo ""
echo "备份文件: $LATEST_BACKUP"
echo ""
echo "下一步:"
echo "  1. 测试 API 接口: curl http://localhost:9100/api/open/icdss/standards/items?version=v4.0.0"
echo "  2. 更新前端页面"
echo "  3. 完整测试"
echo ""

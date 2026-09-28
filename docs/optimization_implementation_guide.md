# 未匹配项目优化实施指南

**生成时间**: 2026-08-26  
**当前匹配率**: 80.8% (998/1235)  
**未匹配数量**: 237个  
**优化目标**: 提升至 89%+

---

## 一、问题分析总结

### 1.1 核心发现
- **77.6%** 的未匹配项目包含英文字母
- **85.2%** 的未匹配项目长度在 9-20 字（中等长度）
- **最大问题**: 放疗定位（49个，20.7%）

### 1.2 问题分类

| 类型 | 数量 | 占比 | 解决方案 |
|------|------|------|----------|
| 算法可优化 | 13+ | 5.5% | 补充词表映射 |
| 标准库缺失-放疗 | 49 | 20.7% | 新增放疗大类 |
| 标准库缺失-造影 | 30 | 12.7% | 新增造影大类 |
| 标准库缺失-操作 | 21 | 8.9% | 新增操作大类 |
| 特殊场景 | 7 | 3.0% | 待产品决策 |

---

## 二、优化方案

### 方案概览
```
阶段1: 算法优化（词表补充）
  ├─ DR特殊体位映射
  ├─ MR/CT特殊技术映射
  └─ 预计提升: +3%

阶段2: 标准库补充
  ├─ 放疗定位大类
  ├─ 造影检查大类
  ├─ 操作引导大类
  └─ 预计提升: +18%

总预期: 80.8% → 89%+
```

---

## 三、实施步骤

### 准备工作
```bash
# 1. 确认环境
cd /Users/charlieliu/git_project_vscode/09_medical/mms_platform

# 2. 确认文件
ls -lh scripts/optimize_algorithm_phase1.sql
ls -lh scripts/add_new_standard_items.sql
ls -lh scripts/execute_optimization.sh
ls -lh scripts/verify_optimization.sh

# 3. 备份数据库（重要！）
cd /Users/charlieliu/git_project_vscode/09_medical/acrac_web_mgmt/acrac_backend
poetry run python -c "
import asyncio
from datetime import datetime
from app.config.database import AsyncSessionLocal
from sqlalchemy import text

async def backup():
    async with AsyncSessionLocal() as session:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 备份 nlp_phrase_map
        await session.execute(text(f'''
            CREATE TABLE nlp_phrase_map_backup_{timestamp} AS 
            SELECT * FROM nlp_phrase_map
        '''))
        
        # 备份 standard_check_items
        await session.execute(text(f'''
            CREATE TABLE standard_check_items_backup_{timestamp} AS 
            SELECT * FROM standard_check_items
        '''))
        
        await session.commit()
        print(f'✅ 备份完成: nlp_phrase_map_backup_{timestamp}')
        print(f'✅ 备份完成: standard_check_items_backup_{timestamp}')

asyncio.run(backup())
"
```

### 执行优化

#### 方式1：交互式执行（推荐）
```bash
chmod +x scripts/execute_optimization.sh
./scripts/execute_optimization.sh
```

按提示选择：
- 阶段1: 算法优化 → 输入 `y` 确认
- 阶段2: 标准库补充 → 输入 `y` 确认

#### 方式2：手动执行
```bash
# 进入原系统目录
cd /Users/charlieliu/git_project_vscode/09_medical/acrac_web_mgmt/acrac_backend

# 阶段1：算法优化
poetry run python << 'PYEOF'
import asyncio
from sqlalchemy import text
from app.config.database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as session:
        with open('/Users/charlieliu/git_project_vscode/09_medical/mms_platform/scripts/optimize_algorithm_phase1.sql', 'r', encoding='utf-8') as f:
            sql = f.read()
        
        for stmt in sql.split(';'):
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--'):
                try:
                    await session.execute(text(stmt))
                except Exception as e:
                    print(f'警告: {e}')
        
        await session.commit()
        print('✅ 阶段1完成')

asyncio.run(main())
PYEOF

# 阶段2：标准库补充
poetry run python << 'PYEOF'
import asyncio
from sqlalchemy import text
from app.config.database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as session:
        with open('/Users/charlieliu/git_project_vscode/09_medical/mms_platform/scripts/add_new_standard_items.sql', 'r', encoding='utf-8') as f:
            sql = f.read()
        
        for stmt in sql.split(';'):
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--'):
                try:
                    await session.execute(text(stmt))
                except Exception as e:
                    print(f'警告: {e}')
        
        await session.commit()
        print('✅ 阶段2完成')

asyncio.run(main())
PYEOF
```

### 重启MMS服务
```bash
cd /Users/charlieliu/git_project_vscode/09_medical/mms_platform

# 停止服务
./scripts/stop.sh

# 启动服务（引擎会重新加载词表）
./scripts/start.sh

# 等待服务就绪
sleep 5
curl http://localhost:9100/health
```

### 验证效果
```bash
chmod +x scripts/verify_optimization.sh
./scripts/verify_optimization.sh
```

预期输出：
```
✅ MMS服务运行正常

【测试结果】
----------------------------------------

测试: DR特殊体位1
  项目: X线右肱骨穿胸位摄影
  模态: DR
  ✅ 已匹配
     标准项目: DR右肱骨[近肩]穿胸位
     置信度: 0.95

测试: CT放疗定位
  项目: CT肢体增强放疗定位
  模态: CT
  ✅ 已匹配
     标准项目: CT放射治疗计划扫描
     置信度: 0.90

========================================
验证结果统计
========================================
测试用例总数: 7
成功匹配数: 7
匹配率: 100.0%

🎉 所有测试用例均已匹配！
```

---

## 四、效果评估

### 完整匹配测试
```bash
# 重新匹配所有项目（需要较长时间）
cd /Users/charlieliu/git_project_vscode/09_medical/acrac_web_mgmt/acrac_backend

poetry run python << 'PYEOF'
import asyncio
from sqlalchemy import text
from app.config.database import AsyncSessionLocal
import httpx

async def main():
    async with AsyncSessionLocal() as session:
        # 获取所有未匹配项目
        result = await session.execute(text('''
            SELECT h.id, h.order_name, h.modality_hint
            FROM hospital_check_items h
            LEFT JOIN standard_hospital_mapping m ON m.hospital_item_id = h.id
            WHERE h.is_active = true AND m.standard_item_id IS NULL
            LIMIT 50  -- 先测试50个
        '''))
        items = result.fetchall()
        
        print(f'测试 {len(items)} 个未匹配项目...')
        
        matched = 0
        async with httpx.AsyncClient() as client:
            for item in items:
                try:
                    resp = await client.post(
                        'http://localhost:9100/api/match',
                        json={'text': item.order_name, 'modality': item.modality_hint},
                        timeout=30.0
                    )
                    data = resp.json()
                    if data.get('result', {}).get('matched'):
                        matched += 1
                except Exception as e:
                    print(f'错误: {item.order_name} - {e}')
        
        print(f'\n结果: {matched}/{len(items)} 匹配 ({matched/len(items)*100:.1f}%)')

asyncio.run(main())
PYEOF
```

### 统计匹配率变化
```bash
cd /Users/charlieliu/git_project_vscode/09_medical/acrac_web_mgmt/acrac_backend

poetry run python << 'PYEOF'
import asyncio
from sqlalchemy import text
from app.config.database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text('''
            WITH items AS (
                SELECT 
                    h.id,
                    m.standard_item_id
                FROM hospital_check_items h
                LEFT JOIN standard_hospital_mapping m ON m.hospital_item_id = h.id
                WHERE h.is_active = true
            )
            SELECT 
                COUNT(*) as total,
                COUNT(standard_item_id) as matched
            FROM items
        '''))
        row = result.fetchone()
        
        match_rate = row.matched / row.total * 100
        print(f'总项目: {row.total}')
        print(f'已匹配: {row.matched}')
        print(f'匹配率: {match_rate:.1f}%')
        print(f'未匹配: {row.total - row.matched}')

asyncio.run(main())
PYEOF
```

---

## 五、回滚方案（如果需要）

```bash
cd /Users/charlieliu/git_project_vscode/09_medical/acrac_web_mgmt/acrac_backend

poetry run python << 'PYEOF'
import asyncio
from sqlalchemy import text
from app.config.database import AsyncSessionLocal

async def rollback():
    async with AsyncSessionLocal() as session:
        # 查找最新备份
        result = await session.execute(text('''
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name LIKE 'nlp_phrase_map_backup_%'
            ORDER BY table_name DESC
            LIMIT 1
        '''))
        backup_table = result.scalar()
        
        if backup_table:
            print(f'找到备份: {backup_table}')
            
            # 恢复词表
            await session.execute(text(f'''
                DELETE FROM nlp_phrase_map 
                WHERE created_at > (SELECT MAX(created_at) FROM {backup_table})
            '''))
            
            # 删除新增的标准项目
            await session.execute(text('''
                DELETE FROM standard_check_items
                WHERE item_code LIKE 'RT-%' 
                   OR item_code LIKE 'CONTRAST-%'
                   OR item_code LIKE 'GUIDE-%'
            '''))
            
            await session.commit()
            print('✅ 回滚完成')
        else:
            print('❌ 未找到备份')

asyncio.run(rollback())
PYEOF
```

---

## 六、注意事项

### 6.1 执行前确认
- ✅ 已备份数据库
- ✅ MMS服务正在运行
- ✅ 了解回滚步骤

### 6.2 常见问题

**Q: 执行后匹配率没有提升？**
A: 确认是否重启了MMS服务（引擎需要重新加载词表）

**Q: 部分测试用例仍未匹配？**
A: 可能需要调整词表优先级或增加更多映射规则

**Q: 新增的标准项目编码冲突？**
A: 修改SQL中的item_code，确保唯一性

### 6.3 后续优化建议

如果匹配率仍未达标，可以：
1. 分析仍未匹配的项目特征
2. 补充更多词表映射
3. 调整消歧规则优先级
4. 考虑引入LLM辅助匹配（L3层）

---

## 七、预期效果

### 7.1 数值目标
- **优化前**: 80.8% (998/1235)
- **优化后**: 89%+ (1100+/1235)
- **提升幅度**: +8.2% (~100个项目)

### 7.2 覆盖范围
- DR特殊体位: 13个 → ✅ 已解决
- 放疗定位: 49个 → ✅ 已解决
- 造影检查: 30个 → ✅ 部分解决
- 操作引导: 21个 → ✅ 已解决

---

**实施完成后，请更新 `docs/unmatched_analysis_report.md` 并记录实际效果。**

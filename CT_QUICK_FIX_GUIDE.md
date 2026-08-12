# CT 未匹配问题快速修复指南

## 📋 执行清单

### ✅ 准备工作
- [ ] 阅读完整分析报告: `CT_UNMATCH_ANALYSIS_REPORT.md`
- [ ] 确认数据库连接正常
- [ ] 备份数据库（生产环境）
- [ ] 确认测试环境可用

---

## 🚀 Phase 1: 快速修复（1-2天）

### 步骤1: 预览模态错误修正

```bash
# 查看将要修正的数据（不实际修改）
poetry run python scripts/phase1_quick_fix_ct_unmatch.py --dry-run
```

**预期输出**:
```
发现 X 条 ECT 检查误归为 CT
发现 X 条 US 检查误归为 CT
```

### 步骤2: 应用模态修正

```bash
# 实际修改数据库
poetry run python scripts/phase1_quick_fix_ct_unmatch.py --apply

# 验证修正结果
poetry run python scripts/phase1_quick_fix_ct_unmatch.py --verify-only
```

### 步骤3: 修改引擎代码（技术修饰语过滤）

**文件**: `src/match_service/engine/match_engine_v2/preprocess_service.py`

在 `PreprocessService` 类的 `preprocess` 方法中添加：

```python
class PreprocessService:
    # 在类定义顶部添加
    TECH_NOISE_PATTERNS = [
        r'\(心电门控[^)]*\)',
        r'\(多排螺旋[^)]*\)',
        r'\(多平面重[组建][^)]*\)',
        r'\(容积再现[^)]*\)',
        r'\(三维重建[^)]*\)',
        r'\(MPR[^)]*\)',
        r'\(VR[^)]*\)',
        r'\(骨算法[^)]*\)',
        r'多期增强扫描',
        r'双期增强',
    ]
    
    def preprocess(self, record: str, modality: str, version: str):
        """预处理检查名称"""
        # 原有逻辑：保护方括号
        record, bracket_handler = self._protect_brackets(record)
        
        # 新增：清理技术修饰语噪声（CT/MR专用）
        if modality in ('CT', 'MR'):
            for pattern in self.TECH_NOISE_PATTERNS:
                record = re.sub(pattern, '', record, flags=re.IGNORECASE)
            record = record.strip('()（）')
        
        # 原有逻辑：应用预处理规则
        for rule in self.pre_rules.get(version, []):
            record = re.sub(rule['pattern'], rule['target'], record)
        
        return record, bracket_handler
```

### 步骤4: 运行测试

```bash
# 单元测试
poetry run pytest tests/engine/test_match_engine_v2.py -v

# 回归测试（确保无退化）
poetry run pytest tests/engine/ -v

# 测试技术修饰语过滤效果
poetry run python scripts/phase1_quick_fix_ct_unmatch.py --verify-only --full-rematch
```

**预期**: 应看到 4条 ambiguous 项改善为 exact/partial

### 步骤5: 重启服务

```bash
# 停止服务
./scripts/stop.sh

# 启动服务
./scripts/start.sh

# 检查日志
tail -f logs/backend.log
```

---

## 📚 Phase 2: 标准库扩充（3-5天）

### 步骤1: 确认编码范围

```bash
# 检查编码是否可用
poetry run python -c "
import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect('postgresql://postgres:password@127.0.0.1:15432/acrac_db')
    rows = await conn.fetch(\"\"\"
        SELECT item_code, item_name 
        FROM standard_check_items 
        WHERE item_code BETWEEN '20000000000101' AND '20000000000799'
    \"\"\")
    if rows:
        print(f'⚠️  编码冲突: {len(rows)} 条')
        for r in rows:
            print(f'  {r[\"item_code\"]}: {r[\"item_name\"]}')
    else:
        print('✅ 编码范围可用')
    await conn.close()

asyncio.run(check())
"
```

### 步骤2: 执行SQL（测试环境）

```bash
# 执行标准项补充脚本
poetry run python -c "
import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect('postgresql://postgres:password@127.0.0.1:15432/acrac_db')
    
    # 读取SQL文件
    with open('scripts/phase2_add_vascular_standards.sql', 'r', encoding='utf-8') as f:
        sql = f.read()
    
    # 执行（跳过注释和COMMIT）
    statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
    
    try:
        for stmt in statements:
            if 'BEGIN' in stmt or 'COMMIT' in stmt or not stmt:
                continue
            await conn.execute(stmt)
        
        print('✅ 标准项补充完成')
        
        # 验证
        count = await conn.fetchval(\"\"\"
            SELECT COUNT(*) FROM standard_check_items
            WHERE item_code BETWEEN '20000000000101' AND '20000000000799'
        \"\"\")
        print(f'新增标准项: {count} 条')
        
    except Exception as e:
        print(f'❌ 执行失败: {e}')
        raise
    finally:
        await conn.close()

asyncio.run(run())
"
```

**或者直接使用 psql**:

```bash
# 方式1: 通过管道
cat scripts/phase2_add_vascular_standards.sql | \
  poetry run python -c "import sys; print(sys.stdin.read())" | \
  psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db

# 方式2: 使用 \i 命令（如果psql可用）
# psql -h 127.0.0.1 -p 15432 -U postgres -d acrac_db \
#   -f scripts/phase2_add_vascular_standards.sql
```

### 步骤3: 验证新增标准项

```bash
poetry run python -c "
import asyncio
import asyncpg

async def verify():
    conn = await asyncpg.connect('postgresql://postgres:password@127.0.0.1:15432/acrac_db')
    
    # 按类别统计
    stats = await conn.fetch(\"\"\"
        SELECT 
            CASE 
                WHEN scan_method = 'CTA' THEN '血管成像(CTA)'
                WHEN scan_method = 'CTA+CTV' THEN '动静脉血管'
                WHEN scan_method = '造影' THEN '造影检查'
                ELSE '其他'
            END as category,
            COUNT(*) as count,
            STRING_AGG(item_name, ', ') as items
        FROM standard_check_items
        WHERE item_code BETWEEN '20000000000101' AND '20000000000799'
        GROUP BY category
    \"\"\")
    
    print('新增标准项分类:')
    for r in stats:
        print(f\"  {r['category']}: {r['count']} 条\")
        print(f\"    {r['items']}\")
    
    await conn.close()

asyncio.run(verify())
"
```

### 步骤4: 重新匹配测试

```bash
# 完整重匹配测试
poetry run python scripts/phase1_quick_fix_ct_unmatch.py --verify-only --full-rematch

# 查看改善效果
poetry run python scripts/analyze_ct_mr_unmatched.py
```

**预期效果**:
- ambiguous: 10条 → 8条
- none(standard_lib_gap): 15条 → 5条
- 总体匹配率: 0% → 38.7%

---

## 🔧 Phase 3: 消歧规则优化（2-3天）

### 步骤1: 增强多项拆分规则

**文件**: `src/match_service/engine/match_engine_v2/preprocess_service.py`

在 `split_record` 方法开头添加：

```python
def split_record(self, record: str, modality: str) -> list:
    """拆分多项检查记录"""
    
    # 新增：移除无匹配价值的后缀
    IGNORE_SUFFIXES = [
        r'联合.*?FFR\b',
        r'联合.*?储备分数',
        r'骨算法重建$',
        r'三维重建$',
    ]
    
    for pattern in IGNORE_SUFFIXES:
        record = re.sub(pattern, '', record)
    
    # 原有拆分逻辑
    return self._split_by_separators(record, modality)
```

### 步骤2: 补充消歧规则和词典

```bash
# 执行消歧规则补充
poetry run python -c "
import asyncio
import asyncpg

async def add_rules():
    conn = await asyncpg.connect('postgresql://postgres:password@127.0.0.1:15432/acrac_db')
    
    # 补充医学词典
    await conn.execute(\"\"\"
        INSERT INTO medical_dict (word, pos, category, modality)
        VALUES 
            ('化疗前', 'modifier', 'clinical_context', NULL),
            ('基线', 'modifier', 'clinical_context', NULL),
            ('原发部位', 'body', 'anatomy', 'CT')
        ON CONFLICT (word, pos) DO NOTHING
    \"\"\")
    
    print('✅ 消歧规则补充完成')
    await conn.close()

asyncio.run(add_rules())
"
```

### 步骤3: 测试并部署

```bash
# 运行测试
poetry run pytest tests/engine/ -v

# 重启服务
./scripts/stop.sh && ./scripts/start.sh
```

---

## 📊 验证总体效果

### 最终验证脚本

```bash
# 综合验证
poetry run python -c "
import asyncio
import asyncpg
from collections import Counter

async def final_check():
    conn = await asyncpg.connect('postgresql://postgres:password@127.0.0.1:15432/acrac_db')
    
    # CT未匹配统计
    ct_count = await conn.fetchval(\"\"\"
        SELECT COUNT(DISTINCT p.name_zh)
        FROM unmatched_registry u
        JOIN procedure_dictionary p ON p.id = u.procedure_id
        WHERE u.status='open' AND u.modality='CT'
    \"\"\")
    
    # 按原因分类
    reasons = await conn.fetch(\"\"\"
        SELECT reason_code, COUNT(DISTINCT p.name_zh) as cnt
        FROM unmatched_registry u
        JOIN procedure_dictionary p ON p.id = u.procedure_id
        WHERE u.status='open' AND u.modality='CT'
        GROUP BY reason_code
    \"\"\")
    
    print(f'CT未匹配总数: {ct_count} 项')
    print('\\n原因分布:')
    for r in reasons:
        print(f\"  {r['reason_code']:<30} {r['cnt']:>3} 项\")
    
    await conn.close()

asyncio.run(final_check())
"

# 重新分析
poetry run python scripts/analyze_ct_mr_unmatched.py | head -100
```

---

## 🎯 预期目标

| 指标 | 改进前 | 改进后 | 目标达成 |
|------|--------|--------|---------|
| CT未匹配总数 | 31项 | 12项 | ✅ -61% |
| Ambiguous | 10项 | 4项 | ✅ -60% |
| None(标准库缺口) | 15项 | 5项 | ✅ -67% |
| 匹配率 | 0% | 61.3% | ✅ 达标 |

---

## 🔥 快速开始（5分钟版本）

```bash
# 1. 预览修改
poetry run python scripts/phase1_quick_fix_ct_unmatch.py --dry-run

# 2. 应用修改（如果预览OK）
poetry run python scripts/phase1_quick_fix_ct_unmatch.py --apply

# 3. 修改引擎代码（复制上面的代码片段到 preprocess_service.py）

# 4. 测试
poetry run pytest tests/engine/test_match_engine_v2.py -v

# 5. 重启服务
./scripts/stop.sh && ./scripts/start.sh

# 6. 验证效果
poetry run python scripts/analyze_ct_mr_unmatched.py | head -50
```

---

## ⚠️  注意事项

1. **生产环境部署前必须**:
   - 备份数据库
   - 在测试环境完整验证
   - 执行回归测试
   - 灰度发布（10% → 50% → 100%）

2. **编码分配**:
   - 测试编码: 20000000000101-20000000000799
   - 生产编码: 需要统一分配正式编码

3. **监控指标**:
   - 匹配率（daily）
   - Ambiguous率（daily）
   - 新增未匹配项（daily）

4. **回滚方案**:
   ```bash
   # 回滚数据库（如有备份）
   pg_restore -h 127.0.0.1 -p 15432 -U postgres -d acrac_db backup.dump
   
   # 回滚代码
   git revert <commit_hash>
   ./scripts/stop.sh && ./scripts/start.sh
   ```

---

## 📞 支持

- 完整分析报告: `CT_UNMATCH_ANALYSIS_REPORT.md`
- 技术问题: 查看项目 README.md 故障排查章节
- 数据问题: 检查 `unmatched_registry` 表的 `reason_code` 字段

"""
补充核医学关键词到 phrase_map 表

解决 NM 剩余 33 条未匹配问题：
- 部位词：局部、躯干、头部、全身
- 显像类型：白细胞显像、亲肿瘤显像、心脏显像
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    # 连接数据库
    engine = create_async_engine('postgresql+asyncpg://postgres:password@127.0.0.1:15432/acrac_db')

    # 核医学关键词补充列表
    # 字段：(src_word, dst_word, step, modality, version, enable)
    nm_keywords = [
        # 部位词（PET/CT、PET/MR、SPECT 通用）
        ('局部', '局部', 'normalize', 'SPECT', 'V3.8.2', 1),
        ('局部', '局部', 'normalize', 'PET/CT', 'V3.8.2', 1),
        ('局部', '局部', 'normalize', 'PET/MR', 'V3.8.2', 1),

        ('躯干', '躯干', 'normalize', 'SPECT', 'V3.8.2', 1),
        ('躯干', '躯干', 'normalize', 'PET/CT', 'V3.8.2', 1),
        ('躯干', '躯干', 'normalize', 'PET/MR', 'V3.8.2', 1),

        ('头部', '头部', 'normalize', 'SPECT', 'V3.8.2', 1),
        ('头部', '头部', 'normalize', 'PET/CT', 'V3.8.2', 1),
        ('头部', '头部', 'normalize', 'PET/MR', 'V3.8.2', 1),

        ('全身', '全身', 'normalize', 'SPECT', 'V3.8.2', 1),
        ('全身', '全身', 'normalize', 'PET/CT', 'V3.8.2', 1),
        ('全身', '全身', 'normalize', 'PET/MR', 'V3.8.2', 1),

        # 显像类型关键词
        ('白细胞显像', '白细胞显像', 'normalize', 'SPECT', 'V3.8.2', 1),
        ('放射性核素标记白细胞显像', '白细胞显像', 'normalize', 'SPECT', 'V3.8.2', 1),
        ('放射性核素标记白细胞', '白细胞显像', 'normalize', 'SPECT', 'V3.8.2', 1),

        ('亲肿瘤显像', '亲肿瘤显像', 'normalize', 'SPECT', 'V3.8.2', 1),
        ('亲肿瘤', '亲肿瘤显像', 'normalize', 'SPECT', 'V3.8.2', 1),

        ('心脏显像', '心脏显像', 'normalize', 'SPECT', 'V3.8.2', 1),
    ]

    async with engine.begin() as conn:
        print("=" * 80)
        print("补充核医学关键词到 phrase_map 表")
        print("=" * 80)

        # 检查 nlp_phrase_map 表是否存在
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'nlp_phrase_map'
        """))
        table_exists = result.scalar() > 0

        if not table_exists:
            print("\n❌ nlp_phrase_map 表不存在")
            print("提示：可能需要先运行数据库迁移")
            return

        print(f"\n✅ nlp_phrase_map 表已存在")
        print(f"\n准备插入 {len(nm_keywords)} 条核医学关键词...\n")

        inserted_count = 0
        skipped_count = 0

        for src_word, dst_word, step, modality, version, enable in nm_keywords:
            # 检查是否已存在
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM nlp_phrase_map
                WHERE src_word = :src_word AND modality = :modality
            """), {"src_word": src_word, "modality": modality})

            exists = result.scalar() > 0

            if exists:
                print(f"  ⏭️  跳过（已存在）: [{modality}] {src_word} → {dst_word}")
                skipped_count += 1
                continue

            # 插入新关键词
            await conn.execute(text("""
                INSERT INTO nlp_phrase_map (src_word, dst_word, step, modality, version, enable)
                VALUES (:src_word, :dst_word, :step, :modality, :version, :enable)
            """), {
                "src_word": src_word,
                "dst_word": dst_word,
                "step": step,
                "modality": modality,
                "version": version,
                "enable": enable
            })

            print(f"  ✅ 插入: [{modality}] {src_word} → {dst_word} (step={step})")
            inserted_count += 1

        print("\n" + "=" * 80)
        print(f"✅ 完成！")
        print(f"   新插入: {inserted_count} 条")
        print(f"   已跳过: {skipped_count} 条")
        print(f"   总计: {inserted_count + skipped_count} 条")
        print("=" * 80)

if __name__ == '__main__':
    asyncio.run(main())

"""检查MR_0481是否被引擎加载"""
import asyncio
from match_service.db import get_engine
from match_service.engine.match_engine_v2.data_loader import RuleDataLoader

async def check_mr_0481():
    engine = get_engine()
    loader = RuleDataLoader(engine)
    await loader.initialize()

    # 检查MR标准库
    if 'MR' not in loader.df_standard:
        print("❌ MR标准库未加载")
        return

    if 'V3.8.2' not in loader.df_standard['MR']:
        print("❌ V3.8.2版本未加载")
        return

    mr_standards = loader.df_standard['MR']['V3.8.2']
    print(f"✅ MR标准库已加载: {len(mr_standards)} 条")

    # 查找MR_0481
    mr_0481 = mr_standards[mr_standards['checkitem_code'] == 'MR_0481']

    if mr_0481.empty:
        print("❌ MR_0481 未找到")
    else:
        print(f"✅ MR_0481 已加载:")
        print(mr_0481[['checkitem_code', 'checkitem_name', 'three_level_name', 'scan_name']].to_string())

    # 查找肺动脉相关项
    lung_items = mr_standards[mr_standards['checkitem_name'].str.contains('肺动脉', na=False)]
    print(f"\n所有肺动脉相关标准项 ({len(lung_items)} 条):")
    print(lung_items[['checkitem_code', 'checkitem_name', 'three_level_name', 'scan_name']].to_string())

    await engine.dispose()

if __name__ == '__main__':
    asyncio.run(check_mr_0481())

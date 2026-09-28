#!/usr/bin/env python3
"""
Phase 4测试：泛指词汇降级匹配

测试场景：
1. 关节泛指 → 具体关节（双膝关节、双肩关节等）
2. 骨骼泛指 → 具体骨骼项目
3. 脊柱泛指 → 具体节段
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from match_service.core.engine_holder import get_engine_holder


async def main():
    holder = get_engine_holder()
    await holder.initialize()

    if not holder.is_ready:
        print("❌ 引擎未就绪")
        return

    engine = holder.match_engine

    # 测试用例
    test_cases = [
        # 关节类泛指
        ("CT关节(平扫)", "CT", "关节泛指"),
        ("MR关节(平扫)", "MR", "关节泛指"),
        ("CT膝关节(平扫)", "CT", "膝关节泛指"),
        ("MR肩关节(平扫)", "MR", "肩关节泛指"),

        # 骨骼类泛指
        ("CT骨骼(平扫)", "CT", "骨骼泛指"),
        ("MR骨(平扫)", "MR", "骨泛指"),

        # 脊柱类泛指
        ("CT脊柱(平扫)", "CT", "脊柱泛指"),
        ("MR椎体(平扫)", "MR", "椎体泛指"),

        # 血管类泛指
        ("CT脊髓动脉血管成像(CTA)", "CT", "脊髓动脉泛指"),
        ("MR脊髓静脉血管成像(MRV)", "MR", "脊髓静脉泛指"),
    ]

    print("=" * 100)
    print("Phase 4: 泛指词汇降级匹配测试")
    print("=" * 100)

    success_count = 0
    degraded_count = 0
    failed_count = 0

    for text, modality, category in test_cases:
        result = engine.match(text, modality, "V3.8.2")
        tier = result.get('tier', 'none')
        num_standard = result.get('num_standard', 0)

        status = "✅" if tier in ('exact', 'partial', 'degraded') else "❌"

        if tier == 'degraded':
            degraded_count += 1

        if tier in ('exact', 'partial', 'degraded'):
            success_count += 1
        else:
            failed_count += 1

        print(f"\n{status} [{category}]")
        print(f"   输入: {text}")
        print(f"   模态: {modality}")
        print(f"   结果: tier={tier}, 标准项数={num_standard}")

        if num_standard > 0 and tier == 'degraded':
            # 显示匹配到的标准项（最多3个）
            data = result.get('data', [])
            if data:
                standards = data[0].get('standard', [])[:3]
                print(f"   匹配项:")
                for std in standards:
                    print(f"     - {std.get('name', 'N/A')}")

    print("\n" + "=" * 100)
    print("测试总结:")
    print(f"  总计: {len(test_cases)} 个测试用例")
    print(f"  成功: {success_count} 个 (匹配到标准项)")
    print(f"  其中降级匹配: {degraded_count} 个 (泛指→具体)")
    print(f"  失败: {failed_count} 个 (未匹配)")
    print(f"  成功率: {success_count / len(test_cases) * 100:.1f}%")
    print("=" * 100)

    if degraded_count > 0:
        print(f"\n✅ Phase 4泛指词汇降级匹配已生效！{degraded_count}个泛指词汇成功匹配到具体项目")
    else:
        print(f"\n❌ Phase 4未生效，没有泛指词汇匹配到具体项目")


if __name__ == "__main__":
    asyncio.run(main())

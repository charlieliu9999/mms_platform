#!/usr/bin/env python3
"""测试泛指词汇的分词结果"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from match_service.core.engine_holder import get_engine_holder


async def main():
    holder = get_engine_holder()
    await holder.initialize()

    engine = holder.match_engine

    test_texts = [
        "CT关节(平扫)",
        "MR关节(平扫)",
        "CT骨骼(平扫)",
        "MR骨(平扫)",
    ]

    print("=" * 80)
    print("泛指词汇分词测试")
    print("=" * 80)

    for text in test_texts:
        # 调用引擎的内部方法查看分词结果
        result = engine.match(text, "CT", "V3.8.2", trace={})

        print(f"\n输入: {text}")
        print(f"匹配结果: tier={result.get('tier')}")

        # 查看trace信息
        if 'trace' in result:
            print(f"Trace: {result['trace']}")


if __name__ == "__main__":
    asyncio.run(main())

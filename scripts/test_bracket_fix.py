#!/usr/bin/env python
"""
测试方括号修饰语修复

验证 MR面神经[颅外段](平扫) 等标准项能够正确匹配
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from sqlalchemy.ext.asyncio import create_async_engine
from match_service.engine.match_engine_v2.orchestrator import MatchEngineOrchestrator


async def test_bracket_modifier():
    """测试方括号修饰语匹配"""

    # 创建数据库引擎
    engine = create_async_engine(
        "postgresql+asyncpg://postgres:postgres@127.0.0.1:15432/acrac_db",
        echo=False
    )

    # 初始化匹配引擎
    orchestrator = MatchEngineOrchestrator(engine)
    await orchestrator.initialize()

    # 测试用例
    test_cases = [
        {
            'text': 'MR面神经[颅外段](平扫)',
            'modality': 'MR',
            'expected_match': True,
            'expected_name_contains': '面神经[颅外段]',
            'description': '方括号修饰语 - 平扫'
        },
        {
            'text': 'MR面神经[颅外段](增强)',
            'modality': 'MR',
            'expected_match': True,
            'expected_name_contains': '面神经[颅外段]',
            'description': '方括号修饰语 - 增强'
        },
        {
            'text': 'MR面神经[颅外段](平扫+增强)',
            'modality': 'MR',
            'expected_match': True,
            'expected_name_contains': '面神经[颅外段]',
            'description': '方括号修饰语 - 平扫+增强'
        },
        {
            'text': 'CT颅脑[后颅窝](平扫)',
            'modality': 'CT',
            'expected_match': True,
            'expected_name_contains': '后颅窝',
            'description': 'CT后颅窝'
        },
        {
            'text': 'MR垂体[鞍区](平扫+增强)',
            'modality': 'MR',
            'expected_match': True,
            'expected_name_contains': '垂体',
            'description': 'MR垂体鞍区'
        },
    ]

    print("=" * 80)
    print("方括号修饰语修复测试")
    print("=" * 80)

    passed = 0
    failed = 0

    for i, case in enumerate(test_cases, 1):
        text = case['text']
        modality = case['modality']
        description = case['description']

        print(f"\n测试 #{i}: {description}")
        print(f"输入: {text} (模态: {modality})")

        # 执行匹配
        trace = {}
        result = orchestrator.match(text, modality, trace=trace)

        # 检查结果
        matched = result['num_standard'] > 0
        tier = result.get('tier', 'none')

        # 提取匹配的标准项名称
        matched_names = []
        for item in result.get('data', []):
            for std in item.get('standard', []):
                matched_names.append(std.get('name', ''))

        print(f"匹配结果: {'✅ 成功' if matched else '❌ 失败'}")
        print(f"置信度档: {tier}")
        print(f"标准项数: {result['num_standard']}")

        if matched_names:
            print(f"标准项名称:")
            for name in matched_names:
                print(f"  - {name}")

        # 验证预期
        if case['expected_match']:
            if matched:
                # 检查是否包含预期内容
                expected_contains = case.get('expected_name_contains')
                if expected_contains:
                    found = any(expected_contains in name for name in matched_names)
                    if found:
                        print(f"✅ PASSED - 找到包含 '{expected_contains}' 的标准项")
                        passed += 1
                    else:
                        print(f"❌ FAILED - 未找到包含 '{expected_contains}' 的标准项")
                        failed += 1
                else:
                    print(f"✅ PASSED - 成功匹配")
                    passed += 1
            else:
                print(f"❌ FAILED - 预期匹配但未匹配")
                failed += 1

        # 显示trace信息（调试用）
        if 'bracket_protected' in trace.get('1-bracket_protected', {}):
            print(f"\n方括号保护: {trace['1-bracket_protected']}")
        if '11-bracket_restored' in trace:
            print(f"方括号恢复: 已执行")

    print("\n" + "=" * 80)
    print(f"测试总结: 通过 {passed}/{len(test_cases)}, 失败 {failed}/{len(test_cases)}")
    print("=" * 80)

    await engine.dispose()

    return failed == 0


if __name__ == '__main__':
    success = asyncio.run(test_bracket_modifier())
    sys.exit(0 if success else 1)

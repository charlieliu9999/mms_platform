#!/usr/bin/env python
"""
方括号修饰语处理器单元测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from match_service.engine.match_engine_v2.bracket_modifier_handler import BracketModifierHandler


def test_bracket_protection():
    """测试方括号保护和恢复"""
    handler = BracketModifierHandler()

    test_cases = [
        ('MR面神经[颅外段](平扫)', 'MR面神经[颅外段](平扫)'),
        ('CT颅脑[后颅窝](增强)', 'CT颅脑[后颅窝](增强)'),
        ('MR垂体[鞍区](平扫+增强)', 'MR垂体[鞍区](平扫+增强)'),
        ('MR颅脑(平扫)', 'MR颅脑(平扫)'),  # 无方括号
        ('MR面神经[颅外段]和脑干[中脑](平扫)', 'MR面神经[颅外段]和脑干[中脑](平扫)'),  # 多方括号
    ]

    print("=" * 80)
    print("方括号修饰语处理器单元测试")
    print("=" * 80)

    passed = 0
    failed = 0

    for i, (text, expected) in enumerate(test_cases, 1):
        print(f"\n测试 #{i}: {text}")

        # 保护
        protected = handler.protect_brackets(text)
        print(f"  保护后: {protected}")

        # 检查是否正确替换
        if '[' in text:
            if '\x02BRACKET_' in protected and '[' not in protected:
                print(f"  ✅ 方括号已被保护")
            else:
                print(f"  ❌ 方括号保护失败")
                failed += 1
                continue

        # 恢复
        restored = handler.restore_brackets(protected)
        print(f"  恢复后: {restored}")

        # 验证
        if restored == expected:
            print(f"  ✅ PASSED - 恢复正确")
            passed += 1
        else:
            print(f"  ❌ FAILED - 预期: {expected}, 实际: {restored}")
            failed += 1

        # 显示保护映射
        if handler.get_protected_terms():
            print(f"  保护映射: {handler.get_protected_terms()}")

    print("\n" + "=" * 80)
    print(f"测试总结: 通过 {passed}/{len(test_cases)}, 失败 {failed}/{len(test_cases)}")
    print("=" * 80)

    return failed == 0


def test_bracket_in_standard_name():
    """测试标准项名称中的方括号恢复"""
    handler = BracketModifierHandler()

    # 模拟预处理
    original = "MR面神经[颅外段](平扫)"
    protected = handler.protect_brackets(original)

    # 模拟标准项查询结果（包含占位符）
    standard_names = [
        f"MR{handler._protected_map[list(handler._protected_map.keys())[0]]}(平扫)",
        f"MR{handler._protected_map[list(handler._protected_map.keys())[0]]}",
    ]

    print("\n" + "=" * 80)
    print("标准项名称恢复测试")
    print("=" * 80)
    print(f"原始输入: {original}")
    print(f"保护后: {protected}")
    print(f"模拟标准项（含占位符）: {standard_names}")

    # 恢复标准项名称
    restored_names = [handler.restore_brackets(name) for name in standard_names]
    print(f"恢复后标准项: {restored_names}")

    # 验证恢复结果应该包含原始方括号
    success = all('面神经[颅外段]' in name for name in restored_names)

    if success:
        print("✅ PASSED - 标准项名称中的方括号已正确恢复")
    else:
        print("❌ FAILED - 标准项名称恢复失败")

    return success


if __name__ == '__main__':
    test1 = test_bracket_protection()
    test2 = test_bracket_in_standard_name()

    sys.exit(0 if (test1 and test2) else 1)

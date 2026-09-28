#!/usr/bin/env python
"""
测试部位等价映射

验证 盆腔 ↔ 盆腔及盆底结构 等部位映射能正确工作
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from match_service.engine.match_engine_v2.standard_lookup_service import (
    StandardLookupService,
    BODY_PART_EQUIVALENTS
)


def test_body_part_equivalents():
    """测试部位等价映射表"""
    print("=" * 80)
    print("部位等价映射表测试")
    print("=" * 80)

    print("\n映射关系:")
    for key, values in BODY_PART_EQUIVALENTS.items():
        print(f"{key:15s} -> {values}")

    # 验证双向映射
    print("\n双向映射验证:")
    test_pairs = [
        ("盆腔及盆底结构", "盆腔"),
        ("四肢及关节", "四肢"),
        ("颅脑", "脑"),
    ]

    passed = 0
    failed = 0

    for a, b in test_pairs:
        a_equiv = BODY_PART_EQUIVALENTS.get(a, [])
        b_equiv = BODY_PART_EQUIVALENTS.get(b, [])

        a_has_b = b in a_equiv
        b_has_a = a in b_equiv

        if a_has_b and b_has_a:
            print(f"✅ {a} ↔ {b}")
            passed += 1
        else:
            print(f"❌ {a} ↔ {b} (单向或缺失)")
            failed += 1

    print(f"\n双向映射: 通过 {passed}/{len(test_pairs)}, 失败 {failed}/{len(test_pairs)}")
    return failed == 0


def test_expand_body_equivalents():
    """测试部位扩展方法"""
    print("\n" + "=" * 80)
    print("部位扩展方法测试")
    print("=" * 80)

    test_cases = [
        (["盆腔及盆底结构"], ["盆腔及盆底结构", "盆腔"]),
        (["盆腔"], ["盆腔", "盆腔及盆底结构"]),
        (["四肢及关节"], ["四肢及关节", "四肢", "关节"]),
        (["肝脏"], ["肝脏"]),  # 无映射
        (["颅脑", "盆腔"], None),  # 多个部位，结果集合需包含所有扩展
    ]

    passed = 0
    failed = 0

    for bodies, expected in test_cases:
        result = StandardLookupService._expand_body_equivalents(bodies)
        result_set = set(result)

        print(f"\n输入: {bodies}")
        print(f"输出: {result}")

        if expected is None:
            # 多个部位，只验证包含关系
            required = set()
            for body in bodies:
                required.add(body)
                if body in BODY_PART_EQUIVALENTS:
                    required.update(BODY_PART_EQUIVALENTS[body])

            if required.issubset(result_set):
                print(f"✅ PASSED - 包含所有必需部位")
                passed += 1
            else:
                missing = required - result_set
                print(f"❌ FAILED - 缺失: {missing}")
                failed += 1
        else:
            expected_set = set(expected)
            if result_set == expected_set:
                print(f"✅ PASSED")
                passed += 1
            else:
                print(f"❌ FAILED - 预期: {expected_set}")
                failed += 1

    print(f"\n测试总结: 通过 {passed}/{len(test_cases)}, 失败 {failed}/{len(test_cases)}")
    return failed == 0


if __name__ == '__main__':
    test1 = test_body_part_equivalents()
    test2 = test_expand_body_equivalents()

    print("\n" + "=" * 80)
    if test1 and test2:
        print("✅ 所有测试通过")
        sys.exit(0)
    else:
        print("❌ 部分测试失败")
        sys.exit(1)

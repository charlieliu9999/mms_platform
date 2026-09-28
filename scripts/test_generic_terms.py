"""
测试泛指词汇映射优化

验证：添加"关节""骨骼""全身""血管"等泛指词汇的phrase_map规则后，
原本无法解析的项目能够成功匹配
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from match_service.db import get_engine
from match_service.engine.match_engine_v2 import MatchEngineOrchestrator


async def test_generic_terms():
    engine = get_engine()
    orch = MatchEngineOrchestrator(engine)
    await orch.initialize()

    test_cases = [
        # 关节类（应映射到"四肢及关节"）
        ('X线关节(平扫)', 'DR'),
        ('MR关节(平扫)', 'MR'),
        ('CT关节(平扫)', 'CT'),

        # 骨骼类（应映射到"全身骨骼"）
        ('X线骨骼(平扫)', 'DR'),
        ('CT骨骼(平扫)', 'CT'),

        # 全身类
        ('X线全身骨骼(平扫)', 'DR'),
        ('CT全身(平扫)', 'CT'),

        # 血管类
        ('CT血管成像(CTA)', 'CT'),
        ('MR血管成像(MRA)', 'MR'),
    ]

    print('泛指词汇映射测试')
    print('=' * 120)
    print(f'{"状态":^6} | {"Tier":^10} | {"候选数":^8} | {"置信度":^8} | {"模态":^6} | 检查项目')
    print('-' * 120)

    passed = 0
    failed = 0

    for text, modality in test_cases:
        result = orch.match(text, modality)
        tier = result.get('tier', 'unknown')
        num = result.get('num_standard', 0)
        confidence = result.get('confidence', 0.0)

        # 预期：从 lexicon_gap (tier=none) → degraded/partial (有候选)
        # 或者更好的结果（exact）
        expected_pass = tier in ['exact', 'partial', 'degraded'] and num > 0
        status = '✅' if expected_pass else '❌'

        if expected_pass:
            passed += 1
        else:
            failed += 1

        print(f'{status:^6} | {tier:^10} | {num:^8d} | {confidence:^8.2f} | {modality:^6} | {text}')

        # 显示候选标准项（前3个）
        if num > 0:
            data = result.get('data', [])
            if data and len(data) > 0:
                candidates = []
                for block in data[:1]:  # 只看第一个block
                    for std in block.get('standard', [])[:3]:
                        name = std.get('name', '').lstrip('* ')
                        code = std.get('code', '')
                        candidates.append(f"{code}:{name}")
                if candidates:
                    print(f'       候选: {", ".join(candidates[:2])}')

    await engine.dispose()

    print('=' * 120)
    print(f'\n测试结果: ✅通过 {passed}/{len(test_cases)}, ❌失败 {failed}/{len(test_cases)}')

    if failed == 0:
        print('✅ 所有测试通过！泛指词汇映射优化成功')
    else:
        print(f'⚠️  {failed} 个测试失败，需要进一步调整')


if __name__ == '__main__':
    asyncio.run(test_generic_terms())

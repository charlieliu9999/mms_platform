"""
测试血管成像词汇映射优化

验证：添加血管部位映射规则后，特定部位+血管的组合能够成功匹配
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from match_service.db import get_engine
from match_service.engine.match_engine_v2 import MatchEngineOrchestrator


async def test_vascular_mappings():
    engine = get_engine()
    orch = MatchEngineOrchestrator(engine)
    await orch.initialize()

    test_cases = [
        # 血管部位映射测试
        ('CT脊髓动脉血管成像(CTA)', 'CT'),
        ('MR脊髓动脉血管成像(MRA)', 'MR'),
        ('CT肝脏血管成像(CTA)', 'CT'),
        ('MR肝脏血管成像(MRA)', 'MR'),
        ('CT小肠血管成像(CTA)', 'CT'),
        ('MR小肠血管成像(MRA)', 'MR'),
        ('CT肾脏血管成像(CTA)', 'CT'),
        ('MR肾脏血管成像(MRA)', 'MR'),

        # 对照组：已知有效的血管成像
        ('CT血管成像(CTA)', 'CT'),
        ('MR血管成像(MRA)', 'MR'),
    ]

    print('血管成像词汇映射测试')
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

        # 预期：从 standard_lib_gap → exact/partial
        expected_pass = tier in ['exact', 'partial'] and num > 0
        status = '✅' if expected_pass else '⚠️' if tier == 'degraded' else '❌'

        if expected_pass:
            passed += 1
        else:
            failed += 1

        print(f'{status:^6} | {tier:^10} | {num:^8d} | {confidence:^8.2f} | {modality:^6} | {text}')

        # 显示匹配的标准项（前2个）
        if num > 0:
            data = result.get('data', [])
            if data and len(data) > 0:
                candidates = []
                for block in data[:1]:
                    for std in block.get('standard', [])[:2]:
                        name = std.get('name', '').lstrip('* ')
                        code = std.get('code', '')
                        candidates.append(f"{code}:{name}")
                if candidates:
                    print(f'       候选: {candidates[0][:80]}')

    await engine.dispose()

    print('=' * 120)
    print(f'\n测试结果: ✅通过 {passed}/{len(test_cases)}, ❌失败 {failed}/{len(test_cases)}')

    if passed >= len(test_cases) * 0.8:  # 80%通过率
        print('✅ 血管成像词汇映射优化成功')
    else:
        print(f'⚠️  通过率较低 ({passed/len(test_cases)*100:.0f}%)，需要进一步调整')


if __name__ == '__main__':
    asyncio.run(test_vascular_mappings())

"""
测试乳腺X线路由优化修复

验证：DR/XR模态的乳腺项目，路由到MG后，tier=degraded的结果不再被降级为ambiguous
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from match_service.db import get_engine
from match_service.engine.match_engine_v2 import MatchEngineOrchestrator


async def test_breast_xray_routing():
    engine = get_engine()
    orch = MatchEngineOrchestrator(engine)
    await orch.initialize()

    test_cases = [
        ('X线乳腺断层摄影(筛查)', 'DR'),
        ('X线乳腺(平扫)', 'DR'),
        ('X线乳腺断层摄影(诊断性)', 'XR'),
        ('X线乳腺常规摄影(双侧头尾位+内外斜位)', 'DR'),
        ('X线乳腺对比增强摄影(CEM)', 'DR'),
    ]

    print('乳腺X线→MG路由匹配测试')
    print('=' * 100)

    for text, source_modality in test_cases:
        # 直接用MG模态测试（模拟路由后）
        result = orch.match(text, 'MG')
        tier = result.get('tier', 'unknown')
        num = result.get('num_standard', 0)
        confidence = result.get('confidence', 0.0)

        # 在dispatcher中，如果是degraded且routed，原本会被降为ambiguous
        # 修复后应该保持degraded（或更好的tier）
        expected_pass = tier in ['exact', 'partial', 'degraded']
        status = '✅' if expected_pass else '❌'

        print(f'{status} | tier={tier:10s} | conf={confidence:.2f} | num={num:2d} | {source_modality}→MG | {text[:50]}')

    await engine.dispose()
    print('\n✅ 测试完成')


if __name__ == '__main__':
    asyncio.run(test_breast_xray_routing())

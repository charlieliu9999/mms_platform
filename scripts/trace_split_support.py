#!/usr/bin/env python3
"""验证引擎对"组合方案拆解"的支持：扫描组合(平扫+DWI)与多部位拆解"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

SAMPLES = [
    # 扫描组合
    ("MR", "MR颅脑(平扫+DWI)"),
    ("MR", "MR颅脑平扫+DWI"),
    ("MR", "MR盆腔(平扫+DWI)"),
    ("CT", "CT腹部(平扫+增强)"),
    # 多部位组合
    ("MR", "颅脑、颈椎MR平扫"),
    ("MR", "MR颅脑平扫+颈椎平扫"),
]

STEPS = ("3-make_tree", "7-merge_nodes", "8-body_2process_remap", "10-lookup_standard")


async def main():
    from match_service.core.engine_holder import EngineHolder

    holder = EngineHolder()
    await holder.initialize()
    engine = holder.match_engine

    for mod, name in SAMPLES:
        trace = {}
        res = engine.match(name, mod, trace=trace)
        print("=" * 76)
        print(f"[{mod}] {name}  → tier={res.get('tier')} reason={res.get('reason', '')}")
        stds = res.get("standard_items") or res.get("standard") or []
        print(f"   标准项({len(stds)}): {[s.get('name') for s in stds][:6]}")
        for step in STEPS:
            v = trace.get(step)
            if v:
                print(f"   [{step}]")
                for s in v[:10]:
                    print(f"      {s}")
    await holder.dispose()


if __name__ == "__main__":
    asyncio.run(main())

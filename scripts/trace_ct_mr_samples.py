#!/usr/bin/env python3
"""对 CT/MR none/ambiguous 代表样本做深度 trace，定位 lookup 失败根因"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

SAMPLES = [
    ("MR", "MR头颈部(平扫+增强)"),
    ("MR", "MR脑(平扫+DWI)"),
    ("MR", "MR盆腔(平扫+DWI)"),
    ("MR", "MR脊髓(平扫+增强)"),
    ("MR", "MR关节(平扫)"),
    ("MR", "MR全消化道(平扫)"),
    ("MR", "MR支气管(平扫+增强)"),
    ("MR", "MR上肢静脉血管成像(MRV)"),
    ("MR", "MR肺动脉血管成像(MRA)"),
    ("CT", "CT全脊柱(平扫+增强)"),
    ("CT", "CT乳腺(平扫+增强)"),
    ("CT", "CT腹部盆腔(平扫+动静脉双期增强)"),
    ("CT", "CT肩关节(直接造影)"),
    ("MR", "MR面神经[颅外段](平扫)"),
    ("MR", "MR盆腔动态增强扫描(DCE-MRI)"),
]


async def main():
    from match_service.core.engine_holder import EngineHolder

    holder = EngineHolder()
    await holder.initialize()
    engine = holder.match_engine

    for mod, name in SAMPLES:
        trace = {}
        res = engine.match(name, mod, trace=trace)
        print("=" * 76)
        print(f"[{mod}] {name}  → tier={res.get('tier')} reason={res.get('reason','')}")
        data = res.get("data") or []
        for d in data:
            std = d.get("standard") or []
            print(f"   raw={d.get('raw')!r}  standard={[s.get('name') for s in std]}")
        for step in ("3-make_tree", "8-body_2process_remap", "8.5-normalize_vascular",
                     "8.6-dedup_query_equivalent", "9-find_default_process",
                     "10-lookup_standard"):
            val = trace.get(step)
            if val:
                print(f"   {step}:")
                for s in val[:6]:
                    print(f"      {s}")
        ops = trace.get("op")
        if ops:
            print(f"   op: {ops[:10]}")
    await holder.dispose()


if __name__ == "__main__":
    asyncio.run(main())

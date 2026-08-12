#!/usr/bin/env python3
"""
修复"静脉+CTA/MRA"错误组合问题

问题: 用户输入"颈静脉CTA"时，引擎将CTA识别为动脉造影，
导致查询"颈部动静脉血管成像"，但标准库中只有"颈部静脉血管成像(CTV)"

解决: 在预处理阶段，将"静脉+CTA"自动纠正为"静脉+CTV"
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from match_service.db import get_session_factory


async def fix_vein_cta():
    factory = get_session_factory()
    
    async with factory() as session:
        print("=== 修复静脉+CTA错误组合 ===\n")
        
        # 删除可能存在的旧规则
        await session.execute(text("""
            DELETE FROM nlp_phrase_map 
            WHERE src_word IN ('静脉CTA', '静脉血管CTA', '静脉造影CTA',
                               '静脉MRA', '静脉血管MRA', '静脉造影MRA')
        """))
        
        # 添加CT静脉纠正规则(在pre步骤，优先级最高)
        rules = [
            # CT静脉
            ('CT', '静脉CTA', '静脉CTV', 'pre'),
            ('CT', '静脉血管CTA', '静脉血管CTV', 'pre'),
            
            # MR静脉
            ('MR', '静脉MRA', '静脉MRV', 'pre'),
            ('MR', '静脉血管MRA', '静脉血管MRV', 'pre'),
        ]
        
        for modality, src, dst, step in rules:
            await session.execute(text("""
                INSERT INTO nlp_phrase_map (modality, src_word, dst_word, step, version, enable)
                VALUES (:modality, :src, :dst, :step, 'V3.8.2', 0)
            """), {"modality": modality, "src": src, "dst": dst, "step": step})
            print(f"✅ 添加规则: [{modality}] {src} → {dst}")
        
        await session.commit()
        
        print(f"\n✓ 已添加 {len(rules)} 条纠正规则")
        print("\n⚠️  需要重启后端服务以生效:")
        print("  ./scripts/stop.sh && ./scripts/start.sh")


if __name__ == "__main__":
    asyncio.run(fix_vein_cta())

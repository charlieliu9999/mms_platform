#!/usr/bin/env python3
"""
从 VPS 原系统导出 ACR 项目数据
在 VPS 服务器上执行此脚本
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import json
import sys

# VPS 数据库连接（请根据实际情况修改）
DATABASE_URL = "postgresql+asyncpg://postgres:你的密码@127.0.0.1:5432/acrac_db"

async def export_acr_procedures():
    engine = create_async_engine(DATABASE_URL)

    try:
        async with engine.begin() as conn:
            # 导出 ACR 项目数据
            result = await conn.execute(text("""
                SELECT
                    id,
                    semantic_id,
                    name_en,
                    name_zh,
                    modality,
                    body_part,
                    contrast_used,
                    radiation_level,
                    exam_duration,
                    standard_code,
                    description_zh,
                    is_active
                FROM procedure_dictionary
                WHERE is_active = true
                ORDER BY id
            """))

            rows = result.fetchall()
            print(f"✅ 导出 {len(rows)} 条 ACR 项目数据", file=sys.stderr)

            # 转换为字典列表
            procedures = []
            for row in rows:
                procedures.append({
                    'id': row[0],
                    'semantic_id': row[1],
                    'name_en': row[2],
                    'name_zh': row[3],
                    'modality': row[4],
                    'body_part': row[5],
                    'contrast_used': row[6],
                    'radiation_level': row[7],
                    'exam_duration': row[8],
                    'standard_code': row[9],
                    'description_zh': row[10],
                    'is_active': row[11]
                })

            # 统计模态分布
            modality_stats = {}
            for proc in procedures:
                mod = proc['modality'] or 'NULL'
                modality_stats[mod] = modality_stats.get(mod, 0) + 1

            print("\n模态分布:", file=sys.stderr)
            for mod, count in sorted(modality_stats.items(), key=lambda x: -x[1]):
                print(f"  {mod}: {count}", file=sys.stderr)

            # 输出 JSON（到 stdout，可以重定向到文件）
            print(json.dumps(procedures, ensure_ascii=False, indent=2))

    finally:
        await engine.dispose()

if __name__ == '__main__':
    asyncio.run(export_acr_procedures())

#!/usr/bin/env python3
"""Freeze the reviewed ACR PR-series cohort into a versioned manifest.

This is a governance operation, not part of normal evaluation. The command
refuses to replace an existing manifest unless ``--force`` is explicit.
"""

import argparse
import asyncio
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text

from match_service.db import get_engine, get_session_factory

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "data/evaluation/acr_4555_manifest.csv"
EXPECTED_COUNT = 4555
DATASET_ID = "acr-4555-pr-v1"
SOURCE_FILTER = "is_active = true AND semantic_id ~ '^PR[0-9]+$'"


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    metadata_path = args.output.with_suffix(".meta.json")
    if not args.force and (args.output.exists() or metadata_path.exists()):
        parser.error("manifest exists; pass --force only after dataset review approval")

    factory = get_session_factory()
    engine = get_engine()
    try:
        async with factory() as session:
            rows = (
                await session.execute(
                    text(
                        "SELECT semantic_id, name_zh, modality "
                        "FROM procedure_dictionary "
                        f"WHERE {SOURCE_FILTER} ORDER BY semantic_id"
                    )
                )
            ).all()
            db_revision = (
                await session.execute(text("SELECT version_num FROM alembic_version"))
            ).scalar_one()
    finally:
        await engine.dispose()

    if len(rows) != EXPECTED_COUNT:
        parser.error(f"refusing to freeze {len(rows)} records; expected {EXPECTED_COUNT}")
    semantic_ids = [row[0] for row in rows]
    if len(set(semantic_ids)) != EXPECTED_COUNT:
        parser.error("refusing to freeze duplicate semantic_id values")
    if any(not row[1] or not row[2] for row in rows):
        parser.error("refusing to freeze blank name_zh or modality values")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["semantic_id", "name_zh", "modality"])
        writer.writerows(rows)

    metadata = {
        "schema_version": 1,
        "dataset_id": DATASET_ID,
        "dataset_version": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "expected_count": EXPECTED_COUNT,
        "id_field": "semantic_id",
        "id_pattern": "^PR[0-9]+$",
        "source_table": "procedure_dictionary",
        "source_filter": SOURCE_FILTER,
        "source_database_revision": db_revision,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": sha256_file(args.output),
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"frozen {EXPECTED_COUNT} records: {args.output}")
    print(f"manifest_sha256: {metadata['manifest_sha256']}")


if __name__ == "__main__":
    asyncio.run(main())

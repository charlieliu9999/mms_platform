#!/usr/bin/env python3
"""Verify the independent runtime DB, tables, sequences, content and HTTP readiness."""
import argparse
import asyncio
import json
from pathlib import Path
import sys
import urllib.request
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from migrate_to_mms_db import TABLES, connect, fingerprint, identifier
from match_service.config import get_settings


async def verify(args):
    url = get_settings().DATABASE_URL
    if urlsplit(url).path != '/mms_db':
        raise ValueError('Runtime configuration must point to mms_db')
    if get_settings().ENGINE_MODE != 'local':
        raise ValueError('Runtime must use the built-in local engine')
    manifest = json.loads(args.manifest.read_text()) if args.manifest.exists() else None
    connection = await connect(url)
    report = {'database': 'mms_db', 'engine_mode': 'local', 'tables': {}}
    try:
        async with connection.transaction(readonly=True, isolation='repeatable_read'):
            if await connection.fetchval('SELECT current_database()') != 'mms_db':
                raise ValueError('Connected to wrong database')
            revision = await connection.fetchval('SELECT version_num FROM mms_schema_version')
            if revision != args.schema_revision:
                raise ValueError(f'Unexpected independent schema revision: {revision}')
            report['schema_revision'] = revision
            report['rule_migration_revision'] = await connection.fetchval('SELECT version_num FROM alembic_version')
            for table in TABLES:
                actual = await fingerprint(connection, table)
                report['tables'][table] = actual
                if args.strict_content:
                    if not manifest or actual != manifest['tables'][table]['target']:
                        raise ValueError(f'Migrated content differs: {table}')
                print(f"OK {table}: {actual['rows']:,} rows")
                for row in await connection.fetch(
                    "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=$1", table):
                    column = row['column_name']
                    seq = await connection.fetchval('SELECT pg_get_serial_sequence($1,$2)', 'public.' + table, column)
                    if not seq:
                        continue
                    qualified = '.'.join(identifier(p.strip('"')) for p in seq.split('.'))
                    state = await connection.fetchrow(f'SELECT last_value,is_called FROM {qualified}')
                    maximum = await connection.fetchval(f'SELECT MAX({identifier(column)}) FROM public.{identifier(table)}')
                    next_id = state['last_value'] + int(state['is_called'])
                    if maximum is not None and next_id <= maximum:
                        raise ValueError(f'Unsafe sequence: {seq}')
    finally:
        await connection.close()
    if args.base_url:
        health = json.load(urllib.request.urlopen(args.base_url.rstrip('/') + '/api/health', timeout=10))
        if health.get('engine_ready') is not True or health.get('status') != 'ok':
            raise ValueError('HTTP business health is not ready')
        report['health'] = health
    report['status'] = 'passed'
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Independent database validation passed:', args.report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'analysis/mms-db-migration/migration.json')
    parser.add_argument('--strict-content', action='store_true', help='Before serving traffic, compare every migrated row')
    parser.add_argument('--schema-revision', default='20260926_0100', help='Expected audited schema head')
    parser.add_argument('--base-url', help='Also require business health from this HTTP server')
    parser.add_argument('--report', type=Path, default=ROOT / 'analysis/mms-db-migration/runtime-validation.json')
    asyncio.run(verify(parser.parse_args()))

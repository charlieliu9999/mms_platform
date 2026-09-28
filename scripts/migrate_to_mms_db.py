#!/usr/bin/env python3
"""Copy MMS data from one read-only source snapshot into an independent DB.

No source writes or data backups. Refuse nonempty targets. Copy all table data
in one transaction; verify complete content hashes before commit.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
CORE_TABLES = (
    'nlp_medical_dict', 'nlp_phrase_map', 'nlp_ambiguity',
    'standard_check_items', 'match_cache', 'match_feedback',
    'lexicon_suggestion', 'procedure_dictionary', 'procedure_match_results',
    'unmatched_registry',
)
DEPENDENCY_TABLES = (
    'keyword_match_rules', 'mms_eval_tasks', 'mms_eval_details',
    'mms_lexicon_versions', 'mms_optimization_suggestions',
    'technical_detail_candidates', 'technical_detail_candidate_revisions',
    'technical_detail_publications', 'technical_detail_provenance',
)
TABLES = CORE_TABLES + DEPENDENCY_TABLES + ('alembic_version',)


def identifier(value):
    return '"' + value.replace('"', '""') + '"'


def driver_url(url):
    parsed = urlsplit(url)
    if parsed.scheme not in {'postgresql', 'postgresql+asyncpg'}:
        raise ValueError('Only PostgreSQL/asyncpg URLs are supported')
    return urlunsplit(parsed._replace(scheme='postgresql'))


def sqlalchemy_url(url):
    return urlunsplit(urlsplit(url)._replace(scheme='postgresql+asyncpg'))


def database_label(url):
    parsed = urlsplit(url)
    return {'host': parsed.hostname, 'port': parsed.port or 5432,
            'database': parsed.path.lstrip('/')}


async def connect(url):
    return await asyncpg.connect(driver_url(url), timeout=10,
        server_settings={'application_name': 'mms-data-migration', 'timezone': 'UTC'})


async def fingerprint(connection, table):
    # Hash every canonical JSON row, including nulls, nested JSON and duplicates.
    digest = hashlib.sha256()
    count = 0
    async for row in connection.cursor(
        f'SELECT to_jsonb(t)::text FROM public.{identifier(table)} t '
        'ORDER BY to_jsonb(t)::text', prefetch=1000
    ):
        payload = row[0].encode('utf-8')
        digest.update(len(payload).to_bytes(8, 'big'))
        digest.update(payload)
        count += 1
    return {'rows': count, 'sha256': digest.hexdigest()}


async def columns(connection, table):
    return await connection.fetch(
        'SELECT column_name,udt_name,is_nullable,column_default,'
        'character_maximum_length,numeric_precision,numeric_scale '
        "FROM information_schema.columns WHERE table_schema='public' "
        'AND table_name=$1 ORDER BY ordinal_position', table)


async def constraints(connection, table):
    return await connection.fetch(
        'SELECT conname,contype,pg_get_constraintdef(oid) AS definition '
        'FROM pg_constraint WHERE conrelid=$1::regclass ORDER BY conname',
        'public.' + table)


async def indexes(connection, table):
    return await connection.fetch(
        "SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='public' "
        'AND tablename=$1 ORDER BY indexname', table)


async def triggers(connection, table):
    return await connection.fetch(
        'SELECT tgname,pg_get_triggerdef(oid) AS definition FROM pg_trigger '
        'WHERE tgrelid=$1::regclass AND NOT tgisinternal '
        "AND tgname <> 'trg_acrac_vector_sync' ORDER BY tgname", 'public.' + table)


async def ensure_target(source_url, target_url):
    source, target = database_label(source_url), database_label(target_url)
    if source == target or target['database'] == 'acrac_db':
        raise ValueError('Refusing to create a target that is the main/source DB')
    parsed = urlsplit(target_url)
    admin = await connect(urlunsplit(parsed._replace(path='/postgres')))
    try:
        exists = await admin.fetchval('SELECT 1 FROM pg_database WHERE datname=$1', target['database'])
        if not exists:
            await admin.execute('CREATE DATABASE ' + identifier(target['database']) + " TEMPLATE template0 ENCODING 'UTF8'")
            print('Created target database:', target['database'])
    finally:
        await admin.close()
    env = dict(os.environ, MATCH_SVC_DATABASE_URL=sqlalchemy_url(target_url))
    subprocess.run([sys.executable, '-m', 'alembic', '-c', 'alembic-mms.ini', 'upgrade', 'head'],
                   cwd=ROOT, env=env, check=True)


async def copy_table(source, target, table):
    source_columns, target_columns = await columns(source, table), await columns(target, table)
    if not source_columns or source_columns != target_columns:
        raise ValueError(f'Missing table or schema mismatch: {table}')
    names = [r['column_name'] for r in source_columns]
    batch, count = [], 0
    async for row in source.cursor(f'SELECT * FROM public.{identifier(table)}', prefetch=1000):
        batch.append(tuple(row))
        if len(batch) == 1000:
            await target.copy_records_to_table(table, schema_name='public', columns=names, records=batch)
            count += len(batch)
            batch.clear()
    if batch:
        await target.copy_records_to_table(table, schema_name='public', columns=names, records=batch)
        count += len(batch)
    print(f'Copied {table}: {count:,} rows')


async def sync_sequences(source, target):
    state = {}
    for table in TABLES:
        if table == 'alembic_version':
            continue
        for column in await columns(source, table):
            name = column['column_name']
            seq = await source.fetchval('SELECT pg_get_serial_sequence($1,$2)', 'public.' + table, name)
            if not seq:
                continue
            qualified = '.'.join(identifier(part.strip('"')) for part in seq.split('.'))
            row = await source.fetchrow(f'SELECT last_value,is_called FROM {qualified}')
            maximum = await target.fetchval(f'SELECT MAX({identifier(name)}) FROM public.{identifier(table)}')
            last_value = max(row['last_value'], maximum or 1)
            called = row['is_called'] or (maximum is not None and last_value <= maximum)
            await target.execute('SELECT setval($1::regclass,$2::bigint,$3::boolean)', seq, last_value, called)
            state[seq] = {'last_value': last_value, 'is_called': called}
    return state


async def run(args):
    from match_service.config import get_settings
    source_url = args.source_url or os.environ.get('MMS_MIGRATION_SOURCE_URL') or get_settings().DATABASE_URL
    target_url = args.target_url or os.environ.get('MMS_MIGRATION_TARGET_URL')
    if not target_url:
        target_url = urlunsplit(urlsplit(source_url)._replace(path='/mms_db'))
    if database_label(source_url) == database_label(target_url):
        raise ValueError('Source and target are identical; set MMS_MIGRATION_SOURCE_URL explicitly')
    if database_label(target_url)['database'] == 'acrac_db':
        raise ValueError('Main database cannot be a migration target')
    if args.create and args.verify_only:
        raise ValueError('--create cannot be combined with --verify-only')
    print('Source:', database_label(source_url), 'Target:', database_label(target_url))
    if args.create and not args.dry_run and not args.verify_only:
        await ensure_target(source_url, target_url)
    source, target = await connect(source_url), None
    report = {'generated_at': datetime.now(timezone.utc).isoformat(),
              'source': database_label(source_url), 'target': database_label(target_url),
              'mode': 'dry-run' if args.dry_run else 'verify' if args.verify_only else 'migrate',
              'tables': {}, 'core_tables': list(CORE_TABLES),
              'dependency_tables': list(DEPENDENCY_TABLES),
              'excluded_source_triggers': {
                  'procedure_dictionary.trg_acrac_vector_sync':
                  'Main-project vector outbox depends on clinical_recommendations; '
                  'excluded from independent MMS, source trigger retained.'}}
    try:
        async with source.transaction(isolation='repeatable_read', readonly=True):
            if args.dry_run:
                for table in TABLES:
                    report['tables'][table] = {'source': await fingerprint(source, table)}
            else:
                target = await connect(target_url)
                async with target.transaction(isolation='repeatable_read', readonly=args.verify_only):
                    if not args.verify_only:
                        # Preflight every table before any data insert.
                        for table in TABLES:
                            if await target.fetchval(f'SELECT COUNT(*) FROM public.{identifier(table)}'):
                                raise ValueError(f'Target not empty: {table}; refusing overwrite')
                        # VPS catalogs retain FKs from standards/results/registry
                        # to procedure_dictionary. Load the parent before children.
                        copy_order = ('procedure_dictionary',) + tuple(
                            table for table in TABLES if table != 'procedure_dictionary'
                        )
                        for table in copy_order:
                            await copy_table(source, target, table)
                    for table in TABLES:
                        before, after = await fingerprint(source, table), await fingerprint(target, table)
                        if await columns(source, table) != await columns(target, table):
                            raise ValueError(f'Schema mismatch: {table}')
                        if await constraints(source, table) != await constraints(target, table):
                            raise ValueError(f'Constraint mismatch: {table}')
                        if await indexes(source, table) != await indexes(target, table):
                            raise ValueError(f'Index mismatch: {table}')
                        if await triggers(source, table) != await triggers(target, table):
                            raise ValueError(f'Trigger mismatch: {table}')
                        report['tables'][table] = {'source': before, 'target': after, 'equal': before == after}
                        if before != after:
                            raise ValueError(f'Full content verification failed: {table}')
                    if not args.verify_only:
                        report['sequences'] = await sync_sequences(source, target)
        report['core_rows'] = sum(report['tables'][t]['source']['rows'] for t in CORE_TABLES)
        report['dependency_rows'] = sum(report['tables'][t]['source']['rows'] for t in DEPENDENCY_TABLES)
        report['verified'] = not args.dry_run
        report['status'] = 'complete' if not args.dry_run else 'planned'
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(f"{'Verified' if report['verified'] else 'Planned'}: {report['core_rows']:,} core rows + "
              f"{report['dependency_rows']:,} dependency rows; report: {args.report}")
    finally:
        await source.close()
        if target:
            await target.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-url', help='Prefer MMS_MIGRATION_SOURCE_URL to avoid credentials in history')
    parser.add_argument('--target-url', help='Prefer MMS_MIGRATION_TARGET_URL')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--verify-only', action='store_true')
    parser.add_argument('--create', action='store_true', help='Create DB and apply independent Alembic schema')
    parser.add_argument('--report', type=Path, default=ROOT / 'analysis/mms-db-migration/migration.json')
    asyncio.run(run(parser.parse_args()))


if __name__ == '__main__':
    main()

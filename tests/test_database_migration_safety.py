"""Optional live migration safety tests on a disposable Alembic-managed database.

Set MMS_MIGRATION_TEST_SOURCE_URL and MMS_MIGRATION_TEST_TARGET_URL. Never point
TEST_TARGET at mms_db or acrac_db; this suite recreates only the rehearsal schema.
"""
import argparse
import asyncio
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('mms_db_migration', ROOT / 'scripts/migrate_to_mms_db.py')
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


@pytest.fixture
def scratch_database(tmp_path):
    source = os.environ.get('MMS_MIGRATION_TEST_SOURCE_URL')
    target = os.environ.get('MMS_MIGRATION_TEST_TARGET_URL')
    if not source or not target:
        pytest.skip('Disposable migration test database is not configured')
    name = migration.database_label(target)['database']
    assert name.startswith('mms_db_rehearsal_'), 'Refuse non-rehearsal target'
    env = dict(os.environ, MATCH_SVC_DATABASE_URL=migration.sqlalchemy_url(target))
    for action in [('downgrade', 'base'), ('upgrade', 'head')]:
        subprocess.run([sys.executable, '-m', 'alembic', '-c', 'alembic-mms.ini', *action],
                       cwd=ROOT, env=env, check=True)
    return argparse.Namespace(source_url=source, target_url=target, create=False,
                              dry_run=False, verify_only=False, report=tmp_path / 'report.json')


def test_same_database_is_rejected_before_connection(tmp_path):
    args = argparse.Namespace(source_url='postgresql://user@example.invalid/mms_db',
                              target_url='postgresql://user@example.invalid/mms_db',
                              create=False, dry_run=False, verify_only=False, report=tmp_path / 'report.json')
    with pytest.raises(ValueError, match='identical'):
        asyncio.run(migration.run(args))


def test_failure_after_all_inserts_rolls_back_every_table(scratch_database, monkeypatch):
    async def fail_verification(*args):
        raise RuntimeError('Injected late verification failure')
    monkeypatch.setattr(migration, 'fingerprint', fail_verification)
    with pytest.raises(RuntimeError, match='Injected late'):
        asyncio.run(migration.run(scratch_database))

    async def assert_empty():
        target = await migration.connect(scratch_database.target_url)
        try:
            for table in migration.TABLES:
                assert await target.fetchval(f'SELECT COUNT(*) FROM public.{migration.identifier(table)}') == 0
        finally:
            await target.close()
    asyncio.run(assert_empty())
    assert not scratch_database.report.exists()


def test_complete_copy_and_retry_refuses_to_overwrite(scratch_database):
    asyncio.run(migration.run(scratch_database))
    import json
    before = json.loads(scratch_database.report.read_text())
    assert before['verified']
    assert all(t['equal'] for t in before['tables'].values())
    with pytest.raises(ValueError, match='Target not empty'):
        asyncio.run(migration.run(scratch_database))
    scratch_database.verify_only = True
    asyncio.run(migration.run(scratch_database))
    after = json.loads(scratch_database.report.read_text())
    assert before['tables'] == after['tables']

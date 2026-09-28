# MMS independent database release

Source release: aa1c1dd48ea90b5bc8670b95aacee2b0a07d0928 (VPS deployment 2026-09-26).

This publication snapshot keeps the deployed application and Alembic migrations. Runtime environment files, database backups, cache exports and private hospital benchmark CSVs are excluded. Credentials and live database contents are configured separately. Canonical ACR evaluation manifests and finalized lexicon fixtures remain in the source.

Validation recorded at deployment: backend 273 passed, 0 failed, 4 skipped; disposable migration rehearsal 3 passed; VPS ACR-4555 matching 3931 to 3932, zero regressions. Local and VPS datasets differ; these are VPS results.

The source code is unchanged by publication. This snapshot starts a new history so excluded runtime artifacts are not transmitted through older commits. It does not include unrelated uncommitted work in the shared workspace.

Schema setup: alembic -c alembic-mms.ini upgrade head. Data migration refuses nonempty targets. See scripts/migrate_to_mms_db.py and scripts/verify_mms_db_running.py.

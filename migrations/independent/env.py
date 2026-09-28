"""Independent schema history, separate from historical rule migrations."""
import asyncio
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool
from match_service.config import get_settings


def configure(connection):
    context.configure(connection=connection, version_table="mms_schema_version")
    with context.begin_transaction():
        context.run_migrations()


async def run():
    engine = create_async_engine(get_settings().DATABASE_URL, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(configure)
    await engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("MMS bootstrap requires an online PostgreSQL connection")
else:
    asyncio.run(run())


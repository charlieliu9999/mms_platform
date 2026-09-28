"""Alembic 运行环境 — 复用服务自身配置与模型元数据。

设计要点：
- DATABASE_URL 从 match_service.config 读取，不在 alembic.ini 硬编码，
  确保迁移与服务运行时连同一个库（配置单一来源）。
- 使用 async engine（asyncpg），与服务运行时驱动一致，
  避免同步/异步驱动差异导致的方言行为不一致。
- target_metadata 指向 cache.models.Base，autogenerate 才能比对出差异。
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

from match_service.cache.models import Base
from match_service.config import get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# 从服务配置注入实际连接串，覆盖 ini 中的占位值
config.set_main_option("sqlalchemy.url", get_settings().DATABASE_URL)


def include_object(object, name, type_, reflected, compare_to):
    """过滤 autogenerate 范围：只管理 match_service cache 三表。

    与 acrac_backend 共用数据库时，忽略非 cache 表（backend 的业务表由
    backend 自己的迁移管理），避免 autogenerate 误报 removed table。
    """
    if type_ == "table":
        # 只管理 cache 表（白名单），其他全忽略
        return name in {"match_cache", "match_feedback", "lexicon_suggestion"}
    # 索引/约束：跟随表决策
    return True


def run_migrations_offline() -> None:
    """离线模式：仅生成 SQL 脚本，不连库。用于审阅将要执行的 DDL。"""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # 侦测列类型变更（默认关闭，会漏掉 String(20)→String(30) 这类改动）
        compare_type=True,
        # 侦测服务端默认值变更
        compare_server_default=True,
        # 只管理 cache 三表（过滤 backend 业务表）
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

from logging.config import fileConfig
import os
import asyncio
from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from app.core.config import settings
from app.models import Base

config=context.config
if config.config_file_name:fileConfig(config.config_file_name)
url=os.getenv("DATABASE_URL",settings.database_url)
config.set_main_option("sqlalchemy.url",url)
target_metadata=Base.metadata

def run_migrations_offline():
    context.configure(url=url,target_metadata=target_metadata,literal_binds=True,compare_type=True)
    with context.begin_transaction():context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection,target_metadata=target_metadata,compare_type=True)
    with context.begin_transaction():context.run_migrations()

async def run_async_migrations():
    connectable=async_engine_from_config(config.get_section(config.config_ini_section),prefix="sqlalchemy.",poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online():
    asyncio.run(run_async_migrations())

run_migrations_offline() if context.is_offline_mode() else run_migrations_online()

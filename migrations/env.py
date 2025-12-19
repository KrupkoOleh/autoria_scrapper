import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from src.database import Base
from src.models import Car
from src.config import settings

config = context.config
target_metadata = Base.metadata

connectable = create_async_engine(settings.DATABASE_URL_asyncpg)

async def do_run_migrations():
    async with connectable.connect() as connection:
        await connection.run_sync(do_migrations)

def do_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    asyncio.run(do_run_migrations())

if context.is_offline_mode():
    context.configure(url=settings.DATABASE_URL_asyncpg,
                      target_metadata=target_metadata,
                      literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    run_migrations_online()
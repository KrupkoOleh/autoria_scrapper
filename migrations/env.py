from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from src.database import Base
from src.config import settings

config = context.config

target_metadata = Base.metadata


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = create_async_engine(
        settings.DATABASE_URL_asyncpg,
        poolclass=pool.NullPool,
    )

    import asyncio

    async def do_run_migrations():
        async with connectable.connect() as connection:
            await connection.run_sync(do_migrations)

    def do_migrations(connection):
        context.configure(connection=connection,
                          target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

    asyncio.run(do_run_migrations())


if context.is_offline_mode():
    context.configure(url=settings.DATABASE_URL_asyncpg,
                      target_metadata=target_metadata,
                      literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    run_migrations_online()

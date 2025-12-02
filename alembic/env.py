from __future__ import annotations

import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context
from app.config.config import settings  
# -------------------------------------------------------------
# Import your models' metadata here
# -------------------------------------------------------------
# Example: replace with your Base import
from app.models import Base


# Ensure Alembic loads pgvector type
from pgvector.sqlalchemy import Vector  # noqa

# -------------------------------------------------------------
# Alembic setup
# -------------------------------------------------------------
config = context.config
config.set_main_option('sqlalchemy.url', str(settings.database_url_sync))
fileConfig(config.config_file_name)
target_metadata = Base.metadata


# -------------------------------------------------------------
# Type comparator to prevent pgvector ndim errors
# -------------------------------------------------------------
def compare_types(context, inspected_type, metadata_type) -> bool:
    """
    Fix Alembic autogenerate for pgvector by only comparing dimensions.
    Prevents 'ValueError: expected ndim to be 1'.
    """
    if isinstance(inspected_type, Vector) and isinstance(metadata_type, Vector):
        return inspected_type.dim != metadata_type.dim
    return False


# -------------------------------------------------------------
# Offline migrations
# -------------------------------------------------------------
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        type_comparator=compare_types,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# -------------------------------------------------------------
# Online migrations
# -------------------------------------------------------------
def run_migrations_online() -> None:
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            type_comparator=compare_types,
            render_as_batch=False,
        )

        with context.begin_transaction():
            context.run_migrations()


# -------------------------------------------------------------
# Run mode switch
# -------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

import os
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from relayops.db import Base, normalize_url
from relayops import db  # noqa: F401

config = context.config
url = normalize_url(os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url")))
config.set_main_option("sqlalchemy.url", url)
target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    engine = engine_from_config(config.get_section(config.config_ini_section),
                                prefix="sqlalchemy.", poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

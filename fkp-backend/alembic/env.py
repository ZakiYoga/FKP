import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Tambahkan root project ke path agar bisa import app.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env sebelum import settings
from dotenv import load_dotenv
load_dotenv()

from app.core.config import settings
from sqlmodel import SQLModel

# Import SEMUA model agar Alembic mendeteksi tabel
import app.models  # noqa: F401

config = context.config

# Override sqlalchemy.url dari .env (bukan dari alembic.ini)
# Alembic butuh URL sync (psycopg2), bukan asyncpg
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata = semua tabel dari SQLModel
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Mode offline: generate SQL script tanpa koneksi DB."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Mode online: langsung apply ke DB."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,      # Deteksi perubahan tipe kolom
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

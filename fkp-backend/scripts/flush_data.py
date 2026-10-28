import os
import sys

# Tambahkan root project ke path (sama seperti alembic/env.py)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlmodel import SQLModel

from app.core.config import settings
import app.models  # noqa: F401  (daftarkan semua model ke metadata)


def flush_data() -> None:
    if os.getenv("ENV", "development").lower() == "production":
        sys.exit("Ditolak: tidak boleh dijalankan di production.")

    tables = [t.name for t in SQLModel.metadata.sorted_tables]
    if not tables:
        sys.exit("Tidak ada tabel terdaftar di metadata.")

    names = ", ".join(f'"{t}"' for t in tables)

    engine = create_engine(settings.DATABASE_URL_SYNC)
    with engine.begin() as conn:  # satu transaksi
        conn.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))
    engine.dispose()

    print(f"Data dihapus dari {len(tables)} tabel, struktur tetap utuh.")


if __name__ == "__main__":
    flush_data()

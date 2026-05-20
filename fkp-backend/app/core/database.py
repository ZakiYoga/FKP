from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from app.core.config import settings

# ─── Engine async untuk operasi normal aplikasi ───────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,   # Tampilkan SQL query di terminal (debug)
    pool_pre_ping=True,    # Cek koneksi sebelum dipakai
    pool_size=10,
    max_overflow=20,
)

# ─── Session factory ──────────────────────────────────────────────────────────
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Penting: hindari lazy load setelah commit
)


# ─── Dependency injection untuk FastAPI ──────────────────────────────────────
async def get_db() -> AsyncSession:
    """
    Dipakai sebagai Depends() di setiap endpoint.
    Otomatis commit jika sukses, rollback jika ada error.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ─── Inisialisasi tabel (dipakai saat testing, production pakai Alembic) ─────
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

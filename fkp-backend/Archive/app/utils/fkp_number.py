"""
Generator nomor FKP otomatis.
Format: FKPYYYYMMXXX
Contoh: FKP202605001
"""
from datetime import datetime, timezone
from sqlalchemy import text
from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.fkp import FkpComplaint


async def generate_nomor_fkp(db: AsyncSession) -> str:
    # Advisory lock — hanya 1 request yang bisa masuk pada satu waktu
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext('fkp_nomor_lock'))"))

    now = datetime.now(timezone.utc)
    prefix = f"FKP{now.strftime('%Y%m')}"

    result = await db.execute(
        select(func.count(FkpComplaint.id)).where(
            FkpComplaint.nomor_fkp.like(f"{prefix}%")
        )
    )
    count = result.scalar_one() or 0
    return f"{prefix}{str(count + 1).zfill(3)}"
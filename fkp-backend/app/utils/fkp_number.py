"""
Generator nomor FKP otomatis.
Format: FKP-YYYYMM-XXXX
Contoh: FKP-202504-0001
"""
from datetime import datetime, timezone
from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.fkp import FkpComplaint


async def generate_nomor_fkp(db: AsyncSession) -> str:
    now = datetime.now(timezone.utc)
    prefix = f"FKP-{now.strftime('%Y%m')}-"

    # Hitung berapa FKP yang sudah ada bulan ini
    result = await db.execute(
        select(func.count(FkpComplaint.id)).where(
            FkpComplaint.nomor_fkp.like(f"{prefix}%")
        )
    )
    count = result.scalar_one() or 0
    return f"{prefix}{str(count + 1).zfill(4)}"

"""
app/utils/bapkp_number.py

Generator nomor BAPKP (Berita Acara Pemeriksaan Keluhan Pelanggan).

Format: {urutan:03d}/BAPKP-QC.SPP/{bulan_romawi}/{tahun}
contoh: 007/BAPKP-QC.SPP/VII/2026

PENTING: pola concurrency-safety di sini SENGAJA disamakan persis dengan
app/utils/fkp_number.py (generate_nomor_fkp) yang SUDAH ADA di project --
pakai `pg_advisory_xact_lock` (Postgres advisory lock, dilepas otomatis
saat transaksi commit/rollback), BUKAN hitung COUNT lalu commit terpisah
(itu race-prone: 2 request bersamaan bisa dapat urutan yang sama). Jangan
diubah ke pola count-then-commit kalau tidak benar-benar perlu.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.models.bapkp import FkpBapkp

_MONTH_ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]


async def generate_nomor_ba(db: AsyncSession) -> str:
    """
    Sama seperti generate_nomor_fkp(): pakai advisory lock supaya urutan
    nomor tidak pernah bentrok walau 2 QC submit BA bersamaan. Lock
    otomatis dilepas saat transaksi (commit di create_bapkp()) selesai --
    jadi fungsi ini WAJIB dipanggil di dalam transaksi yang sama dengan
    INSERT baris FkpBapkp-nya (lihat bapkp_service.create_bapkp()).
    """
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext('bapkp_nomor_lock'))"))

    now = datetime.now(timezone.utc)
    tahun = now.year

    r = await db.execute(
        select(func.count(FkpBapkp.id)).where(
            func.extract("year", FkpBapkp.created_at) == tahun
        )
    )
    urutan = (r.scalar() or 0) + 1

    bulan_romawi = _MONTH_ROMAN[now.month]
    return f"{urutan:03d}/BAPKP-QC.SPP/{bulan_romawi}/{tahun}"
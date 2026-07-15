"""
Testimoni Service — logika bisnis untuk fitur testimoni pelanggan FKP.

Aturan bisnis:
- Hanya bisa dibuat ketika FKP sudah berstatus 'closed'
- Hanya bisa dibuat oleh user yang terkait FKP (distributor / outlet)
- Satu user hanya boleh punya satu testimoni per FKP
- Bisa diupdate oleh user yang sama
- Bisa dihapus oleh pembuat atau superadmin
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import HTTPException
from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.testimoni import FkpTestimoni
from app.models.fkp import FkpComplaint, FkpStatus
from app.models.distributor import DistributorUser
from app.models.outlet import Outlet
from app.models.user import User
from app.schemas.testimoni import TestimoniCreate, TestimoniUpdate
from app.services.authz_helpers import is_superadmin


# Role yang boleh membuat testimoni
TESTIMONI_CREATOR_ROLES = {"distributor", "outlet", "sc_spv"}


async def _get_fkp_or_404(fkp_id: uuid.UUID, db: AsyncSession) -> FkpComplaint:
    r = await db.execute(select(FkpComplaint).where(FkpComplaint.id == fkp_id))
    fkp = r.scalar_one_or_none()
    if not fkp:
        raise HTTPException(status_code=404, detail="FKP tidak ditemukan.")
    return fkp


async def _validasi_akses_fkp(fkp: FkpComplaint, user: User, kode_role: str, db: AsyncSession):
    """Pastikan user benar-benar terkait dengan FKP ini."""
    if await is_superadmin(user, db):
        return # superadmin bisa akses semua

    if kode_role == "distributor":
        r = await db.execute(select(DistributorUser).where(
            DistributorUser.user_id == user.id,
            DistributorUser.distributor_id == fkp.distributor_id,
        ))
        if not r.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Anda tidak terkait dengan FKP ini.")

    elif kode_role == "outlet":
        r = await db.execute(select(Outlet).where(
            Outlet.pic_user_id == user.id,
            Outlet.distributor_id == fkp.distributor_id,
        ))
        if not r.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Anda tidak terkait dengan FKP ini.")

    elif kode_role == "sc_spv":
        from app.models.sc_spv import ScSpvDistributor
        r = await db.execute(select(ScSpvDistributor).where(
            ScSpvDistributor.sc_spv_user_id == user.id,
            ScSpvDistributor.distributor_id == fkp.distributor_id,
        ))
        if not r.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Anda tidak terkait dengan FKP ini.")

    else:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{kode_role}' tidak diizinkan memberikan testimoni."
        )


def _tentukan_tipe_responden(kode_role: str) -> str:
    mapping = {
        "distributor": "distributor",
        "outlet": "outlet",
        "sc_spv": "distributor",  # SC/SPV mewakili distributor
    }
    return mapping.get(kode_role, kode_role)


async def buat_testimoni(
    fkp_id: uuid.UUID,
    data: TestimoniCreate,
    user: User,
    kode_role: str,
    db: AsyncSession,
) -> FkpTestimoni:
    """Buat testimoni baru untuk FKP."""

    # Validasi role
    if kode_role not in TESTIMONI_CREATOR_ROLES and not await is_superadmin(user, db):
        raise HTTPException(
            status_code=403,
            detail=f"Role '{kode_role}' tidak bisa memberikan testimoni."
        )

    fkp = await _get_fkp_or_404(fkp_id, db)

    # Validasi: hanya bisa testimoni setelah FKP closed
    if fkp.status != FkpStatus.CLOSED:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Testimoni hanya bisa diberikan setelah FKP selesai (closed). "
                f"Status FKP saat ini: '{fkp.status}'."
            )
        )

    # Validasi akses user ke FKP
    await _validasi_akses_fkp(fkp, user, kode_role, db)

    # Cek duplikasi — satu user satu testimoni per FKP
    r = await db.execute(select(FkpTestimoni).where(
        FkpTestimoni.fkp_id == fkp_id,
        FkpTestimoni.user_id == user.id,
    ))
    if r.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Anda sudah memberikan testimoni untuk FKP ini. Gunakan endpoint PATCH untuk mengubahnya."
        )

    testimoni = FkpTestimoni(
        fkp_id=fkp_id,
        user_id=user.id,
        tipe_responden=_tentukan_tipe_responden(kode_role),
        **data.model_dump(exclude_none=True),
    )
    db.add(testimoni)
    await db.commit()
    await db.refresh(testimoni)

    # nama_pemberi bukan field DB — di-enrich di router, bukan di sini
    return testimoni


async def update_testimoni(
    fkp_id: uuid.UUID,
    testimoni_id: uuid.UUID,
    data: TestimoniUpdate,
    user: User,
    kode_role: str,
    db: AsyncSession,
) -> FkpTestimoni:
    """Update testimoni — hanya oleh pembuat atau superadmin."""
    r = await db.execute(select(FkpTestimoni).where(
        FkpTestimoni.id == testimoni_id,
        FkpTestimoni.fkp_id == fkp_id,
    ))
    testimoni = r.scalar_one_or_none()
    if not testimoni:
        raise HTTPException(status_code=404, detail="Testimoni tidak ditemukan.")

    # PERBAIKAN Kategori C: literal "superadmin" → is_superadmin().
    if not await is_superadmin(user, db) and testimoni.user_id != user.id:
        raise HTTPException(status_code=403, detail="Hanya pembuat testimoni yang bisa mengubahnya.")

    for k, v in data.model_dump(exclude_none=True).items():
        setattr(testimoni, k, v)
    testimoni.updated_at = datetime.now(timezone.utc)
    db.add(testimoni)
    await db.commit()
    await db.refresh(testimoni)
    return testimoni


async def hapus_testimoni(
    fkp_id: uuid.UUID,
    testimoni_id: uuid.UUID,
    user: User,
    kode_role: str,
    db: AsyncSession,
) -> dict:
    """Hapus testimoni — hanya oleh pembuat atau superadmin."""
    r = await db.execute(select(FkpTestimoni).where(
        FkpTestimoni.id == testimoni_id,
        FkpTestimoni.fkp_id == fkp_id,
    ))
    testimoni = r.scalar_one_or_none()
    if not testimoni:
        raise HTTPException(status_code=404, detail="Testimoni tidak ditemukan.")

    # PERBAIKAN Kategori C: literal "superadmin" → is_superadmin().
    if not await is_superadmin(user, db) and testimoni.user_id != user.id:
        raise HTTPException(status_code=403, detail="Hanya pembuat testimoni atau superadmin yang bisa menghapus.")

    await db.delete(testimoni)
    await db.commit()
    return {"detail": "Testimoni berhasil dihapus."}


async def get_testimoni_by_fkp(
    fkp_id: uuid.UUID,
    db: AsyncSession,
) -> List[FkpTestimoni]:
    """Ambil semua testimoni untuk satu FKP."""
    r = await db.execute(
        select(FkpTestimoni)
        .where(FkpTestimoni.fkp_id == fkp_id)
        .order_by(FkpTestimoni.created_at.desc())
    )
    return r.scalars().all()


async def get_testimoni_milik_saya(
    fkp_id: uuid.UUID,
    user: User,
    db: AsyncSession,
) -> Optional[FkpTestimoni]:
    """Ambil testimoni milik user tertentu untuk FKP tertentu."""
    r = await db.execute(select(FkpTestimoni).where(
        FkpTestimoni.fkp_id == fkp_id,
        FkpTestimoni.user_id == user.id,
    ))
    return r.scalar_one_or_none()


async def get_ringkasan_testimoni(
    fkp_id: uuid.UUID,
    db: AsyncSession,
) -> dict:
    """
    Hitung ringkasan statistik testimoni untuk satu FKP.
    Return: total, rata-rata per aspek penanganan, rata-rata aplikasi,
            distribusi rating keseluruhan dan distribusi rating aplikasi.
    """
    r = await db.execute(
        select(FkpTestimoni).where(FkpTestimoni.fkp_id == fkp_id)
    )
    semua = r.scalars().all()

    kosong = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}

    if not semua:
        return {
            "total_testimoni": 0,
            "rata_rata_keseluruhan": None,
            "rata_rata_kecepatan": None,
            "rata_rata_komunikasi": None,
            "rata_rata_solusi": None,
            "distribusi_rating": kosong.copy(),
            "rata_rata_aplikasi": None,
            "distribusi_rating_aplikasi": kosong.copy(),
        }

    def _avg(values):
        filtered = [v for v in values if v is not None]
        return round(sum(filtered) / len(filtered), 2) if filtered else None

    distribusi = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    for t in semua:
        distribusi[str(t.rating_keseluruhan)] += 1

    distribusi_app = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    for t in semua:
        if t.rating_aplikasi is not None:
            distribusi_app[str(t.rating_aplikasi)] += 1

    return {
        "total_testimoni": len(semua),
        "rata_rata_keseluruhan": _avg([t.rating_keseluruhan for t in semua]),
        "rata_rata_kecepatan": _avg([t.rating_kecepatan for t in semua]),
        "rata_rata_komunikasi": _avg([t.rating_komunikasi for t in semua]),
        "rata_rata_solusi": _avg([t.rating_solusi for t in semua]),
        "distribusi_rating": distribusi,
        "rata_rata_aplikasi": _avg([t.rating_aplikasi for t in semua]),
        "distribusi_rating_aplikasi": distribusi_app,
    }


async def get_semua_testimoni(
    db: AsyncSession,
    kode_role: str,
    hanya_publik: bool = True,
    min_rating: Optional[int] = None,
    max_rating: Optional[int] = None,
    tipe_responden: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
) -> List[FkpTestimoni]:
    """
    Ambil semua testimoni lintas FKP — untuk dashboard admin.
    Hanya admin_ho, rsm, direktur, superadmin yang bisa akses semua.
    """
    query = select(FkpTestimoni)

    if hanya_publik:
        query = query.where(FkpTestimoni.is_public == True)
    if min_rating is not None:
        query = query.where(FkpTestimoni.rating_keseluruhan >= min_rating)
    if max_rating is not None:
        query = query.where(FkpTestimoni.rating_keseluruhan <= max_rating)
    if tipe_responden:
        query = query.where(FkpTestimoni.tipe_responden == tipe_responden)

    query = query.order_by(FkpTestimoni.created_at.desc()).offset(skip).limit(limit)
    r = await db.execute(query)
    return r.scalars().all()
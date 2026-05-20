"""
Distributor Service — logika bisnis untuk manajemen distributor.

Fungsi list_distributors_by_role() menangani filtering berdasarkan role:
  - superadmin / admin_ho / qc / rsm / direktur / finance  → semua distributor
  - apsm    → semua distributor yang ada di bawah sc_spv bawahannya
  - sc_spv  → hanya distributor yang dia handle (ScSpvDistributor)
  - distributor (user pemilik) → hanya distributor yang dia terdaftar (DistributorUser)
  - outlet  → hanya distributor tempat outlet-nya terdaftar (Outlet.distributor_id via pic_user_id)
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.distributor import Distributor, DistributorUser
from app.models.outlet import Outlet
from app.models.sc_spv import ScSpvDistributor, ApsmScSpv
from app.models.area import Area
from app.models.user import User
from app.schemas.distributor import (
    DistributorCreate, DistributorUpdate, DistributorResponse,
    DistributorUserAdd, DistributorUserResponse,
)


# ─── LIST (dengan filter role) ────────────────────────────────────────────────

async def list_distributors_by_role(
    db: AsyncSession,
    current_user: User,
    kode_role: str,
    area_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
) -> List[Distributor]:
    """
    Mengembalikan list distributor yang bisa dilihat oleh user sesuai rolenya.

    Hierarki akses:
    - superadmin / admin_ho / qc / rsm / direktur → semua distributor
    - apsm    → distributor yang dikelola sc_spv di bawahnya
    - sc_spv  → distributor yang dia handle langsung (ScSpvDistributor)
    - distributor → distributor tempat dia terdaftar sebagai user (DistributorUser)
    - outlet  → 1 distributor tempat outlet-nya terdaftar (Outlet.pic_user_id)
    """

    # ── Role dengan akses penuh ──────────────────────────────────────────────
    if kode_role in ("superadmin", "admin_ho", "qc", "rsm", "direktur", "finance"):
        return await list_distributors(db, area_id=area_id, status=status)

    # ── APSM: distributor di bawah semua sc_spv bawahannya ──────────────────
    if kode_role == "apsm":
        sc_result = await db.execute(
            select(ApsmScSpv.sc_spv_user_id).where(
                ApsmScSpv.apsm_user_id == current_user.id
            )
        )
        sc_spv_ids = sc_result.scalars().all()
        if not sc_spv_ids:
            return []

        dist_result = await db.execute(
            select(ScSpvDistributor.distributor_id).where(
                ScSpvDistributor.sc_spv_user_id.in_(sc_spv_ids)
            )
        )
        dist_ids = dist_result.scalars().all()
        if not dist_ids:
            return []

        query = select(Distributor).where(Distributor.id.in_(dist_ids))
        if area_id:
            query = query.where(Distributor.area_id == area_id)
        if status:
            query = query.where(Distributor.status == status)
        result = await db.execute(query.order_by(Distributor.nama_perusahaan))
        return result.scalars().all()

    # ── SC/SPV: hanya distributor yang dia handle (ScSpvDistributor) ─────────
    if kode_role == "sc_spv":
        dist_result = await db.execute(
            select(ScSpvDistributor.distributor_id).where(
                ScSpvDistributor.sc_spv_user_id == current_user.id
            )
        )
        dist_ids = dist_result.scalars().all()
        if not dist_ids:
            return []

        query = select(Distributor).where(Distributor.id.in_(dist_ids))
        if area_id:
            query = query.where(Distributor.area_id == area_id)
        if status:
            query = query.where(Distributor.status == status)
        result = await db.execute(query.order_by(Distributor.nama_perusahaan))
        return result.scalars().all()

    # ── Distributor: lewat tabel DistributorUser ──────────────────────────────
    if kode_role == "distributor":
        du_result = await db.execute(
            select(DistributorUser.distributor_id).where(
                DistributorUser.user_id == current_user.id
            )
        )
        dist_ids = du_result.scalars().all()
        if not dist_ids:
            return []

        query = select(Distributor).where(Distributor.id.in_(dist_ids))
        if area_id:
            query = query.where(Distributor.area_id == area_id)
        if status:
            query = query.where(Distributor.status == status)
        result = await db.execute(query.order_by(Distributor.nama_perusahaan))
        return result.scalars().all()

    # ── Outlet: Outlet.pic_user_id → Outlet.distributor_id ───────────────────
    if kode_role == "outlet":
        outlet_result = await db.execute(
            select(Outlet).where(Outlet.pic_user_id == current_user.id)
        )
        outlet = outlet_result.scalar_one_or_none()
        if not outlet:
            # Outlet belum tercantum di distributor manapun
            # Frontend menampilkan banner informatif, tombol submit di-disable
            return []

        query = select(Distributor).where(Distributor.id == outlet.distributor_id)
        if status:
            query = query.where(Distributor.status == status)
        result = await db.execute(query)
        distributor = result.scalar_one_or_none()
        return [distributor] if distributor else []

    # Fallback
    return []


# ─── LIST SEMUA (tanpa filter role) ──────────────────────────────────────────

async def list_distributors(
    db: AsyncSession,
    area_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
) -> List[Distributor]:
    """List semua distributor — dipakai oleh role dengan akses penuh."""
    query = select(Distributor)
    if area_id:
        query = query.where(Distributor.area_id == area_id)
    if status:
        query = query.where(Distributor.status == status)
    query = query.order_by(Distributor.nama_perusahaan)
    result = await db.execute(query)
    return result.scalars().all()


# ─── DETAIL ───────────────────────────────────────────────────────────────────

async def get_distributor(distributor_id: uuid.UUID, db: AsyncSession) -> Distributor:
    result = await db.execute(
        select(Distributor).where(Distributor.id == distributor_id)
    )
    distributor = result.scalar_one_or_none()
    if not distributor:
        raise HTTPException(status_code=404, detail="Distributor tidak ditemukan.")
    return distributor


# ─── CREATE ───────────────────────────────────────────────────────────────────

async def create_distributor(data: DistributorCreate, db: AsyncSession) -> Distributor:
    area_result = await db.execute(select(Area).where(Area.id == data.area_id))
    if not area_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Area tidak ditemukan.")

    kode_check = await db.execute(
        select(Distributor).where(Distributor.kode_distributor == data.kode_distributor)
    )
    if kode_check.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Kode distributor '{data.kode_distributor}' sudah digunakan.",
        )

    distributor = Distributor(**data.model_dump())
    db.add(distributor)
    await db.commit()
    await db.refresh(distributor)
    return distributor


# ─── UPDATE ───────────────────────────────────────────────────────────────────

async def update_distributor(
    distributor_id: uuid.UUID, data: DistributorUpdate, db: AsyncSession
) -> Distributor:
    distributor = await get_distributor(distributor_id, db)

    if data.area_id:
        area_result = await db.execute(select(Area).where(Area.id == data.area_id))
        if not area_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Area tidak ditemukan.")

    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(distributor, key, value)
    distributor.updated_at = datetime.now(timezone.utc)

    db.add(distributor)
    await db.commit()
    await db.refresh(distributor)
    return distributor


# ─── DEACTIVATE ───────────────────────────────────────────────────────────────

async def deactivate_distributor(distributor_id: uuid.UUID, db: AsyncSession) -> dict:
    distributor = await get_distributor(distributor_id, db)
    distributor.status = "nonaktif"
    distributor.updated_at = datetime.now(timezone.utc)
    db.add(distributor)
    await db.commit()
    return {"message": f"Distributor '{distributor.nama_perusahaan}' dinonaktifkan."}


# ─── DISTRIBUTOR USER (mapping) ───────────────────────────────────────────────

async def list_distributor_users(
    distributor_id: uuid.UUID, db: AsyncSession
) -> List[DistributorUser]:
    await get_distributor(distributor_id, db)
    result = await db.execute(
        select(DistributorUser).where(DistributorUser.distributor_id == distributor_id)
    )
    return result.scalars().all()


async def add_distributor_user(
    distributor_id: uuid.UUID, data: DistributorUserAdd, db: AsyncSession
) -> DistributorUser:
    await get_distributor(distributor_id, db)

    existing = await db.execute(
        select(DistributorUser).where(
            DistributorUser.distributor_id == distributor_id,
            DistributorUser.user_id == data.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User sudah terdaftar di distributor ini.")

    if data.is_primary:
        old_primary = await db.execute(
            select(DistributorUser).where(
                DistributorUser.distributor_id == distributor_id,
                DistributorUser.is_primary == True,
            )
        )
        for du in old_primary.scalars().all():
            du.is_primary = False
            db.add(du)

    du = DistributorUser(
        distributor_id=distributor_id,
        user_id=data.user_id,
        jabatan=data.jabatan,
        is_primary=data.is_primary,
    )
    db.add(du)
    await db.commit()
    await db.refresh(du)
    return du


async def remove_distributor_user(
    distributor_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> dict:
    result = await db.execute(
        select(DistributorUser).where(
            DistributorUser.distributor_id == distributor_id,
            DistributorUser.user_id == user_id,
        )
    )
    du = result.scalar_one_or_none()
    if not du:
        raise HTTPException(status_code=404, detail="Mapping user-distributor tidak ditemukan.")
    await db.delete(du)
    await db.commit()
    return {"message": "User berhasil dilepas dari distributor."}
"""
Distributor Service — logika bisnis untuk manajemen distributor.

[FIX] Scoping APSM sebelumnya salah: mengambil distributor lewat rantai
ApsmScSpv -> ScSpvDistributor, padahal dokumen desain (section 3.4) eksplisit
menetapkan scoping APSM harus PRIMARY via Area, supaya distributor yang belum
punya SC_SPV tidak menjadi blind spot. Sekarang menggunakan
authz_helpers.get_scoped_distributor_ids() sebagai satu sumber kebenaran,
konsisten dengan fkp_service & outlet_register_service.

Fungsi list_distributors_by_role() menangani filtering berdasarkan role:
  - superadmin (is_superadmin=True) / admin_ho / qc / rsm / direktur / finance → semua distributor
  - apsm    → semua distributor di Area yang dia PIC-i (TERMASUK yang belum punya SC_SPV)
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
from app.models.area import Area
from app.models.user import User
from app.schemas.distributor import (
    DistributorCreate, DistributorUpdate, DistributorResponse,
    DistributorUserAdd, DistributorUserResponse,
)
from app.services.authz_helpers import get_scoped_distributor_ids


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
    Scope ditentukan oleh authz_helpers.get_scoped_distributor_ids() — satu
    sumber kebenaran yang dipakai juga oleh service lain (outlet_register,
    upload, dst) agar tidak ada lagi inkonsistensi scoping antar-modul.
    """
    scoped_ids = await get_scoped_distributor_ids(current_user, kode_role, db)

    # None = akses global (superadmin/admin_ho/qc/rsm/direktur/finance)
    if scoped_ids is None:
        return await list_distributors(db, area_id=area_id, status=status)

    # [] = tidak ada distributor dalam scope user (mis. APSM belum punya area,
    # SC_SPV belum di-assign distributor, outlet belum tercantum, dst)
    if not scoped_ids:
        return []

    query = select(Distributor).where(Distributor.id.in_(scoped_ids))
    if area_id:
        query = query.where(Distributor.area_id == area_id)
    if status:
        query = query.where(Distributor.status == status)
    result = await db.execute(query.order_by(Distributor.nama_perusahaan))
    return result.scalars().all()


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
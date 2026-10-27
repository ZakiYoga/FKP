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

list_distributors_paginated() dan get_distributor_status_summary() memakai aturan
scope yang sama lewat _build_scoped_distributor_query().
"""
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import Case, func, or_
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.wilayah_service import attach_wilayah, ensure_kelurahan

from app.models.distributor import Distributor, DistributorUser
from app.models.area import Area
from app.models.user import User
from app.schemas.distributor import (
    DistributorCreate, DistributorSelfUpdate, DistributorUpdate, DistributorResponse,
    DistributorUserAdd, DistributorUserResponse,
)
from app.services.authz_helpers import assert_distributor_in_scope, get_scoped_distributor_ids


# ─── HELPERS LIST ─────────────────────────────────────────────────────────────

def _escape_like(value: str) -> str:
    """Escape karakter wildcard LIKE agar input user dianggap teks biasa."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def _build_scoped_distributor_query(
    db: AsyncSession,
    current_user: User,
    kode_role: str,
    area_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    """
    Query dasar distributor dengan scoping otomatis per role + filter opsional.
    Mengembalikan None jika user tidak punya scope sama sekali (hasil pasti kosong).

    Scope ditentukan oleh authz_helpers.get_scoped_distributor_ids() — satu
    sumber kebenaran yang dipakai juga oleh service lain (outlet_register,
    upload, dst) agar tidak ada lagi inkonsistensi scoping antar-modul.
    """
    scoped_ids = await get_scoped_distributor_ids(current_user, kode_role, db)

    # [] = tidak ada distributor dalam scope user (mis. APSM belum punya area,
    # SC_SPV belum di-assign distributor, outlet belum tercantum, dst)
    if scoped_ids is not None and not scoped_ids:
        return None

    query = select(Distributor)

    # None = akses global (superadmin/admin_ho/qc/rsm/direktur/finance)
    if scoped_ids is not None:
        query = query.where(Distributor.id.in_(scoped_ids))

    if area_id:
        query = query.where(Distributor.area_id == area_id)
    if status:
        query = query.where(Distributor.status == status)
    if search and search.strip():
        pattern = f"%{_escape_like(search.strip())}%"
        query = query.where(
            or_(
                Distributor.nama_perusahaan.ilike(pattern, escape="\\"),
                Distributor.kode_distributor.ilike(pattern, escape="\\"),
                Distributor.pemilik.ilike(pattern, escape="\\"),
            )
        )

    return query


# ─── LIST (dengan filter role) ────────────────────────────────────────────────

async def list_distributors_by_role(
    db: AsyncSession,
    current_user: User,
    kode_role: str,
    area_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
) -> List[Distributor]:
    """
    Mengembalikan list distributor yang bisa dilihat oleh user sesuai rolenya
    (tanpa pagination). Untuk tampilan berpagination gunakan
    list_distributors_paginated().

    Urutan: aktif lebih dulu, lalu nama_perusahaan. (Sebelumnya order_by pada
    cabang non-global tidak pernah dipakai karena hasilnya tidak di-assign.)
    """
    query = await _build_scoped_distributor_query(
        db, current_user, kode_role, area_id=area_id, status=status,
    )
    if query is None:
        return []

    query = query.order_by(
        Case((Distributor.status == "aktif", 0), else_=1),
        Distributor.nama_perusahaan,
    )

    result = await db.execute(query)
    return result.scalars().all()


async def list_distributors_paginated(
    db: AsyncSession,
    current_user: User,
    kode_role: str,
    page: int = 1,
    page_size: int = 10,
    area_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List distributor berpagination (offset/limit) dengan scoping per role.
    Filter opsional: area_id, status, search (nama_perusahaan/kode_distributor/pemilik).

    Urutan: aktif lebih dulu, lalu nama_perusahaan; id jadi tie-breaker agar
    halaman stabil (tidak ada baris dobel/hilang antar halaman).
    """
    query = await _build_scoped_distributor_query(
        db, current_user, kode_role,
        area_id=area_id, status=status, search=search,
    )
    if query is None:
        return {"items": [], "total": 0, "page": page,
                "page_size": page_size, "total_pages": 0}

    total = (
        await db.execute(
            select(func.count()).select_from(query.order_by(None).subquery())
        )
    ).scalar_one()

    query = query.order_by(
        Case((Distributor.status == "aktif", 0), else_=1),
        Distributor.nama_perusahaan,
        Distributor.id,
    )
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)

    return {
        "items": result.scalars().all(),
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total else 0,
    }


async def get_distributor_status_summary(
    db: AsyncSession,
    current_user: User,
    kode_role: str,
    area_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    """
    Jumlah distributor per status dalam scope user (+ filter area opsional).
    Satu query GROUP BY — ringan, cocok untuk counter di header.
    """
    query = await _build_scoped_distributor_query(
        db, current_user, kode_role, area_id=area_id,
    )
    if query is None:
        return {"counts": {}, "total": 0}

    sub = query.order_by(None).subquery()
    rows = (
        await db.execute(
            select(sub.c.status, func.count()).group_by(sub.c.status)
        )
    ).all()

    counts = {status: n for status, n in rows}
    return {"counts": counts, "total": sum(counts.values())}


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

    query = query.order_by(
        Case((Distributor.status == "aktif", 0), else_=1),
        Distributor.nama_perusahaan,
    )

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

# ─── PROFILE (self-service) ───────────────────────────────────────────────────

async def _assert_readable(
    distributor_id: uuid.UUID, user: User, kode_role: str, db: AsyncSession
) -> None:
    """Scope baca. PermissionError dari authz_helpers diubah jadi 403."""
    try:
        await assert_distributor_in_scope(
            distributor_id, user, kode_role, db,
            forbidden_message="Anda tidak berhak melihat distributor ini.",
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


async def _get_membership(
    user_id: uuid.UUID, distributor_id: uuid.UUID, db: AsyncSession
) -> Optional[DistributorUser]:
    result = await db.execute(
        select(DistributorUser).where(
            DistributorUser.user_id == user_id,
            DistributorUser.distributor_id == distributor_id,
        )
    )
    return result.scalars().first()


def _to_detail(distributor: Distributor, membership: Optional[DistributorUser]) -> Dict[str, Any]:
    is_primary = bool(membership and membership.is_primary)
    can_edit = is_primary and distributor.status == "aktif"

    reason = None
    if not can_edit:
        if not is_primary:
            reason = "Hanya user utama (primary) distributor yang dapat mengubah data."
        else:
            reason = "Distributor nonaktif tidak dapat diubah."

    data = DistributorResponse.model_validate(distributor).model_dump()
    data["can_edit"] = can_edit
    data["edit_blocked_reason"] = reason
    data["is_primary"] = is_primary
    data["jabatan"] = membership.jabatan if membership else None
    return data


async def get_distributor_detail(
    distributor_id: uuid.UUID, user: User, kode_role: str, db: AsyncSession
) -> Dict[str, Any]:
    distributor = await get_distributor(distributor_id, db)
    await _assert_readable(distributor_id, user, kode_role, db)
    membership = await _get_membership(user.id, distributor_id, db)
    data = _to_detail(distributor, membership)
    await attach_wilayah(db, [data])
    return data


async def list_my_distributors(user: User, db: AsyncSession) -> List[Dict[str, Any]]:
    """Distributor tempat user terdaftar (distributor_users) — untuk tab profile."""
    result = await db.execute(
        select(Distributor, DistributorUser)
        .join(DistributorUser, DistributorUser.distributor_id == Distributor.id)
        .where(DistributorUser.user_id == user.id)
        .order_by(
            Case((DistributorUser.is_primary == True, 0), else_=1),
            Case((Distributor.status == "aktif", 0), else_=1),
            Distributor.nama_perusahaan,
            Distributor.id,
        )
    )
    items = [_to_detail(d, du) for d, du in result.all()]
    await attach_wilayah(db, items)
    return items


_REQUIRED_SELF_FIELDS = {"nama_perusahaan", "pemilik"}


async def update_my_distributor(
    distributor_id: uuid.UUID, data: DistributorSelfUpdate, user: User, db: AsyncSession
) -> Dict[str, Any]:
    distributor = await get_distributor(distributor_id, db)
    membership = await _get_membership(user.id, distributor_id, db)

    if not membership or not membership.is_primary:
        raise HTTPException(
            status_code=403,
            detail="Hanya user utama (primary) distributor yang dapat mengubah data ini.",
        )
    if distributor.status != "aktif":
        raise HTTPException(
            status_code=400,
            detail="Hanya distributor berstatus aktif yang dapat diubah.",
        )

    changes = data.model_dump(exclude_unset=True)
    print("SELF-UPDATE CHANGES:", changes, flush=True)
    if "kelurahan_id" in changes:
        await ensure_kelurahan(db, changes["kelurahan_id"])

    if "npwp" in changes and changes["npwp"] is None and distributor.npwp:
        raise HTTPException(
            status_code=400,
            detail="NPWP tidak boleh dikosongkan. Hubungi admin jika perlu menghapusnya.",
        )

    for f in _REQUIRED_SELF_FIELDS & changes.keys():
        v = changes[f]
        if v is None or (isinstance(v, str) and not v.strip()):
            raise HTTPException(status_code=400, detail=f"Field '{f}' tidak boleh kosong.")

    for k, v in changes.items():
        if isinstance(v, str):
            v = v.strip()
            if not v and k not in _REQUIRED_SELF_FIELDS:
                v = None          # string kosong di field opsional → NULL
        
        setattr(distributor, k, v)

    distributor.updated_at = datetime.now(timezone.utc)
    db.add(distributor)
    await db.commit()
    await db.refresh(distributor)
    detail = _to_detail(distributor, membership)
    await attach_wilayah(db, [detail])
    return detail

# ─── CREATE ───────────────────────────────────────────────────────────────────

async def create_distributor(data: DistributorCreate, db: AsyncSession) -> Distributor:
    area_result = await db.execute(select(Area).where(Area.id == data.area_id))
    if not area_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Area tidak ditemukan.")

    await ensure_kelurahan(db, data.kelurahan_id)

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

    if data.kelurahan_id is not None:
        await ensure_kelurahan(db, data.kelurahan_id)

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

# ─── ACTIVATE ─────────────────────────────────────────────────────────────────

async def activate_distributor(distributor_id: uuid.UUID, db: AsyncSession) -> dict:
    distributor = await get_distributor(distributor_id, db)
    if distributor.status == "aktif":
        raise HTTPException(status_code=400, detail="Distributor sudah dalam status aktif.")
    distributor.status = "aktif"
    distributor.updated_at = datetime.now(timezone.utc)
    db.add(distributor)
    await db.commit()
    return {"message": f"Distributor '{distributor.nama_perusahaan}' diaktifkan kembali."}

# ─── DISTRIBUTOR USER (mapping) ───────────────────────────────────────────────

async def list_distributor_users(
    distributor_id: uuid.UUID, user: User, kode_role: str, db: AsyncSession
) -> List[DistributorUser]:
    await get_distributor(distributor_id, db)
    await _assert_readable(distributor_id, user, kode_role, db)
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
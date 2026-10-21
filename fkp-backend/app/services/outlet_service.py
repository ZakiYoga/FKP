"""
Outlet Service — business logic untuk CRUD outlet oleh internal user.

Berbeda dari outlet_register_service.py yang menangani:
  - Registrasi publik (calon outlet daftar sendiri)
  - Approval/reject flow

File ini menangani operasi internal oleh admin_ho, distributor, sc_spv, apsm:
  - Buat outlet langsung (tanpa registrasi publik)
  - Update outlet
  - List outlet dengan scoping per role (biasa, berpagination, ringkasan status)
  - Assign/validasi PIC

Semua pengecekan scope role (siapa boleh akses distributor mana) tetap
di authz_helpers.py — service ini hanya memanggil helper tersebut,
tidak menduplikasi logikanya.
"""
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import Case, func, or_
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outlet import Outlet
from app.models.user import User
from app.models.distributor import Distributor
from app.schemas.outlet import OutletCreate, OutletUpdate
from app.services.authz_helpers import (
    has_global_access,
    assert_distributor_in_scope,
    get_scoped_distributor_ids,
    is_superadmin,
)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

async def get_outlet_or_404(outlet_id: uuid.UUID, db: AsyncSession) -> Outlet:
    result = await db.execute(select(Outlet).where(Outlet.id == outlet_id))
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan.")
    return outlet


async def validate_pic_distributor_consistency(
    pic_user_id: uuid.UUID,
    distributor_id: uuid.UUID,
    db: AsyncSession,
    exclude_outlet_id: Optional[uuid.UUID] = None,
) -> None:
    """
    Pastikan pic_user_id tidak sudah menjadi PIC di outlet dari distributor LAIN.

    Aturan bisnis (sesuai outlet_register_service & auth_service):
    Satu user boleh menjadi PIC di lebih dari satu outlet, ASALKAN semua
    outlet tersebut berada di distributor yang sama.

    exclude_outlet_id dipakai saat update — agar outlet yang sedang diedit
    tidak dihitung sebagai konflik dengan dirinya sendiri.
    """
    query = select(Outlet).where(
        Outlet.pic_user_id == pic_user_id,
        Outlet.distributor_id != distributor_id,
    )
    if exclude_outlet_id:
        query = query.where(Outlet.id != exclude_outlet_id)

    result = await db.execute(query)
    konflik = result.scalars().all()

    if konflik:
        contoh = konflik[0]
        raise HTTPException(
            status_code=400,
            detail=(
                f"User ini sudah menjadi PIC di outlet lain dari distributor yang berbeda "
                f"(contoh: '{contoh.nama_toko}'). "
                f"Satu user hanya boleh menjadi PIC di outlet dalam satu distributor yang sama."
            ),
        )


def _escape_like(value: str) -> str:
    """Escape karakter wildcard LIKE agar input user dianggap teks biasa."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def _build_scoped_outlet_query(
    db: AsyncSession,
    user: User,
    kode_role: str,
    distributor_id: Optional[uuid.UUID] = None,
    area_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    """
    Query dasar outlet dengan scoping otomatis per role + filter opsional.
    Mengembalikan None jika user tidak punya scope sama sekali (hasil pasti kosong).

    Dipakai bersama oleh list_outlets, list_outlets_paginated, dan
    get_outlet_status_summary — satu sumber kebenaran untuk aturan scope,
    mengikuti get_scoped_distributor_ids() dari authz_helpers.
    """
    scoped_ids = await get_scoped_distributor_ids(user, kode_role, db)

    if scoped_ids is not None and not scoped_ids:
        return None

    query = select(Outlet)

    if scoped_ids is None:
        # Akses global — tidak ada filter scope
        pass
    elif kode_role == "outlet":
        # Role outlet: filter by pic_user_id, bukan distributor_id
        query = query.where(Outlet.pic_user_id == user.id)
    else:
        query = query.where(Outlet.distributor_id.in_(scoped_ids))

    if distributor_id:
        query = query.where(Outlet.distributor_id == distributor_id)
    if area_id:
        query = query.where(
            Outlet.distributor_id.in_(
                select(Distributor.id).where(Distributor.area_id == area_id)
            )
        )
    if status:
        query = query.where(Outlet.status == status)
    if search and search.strip():
        pattern = f"%{_escape_like(search.strip())}%"
        query = query.where(
            or_(
                Outlet.nama_toko.ilike(pattern, escape="\\"),
                Outlet.kode_outlet.ilike(pattern, escape="\\"),
                Outlet.pemilik_toko.ilike(pattern, escape="\\"),
            )
        )

    return query


# ─── LIST ─────────────────────────────────────────────────────────────────────

async def list_outlets(
    db: AsyncSession,
    user: User,
    kode_role: str,
    distributor_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
) -> List[Outlet]:
    """
    List outlet dengan scoping otomatis per role (tanpa pagination).
    Filter opsional: distributor_id, status.

    Dipertahankan agar konsumen lama tidak rusak. Untuk tampilan yang
    berpagination gunakan list_outlets_paginated().
    """
    query = await _build_scoped_outlet_query(
        db, user, kode_role, distributor_id=distributor_id, status=status,
    )
    if query is None:
        return []

    query = query.order_by(
        Case((Outlet.status == "aktif", 0), else_=1),
        Outlet.nama_toko,
    )

    result = await db.execute(query)
    return result.scalars().all()


async def list_outlets_paginated(
    db: AsyncSession,
    user: User,
    kode_role: str,
    page: int = 1,
    page_size: int = 10,
    distributor_id: Optional[uuid.UUID] = None,
    area_id: Optional[uuid.UUID] = None,      # ← baru
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    query = await _build_scoped_outlet_query(
        db, user, kode_role,
        distributor_id=distributor_id, area_id=area_id,   # ← area_id diteruskan
        status=status, search=search,
    )
    """
    List outlet berpagination (offset/limit) dengan scoping per role.
    Filter opsional: distributor_id, status, search (nama_toko/kode_outlet/pemilik_toko).

    Urutan:
    - status == "pending": paling lama menunggu dulu (created_at ASC) — antrean FIFO
    - lainnya: aktif lebih dulu, lalu nama_toko
    - id selalu jadi tie-breaker agar halaman stabil (tidak ada baris dobel/hilang)
    """
    query = await _build_scoped_outlet_query(
        db, user, kode_role,
        distributor_id=distributor_id, area_id=area_id, status=status, search=search,
    )
    if query is None:
        return {"items": [], "total": 0, "page": page,
                "page_size": page_size, "total_pages": 0}

    total = (
        await db.execute(
            select(func.count()).select_from(query.order_by(None).subquery())
        )
    ).scalar_one()

    if status == "pending":
        query = query.order_by(Outlet.created_at.asc(), Outlet.id)
    else:
        query = query.order_by(
            Case((Outlet.status == "aktif", 0), else_=1),
            Outlet.nama_toko,
            Outlet.id,
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


async def get_outlet_status_summary(
    db: AsyncSession,
    user: User,
    kode_role: str,
    distributor_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    """
    Jumlah outlet per status dalam scope user (+ filter distributor opsional).
    Satu query GROUP BY — ringan, cocok untuk badge/counter di header.
    """
    query = await _build_scoped_outlet_query(
        db, user, kode_role, distributor_id=distributor_id,
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


# ─── CREATE ───────────────────────────────────────────────────────────────────

async def create_outlet(
    data: OutletCreate,
    user: User,
    kode_role: str,
    db: AsyncSession,
) -> Outlet:
    """
    Buat outlet baru oleh internal user (bukan registrasi publik).

    Aturan:
    - Role non-global wajib lolos assert_distributor_in_scope()
    - pic_user_id hanya boleh diisi oleh admin_ho/superadmin
    - Jika pic_user_id diisi, wajib lolos validate_pic_distributor_consistency()
    - kode_outlet harus unik
    """
    is_global = await has_global_access(user, kode_role, db)

    # Validasi scope distributor untuk role non-global
    if not is_global:
        await assert_distributor_in_scope(
            data.distributor_id,
            user,
            kode_role,
            db,
            forbidden_message="Anda tidak berhak membuat outlet untuk distributor ini.",
        )

    # Cek kode_outlet unik
    existing = await db.execute(
        select(Outlet).where(Outlet.kode_outlet == data.kode_outlet)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Kode outlet '{data.kode_outlet}' sudah digunakan.",
        )

    outlet_data = data.model_dump()

    boleh_assign_pic = kode_role == "admin_ho" or await is_superadmin(user, db)
    if data.pic_user_id is not None and boleh_assign_pic:
        await validate_pic_distributor_consistency(
            pic_user_id=data.pic_user_id,
            distributor_id=data.distributor_id,
            db=db,
        )
    else:
        outlet_data["pic_user_id"] = None

    outlet = Outlet(**outlet_data)
    db.add(outlet)
    await db.commit()
    await db.refresh(outlet)
    return outlet


# ─── UPDATE ───────────────────────────────────────────────────────────────────

async def update_outlet(
    outlet_id: uuid.UUID,
    data: OutletUpdate,
    user: User,
    kode_role: str,
    db: AsyncSession,
) -> Outlet:
    """
    Update outlet.

    Aturan:
    - Role non-global wajib lolos assert_distributor_in_scope() terhadap
      outlet.distributor_id yang sudah ada (distributor_id tidak bisa diubah
      lewat OutletUpdate)
    - Role non-global tidak boleh mengubah field `status` — harus lewat
      approve_registration / reject_registration di outlet_register_service
    - pic_user_id hanya boleh diubah oleh admin_ho/superadmin, dan wajib
      lolos validate_pic_distributor_consistency()
    """
    outlet = await get_outlet_or_404(outlet_id, db)
    is_global = await has_global_access(user, kode_role, db)

    if not is_global:
        await assert_distributor_in_scope(
            outlet.distributor_id,
            user,
            kode_role,
            db,
            forbidden_message="Anda tidak berhak mengubah outlet ini.",
        )

        if data.status is not None:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Perubahan status outlet harus melalui proses approval "
                    "(lihat endpoint registrasi outlet), bukan lewat update biasa."
                ),
            )

    # Validasi pic_user_id jika diubah
    # PERBAIKAN Kategori C: literal "superadmin" → is_superadmin().
    if data.pic_user_id is not None:
        if kode_role != "admin_ho" and not await is_superadmin(user, db):
            raise HTTPException(
                status_code=403,
                detail="Hanya admin_ho atau superadmin yang dapat mengubah PIC outlet.",
            )
        await validate_pic_distributor_consistency(
            pic_user_id=data.pic_user_id,
            distributor_id=outlet.distributor_id,
            db=db,
            exclude_outlet_id=outlet_id,
        )

    for k, v in data.model_dump(exclude_none=True).items():
        setattr(outlet, k, v)
    outlet.updated_at = datetime.now(timezone.utc)
    db.add(outlet)
    await db.commit()
    await db.refresh(outlet)
    return outlet

async def activate_outlet(
    outlet_id: uuid.UUID,
    user: User,
    kode_role: str,
    db: AsyncSession,
) -> Outlet:
    """
    Aktifkan kembali outlet berstatus nonaktif.
    Cermin deactivate_outlet() — scope check sama, arah transisi terbalik.
    """
    outlet = await get_outlet_or_404(outlet_id, db)

    if not await has_global_access(user, kode_role, db):
        await assert_distributor_in_scope(
            outlet.distributor_id,
            user,
            kode_role,
            db,
            forbidden_message="Anda tidak berhak mengaktifkan outlet ini.",
        )

    if outlet.status != "nonaktif":
        raise HTTPException(
            status_code=400,
            detail="Hanya outlet berstatus nonaktif yang bisa diaktifkan kembali.",
        )

    outlet.status = "aktif"
    outlet.updated_at = datetime.now(timezone.utc)
    db.add(outlet)
    await db.commit()
    await db.refresh(outlet)
    return outlet

async def deactivate_outlet(
    outlet_id: uuid.UUID,
    user: User,
    kode_role: str,
    db: AsyncSession,
) -> Outlet:
    """
    Nonaktifkan outlet.

    Aturan:
    - Role non-global wajib lolos assert_distributor_in_scope() terhadap
      distributor outlet tersebut
    - Hanya outlet berstatus aktif yang bisa dinonaktifkan
    """
    outlet = await get_outlet_or_404(outlet_id, db)

    if not await has_global_access(user, kode_role, db):
        await assert_distributor_in_scope(
            outlet.distributor_id,
            user,
            kode_role,
            db,
            forbidden_message="Anda tidak berhak menonaktifkan outlet ini.",
        )

    if outlet.status != "aktif":
        raise HTTPException(
            status_code=400,
            detail="Hanya outlet berstatus aktif yang bisa dinonaktifkan.",
        )

    outlet.status = "nonaktif"
    outlet.updated_at = datetime.now(timezone.utc)
    db.add(outlet)
    await db.commit()
    await db.refresh(outlet)
    return outlet

# ─── ASSIGNABLE USERS ─────────────────────────────────────────────────────────

async def get_assignable_pic_users(
    distributor_id: uuid.UUID,
    db: AsyncSession,
) -> List[User]:
    """
    Kembalikan list user yang boleh di-assign sebagai PIC outlet
    untuk distributor tertentu.

    User yang dikembalikan:
    - is_active = True, DAN
    - Belum jadi PIC di outlet manapun, ATAU sudah jadi PIC tapi
      HANYA di distributor yang sama dengan distributor_id ini.

    Logika: exclude user yang sudah jadi PIC di distributor LAIN.
    Dipakai FE untuk populate dropdown saat buat/edit outlet.
    """
    konflik_subquery = (
        select(Outlet.pic_user_id)
        .where(
            Outlet.pic_user_id.isnot(None),
            Outlet.distributor_id != distributor_id,
        )
        .scalar_subquery()
    )

    result = await db.execute(
        select(User)
        .where(
            User.is_active == True,
            User.id.notin_(konflik_subquery),
        )
        .order_by(User.nama)
    )
    return result.scalars().all()
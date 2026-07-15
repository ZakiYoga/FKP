"""
Outlet Service — business logic untuk CRUD outlet oleh internal user.

Berbeda dari outlet_register_service.py yang menangani:
  - Registrasi publik (calon outlet daftar sendiri)
  - Approval/reject flow

File ini menangani operasi internal oleh admin_ho, distributor, sc_spv, apsm:
  - Buat outlet langsung (tanpa registrasi publik)
  - Update outlet
  - List outlet dengan scoping per role
  - Assign/validasi PIC

Semua pengecekan scope role (siapa boleh akses distributor mana) tetap
di authz_helpers.py — service ini hanya memanggil helper tersebut,
tidak menduplikasi logikanya.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outlet import Outlet
from app.models.user import User
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


# ─── LIST ─────────────────────────────────────────────────────────────────────

async def list_outlets(
    db: AsyncSession,
    user: User,
    kode_role: str,
    distributor_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
) -> List[Outlet]:
    """
    List outlet dengan scoping otomatis per role.
    Filter opsional: distributor_id, status.

    Scoping mengikuti get_scoped_distributor_ids() dari authz_helpers —
    satu sumber kebenaran, tidak ada duplikasi logika scope di sini.
    """
    query = select(Outlet)

    scoped_ids = await get_scoped_distributor_ids(user, kode_role, db)

    if scoped_ids is None:
        # Akses global — tidak ada filter scope
        pass
    elif not scoped_ids:
        return []
    elif kode_role == "outlet":
        # Role outlet: filter by pic_user_id, bukan distributor_id
        query = query.where(Outlet.pic_user_id == user.id)
    else:
        query = query.where(Outlet.distributor_id.in_(scoped_ids))

    if distributor_id:
        query = query.where(Outlet.distributor_id == distributor_id)
    if status:
        query = query.where(Outlet.status == status)

    result = await db.execute(query.order_by(Outlet.nama_toko))
    return result.scalars().all()


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
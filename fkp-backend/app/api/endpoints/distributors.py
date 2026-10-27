"""
Distributor Endpoints:
  GET    /api/distributors/                          → List (difilter otomatis by role, tanpa pagination)
  GET    /api/distributors/page                      → List berpagination + search
  GET    /api/distributors/status-summary            → Jumlah distributor per status
  GET    /api/distributors/public                    → List distributor aktif (publik, tanpa token)
  POST   /api/distributors/                          → Buat baru (superadmin, admin_ho)
  GET    /api/distributors/{id}                      → Detail
  PUT    /api/distributors/{id}                      → Update (superadmin, admin_ho)
  DELETE /api/distributors/{id}                      → Nonaktifkan (superadmin)
  POST   /api/distributors/{id}/activate             → Aktifkan kembali
  GET    /api/distributors/{id}/users                → List user di distributor
  POST   /api/distributors/{id}/users                → Tambah user ke distributor
  DELETE /api/distributors/{id}/users/{user_id}      → Lepas user dari distributor

Akses GET / , /page, /status-summary:
  Semua role yang butuh data distributor diizinkan masuk.
  Filtering data dilakukan sepenuhnya di service layer (list_distributors_by_role,
  list_distributors_paginated, get_distributor_status_summary), bukan di route —
  agar route tetap bersih dan logika bisnis terpusat.

Catatan: route statis (/page, /status-summary, /public) HARUS dideklarasikan
sebelum /{distributor_id}, kalau tidak akan tertangkap sebagai distributor_id
dan memicu 422 (bukan UUID).
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.distributor import Distributor
from app.models.user import User

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_user_with_role, require_permission_dep
from app.services.permission_service import require_permission
from app.schemas.distributor import (
    DistributorCreate, DistributorDetailResponse, DistributorSelfUpdate, DistributorUpdate, DistributorResponse,
    DistributorUserAdd, DistributorUserResponse,
    DistributorListPage, DistributorStatusSummary,
)
from app.services import distributor_service
from app.services.wilayah_service import attach_wilayah

router = APIRouter()


@router.get("/", response_model=List[DistributorResponse], summary="List distributor (difilter by role)")
async def list_distributors(
    area_id: Optional[uuid.UUID] = Query(default=None, description="Filter by area"),
    status: Optional[str] = Query(default=None, description="Filter by status: aktif/nonaktif"),
    db: AsyncSession = Depends(get_db),
    auth=Depends(get_current_user_with_role),
):
    """
    Mengembalikan daftar distributor sesuai role pengguna.
    Semua logika filtering ada di `distributor_service.list_distributors_by_role()`.

    | Role                                              | Data yang dikembalikan                             |
    |---------------------------------------------------|----------------------------------------------------|
    | superadmin / admin_ho / qc / rsm / direktur / finance | Semua distributor                             |
    | apsm                                              | Distributor yang dikelola sc_spv bawahannya    |
    | sc_spv                                            | Distributor yang dia handle langsung           |
    | distributor                                       | Distributor tempat dia terdaftar (DistributorUser) |
    | outlet                                            | 1 distributor tempat outlet-nya terdaftar      |
    """
    user, kode_role = auth

    await require_permission(kode_role, "distributor.read", db)

    rows = await distributor_service.list_distributors_by_role(
            db, current_user=user, kode_role=kode_role, area_id=area_id, status=status,
        )
    items = [DistributorResponse.model_validate(d) for d in rows]
    await attach_wilayah(db, items)
    return items


@router.get("/page", response_model=DistributorListPage, summary="List distributor berpagination")
async def list_distributors_paginated(
    page: int = Query(default=1, ge=1, description="Halaman, mulai dari 1"),
    page_size: int = Query(default=10, ge=1, le=100, description="Jumlah item per halaman (maks 100)"),
    area_id: Optional[uuid.UUID] = Query(default=None, description="Filter by area"),
    status: Optional[str] = Query(default=None, description="Filter by status: aktif/nonaktif"),
    search: Optional[str] = Query(
        default=None, max_length=100,
        description="Cari di nama_perusahaan, kode_distributor, atau pemilik",
    ),
    db: AsyncSession = Depends(get_db),
    auth=Depends(get_current_user_with_role),
):
    """
    List distributor berpagination. Scope role dan permission sama persis dengan
    GET /api/distributors/. Urutan: aktif lebih dulu, lalu nama_perusahaan.
    """
    user, kode_role = auth
    await require_permission(kode_role, "distributor.read", db)

    page_data = await distributor_service.list_distributors_paginated(
            db, current_user=user, kode_role=kode_role, page=page, page_size=page_size,
            area_id=area_id, status=status, search=search,
        )
    page_data["items"] = [DistributorResponse.model_validate(d) for d in page_data["items"]]
    await attach_wilayah(db, page_data["items"])
    return page_data


@router.get("/status-summary", response_model=DistributorStatusSummary, summary="Jumlah distributor per status")
async def get_distributor_status_summary(
    area_id: Optional[uuid.UUID] = Query(default=None, description="Filter by area"),
    db: AsyncSession = Depends(get_db),
    auth=Depends(get_current_user_with_role),
):
    """Jumlah distributor per status dalam scope user — untuk counter di header."""
    user, kode_role = auth
    await require_permission(kode_role, "distributor.read", db)

    return await distributor_service.get_distributor_status_summary(
        db, current_user=user, kode_role=kode_role, area_id=area_id,
    )


@router.get("/public", summary="List distributor aktif (publik)", description="Dipakai di form registrasi outlet — tidak butuh token.",)
async def list_distributors_public(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Distributor.id, Distributor.nama_perusahaan, Distributor.kode_distributor, Distributor.alamat_lengkap)
        .where(Distributor.status == "aktif")
        .order_by(Distributor.nama_perusahaan)
    )
    rows = result.all()
    return [{"id": str(r.id), "nama_perusahaan": r.nama_perusahaan, "kode_distributor": r.kode_distributor, "alamat_lengkap": r.alamat_lengkap} for r in rows]

@router.get("/mine", response_model=List[DistributorDetailResponse], summary="Distributor milik saya (profile)")
async def list_my_distributors(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Distributor tempat user login terdaftar. can_edit true hanya jika is_primary."""
    return await distributor_service.list_my_distributors(user=user, db=db)

@router.post("/", response_model=DistributorResponse, status_code=201, summary="Buat distributor baru")
async def create_distributor(
    data: DistributorCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("distributor.manage")),
):
    return await distributor_service.create_distributor(data, db)


@router.get("/{distributor_id}", response_model=DistributorDetailResponse, summary="Detail distributor")
async def get_distributor(
    distributor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth=Depends(get_current_user_with_role),
):
    user, kode_role = auth
    await require_permission(kode_role, "distributor.read", db)
    return await distributor_service.get_distributor_detail(distributor_id, user, kode_role, db)


@router.put("/{distributor_id}", response_model=DistributorResponse, summary="Update distributor")
async def update_distributor(
    distributor_id: uuid.UUID,
    data: DistributorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("distributor.manage")),
):
    return await distributor_service.update_distributor(distributor_id, data, db)


@router.patch("/{distributor_id}/profile", response_model=DistributorDetailResponse, summary="Edit distributor oleh user primary")
async def update_my_distributor(
    distributor_id: uuid.UUID,
    data: DistributorSelfUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Otorisasi = kepemilikan (DistributorUser.is_primary), bukan permission distributor.manage."""
    return await distributor_service.update_my_distributor(distributor_id, data, user, db)


@router.delete("/{distributor_id}", summary="Nonaktifkan distributor")
async def deactivate_distributor(
    distributor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("distributor.deactivate")),
):
    return await distributor_service.deactivate_distributor(distributor_id, db)

@router.post("/{distributor_id}/activate", summary="Aktifkan kembali distributor")
async def activate_distributor_endpoint(
    distributor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("distributor.activate")),
):
    return await distributor_service.activate_distributor(distributor_id, db)

# ─── DISTRIBUTOR USERS ────────────────────────────────────────────────────────

@router.get("/{distributor_id}/users", response_model=List[DistributorUserResponse], summary="List user di distributor")
async def list_distributor_users(
    distributor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth=Depends(get_current_user_with_role),
):
    user, kode_role = auth
    await require_permission(kode_role, "distributor.user.read", db)
    return await distributor_service.list_distributor_users(distributor_id, user, kode_role, db)


@router.post("/{distributor_id}/users", response_model=DistributorUserResponse, status_code=201, summary="Tambah user ke distributor")
async def add_distributor_user(
    distributor_id: uuid.UUID,
    data: DistributorUserAdd,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("distributor.manage")),
):
    return await distributor_service.add_distributor_user(distributor_id, data, db)


@router.delete("/{distributor_id}/users/{user_id}", summary="Lepas user dari distributor")
async def remove_distributor_user(
    distributor_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("distributor.manage")),
):
    return await distributor_service.remove_distributor_user(distributor_id, user_id, db)
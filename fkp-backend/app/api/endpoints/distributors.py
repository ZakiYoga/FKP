"""
Distributor Endpoints:
  GET    /api/distributors/                          → List (difilter otomatis by role)
  POST   /api/distributors/                          → Buat baru (superadmin, admin_ho)
  GET    /api/distributors/{id}                      → Detail
  PUT    /api/distributors/{id}                      → Update (superadmin, admin_ho)
  DELETE /api/distributors/{id}                      → Nonaktifkan (superadmin)
  GET    /api/distributors/{id}/users                → List user di distributor
  POST   /api/distributors/{id}/users                → Tambah user ke distributor
  DELETE /api/distributors/{id}/users/{user_id}      → Lepas user dari distributor

Akses GET /:
  Semua role yang butuh data distributor diizinkan masuk.
  Filtering data dilakukan sepenuhnya di service layer (list_distributors_by_role),
  bukan di route — agar route tetap bersih dan logika bisnis terpusat.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.distributor import Distributor

from app.core.database import get_db
from app.core.dependencies import get_current_user_with_role, require_permission_dep
from app.services.permission_service import require_permission
from app.schemas.distributor import (
    DistributorCreate, DistributorUpdate, DistributorResponse,
    DistributorUserAdd, DistributorUserResponse,
)
from app.services import distributor_service

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

    # PERBAIKAN RBAC (Kategori B): sebelumnya cek tuple hardcode _READ_ROLES
    # di badan fungsi, tidak terhubung ke dashboard RBAC. Sekarang via
    # require_permission() — DB-driven, superadmin bypass via is_superadmin.
    await require_permission(kode_role, "distributor.read", db)

    return await distributor_service.list_distributors_by_role(
        db, current_user=user, kode_role=kode_role,
        area_id=area_id, status=status,
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


@router.post("/", response_model=DistributorResponse, status_code=201, summary="Buat distributor baru")
async def create_distributor(
    data: DistributorCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("distributor.manage")),
):
    return await distributor_service.create_distributor(data, db)


@router.get("/{distributor_id}", response_model=DistributorResponse, summary="Detail distributor")
async def get_distributor(
    distributor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("distributor.read")),
):
    return await distributor_service.get_distributor(distributor_id, db)


@router.put("/{distributor_id}", response_model=DistributorResponse, summary="Update distributor")
async def update_distributor(
    distributor_id: uuid.UUID,
    data: DistributorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("distributor.manage")),
):
    return await distributor_service.update_distributor(distributor_id, data, db)


@router.delete("/{distributor_id}", summary="Nonaktifkan distributor")
async def deactivate_distributor(
    distributor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("distributor.deactivate")),
):
    return await distributor_service.deactivate_distributor(distributor_id, db)


# ─── DISTRIBUTOR USERS ────────────────────────────────────────────────────────

@router.get(
    "/{distributor_id}/users",
    response_model=List[DistributorUserResponse],
    summary="List user di distributor",
)
async def list_distributor_users(
    distributor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("distributor.user.read")),
):
    return await distributor_service.list_distributor_users(distributor_id, db)


@router.post(
    "/{distributor_id}/users",
    response_model=DistributorUserResponse,
    status_code=201,
    summary="Tambah user ke distributor",
)
async def add_distributor_user(
    distributor_id: uuid.UUID,
    data: DistributorUserAdd,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("distributor.manage")),
):
    return await distributor_service.add_distributor_user(distributor_id, data, db)


@router.delete(
    "/{distributor_id}/users/{user_id}",
    summary="Lepas user dari distributor",
)
async def remove_distributor_user(
    distributor_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("distributor.manage")),
):
    return await distributor_service.remove_distributor_user(distributor_id, user_id, db)
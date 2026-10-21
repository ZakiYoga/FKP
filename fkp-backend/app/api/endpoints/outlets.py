"""
Outlet Endpoints — HTTP layer saja.
Semua business logic ada di outlet_service.py.

── Endpoint ────────────────────────────────────────────────────────────────
  GET    /api/outlets/                        → List outlet (scoped by role, tanpa pagination)
  GET    /api/outlets/page                    → List outlet berpagination + search
  GET    /api/outlets/status-summary          → Jumlah outlet per status
  POST   /api/outlets/                        → Buat outlet baru
  GET    /api/outlets/assignable-users        → Dropdown PIC untuk assign
  GET    /api/outlets/{id}                    → Detail outlet
  PUT    /api/outlets/{id}                    → Update outlet
  DELETE /api/outlets/{id}                    → Nonaktifkan outlet
  POST   /api/outlets/{id}/activate           → Aktifkan kembali outlet

Catatan: route statis (/page, /status-summary, /assignable-users) HARUS
dideklarasikan sebelum /{outlet_id}, kalau tidak akan tertangkap sebagai
outlet_id dan memicu 422 (bukan UUID).
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user, get_current_user_with_role,
    require_permission_dep, get_kode_role,
)
from app.models.outlet import Outlet
from app.models.user import User
from app.schemas.outlet import (
    OutletCreate, OutletUpdate, OutletResponse,
    OutletListPage, OutletStatusSummary,
)
from app.schemas.user import UserBriefResponse
from app.services import outlet_service

router = APIRouter()


@router.get("/", response_model=List[OutletResponse])
async def list_outlets(
    distributor_id: Optional[uuid.UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    auth=Depends(get_current_user_with_role),
):
    user, kode_role = auth
    return await outlet_service.list_outlets(
        db=db,
        user=user,
        kode_role=kode_role,
        distributor_id=distributor_id,
        status=status,
    )


@router.get("/page", response_model=OutletListPage)
async def list_outlets_paginated(
    page: int = Query(default=1, ge=1, description="Halaman, mulai dari 1"),
    page_size: int = Query(default=10, ge=1, le=100, description="Jumlah item per halaman (maks 100)"),
    area_id: Optional[uuid.UUID] = Query(default=None, description="Filter by area"),
    distributor_id: Optional[uuid.UUID] = Query(default=None),
    status: Optional[str] = Query(default=None, description="aktif | pending | nonaktif"),
    search: Optional[str] = Query(
        default=None, max_length=100,
        description="Cari di nama_toko, kode_outlet, atau pemilik_toko",
    ),
    db: AsyncSession = Depends(get_db),
    auth=Depends(get_current_user_with_role),
):
    """
    List outlet berpagination. Scope role sama persis dengan GET /api/outlets/.
    Untuk antrean persetujuan: ?status=pending&page=1&page_size=4
    (diurutkan dari yang paling lama menunggu).
    """
    user, kode_role = auth
    return await outlet_service.list_outlets_paginated(
        db=db, user=user, kode_role=kode_role,
        page=page, page_size=page_size,
        distributor_id=distributor_id, area_id=area_id,
        status=status, search=search,
    )


@router.get("/status-summary", response_model=OutletStatusSummary)
async def get_outlet_status_summary(
    distributor_id: Optional[uuid.UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    auth=Depends(get_current_user_with_role),
):
    """Jumlah outlet per status dalam scope user — untuk badge/counter di header."""
    user, kode_role = auth
    return await outlet_service.get_outlet_status_summary(
        db=db, user=user, kode_role=kode_role, distributor_id=distributor_id,
    )


@router.post("/", response_model=OutletResponse, status_code=201)
async def create_outlet(
    data: OutletCreate,
    db: AsyncSession = Depends(get_db),
    auth=Depends(get_current_user_with_role),
    _=Depends(require_permission_dep("outlet.manage")),
):
    user, kode_role = auth
    return await outlet_service.create_outlet(
        data=data, user=user, kode_role=kode_role, db=db,
    )


@router.get("/assignable-users", response_model=List[UserBriefResponse])
async def list_assignable_pic_users(
    distributor_id: uuid.UUID = Query(..., description="Distributor tujuan outlet"),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission_dep("outlet.assignable_users.read")),
):
    """
    List user yang bisa di-assign sebagai PIC outlet untuk distributor tertentu.
    Dipakai FE untuk populate dropdown saat buat/edit outlet.
    Hanya admin_ho dan superadmin yang bisa memanggil endpoint ini.
    """
    return await outlet_service.get_assignable_pic_users(
        distributor_id=distributor_id, db=db,
    )


@router.get("/{outlet_id}", response_model=OutletResponse)
async def get_outlet(
    outlet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await outlet_service.get_outlet_or_404(outlet_id, db)


@router.put("/{outlet_id}", response_model=OutletResponse)
async def update_outlet(
    outlet_id: uuid.UUID,
    data: OutletUpdate,
    db: AsyncSession = Depends(get_db),
    auth=Depends(get_current_user_with_role),
    _=Depends(require_permission_dep("outlet.manage")),
):
    user, kode_role = auth
    return await outlet_service.update_outlet(
        outlet_id=outlet_id, data=data, user=user, kode_role=kode_role, db=db,
    )

@router.delete("/{outlet_id}")
async def deactivate_outlet(
    outlet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth=Depends(get_current_user_with_role),
    _=Depends(require_permission_dep("outlet.deactivate")),
):
    user, kode_role = auth
    outlet = await outlet_service.deactivate_outlet(
        outlet_id=outlet_id, user=user, kode_role=kode_role, db=db,
    )
    return {"message": f"Outlet '{outlet.nama_toko}' dinonaktifkan."}

@router.post("/{outlet_id}/activate")
async def activate_outlet(
    outlet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth=Depends(get_current_user_with_role),
    _=Depends(require_permission_dep("outlet.activate")),
):
    user, kode_role = auth
    outlet = await outlet_service.activate_outlet(
        outlet_id=outlet_id, user=user, kode_role=kode_role, db=db,
    )
    return {"message": f"Outlet '{outlet.nama_toko}' diaktifkan kembali."}
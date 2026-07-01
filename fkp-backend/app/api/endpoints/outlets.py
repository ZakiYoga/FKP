"""
Outlet Endpoints — HTTP layer saja.
Semua business logic ada di outlet_service.py.

── Endpoint ────────────────────────────────────────────────────────────────
  GET    /api/outlets/                        → List outlet (scoped by role)
  POST   /api/outlets/                        → Buat outlet baru
  GET    /api/outlets/assignable-users        → Dropdown PIC untuk assign
  GET    /api/outlets/{id}                    → Detail outlet
  PUT    /api/outlets/{id}                    → Update outlet
  DELETE /api/outlets/{id}                    → Nonaktifkan outlet
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
from app.schemas.outlet import OutletCreate, OutletUpdate, OutletResponse
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
    _=Depends(require_permission_dep("outlet.deactivate")),
):
    outlet = await outlet_service.get_outlet_or_404(outlet_id, db)
    from datetime import datetime, timezone
    outlet.status = "nonaktif"
    outlet.updated_at = datetime.now(timezone.utc)
    db.add(outlet)
    await db.commit()
    return {"message": f"Outlet '{outlet.nama_toko}' dinonaktifkan."}
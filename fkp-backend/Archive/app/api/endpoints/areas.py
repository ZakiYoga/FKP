"""
Area Endpoints:
  GET    /api/areas/              → List semua area (semua role)
  POST   /api/areas/              → Buat area baru (superadmin)
  GET    /api/areas/{id}          → Detail area + daftar provinsi
  PUT    /api/areas/{id}          → Update area (superadmin, admin_ho)
  GET    /api/areas/{id}/provinsi → List provinsi di area ini
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission_dep
from app.models.wilayah import Provinsi
from app.schemas.area import AreaCreate, AreaUpdate, AreaResponse, ProvinsiResponse
from app.services import area_service

router = APIRouter()


@router.get("/", response_model=List[AreaResponse], summary="List semua area")
async def list_areas(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),   # semua role bisa akses
):
    return await area_service.list_areas(db)


@router.post(
    "/",
    response_model=AreaResponse,
    status_code=201,
    summary="Buat area baru (SuperAdmin)",
)
async def create_area(
    data: AreaCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("area.manage")),
):
    return await area_service.create_area(data, db)


@router.get("/{area_id}", response_model=AreaResponse, summary="Detail area")
async def get_area(
    area_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await area_service.get_area(area_id, db)


@router.put(
    "/{area_id}",
    response_model=AreaResponse,
    summary="Update area (SuperAdmin / Admin HO)",
)
async def update_area(
    area_id: uuid.UUID,
    data: AreaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("area.update")),
):
    return await area_service.update_area(area_id, data, db)


@router.get(
    "/provinsi/all",
    response_model=List[ProvinsiResponse],
    summary="List semua provinsi (untuk dropdown)",
)
async def list_all_provinsi(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Provinsi).order_by(Provinsi.nama_provinsi))
    return result.scalars().all()
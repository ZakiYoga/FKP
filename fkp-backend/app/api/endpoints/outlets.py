"""
Outlet Endpoints:
  GET    /api/outlets/              → List outlet (filter by distributor)
  POST   /api/outlets/              → Buat outlet baru
  GET    /api/outlets/{id}          → Detail outlet
  PUT    /api/outlets/{id}          → Update outlet
  DELETE /api/outlets/{id}          → Nonaktifkan outlet
"""
import uuid
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_user_with_role, require_roles
from app.models.outlet import Outlet
from app.models.distributor import DistributorUser
from app.models.sc_spv import ScSpvDistributor, ApsmScSpv
from app.schemas.outlet import OutletCreate, OutletUpdate, OutletResponse

router = APIRouter()


@router.get("/", response_model=List[OutletResponse], summary="List outlet (difilter by role)")
async def list_outlets(
    distributor_id: Optional[uuid.UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    auth=Depends(get_current_user_with_role),
):
    """
    Mengembalikan daftar outlet sesuai role pengguna.
 
    | Role                                                   | Data yang dikembalikan                              |
    |--------------------------------------------------------|-----------------------------------------------------|
    | superadmin / admin_ho / qc / rsm / direktur / finance | Semua outlet                                        |
    | apsm                                                   | Outlet dari distributor yang dikelola sc_spv-nya    |
    | sc_spv                                                 | Outlet dari distributor yang dia handle             |
    | distributor                                            | Outlet dari distributor tempat dia terdaftar        |
    | outlet                                                 | Hanya outlet miliknya sendiri (via pic_user_id)     |
    """
    user, kode_role = auth
 
    query = select(Outlet)
 
    # ── Role dengan akses penuh ──────────────────────────────────────────────
    if kode_role in ("superadmin", "admin_ho", "qc", "rsm", "direktur", "finance"):
        pass  # Tidak ada pembatasan — lanjut ke filter opsional
 
    # ── Outlet: hanya outlet miliknya sendiri ────────────────────────────────
    elif kode_role == "outlet":
        query = query.where(Outlet.pic_user_id == user.id)
 
    # ── Distributor: outlet dari distributor tempat dia terdaftar ────────────
    elif kode_role == "distributor":
        du_result = await db.execute(
            select(DistributorUser.distributor_id).where(
                DistributorUser.user_id == user.id
            )
        )
        dist_ids = du_result.scalars().all()
        if not dist_ids:
            return []
        query = query.where(Outlet.distributor_id.in_(dist_ids))
 
    # ── SC/SPV: outlet dari distributor yang dia handle ──────────────────────
    elif kode_role == "sc_spv":
        dist_result = await db.execute(
            select(ScSpvDistributor.distributor_id).where(
                ScSpvDistributor.sc_spv_user_id == user.id
            )
        )
        dist_ids = dist_result.scalars().all()
        if not dist_ids:
            return []
        query = query.where(Outlet.distributor_id.in_(dist_ids))
 
    # ── APSM: outlet dari distributor yang dikelola sc_spv bawahannya ────────
    elif kode_role == "apsm":
        sc_result = await db.execute(
            select(ApsmScSpv.sc_spv_user_id).where(
                ApsmScSpv.apsm_user_id == user.id
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
        query = query.where(Outlet.distributor_id.in_(dist_ids))
 
    else:
        raise HTTPException(status_code=403, detail=f"Role '{kode_role}' tidak diizinkan mengakses data outlet.")
 
    # ── Filter opsional ──────────────────────────────────────────────────────
    if distributor_id:
        query = query.where(Outlet.distributor_id == distributor_id)
    if status:
        query = query.where(Outlet.status == status)
 
    result = await db.execute(query.order_by(Outlet.nama_toko))
    return result.scalars().all()


@router.post("/", response_model=OutletResponse, status_code=201, summary="Buat outlet baru")
async def create_outlet(
    data: OutletCreate,
    db: AsyncSession = Depends(get_db),
    auth=Depends(get_current_user_with_role),
    current_user=Depends(require_roles("superadmin", "admin_ho", "apsm", "sc_spv", "distributor")),
):
    user, kode_role = auth
    print(f"DEBUG kode_role: '{kode_role}'")  # lihat di log server
    # Cek kode_outlet unik
    existing = await db.execute(select(Outlet).where(Outlet.kode_outlet == data.kode_outlet))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Kode outlet '{data.kode_outlet}' sudah digunakan.")

    outlet = Outlet(**data.model_dump())
    db.add(outlet)
    await db.commit()
    await db.refresh(outlet)
    return outlet


@router.get("/{outlet_id}", response_model=OutletResponse, summary="Detail outlet")
async def get_outlet(
    outlet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Outlet).where(Outlet.id == outlet_id))
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan.")
    return outlet


@router.put("/{outlet_id}", response_model=OutletResponse, summary="Update outlet")
async def update_outlet(
    outlet_id: uuid.UUID,
    data: OutletUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles("superadmin", "admin_ho", "apsm", "sc_spv", "distributor")),
):
    result = await db.execute(select(Outlet).where(Outlet.id == outlet_id))
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan.")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(outlet, k, v)
    outlet.updated_at = datetime.now(timezone.utc)
    db.add(outlet)
    await db.commit()
    await db.refresh(outlet)
    return outlet


@router.delete("/{outlet_id}", summary="Nonaktifkan outlet")
async def deactivate_outlet(
    outlet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles("superadmin", "admin_ho")),
):
    result = await db.execute(select(Outlet).where(Outlet.id == outlet_id))
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan.")
    outlet.status = "nonaktif"
    outlet.updated_at = datetime.now(timezone.utc)
    db.add(outlet)
    await db.commit()
    return {"message": f"Outlet '{outlet.nama_toko}' dinonaktifkan."}
"""
Hierarchy Endpoints — manajemen hierarki sales RSM → APSM → SC/SPV → Distributor.

RSM ↔ APSM:
  GET    /api/hierarchy/rsm/{rsm_id}/apsm                       → List APSM di bawah RSM
  POST   /api/hierarchy/rsm/apsm                                → Assign APSM ke RSM
  DELETE /api/hierarchy/rsm/{rsm_id}/apsm/{apsm_id}             → Lepas APSM dari RSM
  GET    /api/hierarchy/rsm/{rsm_id}/team                       → Lihat hierarki lengkap

APSM ↔ SC/SPV:
  GET    /api/hierarchy/apsm/{apsm_id}/sc-spv                   → List SC/SPV di bawah APSM
  POST   /api/hierarchy/apsm/sc-spv                             → Assign SC/SPV ke APSM
  DELETE /api/hierarchy/apsm/{apsm_id}/sc-spv/{sc_spv_id}       → Lepas SC/SPV dari APSM
  GET /api/hierarchy/apsm/{apsm_id}/areas

SC/SPV ↔ DISTRIBUTOR:
  GET    /api/hierarchy/sc-spv/{sc_id}/distributors             → List distributor SC/SPV
  POST   /api/hierarchy/sc-spv/distributor                      → Assign distributor ke SC/SPV
  DELETE /api/hierarchy/sc-spv/{sc_id}/distributors/{dist_id}   → Lepas distributor
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission_dep
from app.schemas.hierarchy import (
    AreaBasicInfo, RsmApsmAssign, RsmApsmResponse,
    ApsmScSpvAssign, ApsmScSpvResponse,
    ScSpvDistributorAssign, ScSpvDistributorResponse,
    RsmWithTeam,
)
from sqlmodel import select
from app.models.user import User
from app.models.role import Role
from app.models.sc_spv import RsmApsm, ApsmScSpv, ScSpvDistributor
from app.models.distributor import Distributor
from app.models.area import Area
from app.schemas.hierarchy import UserBasicInfo, DistributorBasicInfo
from app.services import hierarchy_service
from app.services.hierarchy_service import to_user_basic

router = APIRouter()


@router.get(
    "/users/by-role",
    response_model=List[UserBasicInfo],
    summary="List users by kode_role — untuk dropdown hierarki",
)
async def list_users_by_role(
    kode_role: str,
    unassigned: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("hierarchy.read")),
):
    q = (
        select(User)
        .join(Role, User.role_id == Role.id)
        .where(Role.kode_role == kode_role, User.is_active == True)
        .order_by(User.first_name, User.last_name)
    )
    if unassigned:
        if kode_role == "apsm":
            q = q.where(User.id.not_in(select(RsmApsm.apsm_user_id)))
        elif kode_role == "sc_spv":
            q = q.where(User.id.not_in(select(ApsmScSpv.sc_spv_user_id)))

    result = await db.execute(q)
    return [to_user_basic(u) for u in result.scalars().all()]


@router.get(
    "/distributors",
    response_model=List[DistributorBasicInfo],
    summary="List distributor aktif — untuk dropdown assign hierarki",
)
async def list_distributors_for_hierarchy(
    unassigned: bool = False,
    area_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("hierarchy.read")),
):
    q = (
        select(Distributor)
        .where(Distributor.status == "aktif")
        .order_by(Distributor.nama_perusahaan)
    )
    if unassigned:
        q = q.where(Distributor.id.not_in(select(ScSpvDistributor.distributor_id)))
    if area_id:
        q = q.where(Distributor.area_id == area_id)
    result = await db.execute(q)
    return result.scalars().all()

# ─── RSM ↔ APSM ──────────────────────────────────────────────────────────────

@router.get(
    "/rsm/{rsm_user_id}/apsm",
    response_model=List[RsmApsmResponse],
    summary="List APSM di bawah RSM",
)
async def list_rsm_apsm(
    rsm_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("hierarchy.rsm_apsm.read")),
):
    return await hierarchy_service.list_rsm_apsm(rsm_user_id, db)


@router.post(
    "/rsm/apsm",
    response_model=RsmApsmResponse,
    status_code=201,
    summary="Assign APSM ke RSM",
)
async def assign_apsm_to_rsm(
    data: RsmApsmAssign,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("hierarchy.manage")),
):
    return await hierarchy_service.assign_apsm_to_rsm(data, db)


@router.delete(
    "/rsm/{rsm_user_id}/apsm/{apsm_user_id}",
    summary="Lepas APSM dari RSM",
)
async def remove_apsm_from_rsm(
    rsm_user_id: uuid.UUID,
    apsm_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("hierarchy.manage")),
):
    return await hierarchy_service.remove_apsm_from_rsm(rsm_user_id, apsm_user_id, db)


@router.get(
    "/rsm/{rsm_user_id}/team",
    response_model=RsmWithTeam,
    summary="Lihat hierarki lengkap tim RSM (RSM → APSM → SC/SPV → Distributor)",
)
async def get_rsm_team(
    rsm_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("hierarchy.read")),
):
    return await hierarchy_service.get_hierarchy_by_rsm(rsm_user_id, db)


# ─── APSM ↔ SC/SPV ───────────────────────────────────────────────────────────

@router.get(
    "/apsm/{apsm_user_id}/sc-spv",
    response_model=List[ApsmScSpvResponse],
    summary="List SC/SPV di bawah APSM",
)
async def list_apsm_sc_spv(
    apsm_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("hierarchy.apsm_sc_spv.read")),
):
    return await hierarchy_service.list_apsm_sc_spv(apsm_user_id, db)


@router.post(
    "/apsm/sc-spv",
    response_model=ApsmScSpvResponse,
    status_code=201,
    summary="Assign SC/SPV ke APSM",
)
async def assign_sc_spv_to_apsm(
    data: ApsmScSpvAssign,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("hierarchy.manage")),
):
    return await hierarchy_service.assign_sc_spv_to_apsm(data, db)


@router.delete(
    "/apsm/{apsm_user_id}/sc-spv/{sc_spv_user_id}",
    summary="Lepas SC/SPV dari APSM",
)
async def remove_sc_spv_from_apsm(
    apsm_user_id: uuid.UUID,
    sc_spv_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("hierarchy.manage")),
):
    return await hierarchy_service.remove_sc_spv_from_apsm(apsm_user_id, sc_spv_user_id, db)


@router.get(
    "/apsm/{apsm_user_id}/areas",
    response_model=List[AreaBasicInfo],
    summary="Area aktif yang dipegang APSM",
)
async def list_apsm_areas(
    apsm_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("hierarchy.read")),
):
    result = await db.execute(
        select(Area)
        .where(Area.pic_user_id == apsm_user_id, Area.status == "aktif")
        .order_by(Area.nama_area)
    )
    return result.scalars().all()

# ─── SC/SPV ↔ DISTRIBUTOR ────────────────────────────────────────────────────

@router.get(
    "/sc-spv/{sc_spv_user_id}/distributors",
    response_model=List[ScSpvDistributorResponse],
    summary="List distributor yang di-handle SC/SPV",
)
async def list_sc_spv_distributors(
    sc_spv_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("hierarchy.sc_spv_distributor.read")),
):
    return await hierarchy_service.list_sc_spv_distributors(sc_spv_user_id, db)


@router.post(
    "/sc-spv/distributor",
    response_model=ScSpvDistributorResponse,
    status_code=201,
    summary="Assign distributor ke SC/SPV (dengan validasi area APSM atasan)",
)
async def assign_distributor_to_sc_spv(
    data: ScSpvDistributorAssign,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("hierarchy.manage")),
):
    return await hierarchy_service.assign_distributor_to_sc_spv(data, db)


@router.delete(
    "/sc-spv/{sc_spv_user_id}/distributors/{distributor_id}",
    summary="Lepas distributor dari SC/SPV",
)
async def remove_distributor_from_sc_spv(
    sc_spv_user_id: uuid.UUID,
    distributor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("hierarchy.manage")),
):
    return await hierarchy_service.remove_distributor_from_sc_spv(sc_spv_user_id, distributor_id, db)
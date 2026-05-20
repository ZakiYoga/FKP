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

SC/SPV ↔ DISTRIBUTOR:
  GET    /api/hierarchy/sc-spv/{sc_id}/distributors             → List distributor SC/SPV
  POST   /api/hierarchy/sc-spv/distributor                      → Assign distributor ke SC/SPV
  DELETE /api/hierarchy/sc-spv/{sc_id}/distributors/{dist_id}   → Lepas distributor
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.schemas.hierarchy import (
    RsmApsmAssign, RsmApsmResponse,
    ApsmScSpvAssign, ApsmScSpvResponse,
    ScSpvDistributorAssign, ScSpvDistributorResponse,
    RsmWithTeam,
)
from app.services import hierarchy_service

router = APIRouter()

ADMIN_ROLES = ("superadmin", "admin_ho")


# ─── RSM ↔ APSM ──────────────────────────────────────────────────────────────

@router.get(
    "/rsm/{rsm_user_id}/apsm",
    response_model=List[RsmApsmResponse],
    summary="List APSM di bawah RSM",
)
async def list_rsm_apsm(
    rsm_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(*ADMIN_ROLES, "rsm")),
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
    current_user=Depends(require_roles(*ADMIN_ROLES)),
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
    current_user=Depends(require_roles(*ADMIN_ROLES)),
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
    current_user=Depends(require_roles(*ADMIN_ROLES, "rsm", "direktur")),
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
    current_user=Depends(require_roles(*ADMIN_ROLES, "apsm", "rsm")),
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
    current_user=Depends(require_roles(*ADMIN_ROLES)),
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
    current_user=Depends(require_roles(*ADMIN_ROLES)),
):
    return await hierarchy_service.remove_sc_spv_from_apsm(apsm_user_id, sc_spv_user_id, db)


# ─── SC/SPV ↔ DISTRIBUTOR ────────────────────────────────────────────────────

@router.get(
    "/sc-spv/{sc_spv_user_id}/distributors",
    response_model=List[ScSpvDistributorResponse],
    summary="List distributor yang di-handle SC/SPV",
)
async def list_sc_spv_distributors(
    sc_spv_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(*ADMIN_ROLES, "apsm", "sc_spv", "rsm")),
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
    current_user=Depends(require_roles(*ADMIN_ROLES)),
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
    current_user=Depends(require_roles(*ADMIN_ROLES)),
):
    return await hierarchy_service.remove_distributor_from_sc_spv(sc_spv_user_id, distributor_id, db)

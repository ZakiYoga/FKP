"""
Outlet Registration Management Endpoints:
  GET  /api/outlet-registrations/               → List outlet pending (admin/distributor)
  GET  /api/outlet-registrations/{outlet_id}    → Detail satu registrasi
  POST /api/outlet-registrations/{outlet_id}/approve  → Setujui registrasi
  POST /api/outlet-registrations/{outlet_id}/reject   → Tolak registrasi
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_db
from app.core.dependencies import get_current_user_with_role, require_roles
from app.models.outlet import Outlet
from app.models.user import User
from app.schemas.outlet_register import (
    OutletRegistrationDetail,
    OutletRegistrationListResponse,
    OutletApproveRequest,
    OutletApproveResponse,
    OutletRejectRequest,
    OutletRejectResponse,
)
from app.services.outlet_register_service import (
    list_pending_registrations,
    approve_registration,
    reject_registration,
)

router = APIRouter()

APPROVE_REJECT_ROLES = ("superadmin", "admin_ho", "distributor", "sc_spv", "apsm")


# ─── LIST PENDAFTARAN PENDING ─────────────────────────────────────────────────

@router.get(
    "/",
    response_model=OutletRegistrationListResponse,
    summary="Daftar outlet yang menunggu verifikasi",
    description=(
        "Mengembalikan outlet dengan status `pending`. "
        "**superadmin/admin_ho** melihat semua. "
        "**distributor** hanya melihat outlet di bawah distributornya."
    ),
)
async def list_registrations(
    distributor_id: Optional[uuid.UUID] = Query(default=None, description="Filter by distributor (opsional)"),
    db: AsyncSession = Depends(get_db),
    auth=Depends(get_current_user_with_role),
):
    user, kode_role = auth
    try:
        return await list_pending_registrations(
            session=db,
            requesting_user=user,
            kode_role=kode_role,
            distributor_id=distributor_id,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# ─── DETAIL SATU REGISTRASI ───────────────────────────────────────────────────

@router.get(
    "/{outlet_id}",
    response_model=OutletRegistrationDetail,
    summary="Detail satu pendaftaran outlet",
)
async def get_registration_detail(
    outlet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth=Depends(get_current_user_with_role),
):
    user, kode_role = auth

    result = await db.execute(select(Outlet).where(Outlet.id == outlet_id))
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan.")

    # Batasi akses: distributor hanya bisa lihat outlet miliknya
    if kode_role == "distributor":
        from app.models.distributor import DistributorUser
        du_result = await db.execute(
            select(DistributorUser.distributor_id).where(
                DistributorUser.user_id == user.id
            )
        )
        dist_ids = du_result.scalars().all()
        if outlet.distributor_id not in dist_ids:
            raise HTTPException(status_code=403, detail="Akses ditolak.")

    elif kode_role not in ("superadmin", "admin_ho", "qc", "rsm", "direktur", "sc_spv", "apsm"):
        raise HTTPException(status_code=403, detail=f"Role '{kode_role}' tidak diizinkan.")

    # Ambil email dari User terkait
    email = outlet.email or ""
    if outlet.pic_user_id:
        u_result = await db.execute(
            select(User.email).where(User.id == outlet.pic_user_id)
        )
        email = u_result.scalar_one_or_none() or email

    return OutletRegistrationDetail(
        outlet_id=outlet.id,
        user_id=outlet.pic_user_id,
        kode_outlet=outlet.kode_outlet,
        nama_toko=outlet.nama_toko,
        pemilik_toko=outlet.pemilik_toko,
        tipe_toko=outlet.tipe_toko,
        no_hp=outlet.no_hp,
        email=email,
        alamat_lengkap=outlet.alamat_lengkap,
        distributor_id=outlet.distributor_id,
        status=outlet.status,
        created_at=outlet.created_at,
    )


# ─── APPROVE ─────────────────────────────────────────────────────────────────

@router.post(
    "/{outlet_id}/approve",
    response_model=OutletApproveResponse,
    summary="Setujui pendaftaran outlet",
    description=(
        "Mengubah status outlet dari `pending` → `aktif` "
        "dan mengaktifkan akun user outlet tersebut. "
        "Role yang diizinkan: superadmin, admin_ho, distributor, sc_spv, apsm."
    ),
)
async def approve_outlet_registration(
    outlet_id: uuid.UUID,
    payload: OutletApproveRequest = OutletApproveRequest(),
    db: AsyncSession = Depends(get_db),
    auth=Depends(get_current_user_with_role),
):
    user, kode_role = auth

    if kode_role not in APPROVE_REJECT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{kode_role}' tidak diizinkan melakukan persetujuan.",
        )

    try:
        return await approve_registration(
            outlet_id=outlet_id,
            payload=payload,
            session=db,
            requesting_user=user,
            kode_role=kode_role,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# ─── REJECT ──────────────────────────────────────────────────────────────────

@router.post(
    "/{outlet_id}/reject",
    response_model=OutletRejectResponse,
    summary="Tolak pendaftaran outlet",
    description=(
        "Mengubah status outlet dari `pending` → `ditolak`. "
        "Akun user tetap tidak aktif. Alasan penolakan wajib diisi. "
        "Role yang diizinkan: superadmin, admin_ho, distributor, sc_spv, apsm."
    ),
)
async def reject_outlet_registration(
    outlet_id: uuid.UUID,
    payload: OutletRejectRequest,
    db: AsyncSession = Depends(get_db),
    auth=Depends(get_current_user_with_role),
):
    user, kode_role = auth

    if kode_role not in APPROVE_REJECT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{kode_role}' tidak diizinkan melakukan penolakan.",
        )

    try:
        return await reject_registration(
            outlet_id=outlet_id,
            payload=payload,
            session=db,
            requesting_user=user,
            kode_role=kode_role,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
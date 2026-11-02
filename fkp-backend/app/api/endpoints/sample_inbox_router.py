"""
Router — Sample Inbox ("Sample Masuk"): list sample lintas FKP.

Dipasang di main.py dengan prefix="/api/samples". Sengaja BUKAN
/api/fkp/samples karena bentrok dengan route /{fkp_id} milik router FKP.

Permission: sample.view_all (warehouse, qc, admin_ho; superadmin bypass).
Endpoint aksi per-FKP (receive, forward-to-qc, dst.) tetap di sample_router.py.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_kode_role
from app.models.user import User
from app.schemas.sample import SampleInboxPage, SampleStatusSummary
from app.services import sample_service

router = APIRouter()


@router.get("", response_model=SampleInboxPage)
async def list_samples_inbox(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(
        None,
        description="Satu atau beberapa status dipisah koma, mis. forwarded_to_qc,under_qc_review",
    ),
    search: Optional[str] = Query(
        None,
        description="ILIKE pada nomor FKP, nama produk, nomor resi, nomor tanda terima, nama distributor, nama toko",
    ),
    tanggal_dari: Optional[date] = Query(None, description="Terhadap tanggal_kirim, inklusif"),
    tanggal_sampai: Optional[date] = Query(None, description="Terhadap tanggal_kirim, inklusif"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await sample_service.list_samples_inbox(
        user, kode_role, db,
        page=page, page_size=page_size, status=status, search=search,
        tanggal_dari=tanggal_dari, tanggal_sampai=tanggal_sampai,
    )


@router.get("/summary", response_model=SampleStatusSummary)
async def get_samples_summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await sample_service.get_samples_summary(user, kode_role, db)
"""
Router — Warehouse Surat Jalan Inbox (halaman "Surat Jalan").

Dipasang di main.py dengan prefix="/api/warehouse". Endpoint aksi per-FKP
(create, issue, ship, confirm-delivery, pdf) tetap di warehouse_router.py
(/api/fkp/{fkp_id}/warehouse/surat-jalan/...) dan tidak berubah.

Permission: warehouse.surat_jalan.view_all (warehouse, admin_ho, rsm, direktur; superadmin bypass).
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_kode_role
from app.models.user import User
from app.schemas.warehouse import (
    PendingSjPage, SuratJalanInboxPage, SuratJalanSummary,
)
from app.services import warehouse_inbox_service

router = APIRouter()


# Urutan penting: "/summary" dan "/pending-fkp" tidak bentrok dengan "" karena
# tidak ada route berparameter di router ini.

@router.get("/surat-jalan", response_model=SuratJalanInboxPage)
async def list_surat_jalan_inbox(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(
        None, description="Satu atau beberapa status dipisah koma, mis. draft,issued",
    ),
    search: Optional[str] = Query(
        None, description="ILIKE pada no. SJ, no. FKP, nama penerima, no. resi, distributor, toko",
    ),
    tanggal_dari: Optional[date] = Query(None, description="Terhadap tanggal_surat_jalan, inklusif"),
    tanggal_sampai: Optional[date] = Query(None, description="Terhadap tanggal_surat_jalan, inklusif"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await warehouse_inbox_service.list_surat_jalan_inbox(
        user, kode_role, db, page=page, page_size=page_size, status=status,
        search=search, tanggal_dari=tanggal_dari, tanggal_sampai=tanggal_sampai,
    )


@router.get("/surat-jalan/summary", response_model=SuratJalanSummary)
async def get_surat_jalan_summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await warehouse_inbox_service.get_surat_jalan_summary(user, kode_role, db)


@router.get("/surat-jalan/pending-fkp", response_model=PendingSjPage)
async def list_pending_fkp(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="ILIKE pada no. FKP, distributor, toko"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await warehouse_inbox_service.list_pending_fkp(
        user, kode_role, db, page=page, page_size=page_size, search=search,
    )
"""
Router — Warehouse Surat Jalan.

Dipasang di main.py dengan prefix="/api/fkp", sehingga path lengkapnya
persis sesuai §10.1 dokumen rencana: /api/fkp/{fkp_id}/warehouse/surat-jalan/...
"""
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_kode_role
from app.core.config import settings
from app.models.user import User
from app.schemas.warehouse import (
    SuratJalanCreate, SuratJalanUpdate, SuratJalanShipRequest, SuratJalanResponse,
)
from app.services import warehouse_service

router = APIRouter()


@router.post("/{fkp_id}/warehouse/surat-jalan", response_model=SuratJalanResponse, status_code=201)
async def create_surat_jalan(
    fkp_id: uuid.UUID,
    data: SuratJalanCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await warehouse_service.create_surat_jalan(fkp_id, data, user, kode_role, db)


@router.get("/{fkp_id}/warehouse/surat-jalan", response_model=list[SuratJalanResponse])
async def list_surat_jalan(
    fkp_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await warehouse_service.list_surat_jalan(fkp_id, user, kode_role, db)


@router.get("/{fkp_id}/warehouse/surat-jalan/{sj_id}", response_model=SuratJalanResponse)
async def get_surat_jalan(
    fkp_id: uuid.UUID,
    sj_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await warehouse_service.get_surat_jalan_detail(fkp_id, sj_id, user, kode_role, db)


@router.patch("/{fkp_id}/warehouse/surat-jalan/{sj_id}", response_model=SuratJalanResponse)
async def update_surat_jalan(
    fkp_id: uuid.UUID,
    sj_id: uuid.UUID,
    data: SuratJalanUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await warehouse_service.update_surat_jalan(fkp_id, sj_id, data, user, kode_role, db)


@router.post("/{fkp_id}/warehouse/surat-jalan/{sj_id}/issue", response_model=SuratJalanResponse)
async def issue_surat_jalan(
    fkp_id: uuid.UUID,
    sj_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await warehouse_service.issue_surat_jalan(fkp_id, sj_id, user, kode_role, db)


@router.post("/{fkp_id}/warehouse/surat-jalan/{sj_id}/ship", response_model=SuratJalanResponse)
async def ship_surat_jalan(
    fkp_id: uuid.UUID,
    sj_id: uuid.UUID,
    data: SuratJalanShipRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await warehouse_service.ship_surat_jalan(fkp_id, sj_id, data, user, kode_role, db)


@router.post("/{fkp_id}/warehouse/surat-jalan/{sj_id}/confirm-delivery", response_model=SuratJalanResponse)
async def confirm_delivery(
    fkp_id: uuid.UUID,
    sj_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await warehouse_service.confirm_delivery_sj(fkp_id, sj_id, user, kode_role, db)


@router.get("/{fkp_id}/warehouse/surat-jalan/{sj_id}/pdf")
async def download_surat_jalan_pdf(
    fkp_id: uuid.UUID,
    sj_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    """
    [Konsisten dengan fix keamanan #1 — sesi audit sebelumnya] Download PDF
    HANYA lewat endpoint terautentikasi ini, bukan static file publik.
    Scope check lewat get_surat_jalan_detail() (reuse get_fkp_detail()).
    """
    sj = await warehouse_service.get_surat_jalan_detail(fkp_id, sj_id, user, kode_role, db)
    if not sj.url_pdf:
        raise HTTPException(status_code=404, detail="PDF belum diterbitkan — surat jalan masih berstatus draft.")

    prefix = "/uploads/"
    relative_path = sj.url_pdf[len(prefix):] if sj.url_pdf.startswith(prefix) else sj.url_pdf
    file_path = os.path.join(settings.UPLOAD_DIR, relative_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File PDF tidak ditemukan di server.")

    return FileResponse(file_path, filename=f"SJ_{sj.nomor_surat_jalan}.pdf", media_type="application/pdf")
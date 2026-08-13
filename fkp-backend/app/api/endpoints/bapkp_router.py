"""
app/api/endpoints/bapkp_router.py

Endpoint REST untuk BAPKP (Berita Acara Pemeriksaan Keluhan Pelanggan).

Mengikuti pola yang SUDAH DIPAKAI di project ini untuk sub-modul FKP
(lihat app/api/endpoints/sample_router.py & warehouse_router.py): router
TANPA prefix di dalam file, prefix "/api/fkp" ditambahkan saat
di-mount di app/main.py. Endpoint fkp.py yang sudah ada JANGAN diubah --
ini file terpisah, sama seperti sample_router.py/warehouse_router.py
tidak menyatu ke fkp.py.

Path pakai segmen "/bapkp" (BUKAN "/berita-acara") supaya tidak bentrok
dengan route "Berita Acara Pemusnahan" yang sudah ada di fkp.py:
    GET  /api/fkp/{fkp_id}/berita-acara         (metadata BA Pemusnahan)
    GET  /api/fkp/{fkp_id}/berita-acara/pdf     (download BA Pemusnahan)
    POST /api/fkp/berita-acara/manual           (generate manual)

Route baru di file ini:
    GET   /api/fkp/{fkp_id}/bapkp/draft
    POST  /api/fkp/{fkp_id}/bapkp
    GET   /api/fkp/{fkp_id}/bapkp
    PATCH /api/fkp/{fkp_id}/bapkp
    GET   /api/fkp/{fkp_id}/bapkp/pdf

Registrasi di main.py (tambahkan baris ini, lihat INTEGRASI_BAPKP.md):
    from app.api.endpoints import bapkp_router
    app.include_router(bapkp_router.router, prefix="/api/fkp", tags=["BAPKP"])
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

# Dependency yang SUDAH ADA di project (sama seperti dipakai fkp.py) --
# BUKAN app.api.deps (modul itu tidak ada di project ini).
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_kode_role
from app.core.config import settings
from app.models.user import User

from app.schemas.bapkp import (
    BapkpCreate,
    BapkpDraftResponse,
    BapkpItemDetail,
    BapkpResponse,
    BapkpUpdate,
)
from app.services import bapkp_service
from app.services.bapkp_pdf_service import generate_bapkp_pdf
from app.services.permission_service import require_permission

router = APIRouter()


def _context_to_response(context: dict) -> BapkpResponse:
    """Map dict hasil build_bapkp_context() -> BapkpResponse."""
    ba = context["ba"]
    outlet = context.get("outlet") or {}
    return BapkpResponse(
        id=ba["id"],
        fkp_id=context["fkp"]["id"],
        nomor_fkp=context["fkp"]["nomor_fkp"],
        nomor_ba=ba["nomor_ba"],
        hari_pemeriksaan=ba["hari_pemeriksaan"],
        tanggal_pemeriksaan=ba["tanggal_pemeriksaan"],
        tanggal_diterima_qc=ba["tanggal_diterima_qc"],
        tenggat_terpenuhi=ba["tenggat_terpenuhi"],
        catatan_pemeriksaan=ba["catatan_pemeriksaan"],
        outlet_nama=outlet.get("nama_toko"),
        distributor_nama=outlet.get("distributor_name"),
        items=[
            BapkpItemDetail(
                fkp_item_id=item["id"],
                nama_produk=item["nama_produk"],
                jenis_kemasan=item["jenis_kemasan"],
                batch_number=item["batch_number"],
                qty=item["qty"],
                deskripsi_keluhan=item["deskripsi_keluhan"],
                ada_sample_keluhan=item["ada_sample_keluhan"],
                kondisi_sample=item["kondisi_sample"],
                tanggal_kadaluarsa=item["tanggal_kadaluarsa"],
                umur_produk=item["umur_produk"],
                tanggal_dikirim=item["tanggal_dikirim"],
                lama_di_gudang_spp=item["lama_di_gudang_spp"],
            )
            for item in context["items"]
        ],
        dibuat_oleh=ba["dibuat_oleh"],
        created_at=ba["created_at"],
        updated_at=ba["updated_at"],
    )


@router.get("/{fkp_id}/bapkp/draft", response_model=BapkpDraftResponse)
async def get_bapkp_draft(
    fkp_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    """Auto-fill: dipanggil SEBELUM user mengisi form BAPKP."""
    return await bapkp_service.get_bapkp_draft(fkp_id, user, kode_role, db)


@router.post("/{fkp_id}/bapkp", response_model=BapkpResponse, status_code=201)
async def create_bapkp(
    fkp_id: UUID,
    data: BapkpCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    await bapkp_service.create_bapkp(fkp_id, data, user, kode_role, db)
    context = await bapkp_service.get_bapkp_detail(fkp_id, user, kode_role, db)
    return _context_to_response(context)


@router.patch("/{fkp_id}/bapkp", response_model=BapkpResponse)
async def update_bapkp(
    fkp_id: UUID,
    data: BapkpUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    await bapkp_service.update_bapkp(fkp_id, data, user, kode_role, db)
    context = await bapkp_service.get_bapkp_detail(fkp_id, user, kode_role, db)
    return _context_to_response(context)


@router.get("/{fkp_id}/bapkp", response_model=BapkpResponse)
async def get_bapkp_detail(
    fkp_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    context = await bapkp_service.get_bapkp_detail(fkp_id, user, kode_role, db)
    return _context_to_response(context)


@router.get("/{fkp_id}/bapkp/pdf")
async def download_bapkp_pdf(
    fkp_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    # generate_bapkp_pdf() sendiri tidak cek permission/scope -- cek
    # eksplisit di sini dulu, sama pola dgn download_fkp_pdf() di fkp.py.
    await require_permission(kode_role, "fkp.bapkp.view", db)
    bapkp_service._assert_role_boleh_akses_bapkp(kode_role)

    pdf_bytes, nomor_ba = await generate_bapkp_pdf(
        fkp_id, db, generated_by=user.id, upload_dir=settings.UPLOAD_DIR
    )
    filename = f"BAPKP-{nomor_ba.replace('/', '-')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
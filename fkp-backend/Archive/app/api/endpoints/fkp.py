"""
FKP Router — endpoint lengkap untuk semua operasi FKP.

Termasuk:
  - CRUD FKP master dan item
  - Transisi status (submit, review, approve, reject, close)
  - Upload attachment
  - Generate PDF (FKP dan Berita Acara Pemusnahan)

── PERUBAHAN (migrasi RBAC dinamis) ───────────────────────────────────────
4 fungsi service berikut sekarang menerima parameter `kode_role` tambahan
(sebelumnya gap keamanan — tidak ada cek role sama sekali):
  - add_fkp_item
  - update_fkp_item
  - delete_fkp_item
  - input_surat_jalan
kode_role sudah tersedia di tiap endpoint lewat Depends(get_kode_role),
jadi cukup diteruskan ke pemanggilan fungsi.

── PERBAIKAN LANJUTAN (audit keamanan) ────────────────────────────────────
  - download_fkp_pdf() & preview_fkp_html(): sebelumnya tidak ada validasi
    kode_role/scope sama sekali, sehingga FKP milik pihak lain bisa diunduh
    siapa saja yang login. Sekarang divalidasi lewat
    validate_fkp_formulir_access(), sama seperti /formulir-pdf. Endpoint
    preview juga dimatikan total di luar mode settings.DEBUG.
  - upload_bukti(): BUG KRITIS — kode_role tidak pernah terkirim ke
    upload_attachment() karena argumen positional bergeser satu slot
    (fkp_item_id tertukar masuk ke slot kode_role, dst). Semua upload
    attachment oleh role non-superadmin akan ditolak 403. Sekarang dipanggil
    dengan keyword arguments eksplisit.

── PERBAIKAN RBAC DINAMIS (Kategori B audit RBAC) ─────────────────────────
4 fungsi Berita Acara (download_berita_acara_pdf,
download_berita_acara_pdf_with_override, generate_berita_acara_metadata,
generate_berita_acara_manual) sebelumnya mengecek tuple konstanta
_BA_ROLES/_BA_MANUAL_ROLES manual di badan fungsi — tidak ada dependency
require_roles() sama sekali sehingga tidak pernah terhubung ke dashboard
RBAC, walau modul fkp lain sudah bermigrasi. Sekarang via
require_permission() yang DB-driven (fkp.berita_acara.read /
fkp.berita_acara.manual), superadmin tetap bypass total via is_superadmin.
_BA_ROLES dan _BA_MANUAL_ROLES dihapus karena tidak lagi dipakai.
"""
import os
import uuid
from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, Depends, Response, UploadFile, File, Query, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_kode_role
from app.core.config import settings
from app.models.user import User
from app.models.fkp import TipeDokumen, FkpStatus, FkpAttachment
import traceback

from app.schemas.fkp import (
    FkpCreate, FkpUpdate, FkpDetailResponse, FkpListResponse,
    FkpItemCreate, FkpItemUpdate, FkpItemResponse,
    ApsmReviewRequest, AdminHoReviewRequest,
    RsmApproveRequest, DirekturApproveRequest,
    InvestigasiQcRequest, RejectRequest, RevisionRequest,
    UpdatePengirimanRequest, ResolusiCreate,
    SuratJalanRequest, AttachmentResponse,
    FkpDocumentCreate, FkpDocumentResponse,
)
from app.schemas.berita_acara import (
    BeritaAcaraFromFkpRequest,
    BeritaAcaraManualRequest,
    BeritaAcaraGenerateResponse,
)
from app.schemas.finance import InvoiceCreateRequest, InvoiceResponse

from app.services import fkp_service, upload_service
from app.services.permission_service import require_permission
from app.services.fkp_service import (
    create_fkp, update_fkp, list_fkp, get_fkp_detail,
    submit_fkp, apsm_review, admin_ho_review,
    rsm_approve_investigasi, qc_investigasi,
    admin_ho_request_resolusi_approval, rsm_approve_resolusi,
    direktur_approve, update_pengiriman, request_revision,
    reject_fkp, input_surat_jalan, close_fkp,
    add_fkp_item, update_fkp_item, delete_fkp_item,
    buat_dokumen, hapus_dokumen, 
    list_fkp_penerbitan as _list, validate_fkp_formulir_access
)
from app.services.fkp_pdf_service import generate_fkp_pdf
from app.services.berita_acara_pdf_service import (
    generate_berita_acara_pdf,
    generate_berita_acara_pdf_manual,
)

router = APIRouter()

# ─── Role constants ───────────────────────────────────────────────────────────
# _BA_ROLES dan _BA_MANUAL_ROLES DIHAPUS (Kategori B audit RBAC) — diganti
# require_permission(kode_role, "fkp.berita_acara.read"/".manual", db) di
# masing-masing fungsi. Mapping role identik dengan tuple lama, dikelola
# lewat seeds/seed_permissions.py + dashboard RBAC.

# Status yang diizinkan untuk download (bukan draft, bukan need_revision)
_FORMULIR_DOWNLOADABLE_STATUS = {
    FkpStatus.SUBMITTED,
    FkpStatus.APSM_REVIEWED,
    FkpStatus.RSM_APPROVAL_INVESTIGASI,
    FkpStatus.IN_INVESTIGATION,
    FkpStatus.INVESTIGATED,
    FkpStatus.RSM_APPROVAL_RESOLUSI,
    FkpStatus.DIREKTUR_APPROVAL,
    FkpStatus.ACCEPTED,
    FkpStatus.IN_PROCESS,
    FkpStatus.CLOSED,
    FkpStatus.REJECTED,
}

@router.get(
    "/penerbitan",
    response_model=List[FkpListResponse],
    summary="List FKP untuk halaman penerbitan — filtered by role",
)
async def list_fkp_penerbitan(
    status:     Optional[str]  = Query(None),
    tanggal_dari: Optional[str] = Query(None, description="Format YYYY-MM-DD"),
    tanggal_sampai: Optional[str] = Query(None, description="Format YYYY-MM-DD"),
    db:         AsyncSession   = Depends(get_db),
    user:       User           = Depends(get_current_user),
    kode_role:  str            = Depends(get_kode_role),
):
    """
    List FKP untuk penerbitan dokumen formulir.
    - Hanya menampilkan FKP yang sudah melewati draft/need_revision
    - Otomatis difilter berdasarkan scope role
    """
    return await _list(db, user, kode_role, status, tanggal_dari, tanggal_sampai)


@router.get(
    "/{fkp_id}/formulir-pdf",
    summary="Download PDF Formulir FKP — dengan validasi akses per role",
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {}}, "description": "File PDF Formulir FKP"},
        403: {"description": "Tidak punya akses ke FKP ini"},
        404: {"description": "FKP tidak ditemukan"},
        422: {"description": "FKP belum bisa didownload (masih draft/need_revision)"},
    },
)
async def download_formulir_fkp_pdf(
    fkp_id:    uuid.UUID,
    db:        AsyncSession = Depends(get_db),
    user:      User         = Depends(get_current_user),
    kode_role: str          = Depends(get_kode_role),
):
    """
    Download Formulir FKP sebagai PDF.

    Akses per role:
    - outlet       → hanya FKP outlet sendiri
    - distributor  → FKP milik distributor sendiri
    - sc_spv       → FKP distributor yang ditangani
    - apsm         → FKP area APSM
    - admin_ho / qc / rsm / direktur / superadmin / finance → semua FKP
    """

    try:
        await validate_fkp_formulir_access(fkp_id, user, kode_role, db)
    except HTTPException:
        raise

    try:
        pdf_bytes, nomor_fkp = await generate_fkp_pdf(
            fkp_id=fkp_id,
            db=db,
            upload_dir=settings.UPLOAD_DIR,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
            traceback.print_exc()  # ← tambah ini, lihat terminal FastAPI
            raise HTTPException(status_code=500, detail=f"Gagal generate PDF: {e}")

    safe_nomor = nomor_fkp.replace("/", "-")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="Formulir-FKP-{safe_nomor}.pdf"',
            "Content-Length":      str(len(pdf_bytes)),
        },
    )

# ─── Meta ─────────────────────────────────────────────────────────────────────

@router.get("/meta/tipe-dokumen")
async def list_tipe_dokumen():
    """
    Listing semua tipe dokumen yang valid beserta label dan kelompoknya.
    Digunakan FE untuk dropdown pilihan tipe_dokumen saat upload.
    """
    return {
        "tipe_dokumen": [
            {"value": TipeDokumen.FOTO_KELUHAN,             "label": "Foto Keluhan Produk",        "kelompok": "keluhan"},
            {"value": TipeDokumen.FOTO_SAMPLE,              "label": "Foto Sample",                "kelompok": "keluhan"},
            {"value": TipeDokumen.FOTO_EXPIRED,             "label": "Foto Kadaluarsa (Expired)",  "kelompok": "keluhan"},
            {"value": TipeDokumen.FOTO_KODE_PRODUKSI,       "label": "Foto Kode Produksi",         "kelompok": "keluhan"}, 
            {"value": TipeDokumen.FOTO_INVESTIGASI,         "label": "Foto Hasil Investigasi",     "kelompok": "investigasi"},
            {"value": TipeDokumen.SURAT_JALAN,              "label": "Surat Jalan",                "kelompok": "resolusi"},
            {"value": TipeDokumen.FOTO_SERAH_TERIMA,        "label": "Foto Serah Terima Barang",   "kelompok": "resolusi"},
            {"value": TipeDokumen.BERITA_ACARA_PENUKARAN,   "label": "Berita Acara Penukaran",     "kelompok": "resolusi"},
            {"value": TipeDokumen.INVOICE_TERPOTONG,        "label": "Invoice Terpotong",          "kelompok": "resolusi"},
            {"value": TipeDokumen.BUKTI_TRANSFER,           "label": "Bukti Transfer Cashback",    "kelompok": "resolusi"},
            {"value": TipeDokumen.NOTA_RETUR,               "label": "Nota Retur",                 "kelompok": "resolusi"},
            {"value": TipeDokumen.FOTO_PEMUSNAHAN,          "label": "Foto Pemusnahan",            "kelompok": "resolusi"},
            {"value": TipeDokumen.BERITA_ACARA_PEMUSNAHAN,  "label": "Berita Acara Pemusnahan",    "kelompok": "resolusi"},
            {"value": TipeDokumen.BERITA_ACARA_PEMUSNAHAN_TUKAR_BARANG,
                                                             "label": "Berita Acara Pemusnahan & Tukar Barang", "kelompok": "resolusi"},
            {"value": TipeDokumen.TANDA_TERIMA_SAMPLE,      "label": "Tanda Terima Sample",        "kelompok": "sample"},
            {"value": TipeDokumen.FOTO_KONDISI_MASUK,       "label": "Foto Kondisi Sample Masuk",  "kelompok": "sample"},
            {"value": TipeDokumen.HASIL_PEMERIKSAAN_QC,     "label": "Hasil Pemeriksaan QC",       "kelompok": "sample"},
            {"value": TipeDokumen.BA_PEMERIKSAAN,           "label": "Berita Acara Pemeriksaan",   "kelompok": "dokumen"},
            {"value": TipeDokumen.SURAT_PERNYATAAN,         "label": "Surat Pernyataan",           "kelompok": "dokumen"},
            {"value": TipeDokumen.DOKUMEN_LAINNYA,          "label": "Dokumen Lainnya",            "kelompok": "dokumen"},
        ]
    }


# ─── FKP MASTER ───────────────────────────────────────────────────────────────

@router.get("", response_model=List[FkpListResponse])
async def get_list_fkp(
    status:    Optional[str] = Query(None, description="Filter berdasarkan status FKP"),
    prioritas: Optional[str] = Query(None, description="Filter berdasarkan prioritas"),
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """
    Ambil daftar FKP. Otomatis difilter berdasarkan role:
    - outlet/distributor/sc_spv/apsm → hanya FKP area mereka
    - rsm/admin_ho/qc/direktur/superadmin → semua FKP
    """
    return await list_fkp(db, user, kode_role, status, prioritas)


@router.post("", response_model=FkpDetailResponse, status_code=201)
async def buat_fkp(
    data:      FkpCreate,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """Buat FKP baru dengan multi-item sekaligus. Minimal 1 item produk wajib disertakan."""
    return await create_fkp(data, user, kode_role, db)


@router.get("/{fkp_id}", response_model=FkpDetailResponse)
async def detail_fkp(
    fkp_id:    uuid.UUID,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """Ambil detail lengkap FKP termasuk semua items, status logs, dan resolusi."""
    return await get_fkp_detail(fkp_id, db, user, kode_role)


@router.patch("/{fkp_id}", response_model=FkpDetailResponse)
async def edit_fkp(
    fkp_id:    uuid.UUID,
    data:      FkpUpdate,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """Update header FKP (prioritas, catatan, outlet). Hanya saat status draft/need_revision."""
    return await update_fkp(fkp_id, data, user, kode_role, db)


# ─── PDF FKP ──────────────────────────────────────────────────────────────────

@router.get(
    "/{fkp_id}/pdf",
    summary="Download PDF Formulir Keluhan Pelanggan",
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {}}, "description": "File PDF FKP"},
        404: {"description": "FKP tidak ditemukan"},
        500: {"description": "Gagal generate PDF"},
    },
)
async def download_fkp_pdf(
    fkp_id:       uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    kode_role:    str  = Depends(get_kode_role),
):
    """
    Download FKP sebagai PDF siap cetak.

    PERBAIKAN KEAMANAN: sebelumnya endpoint ini hanya butuh login (tidak ada
    validasi kode_role/scope sama sekali), sehingga user dari outlet/distributor
    mana pun bisa mendownload PDF FKP milik pihak lain selama tahu UUID-nya.
    Sekarang divalidasi sama seperti /formulir-pdf.
    """
    await validate_fkp_formulir_access(fkp_id, current_user, kode_role, db)

    try:
        pdf_bytes, nomor_fkp = await generate_fkp_pdf(
            fkp_id=fkp_id,
            db=db,
            upload_dir=settings.UPLOAD_DIR,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal generate PDF: {e}")

    safe_nomor = nomor_fkp.replace("/", "-")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="FKP-{safe_nomor}.pdf"',
            "Content-Length":      str(len(pdf_bytes)),
        },
    )


@router.get(
    "/{fkp_id}/pdf/preview",
    summary="Preview HTML FKP di browser (dev only)",
    response_class=Response,
    include_in_schema=False,
)
async def preview_fkp_html(
    fkp_id:       uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    kode_role:    str  = Depends(get_kode_role),
):
    """
    Preview HTML template FKP di browser — berguna untuk QA tampilan.

    PERBAIKAN dari versi lama:
    Versi lama memanggil build_fkp_context dengan signature yang salah
    (fkp_data=dict, outlet_data=dict, dst). Versi ini menggunakan ORM objects
    langsung sesuai signature aktual fungsi tersebut.

    PERBAIKAN KEAMANAN: endpoint ini sebelumnya tidak punya validasi
    kode_role/scope sama sekali (hanya butuh login), dan tetap bisa diakses
    langsung walau disembunyikan dari Swagger (include_in_schema=False hanya
    menyembunyikan dari dokumentasi, bukan menutup endpoint). Sekarang:
    1) endpoint dimatikan total di luar mode DEBUG,
    2) tetap divalidasi scope-nya seperti /formulir-pdf saat DEBUG aktif.
    """
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not Found")

    await validate_fkp_formulir_access(fkp_id, current_user, kode_role, db)

    from sqlmodel import select as sql_select
    from sqlalchemy.orm import selectinload

    from app.models.distributor import Distributor
    from app.models.fkp import FkpAttachment, FkpComplaint, FkpItem
    from app.models.outlet import Outlet
    from app.services.fkp_pdf_service import build_fkp_context, render_fkp_html
    from app.services.pdf_utils import get_user_nama

    r = await db.execute(sql_select(FkpComplaint).where(FkpComplaint.id == fkp_id))
    fkp = r.scalar_one_or_none()
    if not fkp:
        raise HTTPException(status_code=404, detail="FKP tidak ditemukan")

    outlet = None
    if fkp.outlet_id:
        ro = await db.execute(sql_select(Outlet).where(Outlet.id == fkp.outlet_id))
        outlet = ro.scalar_one_or_none()

    distributor = None
    if fkp.distributor_id:
        rd = await db.execute(
            sql_select(Distributor).where(Distributor.id == fkp.distributor_id)
        )
        distributor = rd.scalar_one_or_none()

    # selectinload wajib ada agar item.product tidak lazy-load
    ri = await db.execute(
        sql_select(FkpItem)
        .where(FkpItem.fkp_id == fkp_id)
        .options(selectinload(FkpItem.product))
        .order_by(FkpItem.created_at)
    )
    items = ri.scalars().all()

    ra = await db.execute(
        sql_select(FkpAttachment).where(FkpAttachment.fkp_id == fkp_id)
    )
    attachments = ra.scalars().all()

    submitted_by_name = await get_user_nama(db, fkp.submitted_by)
    apsm_name         = await get_user_nama(db, fkp.handled_by)
    marketing_name    = await get_user_nama(db, fkp.approved_by_marketing)
    direktur_name     = await get_user_nama(db, fkp.approved_by_direktur)

    context = build_fkp_context(
        fkp               = fkp,
        outlet            = outlet,
        distributor       = distributor,
        items             = list(items),
        attachments       = list(attachments),
        submitted_by_name = submitted_by_name,
        apsm_name         = apsm_name,
        marketing_name    = marketing_name,
        direktur_name     = direktur_name,
        upload_dir        = settings.UPLOAD_DIR,
    )
    html = render_fkp_html(context)
    return Response(content=html, media_type="text/html")


# ─── PDF BERITA ACARA ─────────────────────────────────────────────────────────

@router.get(
    "/{fkp_id}/berita-acara/pdf",
    summary="Download Berita Acara Pemusnahan dari FKP",
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {}}, "description": "File PDF Berita Acara"},
        400: {"description": "FKP belum memiliki resolusi pemusnahan"},
        403: {"description": "Role tidak diizinkan"},
        404: {"description": "FKP tidak ditemukan"},
        500: {"description": "Gagal generate PDF"},
    },
)
async def download_berita_acara_pdf(
    fkp_id:    uuid.UUID,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """
    Generate dan download Berita Acara Pemusnahan dari FKP.

    Syarat:
    - FKP harus sudah memiliki resolusi dengan metode_penanganan_fisik = 'dimusnahkan'
    (tidak lagi tergantung tipe_resolusi)
    """
    # PERBAIKAN RBAC (Kategori B): sebelumnya cek tuple hardcode _BA_ROLES
    # di badan fungsi, tidak terhubung ke dashboard RBAC. Sekarang via
    # require_permission() — DB-driven, superadmin bypass via is_superadmin.
    await require_permission(kode_role, "fkp.berita_acara.read", db)

    try:
        pdf_bytes, nomor_dokumen, _ = await generate_berita_acara_pdf(
            fkp_id=fkp_id,
            db=db,
            current_user=user,
            override=None,
            upload_dir=settings.UPLOAD_DIR,
        )
    except ValueError as e:
        detail = str(e)
        code   = 404 if "tidak ditemukan" in detail.lower() else 400
        raise HTTPException(status_code=code, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal generate PDF: {e}")

    safe_nomor = nomor_dokumen.replace("/", "-")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="BA-{safe_nomor}.pdf"',
            "Content-Length":      str(len(pdf_bytes)),
        },
    )


@router.post(
    "/{fkp_id}/berita-acara/pdf",
    summary="Download Berita Acara dengan override field",
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {}}, "description": "File PDF Berita Acara"},
        400: {"description": "Validasi gagal"},
        403: {"description": "Role tidak diizinkan"},
        404: {"description": "FKP tidak ditemukan"},
        500: {"description": "Gagal generate PDF"},
    },
)
async def download_berita_acara_pdf_with_override(
    fkp_id:    uuid.UUID,
    payload:   BeritaAcaraFromFkpRequest = BeritaAcaraFromFkpRequest(),
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """
    Sama seperti GET, tapi menerima body untuk override field tertentu:
    metode pemusnahan, nama-nama TTD, catatan tambahan.

    Berguna bila data DB belum lengkap atau perlu koreksi sebelum cetak.
    Role yang diizinkan: lihat permission fkp.berita_acara.read di dashboard RBAC.
    """
    # PERBAIKAN RBAC (Kategori B): lihat penjelasan di download_berita_acara_pdf.
    await require_permission(kode_role, "fkp.berita_acara.read", db)

    try:
        pdf_bytes, nomor_dokumen, _ = await generate_berita_acara_pdf(
            fkp_id=fkp_id,
            db=db,
            current_user=user,
            override=payload,
            upload_dir=settings.UPLOAD_DIR,
        )
    except ValueError as e:
        detail = str(e)
        code   = 404 if "tidak ditemukan" in detail.lower() else 400
        raise HTTPException(status_code=code, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal generate PDF: {e}")

    safe_nomor = nomor_dokumen.replace("/", "-")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="BA-{safe_nomor}.pdf"',
            "Content-Length":      str(len(pdf_bytes)),
        },
    )


@router.post(
    "/{fkp_id}/berita-acara",
    response_model=BeritaAcaraGenerateResponse,
    summary="Generate Berita Acara — return metadata + URL download",
    responses={
        200: {"description": "Metadata dokumen BA yang berhasil digenerate"},
        400: {"description": "Validasi gagal"},
        403: {"description": "Role tidak diizinkan"},
        404: {"description": "FKP tidak ditemukan"},
    },
)
async def generate_berita_acara_metadata(
    fkp_id:    uuid.UUID,
    payload:   BeritaAcaraFromFkpRequest = BeritaAcaraFromFkpRequest(),
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """
    Generate BA dan simpan ke DB. Return JSON metadata termasuk doc_id dan
    url_download — cocok untuk FE yang perlu menampilkan daftar dokumen FKP
    setelah generate tanpa langsung download file.

    Role yang diizinkan: lihat permission fkp.berita_acara.read di dashboard RBAC.
    """
    # PERBAIKAN RBAC (Kategori B): lihat penjelasan di download_berita_acara_pdf.
    await require_permission(kode_role, "fkp.berita_acara.read", db)

    try:
        _, nomor_dokumen, doc_id = await generate_berita_acara_pdf(
            fkp_id=fkp_id,
            db=db,
            current_user=user,
            override=payload,
            upload_dir=settings.UPLOAD_DIR,
        )
    except ValueError as e:
        detail = str(e)
        code   = 404 if "tidak ditemukan" in detail.lower() else 400
        raise HTTPException(status_code=code, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal generate PDF: {e}")

    return BeritaAcaraGenerateResponse(
        message       = "Berita Acara berhasil digenerate.",
        nomor_dokumen = nomor_dokumen,
        fkp_id        = fkp_id,
        doc_id        = doc_id,
        url_download  = f"/api/fkp/{fkp_id}/berita-acara/pdf",
    )


@router.post(
    "/berita-acara/manual",
    response_model=BeritaAcaraGenerateResponse,
    summary="Generate Berita Acara manual (tanpa FKP wajib)",
    responses={
        200: {"description": "Metadata BA manual"},
        403: {"description": "Role tidak diizinkan"},
        404: {"description": "fkp_id diisi tapi FKP tidak ditemukan"},
        500: {"description": "Gagal generate PDF"},
    },
)
async def generate_berita_acara_manual(
    payload:   BeritaAcaraManualRequest,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """
    Generate Berita Acara dari input manual tanpa melalui alur FKP normal.

    - Jika `fkp_id` di body diisi → PDF disimpan ke FkpDocument FKP tersebut,
      dan url_download mengarah ke endpoint download FKP terkait.
    - Jika `fkp_id` kosong → PDF hanya bisa diunduh via url_download yang
      menggunakan endpoint stream terpisah (belum diimplementasi, extend sesuai kebutuhan).

    Role yang diizinkan: lihat permission fkp.berita_acara.manual di dashboard RBAC.
    """
    # PERBAIKAN RBAC (Kategori B): sebelumnya cek tuple hardcode
    # _BA_MANUAL_ROLES. Sekarang via require_permission(), DB-driven.
    await require_permission(kode_role, "fkp.berita_acara.manual", db)

    try:
        pdf_bytes, nomor_dokumen, doc_id = await generate_berita_acara_pdf_manual(
            request=payload,
            db=db,
            current_user=user,
            upload_dir=settings.UPLOAD_DIR,
        )
    except ValueError as e:
        detail = str(e)
        code   = 404 if "tidak ditemukan" in detail.lower() else 400
        raise HTTPException(status_code=code, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal generate PDF: {e}")

    url_download = (
        f"/api/fkp/{payload.fkp_id}/berita-acara/pdf"
        if payload.fkp_id
        else None  # tanpa fkp_id, tidak ada endpoint permanen untuk download
    )

    return BeritaAcaraGenerateResponse(
        message       = "Berita Acara manual berhasil digenerate.",
        nomor_dokumen = nomor_dokumen,
        fkp_id        = payload.fkp_id,
        doc_id        = doc_id,
        url_download  = url_download,
    )


# ─── FKP ITEMS ────────────────────────────────────────────────────────────────

@router.post("/{fkp_id}/items", response_model=FkpItemResponse, status_code=201)
async def tambah_item(
    fkp_id:    uuid.UUID,
    data:      FkpItemCreate,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """Tambah item produk baru ke FKP. Hanya bisa saat status draft atau need_revision."""
    # PERBAIKAN RBAC: kode_role sekarang diteruskan — sebelumnya gap keamanan
    # (add_fkp_item tidak menerima/mengecek role sama sekali).
    return await add_fkp_item(fkp_id, data.model_dump(exclude_none=True), user, kode_role, db)


@router.patch("/{fkp_id}/items/{item_id}", response_model=FkpItemResponse)
async def edit_item(
    fkp_id:    uuid.UUID,
    item_id:   uuid.UUID,
    data:      FkpItemUpdate,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """Edit item produk. Hanya bisa saat status draft atau need_revision."""
    # PERBAIKAN RBAC: kode_role sekarang diteruskan.
    return await update_fkp_item(fkp_id, item_id, data, user, kode_role, db)


@router.delete("/{fkp_id}/items/{item_id}")
async def hapus_item(
    fkp_id:    uuid.UUID,
    item_id:   uuid.UUID,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """Hapus item dari FKP. Minimal 1 item harus tetap ada."""
    # PERBAIKAN RBAC: kode_role sekarang diteruskan.
    return await delete_fkp_item(fkp_id, item_id, user, kode_role, db)


# ─── TRANSISI STATUS ──────────────────────────────────────────────────────────

@router.post("/{fkp_id}/submit", response_model=FkpDetailResponse)
async def submit(
    fkp_id:    uuid.UUID,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """Submit FKP dari status draft/need_revision ke submitted."""
    return await submit_fkp(fkp_id, user, kode_role, db)


@router.post("/{fkp_id}/apsm-review", response_model=FkpDetailResponse)
async def review_apsm(
    fkp_id:    uuid.UUID,
    data:      ApsmReviewRequest,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """APSM submit review + rekomendasi per item. Status: submitted → apsm_reviewed."""
    return await apsm_review(fkp_id, data, user, kode_role, db)


@router.post("/{fkp_id}/admin-ho-review", response_model=FkpDetailResponse)
async def review_admin_ho(
    fkp_id:    uuid.UUID,
    data:      AdminHoReviewRequest,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """Admin HO review + rekomendasi, teruskan ke RSM. Status: apsm_reviewed → rsm_approval_investigasi."""
    return await admin_ho_review(fkp_id, data, user, kode_role, db)


@router.post("/{fkp_id}/rsm-approve-investigasi", response_model=FkpDetailResponse)
async def rsm_approve_inv(
    fkp_id:    uuid.UUID,
    data:      RsmApproveRequest,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """RSM approve/tolak investigasi. Approve → in_investigation. Tolak → rejected."""
    return await rsm_approve_investigasi(fkp_id, data, user, kode_role, db)


@router.post("/{fkp_id}/qc-investigasi", response_model=FkpDetailResponse)
async def investigasi_qc(
    fkp_id:    uuid.UUID,
    data:      InvestigasiQcRequest,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """QC mengisi hasil investigasi per item. Status: in_investigation → investigated."""
    return await qc_investigasi(fkp_id, data, user, kode_role, db)


@router.post("/{fkp_id}/request-resolusi-approval", response_model=FkpDetailResponse)
async def request_resolusi_approval(
    fkp_id:    uuid.UUID,
    catatan:   Optional[str] = None,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """Admin HO minta persetujuan resolusi ke RSM. Status: investigated → rsm_approval_resolusi."""
    return await admin_ho_request_resolusi_approval(fkp_id, catatan, user, kode_role, db)


@router.post("/{fkp_id}/rsm-approve-resolusi", response_model=FkpDetailResponse)
async def rsm_approve_res(
    fkp_id:    uuid.UUID,
    data:      RsmApproveRequest,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """RSM approve/tolak resolusi. Approve → direktur_approval. Tolak → rejected."""
    return await rsm_approve_resolusi(fkp_id, data, user, kode_role, db)


@router.post("/{fkp_id}/direktur-approve", response_model=FkpDetailResponse)
async def approve_direktur(
    fkp_id:    uuid.UUID,
    data:      DirekturApproveRequest,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """Direktur approve/tolak FKP. Approve → accepted. Tolak → rejected."""
    return await direktur_approve(fkp_id, data, user, kode_role, db)


@router.post("/{fkp_id}/update-pengiriman", response_model=FkpDetailResponse)
async def proses_pengiriman(
    fkp_id:    uuid.UUID,
    data:      UpdatePengirimanRequest,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """
    DEPRECATED — gunakan POST /resolusi saat status 'accepted'.
    Endpoint ini masih aktif untuk backward compatibility.
    """
    return await update_pengiriman(fkp_id, data, user, kode_role, db)


@router.post("/{fkp_id}/close", response_model=FkpDetailResponse)
async def tutup_fkp(
    fkp_id:    uuid.UUID,
    catatan:   Optional[str] = None,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """Tutup FKP setelah resolusi selesai. Status: in_process → closed."""
    return await close_fkp(fkp_id, catatan, user, kode_role, db)


@router.post("/{fkp_id}/request-revision", response_model=FkpDetailResponse)
async def minta_revisi(
    fkp_id:    uuid.UUID,
    data:      RevisionRequest,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """Minta revisi. Status mundur otomatis sesuai role dan status saat ini."""
    return await request_revision(fkp_id, data, user, kode_role, db)


@router.post("/{fkp_id}/reject", response_model=FkpDetailResponse)
async def tolak_fkp(
    fkp_id:    uuid.UUID,
    data:      RejectRequest,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """Tolak FKP. Status → rejected. Alasan penolakan wajib diisi."""
    return await reject_fkp(fkp_id, data, user, kode_role, db)


# ─── RESOLUSI ─────────────────────────────────────────────────────────────────

@router.post("/{fkp_id}/resolusi", response_model=FkpDetailResponse, status_code=201)
async def buat_resolusi(
    fkp_id:    uuid.UUID,
    data:      ResolusiCreate,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """
    Admin HO buat/update resolusi. Satu endpoint, dua fase:

    - Status 'investigated'       → isi tipe + metode fisik (wajib)
    - Status 'rsm_approval_resolusi' → edit tipe/metode jika RSM minta revisi
    - Status 'accepted'           → isi detail eksekusi (nomor DO / rekening / dll)

    [DIUBAH — Modul Sample Shipment] Endpoint ini TIDAK LAGI otomatis
    memindahkan status ke in_process. Setelah field eksekusi Fase 2 terisi,
    gunakan salah satu endpoint pemicu berikut sesuai tipe_resolusi:
      - tukar_barang        → POST /{fkp_id}/warehouse/surat-jalan
      - potong_tagihan      → POST /{fkp_id}/finance/invoice
      - lainnya             → POST /{fkp_id}/confirm-resolusi
    """
    return await fkp_service.buat_resolusi(fkp_id, data, user, kode_role, db)


@router.post("/{fkp_id}/confirm-resolusi", response_model=FkpDetailResponse)
async def confirm_resolusi(
    fkp_id:    uuid.UUID,
    catatan:   Optional[str] = None,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """
    [BARU — Modul Sample Shipment, Phase 5] Trigger accepted → in_process
    untuk resolusi SELAIN tukar_barang & potong_tagihan (yaitu
    tidak_ada_kompensasi, dengan atau tanpa metode_penanganan_fisik =
    dimusnahkan). Hanya admin_ho/superadmin.

    Gate: kalau metode_penanganan_fisik = dimusnahkan, wajib sudah ada
    attachment 'Berita Acara Pemusnahan dan Tukar Barang'. Kalau
    tipe_resolusi = tidak_ada_kompensasi, `catatan` wajib diisi.
    """
    return await fkp_service.confirm_resolusi(fkp_id, catatan, user, kode_role, db)


@router.patch("/{fkp_id}/surat-jalan", response_model=FkpDetailResponse)
async def update_surat_jalan(
    fkp_id:    uuid.UUID,
    data:      SuratJalanRequest,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """Input/update nomor surat jalan untuk resolusi tukar_barang."""
    # PERBAIKAN RBAC: kode_role sekarang diteruskan — sebelumnya gap keamanan
    # (input_surat_jalan tidak menerima/mengecek role sama sekali, sehingga
    # role apapun bisa mengubah nomor surat jalan).
    return await input_surat_jalan(fkp_id, data.nomor_surat_jalan, user, kode_role, db)


# ─── UPLOAD ATTACHMENT ────────────────────────────────────────────────────────

@router.post("/{fkp_id}/attachments", response_model=AttachmentResponse, status_code=201)
async def upload_bukti(
    fkp_id:      uuid.UUID,
    file:        UploadFile = File(...),
    fkp_item_id: Optional[uuid.UUID] = Query(
        None,
        description="UUID item produk. Jika diisi, foto dikaitkan ke item tertentu.",
    ),
    tipe_dokumen: Optional[str] = Query(
        None,
        description="Tipe dokumen dari TipeDokumen.ALL. Default: foto_keluhan.",
    ),
    keterangan: Optional[str] = Query(
        None,
        description="Deskripsi singkat file.",
    ),
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """Upload foto/dokumen bukti keluhan. Format: JPEG, PNG, WebP, MP4, MOV."""
    # PERBAIKAN BUG KRITIS: sebelumnya dipanggil positional
    # (fkp_id, file, user, db, fkp_item_id, tipe_dokumen, keterangan) padahal
    # signature asli upload_attachment() adalah
    # (fkp_id, file, user, db, kode_role, fkp_item_id, tipe_dokumen, keterangan).
    # Akibatnya kode_role TIDAK PERNAH terkirim (tergeser oleh fkp_item_id),
    # sehingga has_global_access()/get_scoped_distributor_ids() menerima nilai
    # yang salah dan upload selalu ditolak 403 untuk semua role non-superadmin.
    # Sekarang dipanggil dengan keyword arguments agar urutan tidak lagi
    # jadi sumber bug.
    return await upload_service.upload_attachment(
        fkp_id=fkp_id,
        file=file,
        user=user,
        db=db,
        kode_role=kode_role,
        fkp_item_id=fkp_item_id,
        tipe_dokumen=tipe_dokumen,
        keterangan=keterangan,
    )


@router.get("/{fkp_id}/attachments/{attachment_id}/file")
async def download_attachment(
    fkp_id:        uuid.UUID,
    attachment_id: uuid.UUID,
    db:            AsyncSession = Depends(get_db),
    user:          User = Depends(get_current_user),
    kode_role:     str  = Depends(get_kode_role),
):
    """
    [FIX KRITIS] Pengganti akses statis publik /uploads/... .
    File attachment sekarang HANYA bisa diunduh lewat endpoint ini, yang
    memakai scope check identik dengan get_fkp_detail() — user harus
    berada dalam scope FKP ini (outlet/distributor/sc_spv/apsm sesuai
    area, atau role dengan akses global). Tanpa token valid & tanpa lolos
    scope, file tidak bisa diakses sama sekali.
    """
    # Lolos scope check FKP yang sama dengan endpoint detail_fkp —
    # otomatis raise 403/404 jika user di luar jangkauan.
    await get_fkp_detail(fkp_id, db, user, kode_role)

    r = await db.execute(
        select(FkpAttachment).where(
            FkpAttachment.id == attachment_id,
            FkpAttachment.fkp_id == fkp_id,
        )
    )
    attachment = r.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="File tidak ditemukan.")

    # [FIX GAP #6 — Sample Shipment] Lapis kedua: get_fkp_detail() di atas
    # hanya memvalidasi scope FKP, bukan tipe dokumen. Tanpa gate ini, user
    # outlet/distributor/sc_spv yang tahu/menebak attachment_id tetap bisa
    # mengunduh file hasil_pemeriksaan_qc langsung meski sudah disaring dari
    # listing (lihat fkp_service._filter_internal_documents()).
    if (
        attachment.tipe_dokumen == TipeDokumen.HASIL_PEMERIKSAAN_QC
        and kode_role in ("outlet", "distributor", "sc_spv")
    ):
        raise HTTPException(
            status_code=403,
            detail="Dokumen hasil pemeriksaan QC bersifat internal dan tidak dapat diunduh oleh role ini.",
        )

    prefix = "/uploads/"
    relative_path = attachment.url[len(prefix):] if attachment.url.startswith(prefix) else attachment.url
    file_path = os.path.join(settings.UPLOAD_DIR, relative_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File fisik tidak ditemukan di server.")

    return FileResponse(file_path, filename=attachment.nama_file)


@router.delete("/{fkp_id}/attachments/{attachment_id}")
async def hapus_attachment(
    fkp_id:        uuid.UUID,
    attachment_id: uuid.UUID,
    db:            AsyncSession = Depends(get_db),
    user:          User = Depends(get_current_user),
    kode_role:     str  = Depends(get_kode_role),
):
    """Hapus file bukti. Hanya bisa oleh uploader atau superadmin."""
    return await upload_service.delete_attachment(
        attachment_id=attachment_id, user=user, kode_role=kode_role, db=db
    )


# ─── FINANCE ──────────────────────────────────────────────────────────────────

@router.post("/{fkp_id}/finance/invoice", response_model=InvoiceResponse, status_code=201)
async def terbitkan_invoice(
    fkp_id:    uuid.UUID,
    data:      InvoiceCreateRequest,
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
    db:        AsyncSession = Depends(get_db),
):
    """
    [BARU — Modul Sample Shipment, Phase 7] Generate PDF invoice potong
    tagihan + trigger accepted → in_process. Hanya finance/admin_ho/superadmin.
    nomor_invoice input manual. nilai_nota_penjualan WAJIB diisi di sini
    (bukan di /finance/proses) karena nilai_cashback harus sudah terhitung
    saat PDF invoice ini digenerate — lihat CATATAN di fkp_service.terbitkan_invoice().
    Setelah ini, gunakan POST .../finance/proses untuk konfirmasi pembayaran
    benar-benar sudah ditransfer.
    """
    return await fkp_service.terbitkan_invoice(
        fkp_id, data.nomor_invoice, data.nilai_nota_penjualan, data.catatan, user, kode_role, db
    )


@router.get("/{fkp_id}/finance/invoice/{doc_id}")
async def download_invoice_pdf(
    fkp_id:    uuid.UUID,
    doc_id:    uuid.UUID,
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
    db:        AsyncSession = Depends(get_db),
):
    """
    Download PDF invoice — HANYA lewat endpoint terautentikasi ini, bukan
    static file publik (konsisten dengan fix keamanan #1 sesi audit
    sebelumnya). Scope check via get_fkp_detail() (dipanggil di dalamnya).
    """
    await fkp_service.get_fkp_detail(fkp_id, db, user, kode_role)

    r = await db.execute(
        select(FkpDocument).where(FkpDocument.id == doc_id, FkpDocument.fkp_id == fkp_id)
    )
    doc = r.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan.")

    prefix = "/uploads/"
    relative_path = doc.url_file[len(prefix):] if doc.url_file.startswith(prefix) else doc.url_file
    file_path = os.path.join(settings.UPLOAD_DIR, relative_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File PDF tidak ditemukan di server.")

    return FileResponse(file_path, filename=f"Invoice_{doc.nomor_dokumen}.pdf", media_type="application/pdf")


@router.post("/{fkp_id}/finance/proses", response_model=FkpDetailResponse)
async def proses_finance(
    fkp_id:               uuid.UUID,
    catatan:              Optional[str]     = Query(default=None),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
    db:        AsyncSession = Depends(get_db),
):
    """
    [DIUBAH — Modul Sample Shipment] Sekarang HANYA untuk konfirmasi
    pembayaran sudah ditransfer — tidak lagi trigger accepted → in_process
    (itu sekarang tugas POST .../finance/invoice). Hanya bisa dipanggil
    saat status 'in_process'.

    [FIX] nilai_nota_penjualan TIDAK LAGI diterima di sini — nilai itu
    (dan nilai_cashback turunannya) sudah final & tercetak di PDF sejak
    POST .../finance/invoice. Kalau ada koreksi nilai nota, terbitkan
    invoice baru, jangan ubah lewat endpoint ini.
    """
    return await fkp_service.proses_finance(
        fkp_id, catatan, user, kode_role, db
    )


# ─── DOKUMEN FORMAL ───────────────────────────────────────────────────────────

@router.post("/{fkp_id}/documents", response_model=FkpDocumentResponse, status_code=201)
async def tambah_dokumen(
    fkp_id:    uuid.UUID,
    data:      FkpDocumentCreate,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """Admin HO menambahkan dokumen formal ke FKP (BA, surat jalan, invoice, dsb)."""
    return await buat_dokumen(fkp_id, data, user, kode_role, db)


@router.delete("/{fkp_id}/documents/{dokumen_id}")
async def hapus_dokumen_fkp(
    fkp_id:     uuid.UUID,
    dokumen_id: uuid.UUID,
    db:         AsyncSession = Depends(get_db),
    user:       User = Depends(get_current_user),
    kode_role:  str  = Depends(get_kode_role),
):
    """Hapus dokumen dari FKP. Hanya oleh pembuat atau superadmin."""
    return await hapus_dokumen(fkp_id, dokumen_id, user, kode_role, db)
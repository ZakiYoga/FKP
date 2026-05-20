"""
FKP Router — endpoint lengkap untuk semua operasi FKP.

Termasuk:
  - CRUD FKP master dan item
  - Transisi status (submit, review, approve, reject, close)
  - Upload attachment
  - Generate PDF (FKP dan Berita Acara Pemusnahan)
"""
import uuid
from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, Depends, Response, UploadFile, File, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user, get_kode_role
from app.core.config import settings
from app.models.user import User
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
from app.services import fkp_service, upload_service
from app.services.fkp_service import (
    create_fkp, update_fkp, list_fkp, get_fkp_detail,
    submit_fkp, apsm_review, admin_ho_review,
    rsm_approve_investigasi, qc_investigasi,
    admin_ho_request_resolusi_approval, rsm_approve_resolusi,
    direktur_approve, update_pengiriman, request_revision,
    reject_fkp, input_surat_jalan, close_fkp,
    add_fkp_item, update_fkp_item, delete_fkp_item,
    buat_dokumen, hapus_dokumen,
)
from app.services.fkp_pdf_service import generate_fkp_pdf
from app.services.berita_acara_pdf_service import (
    generate_berita_acara_pdf,
    generate_berita_acara_pdf_manual,
)

router = APIRouter()

# ─── Role constants ───────────────────────────────────────────────────────────

# Role yang boleh generate/download Berita Acara dari FKP
_BA_ROLES = ("superadmin", "admin_ho", "qc", "rsm")

# Role yang boleh generate BA manual
_BA_MANUAL_ROLES = ("superadmin", "admin_ho", "qc", "rsm", "direktur")


# ─── Meta ─────────────────────────────────────────────────────────────────────

@router.get("/meta/tipe-dokumen")
async def list_tipe_dokumen():
    """
    Listing semua tipe dokumen yang valid beserta label dan kelompoknya.
    Digunakan FE untuk dropdown pilihan tipe_dokumen saat upload.
    """
    from app.models.fkp import TipeDokumen
    return {
        "tipe_dokumen": [
            {"value": TipeDokumen.FOTO_KELUHAN,             "label": "Foto Keluhan Produk",        "kelompok": "keluhan"},
            {"value": TipeDokumen.FOTO_SAMPLE,              "label": "Foto Sample",                "kelompok": "keluhan"},
            {"value": TipeDokumen.FOTO_INVESTIGASI,         "label": "Foto Hasil Investigasi",     "kelompok": "investigasi"},
            {"value": TipeDokumen.SURAT_JALAN,              "label": "Surat Jalan",                "kelompok": "resolusi"},
            {"value": TipeDokumen.FOTO_SERAH_TERIMA,        "label": "Foto Serah Terima Barang",   "kelompok": "resolusi"},
            {"value": TipeDokumen.BERITA_ACARA_PENUKARAN,   "label": "Berita Acara Penukaran",     "kelompok": "resolusi"},
            {"value": TipeDokumen.INVOICE_TERPOTONG,        "label": "Invoice Terpotong",          "kelompok": "resolusi"},
            {"value": TipeDokumen.BUKTI_TRANSFER,           "label": "Bukti Transfer Cashback",    "kelompok": "resolusi"},
            {"value": TipeDokumen.NOTA_RETUR,               "label": "Nota Retur",                 "kelompok": "resolusi"},
            {"value": TipeDokumen.FOTO_PEMUSNAHAN,          "label": "Foto Pemusnahan",            "kelompok": "resolusi"},
            {"value": TipeDokumen.BERITA_ACARA_PEMUSNAHAN,  "label": "Berita Acara Pemusnahan",    "kelompok": "resolusi"},
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
):
    """Download FKP sebagai PDF siap cetak."""
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
):
    """
    Preview HTML template FKP di browser — berguna untuk QA tampilan.

    PERBAIKAN dari versi lama:
    Versi lama memanggil build_fkp_context dengan signature yang salah
    (fkp_data=dict, outlet_data=dict, dst). Versi ini menggunakan ORM objects
    langsung sesuai signature aktual fungsi tersebut.
    """
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

    if kode_role not in _BA_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{kode_role}' tidak diizinkan mengunduh Berita Acara.",
        )

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
    Role yang diizinkan: superadmin, admin_ho, qc, rsm
    """
    if kode_role not in _BA_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{kode_role}' tidak diizinkan mengunduh Berita Acara.",
        )

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

    Role yang diizinkan: superadmin, admin_ho, qc, rsm
    """
    if kode_role not in _BA_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{kode_role}' tidak diizinkan generate Berita Acara.",
        )

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

    Role yang diizinkan: superadmin, admin_ho, qc, rsm, direktur
    """
    if kode_role not in _BA_MANUAL_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{kode_role}' tidak diizinkan generate Berita Acara manual.",
        )

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
    return await add_fkp_item(fkp_id, data.model_dump(exclude_none=True), user, db)


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
    return await update_fkp_item(fkp_id, item_id, data, user, db)


@router.delete("/{fkp_id}/items/{item_id}")
async def hapus_item(
    fkp_id:    uuid.UUID,
    item_id:   uuid.UUID,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """Hapus item dari FKP. Minimal 1 item harus tetap ada."""
    return await delete_fkp_item(fkp_id, item_id, user, db)


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
                                    → otomatis pindah ke in_process
    """
    return await fkp_service.buat_resolusi(fkp_id, data, user, kode_role, db)


@router.patch("/{fkp_id}/surat-jalan", response_model=FkpDetailResponse)
async def update_surat_jalan(
    fkp_id:    uuid.UUID,
    data:      SuratJalanRequest,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """Input/update nomor surat jalan untuk resolusi tukar_barang."""
    return await input_surat_jalan(fkp_id, data.nomor_surat_jalan, user, db)


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
    return await upload_service.upload_attachment(
        fkp_id, file, user, db, fkp_item_id, tipe_dokumen, keterangan
    )


@router.delete("/{fkp_id}/attachments/{attachment_id}")
async def hapus_attachment(
    fkp_id:        uuid.UUID,
    attachment_id: uuid.UUID,
    db:            AsyncSession = Depends(get_db),
    user:          User = Depends(get_current_user),
    kode_role:     str  = Depends(get_kode_role),
):
    """Hapus file bukti. Hanya bisa oleh uploader atau superadmin."""
    return await upload_service.delete_attachment(attachment_id, user, kode_role, db)


# ─── FINANCE ──────────────────────────────────────────────────────────────────

@router.post("/{fkp_id}/finance/proses", response_model=FkpDetailResponse)
async def proses_finance(
    fkp_id:               uuid.UUID,
    catatan:              Optional[str]     = Query(default=None),
    nilai_nota_penjualan: Optional[Decimal] = Query(default=None, description="Nilai nota penjualan aktual"),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
    db:        AsyncSession = Depends(get_db),
):
    return await fkp_service.proses_finance(
        fkp_id, catatan, nilai_nota_penjualan, user, kode_role, db
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
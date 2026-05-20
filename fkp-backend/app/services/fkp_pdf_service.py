"""
app/services/fkp_pdf_service.py

Service generate PDF Formulir Keluhan Pelanggan (FKP).
Mengambil data dari:
  - FkpComplaint   → header FKP, prioritas, catatan, TTD
  - FkpItem        → daftar produk yang dikeluhkan (+ relasi product di-eager load)
  - FkpAttachment  → foto per item (foto_keluhan, foto_sample, dll.)
  - Outlet         → nama toko, alamat, no. HP, email
  - Distributor    → nama perusahaan
  - User           → nama TTD (submitted_by, handled_by, approved_by_*)

Dependencies:
    pip install xhtml2pdf jinja2

Integrasi ke router (sudah ada di fkp.py):
    from app.services.fkp_pdf_service import generate_fkp_pdf

    @router.get("/{fkp_id}/pdf")
    async def download_fkp_pdf(fkp_id: UUID, ...):
        pdf_bytes, nomor_fkp = await generate_fkp_pdf(fkp_id, db, upload_dir=settings.UPLOAD_DIR)
        ...
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import selectinload

from app.services.pdf_utils import (
    build_jinja_env,
    get_user_nama,
    load_file_base64,
    load_logo_base64,
    render_html_to_pdf,
)

if TYPE_CHECKING:
    from app.models.distributor import Distributor
    from app.models.fkp import FkpAttachment, FkpComplaint, FkpItem
    from app.models.outlet import Outlet

# ─── Konstanta ────────────────────────────────────────────────────────────────

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "FKP"
TEMPLATE_NAME = "fkp_template.html"

# Mapping tipe attachment → slot foto di template
_FOTO_TIPE_MAP: Dict[str, str] = {
    "foto_expired":       "expired",
    "foto_keluhan":       "keluhan",
    "foto_sample":        "keluhan",        # foto_sample masuk slot keluhan/sample
    "foto_kode_produksi": "kode_produksi",
}


# ─── Build Context ────────────────────────────────────────────────────────────

def build_fkp_context(
    fkp:               "FkpComplaint",
    outlet:            Optional["Outlet"],
    distributor:       Optional["Distributor"],
    items:             List["FkpItem"],
    attachments:       List["FkpAttachment"],
    submitted_by_name: str = "",
    apsm_name:         str = "",
    marketing_name:    str = "",
    direktur_name:     str = "",
    upload_dir:        str = "uploads",
) -> Dict:
    """
    Terima ORM objects langsung → bangun context Jinja2.

    Catatan: items harus di-query dengan selectinload(FkpItem.product)
    sebelum fungsi ini dipanggil agar item.product tidak lazy-load.
    """
    from app.models.fkp import JenisKeluhan

    # ── Kelompokkan attachment per fkp_item_id ────────────────────────────────
    att_by_item: Dict[str, List] = {}
    for att in attachments:
        key = str(att.fkp_item_id) if att.fkp_item_id else "__fkp__"
        att_by_item.setdefault(key, []).append(att)

    # ── Enrich setiap item ────────────────────────────────────────────────────
    enriched_items: List[Dict] = []
    for item in items:
        item_id          = str(item.id)
        item_attachments = att_by_item.get(item_id, [])

        # Resolve base64 per attachment
        enriched_atts = [
            {
                "tipe_dokumen": att.tipe_dokumen,
                "nama_file":    att.nama_file,
                "tipe_file":    att.tipe_file,
                "keterangan":   att.keterangan,
                "base64":       load_file_base64(upload_dir, att.url),
            }
            for att in item_attachments
        ]

        # Checkbox foto types untuk template
        foto_types: set[str] = {
            _FOTO_TIPE_MAP[att.tipe_dokumen]
            for att in item_attachments
            if att.tipe_dokumen in _FOTO_TIPE_MAP
        }

        # Nama produk dan kemasan: item override > relasi product
        # item.product sudah di-eager load via selectinload di generate_fkp_pdf
        nama_produk = (
            item.nama_produk_custom
            or (item.product.nama_produk if item.product else None)
            or "—"
        )
        jenis_kemasan = (
            item.jenis_kemasan
            or (item.product.jenis_kemasan if item.product else None)
            or "—"
        )

        enriched_items.append({
            "id":                  str(item.id),
            "nama_produk":         nama_produk,
            "jenis_kemasan":       jenis_kemasan,
            "qty":                 item.qty,
            "batch_number":        item.batch_number,
            "expired_date":        item.expired_date,
            "tanggal_pembelian":   item.tanggal_pembelian,
            "tanggal_dikonsumsi":  item.tanggal_dikonsumsi,
            "jenis_keluhan":       item.jenis_keluhan,
            "jenis_keluhan_label": JenisKeluhan.LABELS.get(item.jenis_keluhan, item.jenis_keluhan),
            "deskripsi_keluhan":   item.deskripsi_keluhan,
            "ada_sample_keluhan":  item.ada_sample_keluhan,
            "kondisi_sample":      item.kondisi_sample or "",
            "foto_types":          list(foto_types),
            "attachments":         enriched_atts,
        })

    # ── Outlet dict ───────────────────────────────────────────────────────────
    outlet_ctx = None
    if outlet:
        outlet_ctx = {
            "nama_toko":      outlet.nama_toko,
            "pemilik_toko":   outlet.pemilik_toko,
            "no_hp":          outlet.no_hp,
            "email":          outlet.email,
            "alamat_lengkap": outlet.alamat_lengkap,
        }

    # ── Distributor dict ──────────────────────────────────────────────────────
    distributor_ctx = None
    if distributor:
        distributor_ctx = {
            "nama_perusahaan": distributor.nama_perusahaan,
            "pemilik":         getattr(distributor, "pemilik", None),
            "no_telepon":      getattr(distributor, "no_telepon", None),
        }

    return {
        "fkp": {
            "id":                  str(fkp.id),
            "nomor_fkp":           fkp.nomor_fkp,
            "status":              fkp.status,
            "prioritas":           fkp.prioritas,
            "lokasi_pembelian":    fkp.lokasi_pembelian,
            "catatan_distributor": fkp.catatan_distributor,
            "tanggal_pengajuan":   fkp.tanggal_pengajuan,
        },
        "outlet":            outlet_ctx,
        "distributor":       distributor_ctx,
        "items":             enriched_items,
        "submitted_by_name": submitted_by_name,
        "apsm_name":         apsm_name,
        "marketing_name":    marketing_name,
        "direktur_name":     direktur_name,
        "logo_base64":       load_logo_base64(),
        "generated_at":      datetime.now(timezone.utc),
    }


# ─── Render & Generate ────────────────────────────────────────────────────────

def render_fkp_html(context: Dict) -> str:
    env = build_jinja_env(TEMPLATES_DIR)
    return env.get_template(TEMPLATE_NAME).render(**context)


def generate_fkp_pdf_from_context(context: Dict) -> bytes:
    return render_html_to_pdf(render_fkp_html(context))


# ─── FastAPI Integration ──────────────────────────────────────────────────────

async def generate_fkp_pdf(
    fkp_id:     UUID,
    db,
    upload_dir: str = "uploads",
) -> tuple[bytes, str]:
    """
    Query seluruh data FKP dari DB → build context → generate PDF.
    Return: (pdf_bytes, nomor_fkp)
    """
    from sqlmodel import select as sql_select

    from app.models.distributor import Distributor
    from app.models.fkp import FkpAttachment, FkpComplaint, FkpItem
    from app.models.outlet import Outlet

    # ── FkpComplaint ──────────────────────────────────────────────────────────
    result = await db.execute(
        sql_select(FkpComplaint).where(FkpComplaint.id == fkp_id)
    )
    fkp = result.scalar_one_or_none()
    if fkp is None:
        raise ValueError(f"FKP {fkp_id} tidak ditemukan")

    # ── Outlet ────────────────────────────────────────────────────────────────
    outlet = None
    if fkp.outlet_id:
        r = await db.execute(sql_select(Outlet).where(Outlet.id == fkp.outlet_id))
        outlet = r.scalar_one_or_none()

    # ── Distributor ───────────────────────────────────────────────────────────
    distributor = None
    if fkp.distributor_id:
        r = await db.execute(
            sql_select(Distributor).where(Distributor.id == fkp.distributor_id)
        )
        distributor = r.scalar_one_or_none()

    # ── FkpItem — WAJIB eager load relasi product ─────────────────────────────
    # Tanpa selectinload, item.product akan lazy-load dan crash di AsyncSession
    r = await db.execute(
        sql_select(FkpItem)
        .where(FkpItem.fkp_id == fkp_id)
        .options(selectinload(FkpItem.product))
        .order_by(FkpItem.created_at)
    )
    items = r.scalars().all()

    # ── FkpAttachment ─────────────────────────────────────────────────────────
    r = await db.execute(
        sql_select(FkpAttachment).where(FkpAttachment.fkp_id == fkp_id)
    )
    attachments = r.scalars().all()

    # ── Resolve nama TTD ──────────────────────────────────────────────────────
    submitted_by_name = await get_user_nama(db, fkp.submitted_by)
    apsm_name         = await get_user_nama(db, fkp.handled_by)
    marketing_name    = await get_user_nama(db, fkp.approved_by_marketing)
    direktur_name     = await get_user_nama(db, fkp.approved_by_direktur)

    # ── Build context & render ────────────────────────────────────────────────
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
        upload_dir        = upload_dir,
    )

    return generate_fkp_pdf_from_context(context), fkp.nomor_fkp
"""
app/services/berita_acara_pdf_service.py

Service generate PDF Berita Acara Pemusnahan dan Tukar Barang.

PERUBAHAN: fallback rekomendasi per item sekarang membaca
  item.rekomendasi_penanganan_admin_ho  (was: item.rekomendasi_admin_ho)
  item.rekomendasi_kompensasi_admin_ho  (tersedia untuk konteks tambahan)
"""

from __future__ import annotations

import uuid as _uuid_module
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import selectinload

from app.models.fkp import (
    FkpAttachment,
    FkpComplaint,
    FkpDocument,
    FkpItem,
    FkpResolution,
    RekomendasiTipe,
    TipeDokumen,
    TipeResolusi,
)
from app.models.outlet import Outlet
from app.services.pdf_utils import (
    build_jinja_env,
    format_date,
    get_user_nama,
    load_file_base64,
    load_logo_base64,
    render_html_to_pdf,
)

if TYPE_CHECKING:
    from app.models.user import User
    from app.schemas.berita_acara import (
        BeritaAcaraFromFkpRequest,
        BeritaAcaraManualRequest,
    )

# ─── Konstanta ────────────────────────────────────────────────────────────────

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "BA"
TEMPLATE_NAME = "berita_acara_pemusnahan.html"

_METODE_MAP: Dict[str, str] = {
    # Metode penanganan fisik (MetodePenangananFisik)
    "dimusnahkan":           "dibakar",
    "dijual_pakan_ternak":   "dijual_pakan_ternak",
    "dikirim_ke_ho":         "dikembalikan_ho",
    "disimpan_distributor":  "disimpan_distributor",
    "di_repack_oleh_pihak_internal": "di_repack_oleh_pihak_internal",
    # Rekomendasi lama dari APSM/Admin HO (backward compat)
    RekomendasiTipe.MUSNAHKAN:   "dibakar",
    RekomendasiTipe.KIRIM_KE_HO: "dikembalikan_ho",
    # String literal legacy
    "dibakar":               "dibakar",
    "dihancurkan":           "dihancurkan",
    "dikembalikan_ho":       "dikembalikan_ho",
}

_TINDAK_MAP: Dict[str, str] = {
    "tukar_barang":               "penukaran_barang",
    "potong_tagihan":             "potong_tagihan",
    "tidak_ada_kompensasi":       "tanpa_kompensasi",
    RekomendasiTipe.GANTI_BARANG:   "penukaran_barang",
    RekomendasiTipe.POTONG_TAGIHAN: "potong_tagihan",
    "penukaran_barang":           "penukaran_barang",
}

_HARI_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

NOMOR_DOKUMEN_DEFAULT = "SPP/QC/FORM 26"


# ─── Internal: shared context builder ────────────────────────────────────────

def _assemble_context(
    nomor_dokumen:        str,
    tanggal_pelaksanaan:  Optional[date],
    hari:                 Optional[str],
    lokasi_pelaksanaan:   Optional[str],
    metode_pemusnahan:    Optional[str],
    lokasi_pemusnahan:    Optional[str],
    pihak_pelaksana:      Optional[str],
    dokumentasi_lampiran: Optional[str],
    tindak_lanjut:        Optional[str],
    catatan_tambahan:     Optional[str],
    nama_pengaju:         Optional[str],
    nama_saksi_internal:  Optional[str],
    nama_saksi_eksternal: Optional[str],
    nama_penyetuju:       Optional[str],
    items_ctx:            List[Dict],
    foto_ctx:             List[Dict],
) -> Dict:
    return {
        "ba": {
            "nomor_dokumen":        nomor_dokumen,
            "revisi":               "00",
            "tanggal_dokumen":      tanggal_pelaksanaan,
            "hari":                 hari or "",
            "tanggal_pelaksanaan":  tanggal_pelaksanaan,
            "lokasi_pelaksanaan":   lokasi_pelaksanaan,
            "metode_pemusnahan":    metode_pemusnahan,
            "lokasi_pemusnahan":    lokasi_pemusnahan,
            "pihak_pelaksana":      pihak_pelaksana or "—",
            "dokumentasi_lampiran": dokumentasi_lampiran,
            "tindak_lanjut":        tindak_lanjut,
            "catatan_tambahan":     catatan_tambahan,
            "nama_pengaju":         nama_pengaju or "—",
            "nama_saksi_internal":  nama_saksi_internal or "—",
            "nama_saksi_eksternal": nama_saksi_eksternal or "—",
            "nama_penyetuju":       nama_penyetuju or "—",
        },
        "items":        items_ctx,
        "foto_list":    foto_ctx,
        "logo_base64":  load_logo_base64(),
        "generated_at": datetime.now(timezone.utc),
    }


# ─── Skenario A: Build context dari ORM objects ───────────────────────────────

def build_berita_acara_context(
    fkp:                 FkpComplaint,
    resolution:          Optional[FkpResolution],
    items:               List[FkpItem],
    attachments:         List[FkpAttachment],
    outlet:              Optional[Outlet],
    submitted_by_name:   str = "",
    saksi_internal_name: str = "",
    penyetuju_name:      str = "",
    override:            Optional["BeritaAcaraFromFkpRequest"] = None,
    nomor_dokumen:       str = NOMOR_DOKUMEN_DEFAULT,
    upload_dir:          str = "uploads",
) -> Dict:
    """
    Skenario A: terima ORM objects dari DB → build context Jinja2.

    PERUBAHAN: fallback rekomendasi per item sekarang membaca
      item.rekomendasi_penanganan_admin_ho  (was: item.rekomendasi_admin_ho)
    """

    # ── Tanggal & hari ────────────────────────────────────────────────────────
    tanggal_pelaksanaan: Optional[date] = None
    if resolution and resolution.tanggal_pemusnahan:
        tanggal_pelaksanaan = resolution.tanggal_pemusnahan
    elif fkp.tanggal_selesai:
        tanggal_pelaksanaan = fkp.tanggal_selesai.date()

    hari_str = _HARI_ID[tanggal_pelaksanaan.weekday()] if tanggal_pelaksanaan else ""

    # ── Metode pemusnahan ─────────────────────────────────────────────────────
    metode_val: Optional[str] = None
    if resolution:
        # Prioritas 1: field metode_penanganan_fisik
        if resolution.metode_penanganan_fisik:
            metode_val = _METODE_MAP.get(resolution.metode_penanganan_fisik)
        # Prioritas 2: fallback ke tipe_resolusi (backward compat)
        if not metode_val:
            metode_val = _METODE_MAP.get(resolution.tipe_resolusi or "")
        # Prioritas 3: fallback ke rekomendasi penanganan per item
        # PERUBAHAN: gunakan rekomendasi_penanganan_admin_ho (was: rekomendasi_admin_ho)
        if not metode_val:
            for item in items:
                mapped = _METODE_MAP.get(item.rekomendasi_penanganan_admin_ho or "")
                if mapped:
                    metode_val = mapped
                    break
    if override and override.metode_pemusnahan:
        metode_val = override.metode_pemusnahan

    # ── Tindak lanjut ─────────────────────────────────────────────────────────
    tindak_val: Optional[str] = None
    if resolution:
        tindak_val = _TINDAK_MAP.get(resolution.tipe_resolusi)

    # ── Lokasi ────────────────────────────────────────────────────────────────
    lokasi = resolution.lokasi_pemusnahan if resolution else None

    # ── Nama-nama TTD ─────────────────────────────────────────────────────────
    pihak = (
        (override.pihak_pelaksana if override and override.pihak_pelaksana else None)
        or submitted_by_name
        or "—"
    )
    saksi_eksternal = (
        (override.nama_saksi_eksternal if override and override.nama_saksi_eksternal else None)
        or (outlet.nama_toko if outlet else None)
        or "—"
    )
    penyetuju = (
        (override.nama_penyetuju if override and override.nama_penyetuju else None)
        or penyetuju_name
        or "—"
    )

    catatan_tambahan = override.catatan_tambahan if override else None

    # ── Items → tabel barang ──────────────────────────────────────────────────
    items_ctx: List[Dict] = []
    for item in items:
        nama_produk = (
            item.nama_produk_custom
            or (item.product.nama_produk if item.product else None)
            or "—"
        )
        batch_parts = [
            p for p in [
                item.batch_number,
                format_date(item.expired_date) if item.expired_date else None,
            ] if p
        ]
        ket_parts = [p for p in [item.deskripsi_keluhan, item.catatan_qc] if p]

        items_ctx.append({
            "nama_barang": nama_produk,
            "batch_no_ed": " / ".join(batch_parts),
            "jumlah":      f"{item.qty} pcs",
            "keterangan":  " | ".join(ket_parts),
        })

    # ── Foto lampiran ─────────────────────────────────────────────────────────
    foto_ctx: List[Dict] = []
    for i, att in enumerate(attachments):
        foto_ctx.append({
            "judul":      att.keterangan or f"Foto Pemusnahan {i + 1}",
            "base64":     load_file_base64(upload_dir, att.url),
            "tipe_file":  att.tipe_file or "image/jpeg",
            "keterangan": att.keterangan or "",
        })

    dok_lampiran = (
        f"Lihat lampiran foto ({len(foto_ctx)} foto)" if foto_ctx else None
    )

    return _assemble_context(
        nomor_dokumen        = nomor_dokumen,
        tanggal_pelaksanaan  = tanggal_pelaksanaan,
        hari                 = hari_str,
        lokasi_pelaksanaan   = lokasi,
        metode_pemusnahan    = metode_val,
        lokasi_pemusnahan    = lokasi,
        pihak_pelaksana      = pihak,
        dokumentasi_lampiran = dok_lampiran,
        tindak_lanjut        = tindak_val,
        catatan_tambahan     = catatan_tambahan,
        nama_pengaju         = submitted_by_name or "—",
        nama_saksi_internal  = saksi_internal_name or "—",
        nama_saksi_eksternal = saksi_eksternal,
        nama_penyetuju       = penyetuju,
        items_ctx            = items_ctx,
        foto_ctx             = foto_ctx,
    )


# ─── Skenario B: Build context dari request body (manual) ────────────────────

def build_berita_acara_context_from_request(
    request:       "BeritaAcaraManualRequest",
    nomor_dokumen: str = NOMOR_DOKUMEN_DEFAULT,
) -> Dict:
    """Skenario B: terima BeritaAcaraManualRequest → build context Jinja2."""

    hari_str = request.hari or ""
    if not hari_str and request.tanggal_pelaksanaan:
        hari_str = _HARI_ID[request.tanggal_pelaksanaan.weekday()]

    items_ctx: List[Dict] = [
        {
            "nama_barang": item.nama_barang,
            "batch_no_ed": item.batch_no_ed or "",
            "jumlah":      item.jumlah or "",
            "keterangan":  item.keterangan or "",
        }
        for item in (request.items or [])
    ]

    return _assemble_context(
        nomor_dokumen        = nomor_dokumen,
        tanggal_pelaksanaan  = request.tanggal_pelaksanaan,
        hari                 = hari_str,
        lokasi_pelaksanaan   = request.lokasi_pelaksanaan,
        metode_pemusnahan    = request.metode_pemusnahan,
        lokasi_pemusnahan    = request.lokasi_pemusnahan,
        pihak_pelaksana      = request.pihak_pelaksana,
        dokumentasi_lampiran = request.dokumentasi_lampiran,
        tindak_lanjut        = request.tindak_lanjut,
        catatan_tambahan     = None,
        nama_pengaju         = request.nama_pengaju,
        nama_saksi_internal  = request.nama_saksi_internal,
        nama_saksi_eksternal = request.nama_saksi_eksternal,
        nama_penyetuju       = request.nama_penyetuju,
        items_ctx            = items_ctx,
        foto_ctx             = [],
    )


# ─── Render & Generate ────────────────────────────────────────────────────────

def render_berita_acara_html(context: Dict) -> str:
    env = build_jinja_env(TEMPLATES_DIR)
    return env.get_template(TEMPLATE_NAME).render(**context)


def generate_berita_acara_pdf_from_context(context: Dict) -> bytes:
    return render_html_to_pdf(render_berita_acara_html(context))


# ─── Helper: simpan ke FkpDocument ───────────────────────────────────────────

async def _save_to_fkp_document(
    db,
    fkp_id:        UUID,
    nomor_dokumen: str,
    pdf_bytes:     bytes,
    uploaded_by:   UUID,
    upload_dir:    str = "uploads",
) -> FkpDocument:
    filename  = f"BA_{nomor_dokumen.replace('/', '-')}_{_uuid_module.uuid4().hex[:8]}.pdf"
    save_path = Path(upload_dir) / "berita_acara" / filename
    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_bytes(pdf_bytes)

    doc = FkpDocument(
        fkp_id          = fkp_id,
        tipe_dokumen    = TipeDokumen.BERITA_ACARA_PEMUSNAHAN,
        nomor_dokumen   = nomor_dokumen,
        tanggal_dokumen = datetime.now(timezone.utc).date(),
        url_file        = f"/uploads/berita_acara/{filename}",
        dibuat_oleh     = uploaded_by,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


# ─── Skenario A: FastAPI Integration ─────────────────────────────────────────

async def generate_berita_acara_pdf(
    fkp_id:       UUID,
    db,
    current_user: "User",
    override:     Optional["BeritaAcaraFromFkpRequest"] = None,
    upload_dir:   str = "uploads",
) -> tuple[bytes, str, UUID]:
    """
    Skenario A — generate BA dari FKP yang sudah ada di DB.
    Return: (pdf_bytes, nomor_dokumen, fkp_document_id)
    """
    from sqlmodel import select as sql_select

    result = await db.execute(
        sql_select(FkpComplaint).where(FkpComplaint.id == fkp_id)
    )
    fkp = result.scalar_one_or_none()
    if fkp is None:
        raise ValueError(f"FKP {fkp_id} tidak ditemukan")

    r = await db.execute(
        sql_select(FkpResolution).where(FkpResolution.fkp_id == fkp_id)
    )
    resolution = r.scalar_one_or_none()

    if resolution is None:
        raise ValueError(
            "Berita Acara belum dapat diterbitkan: FKP ini belum memiliki resolusi."
        )
    if resolution.metode_penanganan_fisik != "dimusnahkan":
        raise ValueError(
            f"Berita Acara Pemusnahan hanya dapat diterbitkan jika "
            f"metode_penanganan_fisik = 'dimusnahkan'. "
            f"Saat ini: '{resolution.metode_penanganan_fisik}'."
        )

    # FkpItem — eager load relasi product
    r = await db.execute(
        sql_select(FkpItem)
        .where(FkpItem.fkp_id == fkp_id)
        .options(selectinload(FkpItem.product))
        .order_by(FkpItem.created_at)
    )
    items = r.scalars().all()

    # FkpAttachment — hanya foto pemusnahan
    r = await db.execute(
        sql_select(FkpAttachment).where(
            FkpAttachment.fkp_id == fkp_id,
            FkpAttachment.tipe_dokumen == TipeDokumen.FOTO_PEMUSNAHAN,
        )
    )
    attachments = r.scalars().all()

    outlet = None
    if fkp.outlet_id:
        r = await db.execute(sql_select(Outlet).where(Outlet.id == fkp.outlet_id))
        outlet = r.scalar_one_or_none()

    submitted_by_name   = await get_user_nama(db, fkp.submitted_by)
    saksi_internal_name = await get_user_nama(db, fkp.handled_by)
    penyetuju_name      = await get_user_nama(db, fkp.approved_by_marketing)

    nomor_dokumen = f"BA/{fkp.nomor_fkp}"

    context = build_berita_acara_context(
        fkp                 = fkp,
        resolution          = resolution,
        items               = list(items),
        attachments         = list(attachments),
        outlet              = outlet,
        submitted_by_name   = submitted_by_name,
        saksi_internal_name = saksi_internal_name,
        penyetuju_name      = penyetuju_name,
        override            = override,
        nomor_dokumen       = nomor_dokumen,
        upload_dir          = upload_dir,
    )

    pdf_bytes = generate_berita_acara_pdf_from_context(context)

    doc = await _save_to_fkp_document(
        db            = db,
        fkp_id        = fkp_id,
        nomor_dokumen = nomor_dokumen,
        pdf_bytes     = pdf_bytes,
        uploaded_by   = current_user.id,
        upload_dir    = upload_dir,
    )

    return pdf_bytes, nomor_dokumen, doc.id


# ─── Skenario B: FastAPI Integration (manual) ────────────────────────────────

async def generate_berita_acara_pdf_manual(
    request:      "BeritaAcaraManualRequest",
    db,
    current_user: "User",
    upload_dir:   str = "uploads",
) -> tuple[bytes, str, Optional[UUID]]:
    """
    Skenario B — generate BA dari inputan manual user (tanpa FKP wajib).
    Return: (pdf_bytes, nomor_dokumen, fkp_document_id_or_None)
    """
    from sqlmodel import select as sql_select

    if request.fkp_id:
        r = await db.execute(
            sql_select(FkpComplaint).where(FkpComplaint.id == request.fkp_id)
        )
        if r.scalar_one_or_none() is None:
            raise ValueError(f"FKP {request.fkp_id} tidak ditemukan")

    nomor_dokumen = (
        f"BA/{request.fkp_id}"
        if request.fkp_id
        else f"BA/MANUAL/{_uuid_module.uuid4().hex[:8].upper()}"
    )

    context   = build_berita_acara_context_from_request(request, nomor_dokumen)
    pdf_bytes = generate_berita_acara_pdf_from_context(context)

    doc_id: Optional[UUID] = None
    if request.fkp_id:
        doc = await _save_to_fkp_document(
            db            = db,
            fkp_id        = request.fkp_id,
            nomor_dokumen = nomor_dokumen,
            pdf_bytes     = pdf_bytes,
            uploaded_by   = current_user.id,
            upload_dir    = upload_dir,
        )
        doc_id = doc.id

    return pdf_bytes, nomor_dokumen, doc_id
"""
app/services/fkp_pdf_service.py

Service generate PDF Formulir Keluhan Pelanggan (FKP) — Jinja2 + WeasyPrint.

ALUR (baca dari bawah ke atas kalau mau menelusuri dari router):

  generate_fkp_pdf()                 ← dipanggil router; query semua data dari DB
    ├─ _get_kode_tracking_fkp()      ← nomor FKP{DDMMYY}{urutan}
    ├─ _get_tanggal_diterima_qc()    ← dari FkpStatusLog
    ├─ _get_apsm_reviewer_name()     ← dari FkpStatusLog
    ├─ build_fkp_context()           ← ORM objects → dict untuk template
    │    ├─ _build_pelanggan_context()   ← outlet, fallback distributor
    │    └─ _build_item_context()        ← 1 item produk + lampirannya
    └─ generate_fkp_pdf_from_context()
         └─ render_fkp_html() → render_html_to_pdf()  (pdf_utils.py)

Template: app/templates/FKP/fkp_template.html (+ _macros.html).

Data sumber:
  FkpComplaint  → header FKP, catatan, penanda approval
  FkpItem       → produk yang dikeluhkan (+ relasi product, eager load)
  FkpAttachment → foto per item
  Outlet        → data pelanggan bila FKP punya outlet
  Distributor   → data pelanggan bila FKP TIDAK punya outlet (diajukan
                  distributor / sc_spv / apsm), dan nama distributor
                  yang ditampilkan di bawah nama outlet
  User          → nama penandatangan
  FkpStatusLog  → tanggal diterima QC, nama reviewer APSM

QR Code:
  Di-generate ulang di server (WeasyPrint tidak menjalankan JS). Isinya
  {FRONTEND_BASE_URL}/track/{fkp.id}, sama dengan link di UI.

Kode tracking (header dokumen):
  FKP{DDMMYY}{urutan 3 digit}, tanpa underscore. Tanggal & urutan dihitung
  per hari kalender WIB dari tanggal_pengajuan.

Tanda tangan kolom ke-4 (dinamis, saling eksklusif):
  fkp.approved_by_direktur terisi  → "Direktur"
  fkp.approved_by_rsm_final terisi → "MSM" (jalur cepat)

Dependencies:
    pip install weasyprint jinja2 "qrcode[pil]"
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.services.pdf_utils import (
    build_jinja_env,
    generate_qr_base64,
    get_user_nama,
    load_file_base64,
    load_logo_base64,
    render_html_to_pdf,
)

if TYPE_CHECKING:
    from app.models.distributor import Distributor
    from app.models.fkp import FkpAttachment, FkpComplaint, FkpItem
    from app.models.outlet import Outlet

logger = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════════════════
# 1. KONSTANTA
# ═════════════════════════════════════════════════════════════════════════════

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "FKP"
TEMPLATE_NAME = "fkp_template.html"

WIB = timezone(timedelta(hours=7))

# Tipe attachment → slot checkbox "Foto Produk" di template.
_FOTO_TIPE_MAP: Dict[str, str] = {
    "foto_expired":       "expired",
    "foto_kode_produksi": "kode_produksi",
    "foto_keluhan":       "keluhan",
    "foto_sample":        "keluhan",
}

# Di lapangan foto expired & kode produksi selalu berdekatan (satu foto
# menangkap keduanya), jadi kalau salah satu ada, KEDUANYA dicentang.
_FOTO_EXPIRED_KODE_LINKED = {"expired", "kode_produksi"}

# Nilai kondisi_sample yang punya checkbox sendiri. Selain ini (mis.
# 'kemasan_plastik', 'lainnya') masuk ke checkbox "Lainnya".
_KONDISI_SAMPLE_BAKU = ("utuh", "terbuka")


# ═════════════════════════════════════════════════════════════════════════════
# 2. BUILDER CONTEXT (ORM → dict untuk template)
# ═════════════════════════════════════════════════════════════════════════════

def _build_pelanggan_context(
    outlet: Optional["Outlet"],
    distributor: Optional["Distributor"],
) -> Optional[Dict]:
    """
    Data 'Nama Pelanggan / Alamat / Telepon / Email' di Section A.

    outlet_id opsional saat FKP dibuat (create_fkp), jadi:
      - Ada outlet   → seluruh data dari OUTLET (tidak dicampur dengan data
                       distributor). distributor_nama disertakan supaya
                       dokumen jelas outlet ini di bawah distributor mana.
      - Tanpa outlet → seluruh data dari DISTRIBUTOR.
    """
    if outlet:
        return {
            "tipe":            "outlet",
            "nama":            outlet.nama_toko,
            "alamat":          outlet.alamat_lengkap,
            "no_telepon":      outlet.no_hp,
            "email":           outlet.email,
            "distributor_nama": distributor.nama_perusahaan if distributor else None,
        }

    if distributor:
        return {
            "tipe":            "distributor",
            "nama":            distributor.nama_perusahaan,
            "alamat":          getattr(distributor, "alamat_lengkap", None),
            "no_telepon":      getattr(distributor, "no_telepon", None),
            "email":           getattr(distributor, "email_perusahaan", None),
            "distributor_nama": distributor.nama_perusahaan,
        }

    return None


def _build_item_context(
    item: "FkpItem",
    item_attachments: List["FkpAttachment"],
    upload_dir: str,
) -> Dict:
    """Satu produk yang dikeluhkan + lampiran fotonya."""
    from app.models.fkp import (
        JenisKeluhan, KondisiSample, MetodePenangananFisik, RekomendasiTipe,
    )

    # ── a. Lampiran: baca file → base64. File yang hilang di disk dilewati
    #       (dan dilog) supaya tidak muncul gambar rusak "base64,None".
    lampiran: List[Dict] = []
    for att in item_attachments:
        b64 = load_file_base64(upload_dir, att.url)
        if not b64:
            logger.warning(
                "Lampiran FKP tidak ditemukan di disk: url=%s upload_dir=%s",
                att.url, upload_dir,
            )
            continue
        lampiran.append({
            "tipe_dokumen": att.tipe_dokumen,
            "nama_file":    att.nama_file,
            "tipe_file":    att.tipe_file,
            "keterangan":   att.keterangan,
            "base64":       b64,
        })

    # ── b. Checkbox "Foto Produk" — berdasarkan tipe attachment di DB.
    foto_types: set[str] = {
        _FOTO_TIPE_MAP[att.tipe_dokumen]
        for att in item_attachments
        if att.tipe_dokumen in _FOTO_TIPE_MAP
    }
    if foto_types & _FOTO_EXPIRED_KODE_LINKED:
        foto_types |= _FOTO_EXPIRED_KODE_LINKED

    # ── c. Nama produk & kemasan: snapshot item > katalog produk.
    nama_produk = item.product.nama_produk if item.product else "—"
    jenis_kemasan = (
        item.jenis_kemasan
        or (item.product.jenis_kemasan if item.product else None)
        or "—"
    )

    # ── d. Kondisi sample: utuh / terbuka punya checkbox sendiri, sisanya
    #       ('kemasan_plastik', 'lainnya') dicentang di "Lainnya".
    kondisi = item.kondisi_sample or ""
    kondisi_label = KondisiSample.LABELS.get(kondisi, "")
    kondisi_lainnya_aktif = bool(kondisi) and kondisi not in _KONDISI_SAMPLE_BAKU
    if kondisi_lainnya_aktif:
        kondisi_lainnya_teks = item.kondisi_sample_lainnya or (
            kondisi_label if kondisi != "lainnya" else ""
        )
    else:
        kondisi_lainnya_teks = ""

    # ── e. Rekomendasi APSM (label bahasa Indonesia).
    rekomendasi_fisik = MetodePenangananFisik.LABELS.get(
        item.rekomendasi_penanganan_apsm, item.rekomendasi_penanganan_apsm or "-"
    )
    rekomendasi_penanganan = RekomendasiTipe.LABELS.get(
        item.rekomendasi_kompensasi_apsm, item.rekomendasi_kompensasi_apsm or "-"
    )

    return {
        "id":                     str(item.id),
        "nama_produk":            nama_produk,
        "jenis_kemasan":          jenis_kemasan,
        "qty":                    item.qty,
        "batch_number":           item.batch_number,
        "expired_date":           item.expired_date,
        "tanggal_pembelian":      item.tanggal_pembelian,
        "tanggal_dikonsumsi":     item.tanggal_dikonsumsi,
        "jenis_keluhan":          item.jenis_keluhan,
        "jenis_keluhan_label":    JenisKeluhan.LABELS.get(item.jenis_keluhan, item.jenis_keluhan),
        "deskripsi_keluhan":      item.deskripsi_keluhan,
        # checkbox
        "ada_sample_keluhan":     item.ada_sample_keluhan,
        "kondisi_sample":         kondisi,
        "kondisi_lainnya_aktif":  kondisi_lainnya_aktif,
        "kondisi_lainnya_teks":   kondisi_lainnya_teks,
        "foto_types":             sorted(foto_types),
        # rekomendasi & persetujuan
        "rekomendasi_fisik":      rekomendasi_fisik,
        "rekomendasi_penanganan": rekomendasi_penanganan,
        "rekomendasi_persentase": item.persentase_disetujui_apsm,
        "persentase_qc":          item.persentase_disetujui_qc,
        # lampiran
        "attachments":            lampiran,
    }


def build_fkp_context(
    fkp:                 "FkpComplaint",
    outlet:              Optional["Outlet"],
    distributor:         Optional["Distributor"],
    items:               List["FkpItem"],
    attachments:         List["FkpAttachment"],
    submitted_by_name:   str = "",
    apsm_name:           str = "",
    marketing_name:      str = "",
    direktur_name:       str = "",
    rsm_final_name:      str = "",
    upload_dir:          str = "uploads",
    base_url:            str = "",
    fkp_kode_tracking:   str = "",
    tanggal_diterima_qc: Optional[datetime] = None,
) -> Dict:
    """Terima ORM objects langsung → bangun context Jinja2."""
    from app.models.fkp import (
        JenisKeluhan, KondisiSample, MetodePenangananFisik,
        RekomendasiTipe, BATAS_QTY_DIREKTUR, KEMASAN_DIHITUNG_JALUR,
    )

    # ── 1. Kelompokkan attachment per item ───────────────────────────────────
    att_by_item: Dict[str, List] = {}
    for att in attachments:
        key = str(att.fkp_item_id) if att.fkp_item_id else "__fkp__"
        att_by_item.setdefault(key, []).append(att)

    # ── 2. Item produk ───────────────────────────────────────────────────────
    enriched_items = [
        _build_item_context(item, att_by_item.get(str(item.id), []), upload_dir)
        for item in items
    ]

    # ── 3. Pelanggan (outlet / fallback distributor) ─────────────────────────
    pelanggan_ctx = _build_pelanggan_context(outlet, distributor)

    # ── 4. QR tracking ───────────────────────────────────────────────────────
    tracking_url   = f"{base_url.rstrip('/')}/track/{fkp.id}"
    qr_code_base64 = generate_qr_base64(tracking_url)

    # ── 5. Jalur cepat vs reguler → menentukan baris catatan MSM ─────────────
    # CATATAN: sengaja menjumlah qty SEMUA kemasan (termasuk pcs/renceng).
    # Aturan backend (_hitung_total_qty_jalur) hanya menghitung zak/ball/karton;
    # disamakan nanti setelah aturan pcs/renceng final.
    total_qty      = sum(item.qty for item in items)
    is_jalur_cepat = total_qty <= BATAS_QTY_DIREKTUR

    label_catatan_msm_final = (
        "Catatan MSM (Persetujuan Akhir)" if is_jalur_cepat else "Catatan MSM (Resolusi)"
    )

    # ── 6. Context akhir ─────────────────────────────────────────────────────
    return {
        "fkp": {
            "id":                  str(fkp.id),
            "nomor_fkp":           fkp.nomor_fkp,
            "status":              fkp.status,
            "prioritas":           fkp.prioritas,
            "lokasi_pembelian":    fkp.lokasi_pembelian,
            "catatan_distributor": fkp.catatan_distributor,
            "tanggal_pengajuan":   fkp.tanggal_pengajuan,
            "tanggal_diterima_qc": tanggal_diterima_qc,
            # penanda approval → menentukan label & nama TTD kolom ke-4
            "approved_by_direktur":  fkp.approved_by_direktur,
            "approved_by_rsm_final": fkp.approved_by_rsm_final,
        },
        "pelanggan":               pelanggan_ctx,
        "items":                   enriched_items,
        # penandatangan
        "submitted_by_name":       submitted_by_name,
        "apsm_name":               apsm_name,
        "marketing_name":          marketing_name,
        "direktur_name":           direktur_name,
        "rsm_final_name":          rsm_final_name,
        # catatan Section C
        "catatan_marketing":       fkp.catatan_admin or "-",
        "catatan_msm_investigasi": fkp.catatan_rsm_investigasi or "-",
        "catatan_msm_final":       fkp.catatan_rsm_resolusi or "-",
        "label_catatan_msm_final": label_catatan_msm_final,
        "is_jalur_cepat":          is_jalur_cepat,
        # aset & meta dokumen
        "logo_base64":             load_logo_base64(),
        "qr_code_base64":          qr_code_base64,
        "generated_at":            datetime.now(timezone.utc),
        "fkp_kode_tracking":       fkp_kode_tracking,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 3. RENDER
# ═════════════════════════════════════════════════════════════════════════════

def render_fkp_html(context: Dict) -> str:
    env = build_jinja_env(TEMPLATES_DIR)
    return env.get_template(TEMPLATE_NAME).render(**context)


def generate_fkp_pdf_from_context(context: Dict) -> bytes:
    return render_html_to_pdf(render_fkp_html(context))


# ═════════════════════════════════════════════════════════════════════════════
# 4. HELPER QUERY DB
# ═════════════════════════════════════════════════════════════════════════════

async def _get_kode_tracking_fkp(db, fkp) -> str:
    """
    Format: FKP{DDMMYY}{urutan 3 digit}, tanpa underscore.

    Urutan = jumlah FKP yang diajukan pada HARI KALENDER (WIB) yang sama dan
    waktu pengajuannya <= FKP ini (FKP ini ikut terhitung).

    (Versi lama membandingkan tanggal_pengajuan dengan '==' pada timestamp
    penuh, sehingga hasilnya selalu 1 → semua FKP berakhiran 001.)
    """
    from sqlmodel import select as sql_select
    from app.models.fkp import FkpComplaint

    diajukan = fkp.tanggal_pengajuan
    if diajukan is None:
        return ""
    if diajukan.tzinfo is None:
        diajukan = diajukan.replace(tzinfo=timezone.utc)

    diajukan_wib = diajukan.astimezone(WIB)
    awal_hari    = diajukan_wib.replace(hour=0, minute=0, second=0, microsecond=0)
    akhir_hari   = awal_hari + timedelta(days=1)

    result = await db.execute(
        sql_select(func.count()).select_from(FkpComplaint).where(
            FkpComplaint.tanggal_pengajuan >= awal_hari,
            FkpComplaint.tanggal_pengajuan < akhir_hari,
            FkpComplaint.tanggal_pengajuan <= diajukan,
        )
    )
    urutan = result.scalar_one()
    return f"FKP{diajukan_wib.strftime('%d%m%y')}{urutan:03d}"


async def _get_tanggal_diterima_qc(db, fkp) -> Optional[datetime]:
    """
    'Tanggal Diterima QC' diturunkan dari FkpStatusLog (bukan kolom sendiri):
      - Jalur reguler: transisi ke 'in_investigation'.
      - Jalur cepat  : transisi ke 'rsm_approval_final' (QC bekerja paralel,
                       tidak pernah ada 'in_investigation').
    Diambil log paling awal di antara keduanya.
    """
    from sqlmodel import select as sql_select
    from app.models.fkp import FkpStatus, FkpStatusLog

    result = await db.execute(
        sql_select(FkpStatusLog.changed_at)
        .where(
            FkpStatusLog.fkp_id == fkp.id,
            FkpStatusLog.status_baru.in_([
                FkpStatus.IN_INVESTIGATION,
                FkpStatus.RSM_APPROVAL_FINAL,
            ]),
        )
        .order_by(FkpStatusLog.changed_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_apsm_reviewer_name(db, fkp) -> str:
    """
    Tidak ada kolom khusus untuk reviewer APSM; jejaknya hanya di
    FkpStatusLog.changed_by pada transisi ke 'apsm_reviewed'.
    """
    from sqlmodel import select as sql_select
    from app.models.fkp import FkpStatus, FkpStatusLog

    result = await db.execute(
        sql_select(FkpStatusLog.changed_by)
        .where(
            FkpStatusLog.fkp_id == fkp.id,
            FkpStatusLog.status_baru == FkpStatus.APSM_REVIEWED,
        )
        .order_by(FkpStatusLog.changed_at.asc())
        .limit(1)
    )
    user_id = result.scalar_one_or_none()
    return await get_user_nama(db, user_id) if user_id else ""


# ═════════════════════════════════════════════════════════════════════════════
# 5. ENTRY POINT (dipanggil router)
# ═════════════════════════════════════════════════════════════════════════════

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

    # ── FkpComplaint ─────────────────────────────────────────────────────────
    result = await db.execute(
        sql_select(FkpComplaint).where(FkpComplaint.id == fkp_id)
    )
    fkp = result.scalar_one_or_none()
    if fkp is None:
        raise ValueError(f"FKP {fkp_id} tidak ditemukan")

    # ── Outlet (opsional) ────────────────────────────────────────────────────
    outlet = None
    if fkp.outlet_id:
        r = await db.execute(sql_select(Outlet).where(Outlet.id == fkp.outlet_id))
        outlet = r.scalar_one_or_none()

    # ── Distributor ──────────────────────────────────────────────────────────
    distributor = None
    if fkp.distributor_id:
        r = await db.execute(
            sql_select(Distributor).where(Distributor.id == fkp.distributor_id)
        )
        distributor = r.scalar_one_or_none()

    # ── FkpItem — WAJIB eager load product (lazy-load crash di AsyncSession) ──
    r = await db.execute(
        sql_select(FkpItem)
        .where(FkpItem.fkp_id == fkp_id)
        .options(selectinload(FkpItem.product))
        .order_by(FkpItem.created_at)
    )
    items = r.scalars().all()

    # ── FkpAttachment ────────────────────────────────────────────────────────
    r = await db.execute(
        sql_select(FkpAttachment).where(FkpAttachment.fkp_id == fkp_id)
    )
    attachments = r.scalars().all()

    # ── Nama penandatangan (get_user_nama mengembalikan "" untuk None) ───────
    submitted_by_name = await get_user_nama(db, fkp.submitted_by)
    apsm_name         = await _get_apsm_reviewer_name(db, fkp)
    marketing_name    = await get_user_nama(db, fkp.handled_by)
    direktur_name     = await get_user_nama(db, fkp.approved_by_direktur)
    rsm_final_name    = await get_user_nama(db, fkp.approved_by_rsm_final)

    # ── Turunan dari status log & nomor tracking ─────────────────────────────
    tanggal_diterima_qc = await _get_tanggal_diterima_qc(db, fkp)
    kode_tracking       = await _get_kode_tracking_fkp(db, fkp)

    # ── Build context & render ───────────────────────────────────────────────
    context = build_fkp_context(
        fkp                 = fkp,
        outlet              = outlet,
        distributor         = distributor,
        items               = list(items),
        attachments         = list(attachments),
        submitted_by_name   = submitted_by_name,
        apsm_name           = apsm_name,
        marketing_name      = marketing_name,
        direktur_name       = direktur_name,
        rsm_final_name      = rsm_final_name,
        upload_dir          = upload_dir,
        base_url            = settings.FRONTEND_BASE_URL,
        fkp_kode_tracking   = kode_tracking,
        tanggal_diterima_qc = tanggal_diterima_qc,
    )

    return generate_fkp_pdf_from_context(context), fkp.nomor_fkp
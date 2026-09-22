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
  - FkpStatusLog   → tanggal_diterima_qc (BARU, diturunkan dari transisi status,
                      bukan kolom tersendiri — lihat _get_tanggal_diterima_qc())

QR Code:
  QR tracking di-generate ulang di server (bukan reuse dari frontend) karena
  WeasyPrint tidak menjalankan JS browser. Isi QR selalu merujuk ke
  {FRONTEND_BASE_URL}/track/{fkp.id} — identik dengan link yang ditampilkan
  di UI, supaya QR di PDF dan QR di frontend selalu konsisten.

Nomor kode tracking (dipakai untuk QR & header dokumen):
  Format: FKP{DDMMYY}{urutan 3 digit}, TANPA underscore (dikonfirmasi user).
  Contoh: FKP110926001 untuk FKP pertama yang diajukan tanggal 11 Sept 2026.

Tanda tangan kolom ke-4 (dulu selalu "Direktur"):
  BARU — dinamis. Sejak FKP bisa accepted lewat 2 jalur berbeda (lihat
  fkp_service.py: rsm_approve_final() untuk jalur cepat qty ≤ 10 zak, dan
  rsm_approve_resolusi() cabang skip-Direktur untuk pemusnahan/tidak_ada_
  kompensasi), kolom TTD ke-4 HARUS mengikuti siapa yang benar-benar
  meng-approve, bukan asumsi selalu Direktur:
    - fkp.approved_by_direktur terisi → label "Direktur", nama Direktur.
    - fkp.approved_by_rsm_final terisi (approved_by_direktur kosong)
      → label "RSM (Manager Sales & Marketing)", nama RSM/MSM yang approve.
  Kedua field itu SALING EKSKLUSIF (lihat catatan di models/fkp.py).

Dependencies:
    pip install xhtml2pdf jinja2 "qrcode[pil]"

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
    from app.models.fkp import (
        FkpAttachment, FkpComplaint, FkpItem,
        JenisKeluhan, KondisiSample, MetodePenangananFisik,
        RekomendasiTipe, BATAS_QTY_DIREKTUR,
    )
    from app.models.outlet import Outlet

# ─── Konstanta ────────────────────────────────────────────────────────────────

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "FKP"
TEMPLATE_NAME = "fkp_template.html"

# Mapping tipe attachment → slot foto di template
_FOTO_TIPE_MAP: Dict[str, str] = {
    "foto_expired":       "expired",
    "foto_keluhan":       "keluhan",
    "foto_sample":        "keluhan",
}

# BARU (poin 4) — di lapangan foto expired & foto kode produksi SELALU
# berdekatan (satu foto sekaligus menangkap keduanya), jadi kalau salah satu
# tipe attachment-nya ada, checkbox KEDUANYA dianggap terisi. Dipakai di
# build_fkp_context() untuk menentukan foto_types per item — TIDAK lagi di
# template (menghindari bug operator precedence Jinja `'x' or 'y' in list`
# yang sebelumnya selalu truthy).
_FOTO_EXPIRED_KODE_LINKED = {"expired", "kode_produksi"}


# ─── Build Context ────────────────────────────────────────────────────────────

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
    rsm_final_name:       str = "",
    upload_dir:          str = "uploads",
    base_url:            str = "",
    fkp_kode_tracking:   str = "",
    tanggal_diterima_qc: Optional[datetime] = None,
) -> Dict:
    """
    Terima ORM objects langsung → bangun context Jinja2.
    """
    from app.models.fkp import (
        JenisKeluhan, KondisiSample, MetodePenangananFisik,
        RekomendasiTipe, BATAS_QTY_DIREKTUR,
    )

    # ── Kelompokkan attachment per fkp_item_id ────────────────────────────────
    att_by_item: Dict[str, List] = {}
    for att in attachments:
        key = str(att.fkp_item_id) if att.fkp_item_id else "__fkp__"
        att_by_item.setdefault(key, []).append(att)

    # ── Enrich setiap item ────────────────────────────────────────────────────
    enriched_items: List[Dict] = []

    for idx, item in enumerate(items, start=1):
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

        # ── Checkbox foto types (FIX poin 4) ────────────────────────────────
        # Foto expired & kode produksi SELALU berdekatan secara fisik —
        # kalau salah satu tipe attachment-nya ada, KEDUANYA dianggap
        # tercentang. foto_keluhan/foto_sample tetap independen.
        raw_types: set[str] = {
            _FOTO_TIPE_MAP[att.tipe_dokumen]
            for att in item_attachments
            if att.tipe_dokumen in _FOTO_TIPE_MAP
        }
        foto_types: set[str] = set(raw_types)
        if raw_types & _FOTO_EXPIRED_KODE_LINKED:
            foto_types |= _FOTO_EXPIRED_KODE_LINKED

        # Nama produk dan kemasan: item override > relasi product
        # item.product sudah di-eager load via selectinload di generate_fkp_pdf
        nama_produk = item.product.nama_produk if item.product else "—"
        jenis_kemasan = (
            item.jenis_kemasan
            or (item.product.jenis_kemasan if item.product else None)
            or "—"
        )

        # ── Kondisi sample  ───────────────────────────────
        kondisi_sample_value = item.kondisi_sample or ""
        kondisi_sample_label = KondisiSample.LABELS.get(kondisi_sample_value, "")

        # ── Rekomendasi Sales (APSM) per item — untuk ringkasan Section C ──
        rekomendasi_fisik = MetodePenangananFisik.LABELS.get(
            item.rekomendasi_penanganan_apsm, item.rekomendasi_penanganan_apsm or "-"
        )
        rekomendasi_penanganan = RekomendasiTipe.LABELS.get(
            item.rekomendasi_kompensasi_apsm, item.rekomendasi_kompensasi_apsm or "-"
        )

        enriched_items.append({
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
            "ada_sample_keluhan":     item.ada_sample_keluhan,
            "kondisi_sample":         kondisi_sample_value,
            "kondisi_sample_label":   kondisi_sample_label,
            "kondisi_sample_lainnya": item.kondisi_sample_lainnya or "",
            "rekomendasi_fisik":       rekomendasi_fisik,
            "rekomendasi_penanganan":  rekomendasi_penanganan,
            "rekomendasi_persentase":  item.persentase_disetujui_apsm,
            "catatan_apsm":           item.catatan_apsm or "-",
            "foto_types":             list(foto_types),
            "attachments":            enriched_atts,
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

    # ── QR Code tracking ──────────────────────────────────────────────────────
    # Merujuk langsung ke halaman tracking FKP di frontend, format identik
    # dengan QR yang ditampilkan di UI: {BASE_URL}/track/{fkp.id}
    tracking_url   = f"{base_url.rstrip('/')}/track/{fkp.id}"
    qr_code_base64 = generate_qr_base64(tracking_url)

    total_qty = sum(item.qty for item in items)
    is_jalur_cepat = total_qty <= BATAS_QTY_DIREKTUR

    catatan_marketing        = fkp.catatan_admin or "-"
    catatan_msm_investigasi  = fkp.catatan_rsm_investigasi or "-"
    catatan_msm_final        = fkp.catatan_rsm_resolusi or "-"
    label_catatan_msm_final  = (
        "Catatan MSM (Persetujuan Akhir)" if is_jalur_cepat else "Catatan MSM (Resolusi)"
    )

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
        },
        "outlet":               outlet_ctx,
        "distributor":          distributor_ctx,
        "items":                enriched_items,
        "submitted_by_name":    submitted_by_name,
        "apsm_name":            apsm_name,
        "marketing_name":       marketing_name,
        "direktur_name":        direktur_name,
        "rsm_final_name":       rsm_final_name,
        "catatan_marketing":        catatan_marketing,
        "catatan_msm_investigasi":  catatan_msm_investigasi,
        "catatan_msm_final":        catatan_msm_final,
        "label_catatan_msm_final":  label_catatan_msm_final,
        "logo_base64":          load_logo_base64(),
        "qr_code_base64":       qr_code_base64,
        "generated_at":         datetime.now(timezone.utc),
        "fkp_kode_tracking":    fkp_kode_tracking,
        "is_jalur_cepat":       is_jalur_cepat,
    }


# ─── Render & Generate ────────────────────────────────────────────────────────

def render_fkp_html(context: Dict) -> str:
    env = build_jinja_env(TEMPLATES_DIR)
    return env.get_template(TEMPLATE_NAME).render(**context)


def generate_fkp_pdf_from_context(context: Dict) -> bytes:
    return render_html_to_pdf(render_fkp_html(context))


async def _get_kode_tracking_fkp(db, fkp) -> str:
    """
    Format: FKP{DDMMYY}{urutan 3 digit} — TANPA underscore (dikonfirmasi).
    Urutan dihitung dari jumlah FKP lain dengan tanggal_pengajuan yang
    sama, yang created_at-nya lebih dulu atau sama dengan FKP ini.
    """
    from sqlmodel import select as sql_select
    from app.models.fkp import FkpComplaint

    result = await db.execute(
        sql_select(func.count()).select_from(FkpComplaint).where(
            FkpComplaint.tanggal_pengajuan == fkp.tanggal_pengajuan,
            FkpComplaint.created_at <= fkp.created_at,
        )
    )
    urutan = result.scalar_one()
    tanggal_str = fkp.tanggal_pengajuan.strftime("%d%m%y")
    return f"FKP{tanggal_str}{urutan:03d}"


async def _get_tanggal_diterima_qc(db, fkp) -> Optional[datetime]:
    """
    BARU (poin 2) — "Tanggal Diterima QC" diturunkan dari FkpStatusLog,
    BUKAN kolom tersendiri di FkpComplaint. Titik transisi yang dipakai
    beda tergantung jalur FKP (mutually exclusive, satu FKP hanya akan
    match salah satu dari dua kondisi berikut):

      - Jalur biasa (qty > BATAS_QTY_DIREKTUR): transisi ke
        'in_investigation' — saat RSM approve investigasi dan produk
        resmi mulai diinvestigasi QC.
      - Jalur cepat (qty ≤ BATAS_QTY_DIREKTUR): TIDAK PERNAH ada transisi
        ke 'in_investigation' (lihat qc_catatan_investigasi_paralel() —
        QC bekerja paralel, non-blocking). Titik ekuivalennya adalah
        transisi ke 'rsm_approval_final' — yaitu saat Admin HO meneruskan
        FKP ke RSM untuk persetujuan akhir, yang juga menjadi titik QC
        bisa mulai bekerja secara paralel.

    Ambil log PALING AWAL di antara dua kandidat status_baru tersebut
    (harusnya cuma salah satu yang match, tapi pakai MIN untuk aman kalau
    suatu saat ada data historis yang tidak terduga).
    """
    from sqlmodel import select as sql_select
    from app.models.fkp import FkpStatusLog, FkpStatus

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
    Tidak ada kolom khusus di FkpComplaint untuk siapa yang melakukan
    APSM review — satu-satunya jejaknya ada di FkpStatusLog.changed_by
    pada baris transisi ke status 'apsm_reviewed'.
    """
    from sqlmodel import select as sql_select
    from app.models.fkp import FkpStatusLog, FkpStatus

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
    apsm_name         = await _get_apsm_reviewer_name(db, fkp)
    marketing_name    = await get_user_nama(db, fkp.handled_by)
    # get_user_nama mengembalikan "" untuk None, konsisten pola yang sudah ada).
    direktur_name  = await get_user_nama(db, fkp.approved_by_direktur)
    rsm_final_name = await get_user_nama(db, fkp.approved_by_rsm_final)

    # ── Tanggal diterima QC (BARU, poin 2) ─────────────────────────────────
    tanggal_diterima_qc = await _get_tanggal_diterima_qc(db, fkp)

    # ── Build context & render ────────────────────────────────────────────────
    kode_tracking = await _get_kode_tracking_fkp(db, fkp)

    context = build_fkp_context(
        fkp                  = fkp,
        outlet               = outlet,
        distributor          = distributor,
        items                = list(items),
        attachments          = list(attachments),
        submitted_by_name    = submitted_by_name,
        apsm_name            = apsm_name,
        marketing_name       = marketing_name,
        direktur_name        = direktur_name,
        rsm_final_name       = rsm_final_name,
        upload_dir           = upload_dir,
        base_url             = settings.FRONTEND_BASE_URL,
        fkp_kode_tracking    = kode_tracking,
        tanggal_diterima_qc  = tanggal_diterima_qc,
    )

    return generate_fkp_pdf_from_context(context), fkp.nomor_fkp
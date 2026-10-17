"""
FKP Service — state machine engine.

── ALUR STATUS ────────────────────────────────────────────────────────────

  draft
    → submitted                   (distributor/outlet/sc_spv/apsm)
    → apsm_reviewed               (apsm)
    → [admin_ho_review()]         (admin_ho — percabangan jalur, lihat bawah)

  JALUR PCS — semua item FKP berkemasan pcs (FkpComplaint.jalur = pcs)
    submitted → pcs_ditangani_apsm (otomatis di submit_fkp()) → closed | rejected
      - Ditangani langsung APSM area (permission fkp.pcs.handle). Tanpa Admin HO,
        RSM, QC, Direktur. pcs tidak boleh bercampur dengan zak/ball/karton.
      - Tahap (pcs_tahap): dalam_pengajuan → dalam_proses → selesai. Hanya maju;
        'selesai' menutup FKP (CLOSED). Lihat apsm_update_tahap_pcs().
      - Reject hanya oleh APSM dan hanya selama pcs_tahap masih kosong
        (terminal, tanpa revisi; user input FKP baru).

  JALUR APPROVAL RSM (jalur = approval_rsm) — total qty klaim saat pengajuan ≤ BATAS_QTY_DIREKTUR
    apsm_reviewed → rsm_approval_final → accepted
      - Admin HO membuat resolusi (buat_resolusi() Fase 1) SAAT status masih
        rsm_approval_final; rsm_approve_final() menolak approve kalau resolusi
        belum ada.
      - RSM adalah approval terakhir. Direktur TIDAK PERNAH dilibatkan.
      - QC investigasi PARALEL (qc_catatan_investigasi_paralel()), tidak
        menahan status.

  JALUR APPROVAL DIREKTUR — total qty klaim saat pengajuan > BATAS_QTY_DIREKTUR
    apsm_reviewed → rsm_approval_investigasi → in_investigation
      → investigated → rsm_approval_resolusi → direktur_approval → accepted
      - Direktur WAJIB approve untuk SEMUA tipe_resolusi (tukar_barang,
        potong_tagihan). Tidak ada cabang
        skip Direktur di jalur ini.

  SETELAH accepted (kedua jalur):
    accepted → in_process   (trigger sesuai tipe_resolusi, BUKAN buat_resolusi()):
                              tukar_barang              → create_surat_jalan()  (modul Warehouse)
                              potong_tagihan            → terbitkan_invoice()
    in_process → closed     (close_fkp())

  Status terminal: rejected, closed.

    Mundur (request_revision(), tujuan dari REVISION_TARGETS):
      submitted                → need_revision   (apsm)
      apsm_reviewed            → submitted       (apsm / admin_ho / superadmin)
      rsm_approval_investigasi → apsm_reviewed   (rsm / admin_ho / superadmin)
      rsm_approval_final       → apsm_reviewed   (rsm / admin_ho / superadmin)
      rsm_approval_resolusi    → investigated    (rsm / admin_ho / superadmin)
    need_revision → submitted lewat submit_fkp() oleh pembuat FKP.

── PENENTUAN JALUR & KETERLIBATAN DIREKTUR ────────────────────────────────
SATU aturan, satu sumber angka:
  total qty klaim saat pengajuan = SUM(FkpItem.qty) seluruh item FKP, hanya
  kemasan di KEMASAN_DIHITUNG_JALUR (zak/ball/karton; pcs tidak ikut
  dihitung: FKP pcs-only masuk jalur pcs di submit_fkp(), bukan di sini), dihitung oleh _hitung_total_qty_jalur().

  - Jalur ditentukan SEKALI di admin_ho_review() lewat angka itu.
  - Direktur terlibat ⇔ FKP berada di jalur approval Direktur. Tidak ada pengecekan
    qty lagi di RSM/Direktur — status FKP itu sendiri yang membawa keputusan.
  - Yang TIDAK mempengaruhi jalur/Direktur: qty_disetujui (acc Admin HO),
    tipe_resolusi, dan persentase persetujuan (APSM/QC/kompensasi).

── RBAC dinamis ───────────────────────────────────────────────────────────
Permission per role TIDAK hardcode sebagai dict Python di sini.
Dua lapis akses, jangan dicampur:
  1. Action/Feature Permission → tabel `permissions` + `role_permissions`,
     dicek lewat require_permission(). Bisa diatur lewat dashboard admin.
  2. Data Scope / Row-level & Ownership → TETAP di kode (fungsi list_fkp,
     list_fkp_penerbitan, get_fkp_detail, validate_fkp_formulir_access,
     _check_apsm_area_scope() dan _check_ownership() untuk WRITE). Tidak
     masuk dashboard karena butuh JOIN/perbandingan data, bukan sekadar
     boolean role.

VALID_TRANSITIONS dan REVISION_TARGETS tetap hardcode — itu business
workflow (urutan status), bukan soal "siapa boleh apa".

── CATATAN KEAMANAN ───────────────────────────────────────────────────────
  - REVISION_TARGETS memuat (APSM_REVIEWED, "admin_ho") -> SUBMITTED supaya
    admin_ho punya jalur mengembalikan FKP saat status masih apsm_reviewed.
  - apsm_review() memanggil _check_apsm_area_scope() — apsm hanya boleh
    mereview FKP distributor di area-nya sendiri (selain permission
    "fkp.apsm_review").

── STATUS ITEM ────────────────────────────────────────────────────────────
status_item per item TIDAK diisi QC. QC hanya mengisi persentase_disetujui_qc
(rekomendasi/insight). Status resmi berubah di dua titik:
  - qty_disetujui = 0 (resolusi tukar_barang, diisi Admin HO di buat_resolusi())
    → 'ditolak' LANGSUNG saat itu juga (alasan_penolakan diisi). Item yang
    dikoreksi kembali ke qty > 0 dibuka lagi: 'pending', atau 'diterima' bila
    FKP sudah melewati approval final. Lihat _validasi_dan_simpan_qty_disetujui().
  - Item yang masih 'pending' ditandai 'diterima' otomatis di titik approval
    TERAKHIR yang menyetujui FKP: rsm_approve_final() (jalur approval RSM) atau
    direktur_approve() (jalur approval Direktur); lihat
    _tandai_item_diterima_setelah_approval_final(). Item 'ditolak' tidak ditimpa.
"""
import uuid
from datetime import datetime, timezone, date, time, timedelta
from decimal import Decimal
from typing import Optional

import logging

from fastapi import HTTPException
from sqlmodel import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import set_committed_value

from app.services.authz_helpers import is_superadmin

from app.models.fkp import (
    BATAS_QTY_DIREKTUR, KEMASAN_DIHITUNG_JALUR, KEMASAN_PCS,
    JalurFkp, TahapPcs, FkpPrioritas,
    FkpComplaint, FkpItem, FkpStatus,
    FkpStatusLog, FkpResolution, FkpAttachment,
    FkpDocument,
    TipeResolusi, MetodePenangananFisik, TipeDokumen, StatusItem,
    AdaSampleKeluhan, KondisiSample,
)

from app.models.product import ProductCatalog
from app.services.product_service import get_kemasan

from app.models.distributor import Distributor, DistributorUser
from app.models.outlet import Outlet
from app.models.sc_spv import ScSpvDistributor
from app.models.user import User
from app.schemas.fkp import (
    FkpCreate, FkpUpdate,
    FkpItemUpdate,
    ApsmReviewRequest, AdminHoReviewRequest,
    RsmApproveRequest, DirekturApproveRequest,
    InvestigasiQcRequest, RejectRequest, RevisionRequest,
    PcsTahapRequest,
)
from app.utils.fkp_number import generate_nomor_fkp
from app.services.notification_service import (
    kirim_notifikasi_transisi, kirim_notifikasi_qc_paralel, kirim_notifikasi_pcs_tahap,
)
from app.services.email_trigger_service import trigger_email_after_transition
from app.services.permission_service import require_permission
from app.services.authz_helpers import get_apsm_distributor_ids

# Zona waktu bisnis (Asia/Jakarta, tanpa DST). tanggal_pengajuan disimpan UTC (timezone-aware),
# jadi filter tanggal dari pengguna harus dibaca sebagai hari kalender WIB.
WIB = timezone(timedelta(hours=7))

logger = logging.getLogger(__name__)

# Kelompok kemasan satu FKP (hasil _tolak_jika_campur)
KELOMPOK_PCS     = "pcs"
KELOMPOK_NON_PCS = "non_pcs"

LABEL_TAHAP_PCS = {
    TahapPcs.DALAM_PENGAJUAN: "Dalam proses pengajuan",
    TahapPcs.DALAM_PROSES:    "Dalam proses",
    TahapPcs.SELESAI:         "Selesai (close)",
}

# ─── DATA SCOPE (Lapis 2) — TETAP DI KODE, TIDAK MASUK DASHBOARD ─────────────
# Dipakai oleh list_fkp, list_fkp_penerbitan, get_fkp_detail,
# validate_fkp_formulir_access — scope baca hierarki ini terpisah dari RBAC
# action permission, jangan dicampur.
# "warehouse" termasuk data-scope GLOBAL (single entity 1 HO, tidak dibatasi
# per lokasi gudang) sehingga list_fkp()/list_fkp_penerbitan()/
# validate_fkp_formulir_access() konsisten untuk role ini.
_ROLE_GLOBAL_ACCESS = {"admin_ho", "qc", "rsm", "direktur", "superadmin", "warehouse"}
# Keputusan "RSM = global" sudah diresmikan di authz_helpers.py
# (GLOBAL_ACCESS_ROLES, Kategori E audit RBAC Juni 2026). Duplikasi
# konstanta ini disengaja, tapi keputusannya HARUS tetap sinkron —
# kalau salah satu diubah, ubah juga yang lain.

# Role yang secara hierarki punya scope BACA lebih luas (lihat list_fkp dst),
# tapi untuk WRITE/EDIT hanya boleh terhadap FKP yang mereka buat sendiri
# (FkpComplaint.submitted_by == user.id). admin_ho, finance, rsm, direktur,
# qc, superadmin TIDAK kena batasan ini — mereka memang punya wewenang
# proses lintas-pembuat sesuai alur kerja.
OWNERSHIP_SCOPED_ROLES = {"outlet", "distributor", "sc_spv", "apsm"}

# Tipe attachment yang dihitung sebagai "foto bukti" saat submit_fkp(). Hanya foto
# fase pengajuan; foto fase lain (investigasi QC, serah terima, pemusnahan, kondisi
# sample masuk) dan dokumen/BA tidak boleh memenuhi syarat ini.
TIPE_FOTO_BUKTI_PENGAJUAN = (
    TipeDokumen.FOTO_KELUHAN,
    TipeDokumen.FOTO_SAMPLE,
    TipeDokumen.FOTO_EXPIRED,
    TipeDokumen.FOTO_KODE_PRODUKSI,
)

# Status di mana QC boleh mengisi catatan investigasi paralel (jalur approval RSM).
# Whitelist, bukan blacklist: status baru di masa depan tidak otomatis lolos.
STATUS_QC_PARALEL = (
    FkpStatus.RSM_APPROVAL_FINAL,
    FkpStatus.ACCEPTED,
    FkpStatus.IN_PROCESS,
)


# ─── STATE MACHINE ────────────────────────────────────────────────────────────

VALID_TRANSITIONS = {
    FkpStatus.DRAFT:                    [FkpStatus.SUBMITTED],
    FkpStatus.SUBMITTED:                [
        FkpStatus.APSM_REVIEWED,
        FkpStatus.NEED_REVISION,
        FkpStatus.PCS_DITANGANI_APSM,        # otomatis dari submit_fkp() untuk FKP pcs-only
    ],
    FkpStatus.APSM_REVIEWED:            [
        FkpStatus.RSM_APPROVAL_INVESTIGASI,  # jalur approval Direktur — total qty klaim > BATAS_QTY_DIREKTUR
        FkpStatus.RSM_APPROVAL_FINAL,        # jalur approval RSM   — total qty klaim ≤ BATAS_QTY_DIREKTUR
        FkpStatus.NEED_REVISION,
        FkpStatus.REJECTED,
    ],
    # ── Jalur approval Direktur ─────────────────────────────────────────────────────
    FkpStatus.RSM_APPROVAL_INVESTIGASI: [
        FkpStatus.IN_INVESTIGATION,
        FkpStatus.NEED_REVISION,
        FkpStatus.APSM_REVIEWED,
        FkpStatus.REJECTED,
    ],
    FkpStatus.IN_INVESTIGATION:         [FkpStatus.INVESTIGATED],
    FkpStatus.INVESTIGATED:             [
        FkpStatus.RSM_APPROVAL_RESOLUSI,
        FkpStatus.REJECTED,
    ],
    # Jalur approval Direktur SELALU lanjut ke Direktur (tidak ada skip ke ACCEPTED).
    # INVESTIGATED = mundur untuk revisi (lihat REVISION_TARGETS).
    FkpStatus.RSM_APPROVAL_RESOLUSI:    [
        FkpStatus.DIREKTUR_APPROVAL,
        FkpStatus.INVESTIGATED,
        FkpStatus.REJECTED,
    ],
    FkpStatus.DIREKTUR_APPROVAL:        [FkpStatus.ACCEPTED, FkpStatus.REJECTED],
    # ── Jalur approval RSM ───────────────────────────────────────────────────────
    # Resolusi SUDAH ADA saat RSM approve (dibuat Admin HO di status ini,
    # lihat rsm_approve_final()). APSM_REVIEWED = kembalikan untuk revisi,
    # simetris dengan RSM_APPROVAL_INVESTIGASI.
    FkpStatus.RSM_APPROVAL_FINAL:       [
        FkpStatus.ACCEPTED,
        FkpStatus.APSM_REVIEWED,
        FkpStatus.REJECTED,
    ],
    # ── Setelah accepted (kedua jalur) ────────────────────────────────────
    FkpStatus.ACCEPTED:                 [FkpStatus.IN_PROCESS],
    FkpStatus.IN_PROCESS:               [FkpStatus.CLOSED],
    FkpStatus.NEED_REVISION:            [FkpStatus.SUBMITTED],
    # ── Jalur pcs (ditangani langsung APSM) ───────────────────────────────
    FkpStatus.PCS_DITANGANI_APSM:       [
        FkpStatus.CLOSED,                # lewat apsm_update_tahap_pcs(tahap=selesai)
        FkpStatus.REJECTED,              # lewat reject_fkp(), hanya saat pcs_tahap kosong
    ],
    FkpStatus.REJECTED:                 [],
    FkpStatus.CLOSED:                   [],
}

# Mapping status tujuan -> permission code DEFAULT. Dipakai _validate_transition()
# bila pemanggil tidak memberi permission_code. VALID_TRANSITIONS (alur status)
# TETAP hardcode: itu business flow, BUKAN soal "siapa boleh apa".
#
# Aksi berikut MENIMPA permission lewat permission_code karena status tujuannya
# dipakai bersama aksi lain (dan wajib mengisi expected_status):
#   rsm_approve_final()       → "fkp.rsm_approve_final"
#   rsm_approve_investigasi() → "fkp.rsm_approve_investigasi"
#   rsm_approve_resolusi()    → "fkp.rsm_approve_resolusi"
#   direktur_approve()        → "fkp.direktur_approve"
# reject_fkp() tetap memakai "fkp.reject".
STATUS_TO_PERMISSION = {
    FkpStatus.SUBMITTED:                "fkp.submit",
    FkpStatus.APSM_REVIEWED:            "fkp.apsm_review",
    FkpStatus.RSM_APPROVAL_INVESTIGASI: "fkp.admin_ho_review",
    FkpStatus.RSM_APPROVAL_FINAL:       "fkp.admin_ho_review",  # aksi admin_ho yang sama, cuma target beda (lihat admin_ho_review)
    FkpStatus.IN_INVESTIGATION:         "fkp.rsm_approve_investigasi",
    FkpStatus.INVESTIGATED:             "fkp.qc_investigasi",
    FkpStatus.RSM_APPROVAL_RESOLUSI:    "fkp.admin_ho_request_resolusi_approval",
    FkpStatus.DIREKTUR_APPROVAL:        "fkp.rsm_approve_resolusi",
    FkpStatus.ACCEPTED:                 "fkp.direktur_approve",
    FkpStatus.IN_PROCESS:               "fkp.resolution.manage",
    FkpStatus.NEED_REVISION:            "fkp.request_revision",
    FkpStatus.REJECTED:                 "fkp.reject",
    FkpStatus.CLOSED:                   "fkp.close",
    # Jalur pcs: fallback saja. Transisi SUBMITTED -> PCS terjadi otomatis di submit_fkp()
    # (permission fkp.submit sudah dicek di sana). CLOSED/REJECTED di jalur pcs memakai
    # permission_code="fkp.pcs.handle" (override eksplisit).
    FkpStatus.PCS_DITANGANI_APSM:       "fkp.submit",
}

# Format: { (status_asal, kode_role): status_tujuan }
# Business logic mundur (request_revision) — TETAP hardcode, bukan permission.
REVISION_TARGETS = {
    # APSM meminta revisi saat FKP baru submitted
    (FkpStatus.SUBMITTED,                "apsm"):       FkpStatus.NEED_REVISION,

    # APSM melakukan review ulang terhadap FKP yang sudah direview
    (FkpStatus.APSM_REVIEWED,            "apsm"):       FkpStatus.SUBMITTED,

    # Admin HO / Superadmin meminta perbaikan dari tahap review APSM
    (FkpStatus.APSM_REVIEWED,            "admin_ho"):   FkpStatus.SUBMITTED,
    (FkpStatus.APSM_REVIEWED,            "superadmin"): FkpStatus.SUBMITTED,

    # RSM meminta revisi investigasi → kembali ke checkpoint APSM
    (FkpStatus.RSM_APPROVAL_INVESTIGASI, "rsm"):        FkpStatus.APSM_REVIEWED,

    # Admin HO / Superadmin meminta revisi investigasi
    (FkpStatus.RSM_APPROVAL_INVESTIGASI, "admin_ho"):   FkpStatus.APSM_REVIEWED,
    (FkpStatus.RSM_APPROVAL_INVESTIGASI, "superadmin"): FkpStatus.APSM_REVIEWED,

    # RSM meminta revisi final → kembali ke checkpoint APSM
    (FkpStatus.RSM_APPROVAL_FINAL,       "rsm"):        FkpStatus.APSM_REVIEWED,

    # Admin HO / Superadmin meminta revisi final
    (FkpStatus.RSM_APPROVAL_FINAL,       "admin_ho"):   FkpStatus.APSM_REVIEWED,
    (FkpStatus.RSM_APPROVAL_FINAL,       "superadmin"): FkpStatus.APSM_REVIEWED,

    # Revisi resolusi → kembali ke hasil investigasi
    (FkpStatus.RSM_APPROVAL_RESOLUSI,    "rsm"):        FkpStatus.INVESTIGATED,
    (FkpStatus.RSM_APPROVAL_RESOLUSI,    "admin_ho"):   FkpStatus.INVESTIGATED,
    (FkpStatus.RSM_APPROVAL_RESOLUSI,    "superadmin"): FkpStatus.INVESTIGATED,
}


# ─── HELPERS ──────────────────────────────────────────────────────────────────


def _tolak_jika_campur(daftar: list[tuple[str, str]]) -> Optional[str]:
    """
    daftar: [(nama_produk, jenis_kemasan)] untuk SEMUA item FKP (kemasan sudah final).
    Return KELOMPOK_PCS / KELOMPOK_NON_PCS, atau None bila daftar kosong.
    Raise 400 bila pcs bercampur dengan zak/ball/karton: penanganannya berbeda
    (FKP pcs ditangani langsung APSM, FKP zak/ball/karton lewat alur approval).
    """
    if not daftar:
        return None
    pcs = [(n, k) for n, k in daftar if k in KEMASAN_PCS]
    non = [(n, k) for n, k in daftar if k not in KEMASAN_PCS]
    if pcs and non:
        item_pcs = ", ".join(dict.fromkeys(n for n, _ in pcs))
        item_non = ", ".join(dict.fromkeys(f"{n} ({k})" for n, k in non))
        raise HTTPException(
            status_code=400,
            detail=(
                "Satu FKP tidak boleh memuat kemasan pcs bersamaan dengan zak/ball/karton, "
                "karena penanganannya berbeda: FKP pcs ditangani langsung oleh APSM, "
                "sedangkan FKP zak/ball/karton melalui alur approval Admin HO dan RSM. "
                f"Item pcs: {item_pcs}. Item zak/ball/karton: {item_non}. "
                "Pisahkan menjadi dua FKP: satu untuk item pcs dan satu untuk item zak/ball/karton."
            ),
        )
    return KELOMPOK_PCS if pcs else KELOMPOK_NON_PCS


async def _daftar_kemasan_item(fkp_id, db) -> list[tuple[str, str]]:
    """[(nama_produk, kemasan efektif)] item yang sudah ada di FKP.
    Kemasan efektif = snapshot item, fallback kolom katalog (sama dengan
    _hitung_total_qty_jalur), supaya item lama yang snapshot-nya NULL ikut terhitung."""
    kemasan_efektif = func.coalesce(FkpItem.jenis_kemasan, ProductCatalog.jenis_kemasan)
    r = await db.execute(
        select(ProductCatalog.nama_produk, kemasan_efektif)
        .select_from(FkpItem)
        .join(ProductCatalog, ProductCatalog.id == FkpItem.product_id)
        .where(FkpItem.fkp_id == fkp_id)
    )
    return [(nama, k) for nama, k in r.all() if k]


async def set_jenis_kemasan(item_dict: dict, db) -> str:
    """
    Tetapkan jenis_kemasan item FKP dari kemasan yang tersedia untuk produknya
    (get_kemasan). Nilai ini menentukan jalur approval
    (lihat _hitung_total_qty_jalur), jadi input user divalidasi:
      - 1 kemasan tersedia, input kosong → diisi otomatis
      - >1 kemasan, input kosong         → 400, minta user memilih
      - input di luar kemasan produk     → 400
      - produk belum punya kemasan       → 400
    Mengembalikan nama produk (dipakai _tolak_jika_campur untuk pesan error).
    """
    pid = item_dict["product_id"]
    r = await db.execute(
        select(ProductCatalog.nama_produk, ProductCatalog.is_active)
        .where(ProductCatalog.id == pid)
    )
    produk = r.first()
    if produk is None:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan di katalog.")
    nama, aktif = produk
    if not aktif:
        raise HTTPException(
            status_code=400,
            detail=f"Produk '{nama}' sudah nonaktif dan tidak dapat dipakai pada FKP. Pilih produk lain.",
        )

    tersedia = (await get_kemasan(db, [pid])).get(pid, [])
    pilihan = item_dict.get("jenis_kemasan")

    if not tersedia:
        raise HTTPException(status_code=400, detail="Kemasan produk ini belum diatur. Hubungi admin katalog.")
    if pilihan is None:
        if len(tersedia) == 1:
            item_dict["jenis_kemasan"] = tersedia[0]
            return nama
        raise HTTPException(status_code=400, detail=f"Pilih jenis_kemasan: {tersedia}.")
    if pilihan not in tersedia:
        raise HTTPException(
            status_code=400,
            detail=f"jenis_kemasan '{pilihan}' tidak tersedia untuk produk ini. Pilihan: {tersedia}.",
        )
    return nama
    
def _normalisasi_kondisi_sample(item: FkpItem) -> None:
    """
    Validasi silang kondisi_sample terhadap ada_sample_keluhan untuk jalur UPDATE
    (schema tidak bisa melakukannya karena update parsial). Mengosongkan kondisi
    bila sample tidak 'ada'.
    """
    if item.ada_sample_keluhan != AdaSampleKeluhan.ADA:
        item.kondisi_sample = None
        item.kondisi_sample_lainnya = None
        return
    if not item.kondisi_sample:
        raise HTTPException(400, "kondisi_sample wajib diisi jika ada_sample_keluhan = 'ada'.")
    if item.kondisi_sample == KondisiSample.LAINNYA:
        if not (item.kondisi_sample_lainnya or "").strip():
            raise HTTPException(400, "kondisi_sample_lainnya wajib diisi jika kondisi_sample = 'lainnya'.")
    else:
        item.kondisi_sample_lainnya = None

async def _validate_transition(fkp, new_status, kode_role, db, permission_code=None, expected_status=None):
    """
    Validasi transisi + permission aksi.
    expected_status: status asal yang WAJIB dipegang FKP untuk aksi ini. Wajib
    diisi untuk aksi yang status tujuannya dipakai aksi lain (ACCEPTED,
    REJECTED, APSM_REVIEWED), supaya aksi tidak bisa dipanggil di luar gilirannya.
    """
    if expected_status is not None and fkp.status != expected_status:
        raise HTTPException(
            status_code=400,
            detail=f"Aksi ini hanya untuk FKP berstatus '{expected_status}', status saat ini '{fkp.status}'.",
        )
    allowed_next = VALID_TRANSITIONS.get(fkp.status, [])
    if new_status not in allowed_next:
        raise HTTPException(
            status_code=400,
            detail=f"Transisi dari '{fkp.status}' ke '{new_status}' tidak diizinkan.",
        )
    permission_code = permission_code or STATUS_TO_PERMISSION.get(new_status)
    if permission_code:
        await require_permission(kode_role, permission_code, db)


def _check_ownership(fkp: "FkpComplaint", user: "User", kode_role: str) -> None:
    """
    Untuk role yang ownership-scoped: hanya boleh edit FKP yang dia buat sendiri,
    walau secara hierarki dia punya akses baca lebih luas.
    admin_ho, finance, rsm, direktur, qc, superadmin TIDAK kena batasan ini
    (mereka memang punya wewenang proses lintas-pembuat sesuai alur kerja).
    """
    if kode_role in OWNERSHIP_SCOPED_ROLES and fkp.submitted_by != user.id:
        raise HTTPException(
            status_code=403,
            detail="Anda hanya dapat mengubah FKP yang Anda buat sendiri.",
        )


async def _check_apsm_area_scope(fkp: "FkpComplaint", user: "User", kode_role: str, db: AsyncSession) -> None:
    """
    Data-scope untuk aksi tulis apsm_review(): apsm hanya boleh mereview FKP
    distributor dalam area-nya. Permission action ("fkp.apsm_review") saja
    tidak cukup karena tidak membatasi data — list_fkp/get_fkp_detail/
    create_fkp sudah membatasi apsm per-area, fungsi ini menyamakan hal itu
    untuk aksi tulis. Memakai resolver scope terpusat di authz_helpers (sama
    yang dipakai upload_service & outlet_register_service) supaya tidak ada
    logic scope APSM yang berbeda-beda di tempat lain.
    """
    if kode_role != "apsm":
        return
    dist_ids = await get_apsm_distributor_ids(user.id, db)
    if fkp.distributor_id not in dist_ids:
        raise HTTPException(
            status_code=403,
            detail="FKP ini di luar area yang Anda tangani.",
        )


def _wajib_catatan_tolak(disetujui: bool, catatan: Optional[str]) -> None:
    """Penolakan oleh RSM/Direktur wajib disertai alasan (konsisten dengan reject_fkp)."""
    if not disetujui and not (catatan or "").strip():
        raise HTTPException(status_code=400, detail="Catatan alasan penolakan wajib diisi.")


async def _log(db, fkp_id, status_lama, status_baru, changed_by, catatan=None):
    db.add(FkpStatusLog(
        fkp_id=fkp_id, status_lama=status_lama, status_baru=status_baru,
        catatan=catatan, changed_by=changed_by,
    ))


async def _get_or_404(fkp_id, db, for_update: bool = False) -> FkpComplaint:
    """for_update=True: kunci baris FKP sampai commit/rollback, supaya dua aksi
    bersamaan pada FKP yang sama berjalan bergiliran (bukan saling menimpa status)."""
    query = select(FkpComplaint).where(FkpComplaint.id == fkp_id)
    if for_update:
        query = query.with_for_update().execution_options(populate_existing=True)
    r = await db.execute(query)
    fkp = r.scalar_one_or_none()
    if not fkp:
        raise HTTPException(status_code=404, detail="FKP tidak ditemukan.")
    return fkp


async def _load_fkp_detail(fkp_id, db) -> FkpComplaint:
    """Load FKP beserta semua relationships (eager load)."""
    r = await db.execute(
        select(FkpComplaint)
        .where(FkpComplaint.id == fkp_id)
        .options(
            selectinload(FkpComplaint.items),
            selectinload(FkpComplaint.distributor).selectinload(Distributor.area),
            selectinload(FkpComplaint.outlet),
            selectinload(FkpComplaint.status_logs),
            selectinload(FkpComplaint.resolution),
            selectinload(FkpComplaint.attachments),
            selectinload(FkpComplaint.documents),
        )
    )
    return r.scalar_one()


async def _hitung_total_qty_jalur(fkp_id, db) -> int:
    """
    Total qty klaim untuk penentuan jalur approval (approval_rsm vs
    approval_direktur), yang sekaligus menentukan keterlibatan Direktur —
    lihat docstring modul.

    - Basis SELALU qty saat pengajuan (FkpItem.qty), BUKAN qty_disetujui.
    - Hanya kemasan di KEMASAN_DIHITUNG_JALUR (zak/ball/karton) yang dihitung.
    - Kemasan efektif = FkpItem.jenis_kemasan, fallback ke
      ProductCatalog.jenis_kemasan bila null.
    - FKP pcs-only TIDAK pernah sampai ke sini: submit_fkp() sudah
      mengarahkannya ke jalur pcs (ditangani APSM) sebelum admin_ho_review().
      Total 0 hanya bisa muncul pada data lama/anomali, dan hasilnya jalur
      approval RSM.

    Dipanggil oleh admin_ho_review() (menentukan jalur) dan
    qc_catatan_investigasi_paralel() (guard jalur approval RSM). Jangan buat
    penghitungan qty kedua di tempat lain — satu helper, satu definisi.
    """
    kemasan_efektif = func.coalesce(
        FkpItem.jenis_kemasan, ProductCatalog.jenis_kemasan
    )
    r = await db.execute(
        select(func.coalesce(func.sum(FkpItem.qty), 0))
        .select_from(FkpItem)
        .join(ProductCatalog, ProductCatalog.id == FkpItem.product_id)
        .where(
            FkpItem.fkp_id == fkp_id,
            kemasan_efektif.in_(KEMASAN_DIHITUNG_JALUR),
        )
    )
    return int(r.scalar() or 0)


async def buat_dokumen(fkp_id: uuid.UUID, data, user, kode_role: str, db):
    """Admin HO (atau superadmin via bypass) menambahkan dokumen formal ke FKP."""
    await require_permission(kode_role, "fkp.document.create", db)

    fkp = await _get_or_404(fkp_id, db)
    if fkp.status in FkpStatus.TERMINAL:
        raise HTTPException(
            status_code=400,
            detail=f"Dokumen tidak bisa ditambah ke FKP dengan status '{fkp.status}'.",
        )

    dokumen = FkpDocument(
        fkp_id=fkp_id,
        dibuat_oleh=user.id,
        **data.model_dump(exclude_none=True),
    )
    db.add(dokumen)
    await db.commit()
    await db.refresh(dokumen)
    return dokumen


async def hapus_dokumen(fkp_id: uuid.UUID, dokumen_id: uuid.UUID, user, kode_role: str, db):
    """
    Hapus dokumen — hanya oleh pembuatnya atau superadmin.
    Ownership check ini bukan permission RBAC biasa (pembuat dokumen tidak
    ditentukan oleh role).

    KEPUTUSAN (Kategori D audit RBAC, opsi 1): kode permission
    "fkp.document.delete" SENGAJA tidak ada di seeds/seed_permissions.py.
    Karena fkp.document.create hanya diberikan ke admin_ho, dokumen FKP
    secara praktis hanya pernah dibuat oleh admin_ho — lapis role di atas
    ownership tidak menambah keamanan riil, hanya kompleksitas. Jangan
    panggil require_permission() di sini kecuali keputusan ini dibalik
    secara sadar (lihat juga catatan di seed_permissions.py).
    """
    r = await db.execute(
        select(FkpDocument).where(
            FkpDocument.id == dokumen_id,
            FkpDocument.fkp_id == fkp_id,
        )
    )
    
    dokumen = r.scalar_one_or_none()
    if not dokumen:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan.")

    is_super = await is_superadmin(user, db)  # dicek setelah dokumen confirmed ada
    if not is_super and dokumen.dibuat_oleh != user.id:
        raise HTTPException(status_code=403, detail="Hanya pembuat dokumen atau superadmin yang bisa menghapus.")

    await db.delete(dokumen)
    await db.commit()
    return {"detail": "Dokumen berhasil dihapus."}

async def _validasi_konsistensi_rekomendasi(fkp_id, tipe_resolusi_baru, db):
    """
    Pastikan semua item yang sudah punya rekomendasi kompensasi
    konsisten dengan tipe_resolusi yang dipilih Admin HO.
    Jika tidak konsisten → tolak dengan pesan jelas.

    Sumber rekomendasi = rekomendasi_kompensasi_apsm. Admin HO tidak lagi
    mengisi rekomendasi per item (murni meneruskan ke RSM), jadi kolom
    rekomendasi_kompensasi_admin_ho tidak dipakai di sini.
    """

    if not tipe_resolusi_baru:
        return

    MAPPING = {
        "ganti_barang":       TipeResolusi.TUKAR_BARANG,
        "potong_tagihan":     TipeResolusi.POTONG_TAGIHAN,
    }

    r = await db.execute(select(FkpItem).where(FkpItem.fkp_id == fkp_id))
    items = r.scalars().all()

    tipe_dari_rekomendasi = {
        MAPPING[i.rekomendasi_kompensasi_apsm]
        for i in items
        if i.rekomendasi_kompensasi_apsm in MAPPING
    }

    # Lebih dari 1 tipe → item tidak konsisten satu sama lain
    if len(tipe_dari_rekomendasi) > 1:
        raise HTTPException(
            status_code=400,
            detail=(
                "Item-item dalam FKP memiliki rekomendasi kompensasi yang tidak konsisten. "
                "Pisahkan ke FKP terpisah sesuai tipe kompensasi masing-masing."
            )
        )

    # Tipe resolusi yang dipilih tidak sesuai rekomendasi mayoritas item
    if tipe_dari_rekomendasi and tipe_resolusi_baru not in tipe_dari_rekomendasi:
        rekomendasi_ada = list(tipe_dari_rekomendasi)[0]
        raise HTTPException(
            status_code=400,
            detail=(
                f"Tipe resolusi '{tipe_resolusi_baru}' tidak sesuai dengan rekomendasi item "
                f"('{rekomendasi_ada}'). Sesuaikan tipe resolusi atau ubah rekomendasi item."
            )
        )


async def _validasi_dan_simpan_qty_disetujui(fkp_id, item_qty_list, db, sudah_approval_final: bool = False):
    """
    Simpan qty_disetujui per item (khusus resolusi tukar_barang) sekaligus
    memutuskan item yang DITOLAK.

    item_qty_list terisi → validasi lalu simpan (qty_disetujui tidak boleh
    melebihi FkpItem.qty):
      - qty_disetujui = 0 → status_item 'ditolak' langsung saat itu juga,
        alasan_penolakan diisi dari ItemQtyDisetujui.
      - qty_disetujui > 0 → qty tersimpan; status_item TIDAK dijadikan
        'diterima' di sini — item 'pending' tetap pending sampai approval
        terakhir (_tandai_item_diterima_setelah_approval_final()). Item yang
        sebelumnya 'ditolak' dibuka lagi: 'diterima' bila
        sudah_approval_final=True (koreksi Fase 2 saat FKP accepted), selain
        itu 'pending'.

    item_qty_list kosong → validasi-saja (dipakai teruskan_ke_warehouse() dan
    Fase 2 buat_resolusi()): semua item berstatus 'diterima' wajib sudah
    punya qty_disetujui.
    """
    if not item_qty_list:
        # Cek apakah ada item diterima yang belum punya qty_disetujui
        r = await db.execute(select(FkpItem).where(
            FkpItem.fkp_id == fkp_id,
            FkpItem.status_item == "diterima",
        ))
        items_diterima = r.scalars().all()
        belum_diisi = [str(i.id) for i in items_diterima if i.qty_disetujui is None]
        if belum_diisi:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"item_qty_disetujui wajib diisi untuk resolusi tukar_barang. "
                    f"Item berstatus 'diterima' yang belum diisi: {belum_diisi}"
                )
            )
        return

    for item_qty in item_qty_list:
        r = await db.execute(select(FkpItem).where(
            FkpItem.id == item_qty.item_id,
            FkpItem.fkp_id == fkp_id,
        ))
        item = r.scalar_one_or_none()
        if not item:
            raise HTTPException(
                status_code=404,
                detail=f"Item {item_qty.item_id} tidak ditemukan dalam FKP ini."
            )
        if item_qty.qty_disetujui > item.qty:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"qty_disetujui ({item_qty.qty_disetujui}) tidak boleh melebihi "
                    f"qty awal ({item.qty}) pada item {item_qty.item_id}."
                )
            )
        item.qty_disetujui = item_qty.qty_disetujui
        if item_qty.qty_disetujui == 0:
            item.status_item = StatusItem.DITOLAK
            item.alasan_penolakan = item_qty.alasan_penolakan
        elif item.status_item == StatusItem.DITOLAK:
            # dibuka kembali lewat koreksi
            item.status_item = (
                StatusItem.DITERIMA if sudah_approval_final else StatusItem.PENDING
            )
            item.alasan_penolakan = None
        item.updated_at = datetime.now(timezone.utc)
        db.add(item)


async def _tandai_item_diterima_setelah_approval_final(fkp_id, db):
    """
    Dipanggil dari approval TERAKHIR yang menyetujui FKP (disetujui=True):
      - jalur approval RSM       → rsm_approve_final()
      - jalur approval Direktur  → direktur_approve()
    rsm_approve_resolusi() BUKAN pemanggil — di jalur approval Direktur, RSM
    bukan approval terakhir.

    Item yang masih 'pending' ditandai 'diterima'. Item yang sudah 'ditolak'
    (qty_disetujui = 0 lewat buat_resolusi(), lihat
    _validasi_dan_simpan_qty_disetujui()) TIDAK ditimpa. Status resmi item
    mengikuti keputusan Admin HO dan approval, bukan rekomendasi QC
    (persentase_disetujui_qc hanya insight).
    """
    r = await db.execute(select(FkpItem).where(
        FkpItem.fkp_id == fkp_id,
        FkpItem.status_item == StatusItem.PENDING,
    ))
    items = r.scalars().all()
    for item in items:
        item.status_item = StatusItem.DITERIMA
        item.updated_at = datetime.now(timezone.utc)
        db.add(item)


async def list_fkp(
    db, user, kode_role,
    status_filter=None, prioritas_filter=None, jalur_filter=None,
    outlet_id=None, distributor_id=None, area_id=None,
    tanggal_dari=None, tanggal_sampai=None,
    eager_full: bool = False,
):
    """
    Daftar FKP, difilter data-scope role (Lapis 2) lalu filter opsional.

    Scope role: outlet/distributor/sc_spv/apsm → FKP dalam cakupannya; finance →
    FKP potong_tagihan pada status FkpStatus.FINANCE_VISIBLE; role global →
    semua FKP; role lain → daftar kosong.

    Filter opsional: status, prioritas (deprecated), jalur (pcs | approval_rsm |
    approval_direktur), outlet_id, distributor_id, area_id, serta tanggal_dari /
    tanggal_sampai (date atau 'YYYY-MM-DD', dibaca sebagai hari kalender WIB
    terhadap FkpComplaint.created_at, kedua batas inklusif).

    eager_full=True memuat semua relasi yang dibutuhkan export Excel (items +
    product, resolution, status_logs, warehouse_surat_jalan, sample_shipments,
    distributor + area, outlet) lewat selectinload — tanpa N+1. Dipakai
    export_service.export_fkp_excel().
    """
    query = select(FkpComplaint)

    if kode_role == "outlet":
        r = await db.execute(select(Outlet).where(Outlet.pic_user_id == user.id))
        outlet_ids = [o.id for o in r.scalars().all()]
        if not outlet_ids:
            return []
        query = query.where(FkpComplaint.outlet_id.in_(outlet_ids))

    elif kode_role == "distributor":
        r = await db.execute(select(DistributorUser).where(DistributorUser.user_id == user.id))
        dist_ids = [du.distributor_id for du in r.scalars().all()]
        if not dist_ids:
            return []
        query = query.where(FkpComplaint.distributor_id.in_(dist_ids))

    elif kode_role == "sc_spv":
        r = await db.execute(select(ScSpvDistributor).where(ScSpvDistributor.sc_spv_user_id == user.id))
        dist_ids = [sd.distributor_id for sd in r.scalars().all()]
        if not dist_ids:
            return []
        query = query.where(FkpComplaint.distributor_id.in_(dist_ids))

    elif kode_role == "apsm":
        from app.models.area import Area
        r = await db.execute(select(Area).where(Area.pic_user_id == user.id))
        area_ids = [a.id for a in r.scalars().all()]
        if not area_ids:
            return []
        r2 = await db.execute(select(Distributor).where(Distributor.area_id.in_(area_ids)))
        dist_ids = [d.id for d in r2.scalars().all()]
        if not dist_ids:
            return []
        query = query.where(FkpComplaint.distributor_id.in_(dist_ids))

    elif kode_role == "finance":
        if status_filter and status_filter not in FkpStatus.FINANCE_VISIBLE:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Finance hanya bisa memfilter status: {FkpStatus.FINANCE_VISIBLE}. "
                    f"Status '{status_filter}' tidak relevan dengan role finance."
                ),
            )
        query = query.where(*_finance_scope_conditions())

    elif kode_role not in _ROLE_GLOBAL_ACCESS:
        return []

    if status_filter:
        query = query.where(FkpComplaint.status == status_filter)
    if prioritas_filter:
        query = query.where(FkpComplaint.prioritas == prioritas_filter)
    if jalur_filter:
        if jalur_filter not in JalurFkp.ALL:
            raise HTTPException(status_code=400, detail=f"jalur harus salah satu dari: {', '.join(JalurFkp.ALL)}.")
        query = query.where(FkpComplaint.jalur == jalur_filter)
    if outlet_id:
        query = query.where(FkpComplaint.outlet_id == outlet_id)
    if distributor_id:
        query = query.where(FkpComplaint.distributor_id == distributor_id)
    if area_id:
        query = query.where(
            FkpComplaint.distributor_id.in_(
                select(Distributor.id).where(Distributor.area_id == area_id)
            )
        )

    def _ke_tanggal(nilai, nama):
        if nilai is None or nilai == "":
            return None
        if isinstance(nilai, datetime):
            return nilai.date()
        if isinstance(nilai, date):
            return nilai
        try:
            return date.fromisoformat(str(nilai))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Format {nama} tidak valid (YYYY-MM-DD).")

    dari = _ke_tanggal(tanggal_dari, "tanggal_dari")
    sampai = _ke_tanggal(tanggal_sampai, "tanggal_sampai")
    if dari and sampai and dari > sampai:
        raise HTTPException(status_code=400, detail="tanggal_dari tidak boleh lebih besar dari tanggal_sampai.")
    if dari:
        query = query.where(FkpComplaint.created_at >= datetime.combine(dari, time.min, tzinfo=WIB))
    if sampai:
        # batas atas eksklusif = awal hari berikutnya (WIB), supaya seluruh hari 'sampai' ikut
        query = query.where(
            FkpComplaint.created_at < datetime.combine(sampai + timedelta(days=1), time.min, tzinfo=WIB)
        )

    if eager_full:
        options = [
            selectinload(FkpComplaint.items).selectinload(FkpItem.product),
            selectinload(FkpComplaint.resolution),
            selectinload(FkpComplaint.status_logs),
            selectinload(FkpComplaint.warehouse_surat_jalan),
            selectinload(FkpComplaint.sample_shipments),
            selectinload(FkpComplaint.distributor).selectinload(Distributor.area),
            selectinload(FkpComplaint.outlet),
        ]
    else:
        options = [
            selectinload(FkpComplaint.distributor),
            selectinload(FkpComplaint.outlet),
        ]

    result = await db.execute(
        query.options(*options).order_by(FkpComplaint.created_at.desc())
    )
    return result.scalars().all()

def _finance_scope_conditions():
    """
    SATU-SATUNYA definisi scope data finance (Lapis 2): FKP berresolusi
    potong_tagihan DAN status ada di FkpStatus.FINANCE_VISIBLE.
    Dipakai oleh list_fkp() dan list_fkp_penerbitan() sebagai filter query.
    Untuk cek satu FKP, pakai _finance_boleh_akses() (aturan yang sama).
    Subquery, bukan daftar fkp_ids yang dimuat ke memori.
    """
    return (
        FkpComplaint.id.in_(
            select(FkpResolution.fkp_id).where(
                FkpResolution.tipe_resolusi == TipeResolusi.POTONG_TAGIHAN
            )
        ),
        FkpComplaint.status.in_(list(FkpStatus.FINANCE_VISIBLE)),
    )

async def _finance_punya_resolusi_potong_tagihan(fkp_id, db) -> bool:
    r = await db.execute(
        select(FkpResolution.id).where(
            FkpResolution.fkp_id == fkp_id,
            FkpResolution.tipe_resolusi == TipeResolusi.POTONG_TAGIHAN,
        )
    )
    return r.first() is not None


async def _finance_boleh_akses(fkp, db) -> bool:
    if fkp.status not in FkpStatus.FINANCE_VISIBLE:
        return False
    return await _finance_punya_resolusi_potong_tagihan(fkp.id, db)


async def _assert_fkp_scope(fkp: "FkpComplaint", user: "User", kode_role: str, db: AsyncSession) -> None:
    """
    SATU-SATUNYA cek data-scope BACA untuk satu FKP (Lapis 2). Dipakai oleh
    get_fkp_detail() dan validate_fkp_formulir_access(). Raise 403 bila FKP di
    luar jangkauan role. Scope untuk query daftar (list_fkp, list_fkp_penerbitan)
    tetap terpisah karena memfilter banyak baris, bukan satu FKP.
    Scope TULIS: _check_ownership() dan _check_apsm_area_scope().
    """
    if kode_role in _ROLE_GLOBAL_ACCESS:
        return

    if kode_role == "outlet":
        q = select(Outlet.id).where(Outlet.pic_user_id == user.id, Outlet.id == fkp.outlet_id)
    elif kode_role == "distributor":
        q = select(DistributorUser.distributor_id).where(
            DistributorUser.user_id == user.id,
            DistributorUser.distributor_id == fkp.distributor_id,
        )
    elif kode_role == "sc_spv":
        q = select(ScSpvDistributor.distributor_id).where(
            ScSpvDistributor.sc_spv_user_id == user.id,
            ScSpvDistributor.distributor_id == fkp.distributor_id,
        )
    elif kode_role == "apsm":
        from app.models.area import Area
        # Single JOIN query — tidak ada N+1
        q = (
            select(Distributor.id)
            .join(Area, Distributor.area_id == Area.id)
            .where(Area.pic_user_id == user.id, Distributor.id == fkp.distributor_id)
        )
    elif kode_role == "finance":
        if not await _finance_boleh_akses(fkp, db):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Akses ditolak. Finance hanya bisa mengakses FKP dengan "
                    "resolusi potong_tagihan pada status yang relevan."
                ),
            )
        return
    else:
        raise HTTPException(status_code=403, detail="Akses ditolak.")

    if (await db.execute(q)).first() is None:
        raise HTTPException(status_code=403, detail="Akses ditolak.")


async def validate_fkp_formulir_access(
    fkp_id: uuid.UUID,
    user: User,
    kode_role: str,
    db: AsyncSession,
) -> FkpComplaint:
    """
    Validasi dua lapis:
    1. Status: FKP harus sudah melewati draft/need_revision
    2. Scope: user hanya bisa akses FKP yang dalam jangkauannya

    Return FkpComplaint jika lolos, raise HTTPException jika gagal.
    Menggunakan 1 query per lapisan — tidak ada N+1.
    """

    DOWNLOADABLE = {
        FkpStatus.SUBMITTED, FkpStatus.APSM_REVIEWED,
        FkpStatus.RSM_APPROVAL_INVESTIGASI, FkpStatus.IN_INVESTIGATION,
        FkpStatus.INVESTIGATED, FkpStatus.RSM_APPROVAL_RESOLUSI,
        FkpStatus.DIREKTUR_APPROVAL, FkpStatus.RSM_APPROVAL_FINAL, FkpStatus.ACCEPTED,
        FkpStatus.IN_PROCESS, FkpStatus.CLOSED, FkpStatus.REJECTED,
    }

    fkp = await _get_or_404(fkp_id, db)

    # Formulir PDF tidak berlaku untuk FKP pcs (template mengandaikan rantai approval
    # dan resolusi yang tidak ada di jalur pcs), termasuk yang sudah closed/rejected.
    if fkp.jalur == JalurFkp.PCS:
        raise HTTPException(
            status_code=422,
            detail="Formulir FKP tidak tersedia untuk FKP kemasan pcs (ditangani langsung oleh APSM).",
        )

    # ── Lapisan 1: cek status ─────────────────────────────────────────────
    if fkp.status not in DOWNLOADABLE:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Formulir FKP belum bisa didownload. "
                f"Status saat ini: '{fkp.status}'. "
                f"Submit FKP terlebih dahulu untuk dapat mencetak formulir."
            ),
        )

    # ── Lapisan 2: cek scope role ─────────────────────────────────────────
    await _assert_fkp_scope(fkp, user, kode_role, db)

    return fkp


async def list_fkp_penerbitan(
    db: AsyncSession,
    user: User,
    kode_role: str,
    status_filter: Optional[str] = None,
    tanggal_dari: Optional[str] = None,
    tanggal_sampai: Optional[str] = None,
):
    """
    List FKP untuk halaman penerbitan dokumen.
    Hanya FKP yang sudah di-submit (bukan draft/need_revision).
    Difilter scope per role — satu query utama, tidak ada N+1.
    """

    DOWNLOADABLE_STATUSES = [
        FkpStatus.SUBMITTED, FkpStatus.APSM_REVIEWED,
        FkpStatus.RSM_APPROVAL_INVESTIGASI, FkpStatus.IN_INVESTIGATION,
        FkpStatus.INVESTIGATED, FkpStatus.RSM_APPROVAL_RESOLUSI,
        FkpStatus.DIREKTUR_APPROVAL, FkpStatus.RSM_APPROVAL_FINAL, FkpStatus.ACCEPTED,
        FkpStatus.IN_PROCESS, FkpStatus.CLOSED, FkpStatus.REJECTED,
    ]

    query = (
        select(FkpComplaint)
        .options(
            selectinload(FkpComplaint.distributor),
            selectinload(FkpComplaint.outlet),
        )
        .where(FkpComplaint.status.in_(DOWNLOADABLE_STATUSES))
        .where(FkpComplaint.jalur.is_distinct_from(JalurFkp.PCS))
    )

    # ── Filter scope per role (single subquery masing-masing) ─────────────
    if kode_role not in _ROLE_GLOBAL_ACCESS:

        if kode_role == "outlet":
            # Ambil semua outlet_id milik user ini dalam 1 query
            r = await db.execute(
                select(Outlet.id).where(Outlet.pic_user_id == user.id)
            )
            outlet_ids = [row[0] for row in r.fetchall()]
            if not outlet_ids:
                return []
            query = query.where(FkpComplaint.outlet_id.in_(outlet_ids))

        elif kode_role == "distributor":
            r = await db.execute(
                select(DistributorUser.distributor_id)
                .where(DistributorUser.user_id == user.id)
            )
            dist_ids = [row[0] for row in r.fetchall()]
            if not dist_ids:
                return []
            query = query.where(FkpComplaint.distributor_id.in_(dist_ids))

        elif kode_role == "sc_spv":
            r = await db.execute(
                select(ScSpvDistributor.distributor_id)
                .where(ScSpvDistributor.sc_spv_user_id == user.id)
            )
            dist_ids = [row[0] for row in r.fetchall()]
            if not dist_ids:
                return []
            query = query.where(FkpComplaint.distributor_id.in_(dist_ids))

        elif kode_role == "apsm":
            from app.models.area import Area
            # JOIN Area → Distributor dalam 1 query
            r = await db.execute(
                select(Distributor.id)
                .join(Area, Distributor.area_id == Area.id)
                .where(Area.pic_user_id == user.id)
            )
            dist_ids = [row[0] for row in r.fetchall()]
            if not dist_ids:
                return []
            query = query.where(FkpComplaint.distributor_id.in_(dist_ids))

        elif kode_role == "finance":
            query = query.where(*_finance_scope_conditions())

        else:
            return []

    # ── Filter tambahan ────────────────────────────────────────────────────
    if status_filter:
        if status_filter not in DOWNLOADABLE_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Status '{status_filter}' tidak valid untuk halaman penerbitan."
            )
        if kode_role == "finance" and status_filter not in FkpStatus.FINANCE_VISIBLE:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Finance hanya bisa memfilter status: {FkpStatus.FINANCE_VISIBLE}. "
                    f"Status '{status_filter}' tidak relevan dengan role finance."
                ),
            )
        query = query.where(FkpComplaint.status == status_filter)

    if tanggal_dari:
        try:
            d = date.fromisoformat(tanggal_dari)
            query = query.where(FkpComplaint.tanggal_pengajuan >= datetime.combine(d, time.min, tzinfo=WIB))
        except ValueError:
            raise HTTPException(status_code=400, detail="Format tanggal_dari tidak valid (YYYY-MM-DD).")

    if tanggal_sampai:
        try:
            d = date.fromisoformat(tanggal_sampai)
            # sampai akhir hari tersebut (WIB): batas atas = awal hari berikutnya, eksklusif
            query = query.where(
                FkpComplaint.tanggal_pengajuan < datetime.combine(d + timedelta(days=1), time.min, tzinfo=WIB)
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Format tanggal_sampai tidak valid (YYYY-MM-DD).")

    query = query.order_by(FkpComplaint.tanggal_pengajuan.desc().nullslast(), FkpComplaint.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


# Role yang TIDAK BOLEH melihat dokumen hasil pemeriksaan QC. Konsisten
# dengan sample_service._sanitize_for_external() yang sudah menyaring field
# narasi `hasil_pemeriksaan` — helper di bawah ini menutup celah yang sama
# untuk FILE-nya (FkpAttachment tipe hasil_pemeriksaan_qc), yang kalau tidak
# disaring ikut terbawa apa adanya lewat _load_fkp_detail().
ROLE_HASIL_QC_HIDDEN = ("outlet", "distributor", "sc_spv")


def _filter_internal_documents(fkp: FkpComplaint, kode_role: str) -> FkpComplaint:
    """Buang attachment bertipe HASIL_PEMERIKSAAN_QC dari fkp.attachments
    sebelum diserialisasi ke response, khusus untuk role eksternal."""
    if kode_role in ROLE_HASIL_QC_HIDDEN:
        set_committed_value(
            fkp, "attachments",
            [a for a in fkp.attachments
             if a.tipe_dokumen != TipeDokumen.HASIL_PEMERIKSAAN_QC],
        )
    return fkp


async def get_fkp_detail(fkp_id, db, user, kode_role):
    fkp = await _get_or_404(fkp_id, db)

    await _assert_fkp_scope(fkp, user, kode_role, db)

    fkp_detail = await _load_fkp_detail(fkp.id, db)
    return _filter_internal_documents(fkp_detail, kode_role)

# ─── CRUD ─────────────────────────────────────────────────────────────────────

async def create_fkp(data: FkpCreate, user: User, kode_role: str, db) -> FkpComplaint:
    """Buat FKP baru dengan multi-item sekaligus."""
    await require_permission(kode_role, "fkp.create", db)

    if data.outlet_id:
        await _validasi_outlet_milik_distributor(data.outlet_id, data.distributor_id, db)

    if kode_role == "outlet":
        r = await db.execute(select(Outlet).where(
            Outlet.pic_user_id == user.id,
            Outlet.distributor_id == data.distributor_id,
        ))

        outlets_milik_user = r.scalars().all()

        if not outlets_milik_user:
            raise HTTPException(status_code=403, detail="Distributor tidak sesuai dengan outlet Anda.")

        outlet_ids_milik_user = {o.id for o in outlets_milik_user}

        if data.outlet_id:
            if data.outlet_id not in outlet_ids_milik_user:
                raise HTTPException(
                    status_code=403,
                    detail="Outlet yang dipilih bukan outlet Anda.",
                )
        elif len(outlets_milik_user) == 1:
            # Hanya 1 kandidat -> aman untuk auto-fill.
            data.outlet_id = outlets_milik_user[0].id
        else:
            # >1 kandidat & FE tidak mengirim outlet_id -> jangan menebak.
            raise HTTPException(
                status_code=400,
                detail=(
                    "Anda terdaftar sebagai PIC di lebih dari satu outlet pada "
                    "distributor ini. Pilih outlet secara eksplisit."
                ),
            )

    elif kode_role == "distributor":
        r = await db.execute(select(DistributorUser).where(
            DistributorUser.user_id == user.id,
            DistributorUser.distributor_id == data.distributor_id,
        ))
        if not r.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Distributor bukan milik Anda.")

    elif kode_role == "sc_spv":
        r = await db.execute(select(ScSpvDistributor).where(
            ScSpvDistributor.sc_spv_user_id == user.id,
            ScSpvDistributor.distributor_id == data.distributor_id,
        ))
        if not r.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Distributor tidak dalam tanggungan Anda.")

    elif kode_role == "apsm":
        from app.models.area import Area
        r = await db.execute(select(Area).where(Area.pic_user_id == user.id))
        area_ids = [a.id for a in r.scalars().all()]
        r2 = await db.execute(select(Distributor).where(
            Distributor.id == data.distributor_id,
            Distributor.area_id.in_(area_ids),
        ))
        if not r2.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Distributor di luar area Anda.")
        
    # Validasi & tetapkan kemasan semua item SEBELUM FKP dibuat
    items_dict, daftar = [], []
    for item_data in data.items:
        item_dict = item_data.model_dump(exclude_none=True)
        nama = await set_jenis_kemasan(item_dict, db)
        items_dict.append(item_dict)
        daftar.append((nama, item_dict["jenis_kemasan"]))
    _tolak_jika_campur(daftar)          # sebelum generate_nomor_fkp(), konsisten dengan validasi kemasan

    nomor_fkp = await generate_nomor_fkp(db)
    fkp = FkpComplaint(
        nomor_fkp=nomor_fkp,
        distributor_id=data.distributor_id,
        outlet_id=data.outlet_id,
        submitted_by=user.id,
        prioritas=FkpPrioritas.REGULER,
        catatan_distributor=data.catatan_distributor,
        status=FkpStatus.DRAFT,
        lokasi_pembelian=data.lokasi_pembelian,
    )
    db.add(fkp)
    await db.flush()

    for item_dict in items_dict:
        db.add(FkpItem(fkp_id=fkp.id, **item_dict))

    await _log(db, fkp.id, None, FkpStatus.DRAFT, user.id, "FKP dibuat")
    await db.commit()
    return await _load_fkp_detail(fkp.id, db)

async def update_fkp(fkp_id, data: FkpUpdate, user, kode_role, db):
    fkp = await _get_or_404(fkp_id, db)

    await require_permission(kode_role, "fkp.update_header", db)
    _check_ownership(fkp, user, kode_role)

    if fkp.status not in FkpStatus.EDITABLE:
        raise HTTPException(status_code=400, detail=f"FKP status '{fkp.status}' tidak bisa diedit.")

    if data.outlet_id is not None:
        await _validasi_outlet_milik_distributor(data.outlet_id, fkp.distributor_id, db)

        if kode_role == "outlet":
            r = await db.execute(select(Outlet.id).where(
                Outlet.id == data.outlet_id,
                Outlet.pic_user_id == user.id,
            ))
            if not r.scalar_one_or_none():
                raise HTTPException(status_code=403, detail="Outlet yang dipilih bukan outlet Anda.")

    NON_NULLABLE = {"outlet_id", "prioritas"}
    perubahan = {
        k: v for k, v in data.model_dump(exclude_unset=True).items()
        if v is not None or k not in NON_NULLABLE
    }
    for k, v in perubahan.items():
        setattr(fkp, k, v)
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await db.commit()
    return await _load_fkp_detail(fkp_id, db)

async def _validasi_outlet_milik_distributor(outlet_id, distributor_id, db) -> Outlet:
    r = await db.execute(select(Outlet).where(Outlet.id == outlet_id))
    outlet = r.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan.")
    if getattr(outlet, "status", None) not in (None, "aktif"):
        raise HTTPException(
            status_code=400,
            detail=f"Outlet '{outlet.nama_toko}' tidak aktif (status: {outlet.status}). "
                   "FKP hanya bisa dibuat untuk outlet dengan status aktif.",
        )
    if outlet.distributor_id != distributor_id:
        raise HTTPException(
            status_code=400,
            detail="Outlet yang dipilih tidak terdaftar pada distributor FKP ini.",
        )
    return outlet

# ─── CRUD FKP ITEMS ───────────────────────────────────────────────────────────

async def add_fkp_item(fkp_id, item_data: dict, user, kode_role, db) -> FkpItem:
    fkp = await _get_or_404(fkp_id, db)

    await require_permission(kode_role, "fkp.item.create", db)
    _check_ownership(fkp, user, kode_role)
    if fkp.status not in FkpStatus.EDITABLE:
        raise HTTPException(status_code=400, detail="Item hanya bisa ditambah saat status draft atau need_revision.")

    item_data = dict(item_data)  # jangan mutasi dict milik pemanggil
    nama = await set_jenis_kemasan(item_data, db)
    lainnya = await _daftar_kemasan_item(fkp_id, db)
    _tolak_jika_campur(lainnya + [(nama, item_data["jenis_kemasan"])])
    item = FkpItem(fkp_id=fkp_id, **item_data)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_fkp_item(fkp_id, item_id, data: FkpItemUpdate, user, kode_role, db) -> FkpItem:
    fkp = await _get_or_404(fkp_id, db)

    await require_permission(kode_role, "fkp.item.update", db)
    _check_ownership(fkp, user, kode_role)

    if fkp.status not in FkpStatus.EDITABLE:
        raise HTTPException(status_code=400, detail="Item hanya bisa diedit saat status draft atau need_revision.")
    r = await db.execute(select(FkpItem).where(FkpItem.id == item_id, FkpItem.fkp_id == fkp_id))
    item = r.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item tidak ditemukan.")

    if "product_id" in data.model_dump(exclude_unset=True) and data.product_id is None:
        raise HTTPException(
            status_code=400,
            detail="product_id tidak boleh dikosongkan — setiap item FKP wajib merujuk produk di katalog.",
        )

    # Kolom yang tidak boleh NULL: null dari klien diabaikan. Kolom lain bisa
    # dikosongkan dengan mengirim null secara eksplisit.
    NON_NULLABLE = {"product_id", "qty", "jenis_keluhan", "ada_sample_keluhan", "ada_foto_sample"}
    perubahan = {
        k: v for k, v in data.model_dump(exclude_unset=True).items()
        if v is not None or k not in NON_NULLABLE
    }
    for k, v in perubahan.items():
        setattr(item, k, v)

    # Validasi ulang hanya bila produk/kemasan berubah, supaya edit qty biasa
    # pada item lama tidak mendadak gagal.
    if data.model_fields_set & {"product_id", "jenis_kemasan"}:
        tmp = {"product_id": item.product_id, "jenis_kemasan": item.jenis_kemasan}
        await set_jenis_kemasan(tmp, db)
        item.jenis_kemasan = tmp["jenis_kemasan"]

    # Cek silang hanya bila salah satu field terkait ikut dikirim, supaya item
    # lama yang kondisi_sample-nya NULL tidak mendadak gagal di-update.
    if data.model_fields_set & {"ada_sample_keluhan", "kondisi_sample", "kondisi_sample_lainnya"}:
        _normalisasi_kondisi_sample(item)

    item.updated_at = datetime.now(timezone.utc)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def delete_fkp_item(fkp_id, item_id, user, kode_role, db):
    fkp = await _get_or_404(fkp_id, db)

    await require_permission(kode_role, "fkp.item.delete", db)
    _check_ownership(fkp, user, kode_role)

    if fkp.status not in FkpStatus.EDITABLE:
        raise HTTPException(status_code=400, detail="Item hanya bisa dihapus saat status draft atau need_revision.")
    r = await db.execute(select(FkpItem).where(FkpItem.id == item_id, FkpItem.fkp_id == fkp_id))
    item = r.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item tidak ditemukan.")
    r2 = await db.execute(
        select(func.count(FkpItem.id)).where(FkpItem.fkp_id == fkp_id)
    )
    jumlah = r2.scalar()
    if jumlah <= 1:
        raise HTTPException(status_code=400, detail="FKP harus memiliki minimal 1 item.")
    await db.delete(item)
    await db.commit()
    return {"detail": "Item berhasil dihapus."}


# ─── TRANSISI STATUS ──────────────────────────────────────────────────────────

async def submit_fkp(fkp_id, user, kode_role, db):
    """
    Draft / Need Revision → Submitted, sekaligus menentukan jalur menurut
    kemasan.

    Syarat: minimal 1 foto bukti pengajuan (TIPE_FOTO_BUKTI_PENGAJUAN),
    minimal 1 item, kemasan tiap item divalidasi/ditetapkan
    (set_jenis_kemasan()), dan pcs TIDAK boleh bercampur dengan
    zak/ball/karton (_tolak_jika_campur(), 400).

    Jalur otomatis:
      - semua item pcs → jalur = pcs, status langsung 'pcs_ditangani_apsm'
        (ditangani APSM area; tanpa apsm_review/admin_ho_review/RSM/QC/Direktur).
      - semua item zak/ball/karton → status 'submitted', jalur dikosongkan;
        jalur approval baru ditentukan admin_ho_review().
    Notifikasi dan email memakai status akhir.
    """
    fkp = await _get_or_404(fkp_id, db, for_update=True)

    # Ownership check — selain permission fkp.submit (dicek di _validate_transition),
    # user lain dari distributor/sc_spv/apsm yang sama tidak bisa submit draft
    # yang bukan buatannya.
    _check_ownership(fkp, user, kode_role)

    await _validate_transition(fkp, FkpStatus.SUBMITTED, kode_role, db)

    r = await db.execute(
        select(FkpAttachment.id).where(
            FkpAttachment.fkp_id == fkp_id,
            FkpAttachment.tipe_dokumen.in_(TIPE_FOTO_BUKTI_PENGAJUAN),
        )
    )
    if r.first() is None:
        raise HTTPException(status_code=400, detail="Minimal 1 foto bukti wajib diupload sebelum submit.")

    r2 = await db.execute(select(FkpItem).where(FkpItem.fkp_id == fkp_id))
    items = r2.scalars().all()
    if not items:
        raise HTTPException(status_code=400, detail="FKP harus memiliki minimal 1 item produk.")

    r_nama = await db.execute(
        select(ProductCatalog.id, ProductCatalog.nama_produk)
        .where(ProductCatalog.id.in_({it.product_id for it in items}))
    )
    nama_produk = {pid: nama for pid, nama in r_nama.all()}

    for it in items:
        tmp = {"product_id": it.product_id, "jenis_kemasan": it.jenis_kemasan}
        try:
            await set_jenis_kemasan(tmp, db)
        except HTTPException as e:
            nama = nama_produk.get(it.product_id, str(it.product_id))
            detail = str(e.detail)
            if nama not in detail:
                detail = f"Produk '{nama}': {detail}"
            raise HTTPException(status_code=e.status_code, detail=detail)
        it.jenis_kemasan = tmp["jenis_kemasan"]
        db.add(it)

    # Gerbang akhir: pcs tidak boleh bercampur dengan zak/ball/karton. update_fkp_item
    # sengaja tidak ketat, jadi draft campuran baru ketahuan di sini.
    kelompok = _tolak_jika_campur(
        [(nama_produk.get(it.product_id, str(it.product_id)), it.jenis_kemasan) for it in items]
    )

    lama = fkp.status
    fkp.status = FkpStatus.SUBMITTED
    if lama == FkpStatus.DRAFT:
        fkp.tanggal_pengajuan = datetime.now(timezone.utc)
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await _log(db, fkp.id, lama, FkpStatus.SUBMITTED, user.id)

    if kelompok == KELOMPOK_PCS:
        # Jalur pcs: langsung ke APSM, tidak lewat apsm_review/admin_ho_review.
        fkp.jalur = JalurFkp.PCS
        fkp.pcs_tahap = None
        fkp.status = FkpStatus.PCS_DITANGANI_APSM
        await _log(db, fkp.id, FkpStatus.SUBMITTED, FkpStatus.PCS_DITANGANI_APSM, user.id,
                   "Otomatis: FKP hanya berisi kemasan pcs, ditangani langsung oleh APSM.")
    else:
        fkp.jalur = None   # reset bila disubmit ulang dari need_revision; diisi di admin_ho_review()

    status_akhir = fkp.status
    await kirim_notifikasi_transisi(db, fkp, lama, status_akhir, user)
    
    await db.commit()
    await trigger_email_after_transition(db, fkp, lama, status_akhir, user)
    return await _load_fkp_detail(fkp.id, db)


async def apsm_review(fkp_id, data: ApsmReviewRequest, user, kode_role, db):
    """Submitted → Apsm Reviewed."""
    fkp = await _get_or_404(fkp_id, db, for_update=True)
    await _validate_transition(fkp, FkpStatus.APSM_REVIEWED, kode_role, db, expected_status=FkpStatus.SUBMITTED)
    await _check_apsm_area_scope(fkp, user, kode_role, db)

    if data.item_reviews:
        for review in data.item_reviews:
            r = await db.execute(select(FkpItem).where(
                FkpItem.id == review.item_id,
                FkpItem.fkp_id == fkp_id,
            ))
            item = r.scalar_one_or_none()
            if item:
                if review.rekomendasi_penanganan_apsm is not None:
                    item.rekomendasi_penanganan_apsm = review.rekomendasi_penanganan_apsm
                if review.rekomendasi_kompensasi_apsm is not None:
                    item.rekomendasi_kompensasi_apsm = review.rekomendasi_kompensasi_apsm
                if review.catatan_apsm is not None:
                    item.catatan_apsm = review.catatan_apsm
                if review.persentase_disetujui_apsm is not None:
                    item.persentase_disetujui_apsm = review.persentase_disetujui_apsm
                item.updated_at = datetime.now(timezone.utc)
                db.add(item)

    lama = fkp.status
    fkp.status = FkpStatus.APSM_REVIEWED
    fkp.catatan_apsm = data.catatan_apsm
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await _log(db, fkp.id, lama, FkpStatus.APSM_REVIEWED, user.id, data.catatan_apsm)
    await kirim_notifikasi_transisi(db, fkp, lama, FkpStatus.APSM_REVIEWED, user)
    await db.commit()
    return await _load_fkp_detail(fkp.id, db)

async def _hitung_qty_tidak_dihitung(fkp_id, db) -> int:
    """HANYA untuk log/tampilan (qty pcs). Jangan dipakai menentukan jalur."""
    kemasan_efektif = func.coalesce(FkpItem.jenis_kemasan, ProductCatalog.jenis_kemasan)
    r = await db.execute(
        select(func.coalesce(func.sum(FkpItem.qty), 0))
        .select_from(FkpItem)
        .join(ProductCatalog, ProductCatalog.id == FkpItem.product_id)
        .where(FkpItem.fkp_id == fkp_id, kemasan_efektif.not_in(KEMASAN_DIHITUNG_JALUR))
    )
    return int(r.scalar() or 0)

async def admin_ho_review(fkp_id, data: AdminHoReviewRequest, user, kode_role, db):
    """
    Apsm Reviewed → Rsm Approval Final (jalur approval RSM) atau
    Rsm Approval Investigasi (jalur approval Direktur).

    INILAH satu-satunya titik penentuan jalur approval FKP zak/ball/karton
    (FKP pcs sudah ditangani APSM sejak submit_fkp()). Ditentukan dari total
    qty klaim saat pengajuan (_hitung_total_qty_jalur()):
      - total ≤ BATAS_QTY_DIREKTUR → RSM_APPROVAL_FINAL, jalur = approval_rsm:
        Admin HO membuat resolusi, RSM approval terakhir, Direktur tidak
        dilibatkan; QC investigasi PARALEL.
      - total > BATAS_QTY_DIREKTUR → RSM_APPROVAL_INVESTIGASI, jalur =
        approval_direktur: investigasi QC → resolusi → RSM → Direktur (wajib)
        → accepted.
    Jalur disimpan di FkpComplaint.jalur. qty_disetujui dan tipe_resolusi
    tidak ikut menentukan jalur. Qty pcs hanya dicatat di log (tidak dihitung).

    Admin HO tidak mengisi rekomendasi per item — murni meneruskan; hanya
    catatan_admin yang dicatat (juga dipakai PDF FKP, section "Rekomendasi
    Sales & Marketing", sampai rekomendasi_marketing dibuat terpisah — lihat
    fkp_pdf_service.py).
    """
    fkp = await _get_or_404(fkp_id, db, for_update=True)

    total_qty = await _hitung_total_qty_jalur(fkp_id, db)
    qty_lain = await _hitung_qty_tidak_dihitung(fkp_id, db)

    target_status = (
        FkpStatus.RSM_APPROVAL_FINAL
        if total_qty <= BATAS_QTY_DIREKTUR
        else FkpStatus.RSM_APPROVAL_INVESTIGASI
    )

    await _validate_transition(fkp, target_status, kode_role, db)

    lama = fkp.status
    fkp.status = target_status
    fkp.catatan_admin = data.catatan_admin
    # Simpan jalur yang benar-benar dijalani FKP ini (filter/dashboard/guard QC paralel).
    fkp.jalur = (
        JalurFkp.APPROVAL_RSM if total_qty <= BATAS_QTY_DIREKTUR
        else JalurFkp.APPROVAL_DIREKTUR
    )
    fkp.handled_by = user.id
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)

    catatan_log = (
        f"{data.catatan_admin or ''} (total qty klaim: {total_qty} zak/ball/karton; "
        f"{qty_lain} pcs tidak dihitung)"
    ).strip()
    await _log(db, fkp.id, lama, target_status, user.id, catatan_log)
    
    await kirim_notifikasi_transisi(db, fkp, lama, target_status, user)
    await db.commit()
    return await _load_fkp_detail(fkp.id, db)


async def rsm_approve_final(fkp_id, data: RsmApproveRequest, user, kode_role, db):
    """
    RSM approval AKHIR jalur approval RSM (total qty klaim ≤
    BATAS_QTY_DIREKTUR). FKP wajib berstatus RSM_APPROVAL_FINAL
    (di-set admin_ho_review()). Direktur TIDAK pernah dilibatkan.

    Resolusi WAJIB sudah dibuat Admin HO (buat_resolusi() Fase 1, termasuk
    item_qty_disetujui bila tukar_barang) selagi status masih
    RSM_APPROVAL_FINAL — approve ditolak (400) bila resolusi belum ada.
    Penolakan (disetujui=False) wajib disertai catatan.

    Approve: mengisi approved_by_rsm_final (TTD ke-4 di PDF = RSM; saling
    eksklusif dengan approved_by_direktur) dan menandai item 'pending'
    menjadi 'diterima' (_tandai_item_diterima_setelah_approval_final()).

    Permission "fkp.rsm_approve_final" diberikan lewat permission_code di
    _validate_transition(), karena status tujuan ACCEPTED/REJECTED dipakai
    aksi lain; expected_status=RSM_APPROVAL_FINAL mencegah aksi dipanggil di
    luar gilirannya.
    """
    fkp = await _get_or_404(fkp_id, db, for_update=True)
    new_status = FkpStatus.ACCEPTED if data.disetujui else FkpStatus.REJECTED

    await _validate_transition(fkp, new_status, kode_role, db,
                            permission_code="fkp.rsm_approve_final",
                            expected_status=FkpStatus.RSM_APPROVAL_FINAL)
    _wajib_catatan_tolak(data.disetujui, data.catatan)

    if data.disetujui:
        r = await db.execute(select(FkpResolution).where(FkpResolution.fkp_id == fkp_id))
        if not r.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=(
                    "Resolusi belum dibuat oleh Admin HO. Buat resolusi "
                    "terlebih dahulu sebelum RSM menyetujui FKP ini."
                ),
            )

    lama = fkp.status
    fkp.status = new_status
    fkp.catatan_rsm_resolusi = data.catatan
    if data.disetujui:
        fkp.approved_by_rsm_final = user.id
        await _tandai_item_diterima_setelah_approval_final(fkp_id, db)
    if not data.disetujui:
        fkp.tanggal_selesai = datetime.now(timezone.utc)
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await _log(db, fkp.id, lama, new_status, user.id, data.catatan)
    await kirim_notifikasi_transisi(db, fkp, lama, new_status, user)
    await db.commit()
    return await _load_fkp_detail(fkp.id, db)


async def rsm_approve_investigasi(fkp_id, data: RsmApproveRequest, user, kode_role, db):
    """JALUR APPROVAL DIREKTUR: RSM approve → In Investigation / tolak → Rejected."""
    fkp = await _get_or_404(fkp_id, db, for_update=True)
    new_status = FkpStatus.IN_INVESTIGATION if data.disetujui else FkpStatus.REJECTED
    await _validate_transition(fkp, new_status, kode_role, db, permission_code="fkp.rsm_approve_investigasi", expected_status=FkpStatus.RSM_APPROVAL_INVESTIGASI)
    _wajib_catatan_tolak(data.disetujui, data.catatan)
    lama = fkp.status
    fkp.status = new_status
    fkp.catatan_rsm_investigasi = data.catatan
    if not data.disetujui:
        fkp.tanggal_selesai = datetime.now(timezone.utc)
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await _log(db, fkp.id, lama, new_status, user.id, data.catatan)
    await kirim_notifikasi_transisi(db, fkp, lama, new_status, user)
    await db.commit()
    return await _load_fkp_detail(fkp.id, db)


async def qc_investigasi(fkp_id, data: InvestigasiQcRequest, user, kode_role, db):
    """JALUR APPROVAL DIREKTUR: QC selesai investigasi → Investigated."""
    fkp = await _get_or_404(fkp_id, db, for_update=True)
    await _validate_transition(fkp, FkpStatus.INVESTIGATED, kode_role, db)

    # [Modul Sample Shipment, Phase 4] Gate: tolak transisi ke INVESTIGATED
    # kalau masih ada sample yang belum selesai diperiksa (status di luar
    # SampleStatus.TERMINAL — examined/cancelled).
    # Import lokal (bukan di top-level file) untuk menghindari circular
    # import: sample_service.py sendiri meng-import beberapa helper dari
    # fkp_service.py (_get_or_404, _check_ownership, get_fkp_detail).
    from app.services.sample_service import all_samples_examined_or_cancelled
    if not await all_samples_examined_or_cancelled(fkp_id, db):
        raise HTTPException(
            status_code=400,
            detail=(
                "Masih ada sample yang belum selesai diperiksa QC. "
                "Selesaikan atau batalkan seluruh sample shipment untuk FKP "
                "ini sebelum menyelesaikan investigasi."
            ),
        )

    # QC tidak mengubah status_item di sini — hanya mengisi
    # persentase_disetujui_qc sebagai rekomendasi. status_item baru berubah
    # jadi 'diterima' otomatis saat approval final disetujui, lihat
    # _tandai_item_diterima_setelah_approval_final().
    if data.item_results:
        for result in data.item_results:
            r = await db.execute(select(FkpItem).where(
                FkpItem.id == result.item_id,
                FkpItem.fkp_id == fkp_id,
            ))
            item = r.scalar_one_or_none()
            if item:
                if result.persentase_disetujui_qc is not None:
                    item.persentase_disetujui_qc = result.persentase_disetujui_qc
                if result.catatan_qc is not None:
                    item.catatan_qc = result.catatan_qc
                if result.alasan_penolakan is not None:
                    item.alasan_penolakan = result.alasan_penolakan
                item.updated_at = datetime.now(timezone.utc)
                db.add(item)

    lama = fkp.status
    fkp.status = FkpStatus.INVESTIGATED
    fkp.catatan_qc = data.catatan_qc
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await _log(db, fkp.id, lama, FkpStatus.INVESTIGATED, user.id,
               f"Sumber: {data.sumber_ketidaksesuaian}. {data.catatan_qc or ''}".strip())
    await kirim_notifikasi_transisi(db, fkp, lama, FkpStatus.INVESTIGATED, user)
    await db.commit()
    return await _load_fkp_detail(fkp.id, db)


async def qc_catatan_investigasi_paralel(fkp_id, data: InvestigasiQcRequest, user, kode_role, db):
    """
    Catatan investigasi QC untuk jalur approval RSM (total qty klaim ≤
    BATAS_QTY_DIREKTUR). BEDA FUNDAMENTAL dari qc_investigasi():

      - TIDAK mengubah fkp.status maupun status_item; berjalan PARALEL dengan
        resolusi / RSM approval / surat jalan, tidak menahan satu pun.
      - Hanya valid pada STATUS_QC_PARALEL (rsm_approval_final, accepted,
        in_process) — whitelist; status lain (termasuk need_revision) → 400.
      - Hanya menyimpan catatan_qc, alasan_penolakan, dan
        persentase_disetujui_qc per item (rekomendasi/insight, bukan
        keputusan). BA hasil pemeriksaan diupload terpisah lewat endpoint
        attachment generic.
      - Memakai skema InvestigasiQcRequest yang sama dengan qc_investigasi().
      - catatan_qc / persentase_disetujui_qc yang terisi dipakai
        _sudah_diinvestigasi_qc() sebagai syarat close_fkp().
      - QC diberi tahu begitu resolusi pertama dibuat (notifikasi di
        buat_resolusi()).

    Guard jalur: total qty dihitung ulang lewat _hitung_total_qty_jalur();
    > BATAS_QTY_DIREKTUR → 400 (pakai qc_investigasi(), yang menahan status).
    """
    await require_permission(kode_role, "fkp.qc_investigasi", db)

    fkp = await _get_or_404(fkp_id, db)

    if fkp.status not in STATUS_QC_PARALEL:
        raise HTTPException(
            status_code=400,
            detail=(f"Catatan investigasi paralel hanya bisa diisi saat FKP berstatus "
                    f"{', '.join(STATUS_QC_PARALEL)}. Status saat ini: '{fkp.status}'."),
        )

    total_qty = await _hitung_total_qty_jalur(fkp_id, db)

    if total_qty > BATAS_QTY_DIREKTUR:
        raise HTTPException(
            status_code=400,
            detail=(
                f"FKP ini total qty klaim {total_qty} zak/ball/karton "
                f"(> {BATAS_QTY_DIREKTUR}) — bukan jalur approval RSM. "
                "Gunakan alur investigasi QC biasa."
            ),
        )

    if data.item_results:
        for result in data.item_results:
            r = await db.execute(select(FkpItem).where(
                FkpItem.id == result.item_id,
                FkpItem.fkp_id == fkp_id,
            ))
            item = r.scalar_one_or_none()
            if item:
                if result.persentase_disetujui_qc is not None:
                    item.persentase_disetujui_qc = result.persentase_disetujui_qc
                if result.catatan_qc is not None:
                    item.catatan_qc = result.catatan_qc
                if result.alasan_penolakan is not None:
                    item.alasan_penolakan = result.alasan_penolakan
                item.updated_at = datetime.now(timezone.utc)
                db.add(item)

    # TIDAK ada perubahan fkp.status maupun status_item — murni catatan.
    fkp.catatan_qc = data.catatan_qc
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)

    # Tidak pakai _log() (FkpStatusLog) di sini karena tidak ada transisi
    # status — bikin timeline FE bingung kalau status_lama == status_baru.
    # Notifikasi tetap dikirim supaya Admin HO/RSM tahu ada insight baru,
    # tapi bukan lewat kirim_notifikasi_transisi() (itu berbasis pasangan
    # status_lama/status_baru).
    await kirim_notifikasi_qc_paralel(db, fkp, user)

    await db.commit()
    return await _load_fkp_detail(fkp.id, db)


async def admin_ho_request_resolusi_approval(fkp_id, catatan, user, kode_role, db):
    """JALUR APPROVAL DIREKTUR: Investigated → Rsm Approval Resolusi."""
    fkp = await _get_or_404(fkp_id, db, for_update=True)
    await _validate_transition(fkp, FkpStatus.RSM_APPROVAL_RESOLUSI, kode_role, db)
    lama = fkp.status
    fkp.status = FkpStatus.RSM_APPROVAL_RESOLUSI
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await _log(db, fkp.id, lama, FkpStatus.RSM_APPROVAL_RESOLUSI, user.id, catatan)
    await kirim_notifikasi_transisi(db, fkp, lama, FkpStatus.RSM_APPROVAL_RESOLUSI, user)
    await db.commit()
    return await _load_fkp_detail(fkp.id, db)


async def rsm_approve_resolusi(fkp_id, data: RsmApproveRequest, user, kode_role, db):
    """
    JALUR APPROVAL DIREKTUR (total qty klaim saat pengajuan > BATAS_QTY_DIREKTUR,
    ditentukan di admin_ho_review()): RSM approve/tolak resolusi.

      - Approve → DIREKTUR_APPROVAL. SELALU, untuk semua tipe_resolusi
        (tukar_barang, potong_tagihan).
        Tidak ada pengecekan qty maupun tipe_resolusi di sini — FKP yang
        sampai di status RSM_APPROVAL_RESOLUSI sudah pasti jalur approval Direktur.
      - Tolak   → REJECTED.

    RSM BUKAN approval terakhir di jalur ini, jadi fungsi ini TIDAK mengisi
    approved_by_rsm_final dan TIDAK memanggil
    _tandai_item_diterima_setelah_approval_final() — keduanya urusan
    direktur_approve().

    Permission yang dicek: "fkp.rsm_approve_resolusi"; 
    FKP wajib berstatus RSM_APPROVAL_RESOLUSI.
    """
    fkp = await _get_or_404(fkp_id, db, for_update=True)

    new_status = FkpStatus.DIREKTUR_APPROVAL if data.disetujui else FkpStatus.REJECTED

    await _validate_transition(fkp, new_status, kode_role, db, permission_code="fkp.rsm_approve_resolusi", expected_status=FkpStatus.RSM_APPROVAL_RESOLUSI)
    _wajib_catatan_tolak(data.disetujui, data.catatan)

    if data.disetujui:
        r = await db.execute(select(FkpResolution).where(FkpResolution.fkp_id == fkp_id))
        if not r.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Resolusi belum dibuat. Tidak bisa memproses persetujuan RSM.",
            )

    lama = fkp.status
    fkp.status = new_status
    fkp.catatan_rsm_resolusi = data.catatan
    if not data.disetujui:
        fkp.tanggal_selesai = datetime.now(timezone.utc)
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await _log(db, fkp.id, lama, new_status, user.id, data.catatan)
    await kirim_notifikasi_transisi(db, fkp, lama, new_status, user)
    await db.commit()
    return await _load_fkp_detail(fkp.id, db)


async def direktur_approve(fkp_id, data: DirekturApproveRequest, user, kode_role, db):
    """
    JALUR APPROVAL DIREKTUR: Direktur Approval → Accepted / Rejected.

    Direktur adalah approval TERAKHIR di jalur approval Direktur dan WAJIB untuk semua
    FKP di jalur ini (total qty klaim saat pengajuan > BATAS_QTY_DIREKTUR),
    apa pun tipe_resolusi-nya. Approve di sini juga:
      - mengisi approved_by_direktur (penanda sah "Direktur benar-benar
        approve"; dipakai PDF FKP untuk nama penandatangan Direktur — lihat
        fkp_pdf_service.py / build_fkp_context). Saling eksklusif dengan
        approved_by_rsm_final (jalur approval RSM).
      - men-trigger status_item semua item FKP jadi 'diterima' (lihat
        _tandai_item_diterima_setelah_approval_final()).
    """
    fkp = await _get_or_404(fkp_id, db, for_update=True)
    new_status = FkpStatus.ACCEPTED if data.disetujui else FkpStatus.REJECTED

    await _validate_transition(fkp, new_status, kode_role, db, permission_code="fkp.direktur_approve", expected_status=FkpStatus.DIREKTUR_APPROVAL)
    _wajib_catatan_tolak(data.disetujui, data.catatan)

    lama = fkp.status
    fkp.status = new_status
    fkp.catatan_direktur = data.catatan
    if data.disetujui:
        fkp.approved_by_direktur = user.id
        await _tandai_item_diterima_setelah_approval_final(fkp_id, db)
    if not data.disetujui:
        fkp.tanggal_selesai = datetime.now(timezone.utc)
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await _log(db, fkp.id, lama, new_status, user.id, data.catatan)
    await kirim_notifikasi_transisi(db, fkp, lama, new_status, user)
    await db.commit()
    return await _load_fkp_detail(fkp.id, db)


async def update_pengiriman(fkp_id, data, user, kode_role, db):
    """
    DEPRECATED — gunakan endpoint POST /resolusi dengan status 'accepted'.
    Stub ini meneruskan ke buat_resolusi agar backward compatible.
    """
    from app.schemas.fkp import ResolusiCreate
    payload = ResolusiCreate(
        resi_pengiriman=data.resi_pengiriman,
        ekspedisi=data.ekspedisi,
        nomor_surat_jalan=data.nomor_surat_jalan,
        keterangan=data.catatan,
    )
    return await buat_resolusi(fkp_id, payload, user, kode_role, db)


async def request_revision(fkp_id, data: RevisionRequest, user, kode_role, db):
    """
    Minta revisi — status tujuan ditentukan REVISION_TARGETS berdasarkan
    (status asal, role). Scope area APSM dicek _check_apsm_area_scope().
    Tidak berlaku untuk FKP jalur pcs (tidak ada entri di REVISION_TARGETS).
    """
    await require_permission(kode_role, "fkp.request_revision", db)

    if not data.catatan:
        raise HTTPException(status_code=400, detail="Catatan alasan revisi wajib diisi.")
    fkp = await _get_or_404(fkp_id, db, for_update=True)
    await _check_apsm_area_scope(fkp, user, kode_role, db)

    target_status = REVISION_TARGETS.get((fkp.status, kode_role))
    if not target_status:
        raise HTTPException(
            status_code=400,
            detail=f"Role '{kode_role}' tidak bisa meminta revisi dari status '{fkp.status}'.",
        )

    lama = fkp.status
    fkp.status = target_status
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await _log(db, fkp.id, lama, target_status, user.id, data.catatan)
    await kirim_notifikasi_transisi(db, fkp, lama, target_status, user)
   
    await db.commit()
    await trigger_email_after_transition(db, fkp, lama, target_status, user, data.catatan)
    return await _load_fkp_detail(fkp.id, db)


async def reject_fkp(fkp_id, data: RejectRequest, user, kode_role, db):
    """
    Tolak FKP; alasan (catatan) wajib.

    Jalur approval: transisi ke REJECTED lewat _validate_transition()
    (permission "fkp.reject"), hanya dari status yang mengizinkannya di
    VALID_TRANSITIONS.
    Jalur pcs (status pcs_ditangani_apsm): hanya APSM area (permission
    "fkp.pcs.handle"), dan hanya selama pcs_tahap masih kosong; setelah
    APSM memilih tahap pertama FKP tidak bisa ditolak. Terminal, tanpa revisi.
    """
    if not data.catatan:
        raise HTTPException(status_code=400, detail="Alasan penolakan wajib diisi.")
    fkp = await _get_or_404(fkp_id, db, for_update=True)

    await _check_apsm_area_scope(fkp, user, kode_role, db) 
    is_pcs = fkp.status == FkpStatus.PCS_DITANGANI_APSM
    # Jalur pcs: hanya APSM (fkp.pcs.handle) yang boleh menolak, bukan fkp.reject, supaya
    # RSM/Admin HO tidak bisa menolak FKP yang bukan wewenangnya.
    await _validate_transition(
        fkp, FkpStatus.REJECTED, kode_role, db,
        permission_code="fkp.pcs.handle" if is_pcs else None,
    )
    if is_pcs and fkp.pcs_tahap is not None:
        raise HTTPException(
            status_code=400,
            detail=(
                "FKP pcs tidak bisa ditolak setelah penanganan dimulai "
                f"(tahap saat ini: '{LABEL_TAHAP_PCS[fkp.pcs_tahap]}'). "
                "Penolakan hanya bisa dilakukan sebelum APSM memilih tahap pertama."
            ),
        )
    lama = fkp.status
    fkp.status = FkpStatus.REJECTED
    fkp.tanggal_selesai = datetime.now(timezone.utc)
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await _log(db, fkp.id, lama, FkpStatus.REJECTED, user.id, data.catatan)
    await kirim_notifikasi_transisi(db, fkp, lama, FkpStatus.REJECTED, user, data.catatan)
   
    await db.commit()
    await trigger_email_after_transition(db, fkp, lama, FkpStatus.REJECTED, user, data.catatan)
    return await _load_fkp_detail(fkp.id, db)


async def apsm_update_tahap_pcs(fkp_id, data: PcsTahapRequest, user, kode_role, db):
    """
    Jalur pcs: APSM memajukan tahap penanganan.
      dalam_pengajuan -> dalam_proses -> selesai
    - HANYA maju. Tahap yang sama atau lebih rendah dari tahap sekarang ditolak.
    - Lompat maju boleh; tahap sebelumnya otomatis tercentang (timestamp diisi).
    - 'selesai' menutup FKP: status -> CLOSED (terminal).
    Tidak memakai close_fkp(): gate BA pemusnahan, surat jalan, invoice, dan QC
    sengaja tidak berlaku di jalur pcs (penggantian dilakukan APSM di luar sistem).
    """
    await require_permission(kode_role, "fkp.pcs.handle", db)

    fkp = await _get_or_404(fkp_id, db, for_update=True)
    if fkp.status != FkpStatus.PCS_DITANGANI_APSM:
        raise HTTPException(
            status_code=400,
            detail=f"Penanganan pcs hanya untuk FKP berstatus '{FkpStatus.PCS_DITANGANI_APSM}', "
                   f"status saat ini '{fkp.status}'.",
        )
    await _check_apsm_area_scope(fkp, user, kode_role, db)

    idx_baru = TahapPcs.URUTAN.index(data.tahap)
    idx_kini = TahapPcs.URUTAN.index(fkp.pcs_tahap) if fkp.pcs_tahap else -1
    if idx_baru <= idx_kini:
        raise HTTPException(
            status_code=400,
            detail=(f"Tahap tidak bisa mundur atau diulang. Tahap saat ini: "
                    f"'{LABEL_TAHAP_PCS[fkp.pcs_tahap]}'."),
        )

    now = datetime.now(timezone.utc)
    kolom = ("pcs_pengajuan_at", "pcs_proses_at", "pcs_selesai_at")
    for j in range(idx_baru + 1):              # centang otomatis tahap sebelumnya
        if getattr(fkp, kolom[j]) is None:
            setattr(fkp, kolom[j], now)

    lama = fkp.status
    fkp.pcs_tahap = data.tahap
    if data.tahap == TahapPcs.SELESAI:
        fkp.status = FkpStatus.CLOSED
        fkp.tanggal_selesai = now
    fkp.updated_at = now
    db.add(fkp)

    # status_lama == status_baru bila belum close: pola yang sama dengan
    # teruskan_ke_warehouse() / proses_finance(), supaya jejak muncul di timeline.
    await _log(db, fkp.id, lama, fkp.status, user.id,
               data.catatan or f"Tahap penanganan pcs: {LABEL_TAHAP_PCS[data.tahap]}")
    await kirim_notifikasi_pcs_tahap(db, fkp, data.tahap, user)

    await db.commit()
    fkp_loaded = await _load_fkp_detail(fkp.id, db)
    if fkp.status == FkpStatus.CLOSED:
        # Perubahan sudah ter-commit; kegagalan email tidak boleh membuat request
        # error (500) padahal FKP sudah tertutup. TODO: hapus try/except ini setelah
        # kirim_email_fkp_closed memastikan fkp.resolution == None (jalur pcs) aman.
        try:
            await trigger_email_after_transition(db, fkp_loaded, lama, FkpStatus.CLOSED, user, data.catatan)
        except Exception:
            logger.exception("Email penutupan FKP pcs gagal dikirim (fkp_id=%s)", fkp_id)
    return fkp_loaded


async def input_surat_jalan(fkp_id, nomor_surat_jalan, user, kode_role, db):
    """
    Admin HO input/update nomor surat jalan kapan pun.
    Dijaga permission fkp.surat_jalan.input. Endpoint pemanggil fungsi ini
    harus meneruskan kode_role.
    """
    await require_permission(kode_role, "fkp.surat_jalan.input", db)

    fkp = await _get_or_404(fkp_id, db)
    fkp.nomor_surat_jalan = nomor_surat_jalan
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await db.commit()
    return await _load_fkp_detail(fkp_id, db)


async def _sudah_diinvestigasi_qc(fkp_id, db) -> bool:
    """
    True kalau FKP ini sudah pernah diinvestigasi QC — dipakai gate close_fkp().

    Tiga penanda (cukup salah satu):
      1. Ada log transisi ke status 'investigated' → jalur approval Direktur
         (qc_investigasi() adalah satu-satunya jalan ke status itu).
      2. FkpComplaint.catatan_qc terisi, atau
      3. minimal 1 item punya persentase_disetujui_qc →
         jalur approval RSM, keduanya hanya bisa terisi lewat
         qc_catatan_investigasi_paralel() (opsional & tidak menahan status,
         jadi perlu dicek eksplisit).
    """
    r = await db.execute(
        select(func.count(FkpStatusLog.id)).where(
            FkpStatusLog.fkp_id == fkp_id,
            FkpStatusLog.status_baru == FkpStatus.INVESTIGATED,
        )
    )
    if (r.scalar() or 0) > 0:
        return True

    r = await db.execute(select(FkpComplaint.catatan_qc).where(FkpComplaint.id == fkp_id))
    if (r.scalar_one_or_none() or "").strip():
        return True

    r = await db.execute(
        select(func.count(FkpItem.id)).where(
            FkpItem.fkp_id == fkp_id,
            FkpItem.persentase_disetujui_qc.is_not(None),
        )
    )
    return (r.scalar() or 0) > 0


async def close_fkp(fkp_id, catatan, user, kode_role, db):
    """
    In Process → Closed (jalur approval RSM / approval Direktur). FKP jalur pcs
    TIDAK ditutup di sini: lihat apsm_update_tahap_pcs(tahap=selesai).

    Syarat, dicek berurutan:
      1. Status harus 'in_process'.
      2. FKP sudah pernah diinvestigasi QC (_sudah_diinvestigasi_qc()): jalur
         approval Direktur otomatis terpenuhi (wajib lewat 'investigated'); jalur
         approval RSM harus punya catatan_qc atau persentase_disetujui_qc dari
         QC paralel.
      3. Resolusi sudah ada.
      4. potong_tagihan: pembayaran cashback sudah dikonfirmasi Finance
         (proses_finance()).
      5. tukar_barang: surat jalan sudah berstatus 'delivered'.
      6. metode_penanganan_fisik = dimusnahkan: BA yang SUDAH DITANDATANGANI
         (FkpAttachment, bukan draft PDF di FkpDocument) bertipe
         BERITA_ACARA_PEMUSNAHAN_TUKAR_BARANG (tukar_barang) atau
         BERITA_ACARA_PEMUSNAHAN (selain itu) sudah diupload.
    """
    fkp = await _get_or_404(fkp_id, db, for_update=True)

    if fkp.status != FkpStatus.IN_PROCESS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"FKP tidak bisa ditutup dari status '{fkp.status}'. "
                f"Status harus 'in_process' sebelum bisa ditutup."
            )
        )

    if not await _sudah_diinvestigasi_qc(fkp_id, db):
        raise HTTPException(
            status_code=400,
            detail=(
                "FKP tidak bisa ditutup — investigasi QC belum pernah dicatat. "
                "QC harus mengisi hasil investigasi (POST .../qc-catatan-paralel) "
                "terlebih dahulu."
            ),
        )

    r_resolusi = await db.execute(select(FkpResolution).where(FkpResolution.fkp_id == fkp_id))
    resolusi = r_resolusi.scalar_one_or_none()

    if not resolusi:
        raise HTTPException(400, "Resolusi belum dibuat untuk FKP ini.")

    if resolusi.tipe_resolusi == TipeResolusi.POTONG_TAGIHAN and not resolusi.diproses_finance:
        raise HTTPException(
            400,
            "FKP tidak bisa ditutup — pembayaran cashback belum dikonfirmasi Finance (proses_finance).",
        )

    if resolusi.tipe_resolusi == TipeResolusi.TUKAR_BARANG:
        from app.services.warehouse_service import surat_jalan_sudah_delivered
        if not await surat_jalan_sudah_delivered(fkp_id, db):
            raise HTTPException(400, "FKP tidak bisa ditutup — surat jalan belum berstatus delivered.")

    if resolusi.metode_penanganan_fisik == MetodePenangananFisik.DIMUSNAHKAN:
        tipe_ba = (
            TipeDokumen.BERITA_ACARA_PEMUSNAHAN_TUKAR_BARANG
            if resolusi.tipe_resolusi == TipeResolusi.TUKAR_BARANG
            else TipeDokumen.BERITA_ACARA_PEMUSNAHAN
        )

        r_bukti = await db.execute(
            select(FkpAttachment.id).where(
                FkpAttachment.fkp_id == fkp_id,
                FkpAttachment.tipe_dokumen == tipe_ba,
            )
        )

        if r_bukti.first() is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"FKP tidak bisa ditutup — dokumen BA bertipe "
                    f"'{tipe_ba}' yang sudah ditandatangani belum diupload."
                ),
            )

    await _validate_transition(fkp, FkpStatus.CLOSED, kode_role, db)
    lama = fkp.status
    fkp.status = FkpStatus.CLOSED
    fkp.tanggal_selesai = datetime.now(timezone.utc)
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await _log(db, fkp.id, lama, FkpStatus.CLOSED, user.id, catatan or "FKP ditutup.")
    await kirim_notifikasi_transisi(db, fkp, lama, FkpStatus.CLOSED, user)

    await db.commit()
    fkp_loaded = await _load_fkp_detail(fkp.id, db)
    await trigger_email_after_transition(db, fkp_loaded, lama, FkpStatus.CLOSED, user, catatan)
    return fkp_loaded

async def buat_resolusi(fkp_id, data, user, kode_role, db):
    """
    Satu fungsi, dua fase — dikontrol oleh status FKP. HANYA menyimpan data
    resolusi; TIDAK PERNAH mengubah fkp.status. Transisi accepted →
    in_process ada di endpoint terpisah sesuai tipe_resolusi:
      - tukar_barang   → create_surat_jalan() (modul Warehouse, setelah
                         teruskan_ke_warehouse())
      - potong_tagihan → terbitkan_invoice()

    Resolusi (tipe_resolusi, qty_disetujui, dst.) TIDAK mempengaruhi jalur
    approval maupun keterlibatan Direktur — itu hanya ditentukan total qty
    klaim saat pengajuan (_hitung_total_qty_jalur()). FKP jalur pcs tidak
    punya resolusi.

    FASE 1 — status 'investigated' & 'rsm_approval_resolusi' (jalur approval
    Direktur) atau 'rsm_approval_final' (jalur approval RSM), yaitu SEBELUM
    approval final:
      Wajib saat membuat: tipe_resolusi + metode_penanganan_fisik
      Boleh: lokasi_pemusnahan (wajib bila dimusnahkan), tanggal_pemusnahan,
             detail_penanganan, persentase_kompensasi_disetujui (wajib untuk
             potong_tagihan), keterangan
      Boleh juga: item_qty_disetujui (khusus tukar_barang) —
             qty_disetujui = 0 → item 'ditolak' (alasan_penolakan wajib di
             ItemQtyDisetujui); > 0 → qty tersimpan, item 'pending' sampai
             approval terakhir. Lihat _validasi_dan_simpan_qty_disetujui().
      TIDAK boleh: field eksekusi (nomor_do, rekening, dll)
      Jalur approval RSM: rsm_approve_final() menolak approve bila resolusi
      belum dibuat di fase ini, dan resolusi PERTAMA di status
      'rsm_approval_final' memicu notifikasi ke QC (investigasi paralel).

    FASE 2 — status 'accepted' DENGAN resolusi:
      Wajib: detail eksekusi sesuai tipe (potong_tagihan: nama_bank,
             nomor_rekening, atas_nama)
      TIDAK boleh ubah: tipe_resolusi, metode_penanganan_fisik
      item_qty_disetujui masih boleh dikoreksi (tukar_barang) selama belum
      diteruskan ke Warehouse (lihat guard di bawah).

    Status 'accepted' TANPA resolusi tidak valid (rsm_approve_final() dan
    rsm_approve_resolusi() mewajibkan resolusi sudah ada) — ditolak 400.
    """
    await require_permission(kode_role, "fkp.resolution.manage", db)

    fkp = await _get_or_404(fkp_id, db, for_update=True)

    # Ambil resolusi yang sudah ada
    r = await db.execute(select(FkpResolution).where(FkpResolution.fkp_id == fkp_id))
    resolusi_existing = r.scalar_one_or_none()
    is_edit = resolusi_existing is not None

    # ── Tentukan field yang boleh disimpan berdasarkan status ─────────────
    FASE_1_FIELDS = {
        "tipe_resolusi", "metode_penanganan_fisik", "detail_penanganan",
        "lokasi_pemusnahan", "tanggal_pemusnahan", "keterangan",
        "persentase_kompensasi_disetujui",
    }

    FASE_2_PEMUSNAHAN = {"tanggal_pemusnahan", "lokasi_pemusnahan"}
    FASE_2_TUKAR_BARANG   = {"nomor_do", "ekspedisi", "resi_pengiriman",
                             "nomor_surat_jalan", "tanggal_pengiriman", "keterangan"} | FASE_2_PEMUSNAHAN
    FASE_2_POTONG_TAGIHAN = {"nama_bank", "nomor_rekening", "atas_nama",
                             "nomor_nota_retur", "keterangan"} | FASE_2_PEMUSNAHAN

    # Status di mana Fase 1 (buat/edit tipe_resolusi + qty_disetujui) valid:
    # jalur approval Direktur (INVESTIGATED, RSM_APPROVAL_RESOLUSI) dan jalur approval RSM
    # (RSM_APPROVAL_FINAL).
    STATUS_FASE_1 = [
        FkpStatus.INVESTIGATED,
        FkpStatus.RSM_APPROVAL_RESOLUSI,
        FkpStatus.RSM_APPROVAL_FINAL,
    ]

    # ── Tentukan field_diizinkan berdasarkan status ───────────────────────
    if fkp.status in STATUS_FASE_1:
        field_diizinkan = FASE_1_FIELDS

    elif fkp.status == FkpStatus.ACCEPTED:
        if not resolusi_existing:
            raise HTTPException(
                status_code=400,
                detail="FKP berstatus 'accepted' tetapi resolusinya belum ada. Hubungi admin.",
            )
        tipe = resolusi_existing.tipe_resolusi
        if tipe == TipeResolusi.TUKAR_BARANG:
            field_diizinkan = FASE_2_TUKAR_BARANG
        elif tipe == TipeResolusi.POTONG_TAGIHAN:
            field_diizinkan = FASE_2_POTONG_TAGIHAN
        else:
            raise HTTPException(
                status_code=400,
                detail=f"tipe_resolusi '{tipe}' tidak didukung. Hubungi admin untuk migrasi data.",
            )

    else:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Resolusi tidak bisa diubah pada status '{fkp.status}'. "
                f"Gunakan status 'investigated', 'rsm_approval_resolusi', atau "
                f"'rsm_approval_final' (jalur approval RSM) untuk membuat resolusi, "
                f"atau 'accepted' untuk mengisi detail eksekusi."
            )
        )

    # ── Filter: buang field di luar yang diizinkan ────────────────────────
    # exclude item_qty_disetujui karena diproses terpisah, bukan masuk ke resolusi
    semua_data = data.model_dump(exclude_none=True, exclude={"item_qty_disetujui"})
    data_tersaring = {k: v for k, v in semua_data.items() if k in field_diizinkan}

    if not data_tersaring and not data.item_qty_disetujui:
        raise HTTPException(
            status_code=400,
            detail=f"Tidak ada field valid yang dikirim untuk status '{fkp.status}'."
        )

    # ── Validasi Fase 1 ───────────────────────────────────────────────────
    if fkp.status in STATUS_FASE_1:

        # Wajib tipe + metode saat buat baru
        if not is_edit:
            if "tipe_resolusi" not in data_tersaring:
                raise HTTPException(status_code=400, detail="tipe_resolusi wajib diisi.")
            if "metode_penanganan_fisik" not in data_tersaring:
                raise HTTPException(status_code=400, detail="metode_penanganan_fisik wajib diisi.")

        # Tentukan nilai efektif (baru override existing)
        tipe_efektif = data_tersaring.get("tipe_resolusi") or \
                       getattr(resolusi_existing, "tipe_resolusi", None)
        metode_efektif = data_tersaring.get("metode_penanganan_fisik") or \
                         getattr(resolusi_existing, "metode_penanganan_fisik", None)

        # Wajib persentase untuk potong_tagihan
        if tipe_efektif == TipeResolusi.POTONG_TAGIHAN:
            persen_baru = data_tersaring.get("persentase_kompensasi_disetujui")
            persen_existing = getattr(resolusi_existing, "persentase_kompensasi_disetujui", None)
            if not (persen_baru or persen_existing):
                raise HTTPException(
                    status_code=400,
                    detail="persentase_kompensasi_disetujui wajib diisi untuk resolusi potong_tagihan."
                )

        # Wajib lokasi jika dimusnahkan
        if metode_efektif == MetodePenangananFisik.DIMUSNAHKAN:
            lokasi_baru = data_tersaring.get("lokasi_pemusnahan")
            lokasi_existing = getattr(resolusi_existing, "lokasi_pemusnahan", None)
            if not (lokasi_baru or lokasi_existing):
                raise HTTPException(
                    status_code=400,
                    detail="lokasi_pemusnahan wajib diisi jika metode_penanganan_fisik = 'dimusnahkan'."
                )

        # Validasi konsistensi rekomendasi item
        await _validasi_konsistensi_rekomendasi(fkp_id, tipe_efektif, db)

        # qty_disetujui diisi DI SINI (Fase 1), sebelum approval final.
        # Hanya relevan untuk tukar_barang (potong_tagihan tidak punya qty per item).
        if tipe_efektif == TipeResolusi.TUKAR_BARANG and data.item_qty_disetujui:
            await _validasi_dan_simpan_qty_disetujui(
                fkp_id, data.item_qty_disetujui, db,
                sudah_approval_final=(fkp.status == FkpStatus.ACCEPTED)
            )

    # ── Validasi Fase 2 ───────────────────────────────────────────────────
    if fkp.status == FkpStatus.ACCEPTED:
        tipe = resolusi_existing.tipe_resolusi

        if tipe == TipeResolusi.POTONG_TAGIHAN:
            wajib = ["nama_bank", "nomor_rekening", "atas_nama"]
            kurang = [
                f for f in wajib
                if f not in data_tersaring
                and not getattr(resolusi_existing, f, None)
            ]
            if kurang:
                raise HTTPException(
                    status_code=400,
                    detail=f"Field wajib untuk potong_tagihan belum diisi: {', '.join(kurang)}."
                )

        if tipe == TipeResolusi.TUKAR_BARANG:
            # Gate kunci setelah diteruskan ke Warehouse
            if resolusi_existing.diteruskan_ke_warehouse and data.item_qty_disetujui:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Qty disetujui sudah dikunci — FKP ini sudah diteruskan "
                        "ke Warehouse dan tidak bisa diubah dari sini."
                    ),
                )
            await _validasi_dan_simpan_qty_disetujui(
                fkp_id, data.item_qty_disetujui, db,
                sudah_approval_final=(fkp.status == FkpStatus.ACCEPTED)
            )

    # ── Simpan resolusi ke DB ─────────────────────────────────────────────
    FIELDS_FKP_COMPLAINT = {"nomor_surat_jalan"}
 
    data_untuk_resolusi = {
        k: v for k, v in data_tersaring.items()
        if k not in FIELDS_FKP_COMPLAINT
    }
 
    if is_edit:
        for k, v in data_untuk_resolusi.items():
            setattr(resolusi_existing, k, v)
        db.add(resolusi_existing)
    else:
        db.add(FkpResolution(
            fkp_id=fkp_id,
            dibuat_oleh=user.id,
            **data_untuk_resolusi,
        ))
 
    if "nomor_surat_jalan" in data_tersaring:
        fkp.nomor_surat_jalan = data_tersaring["nomor_surat_jalan"]

    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)

    # Jalur approval RSM: resolusi hanya dibuat SEKALI, sebelum RSM approve —
    # inilah pemicu notifikasi ke QC untuk investigasi paralel. Tidak lewat
    # kirim_notifikasi_transisi(): qc_catatan_investigasi_paralel() tidak mengubah
    # status, dan buat_resolusi() sendiri juga tidak mengubah status.
    if fkp.status == FkpStatus.RSM_APPROVAL_FINAL and not is_edit:
        from app.services.notification_service import notify_roles, TipeNotifikasi
        await notify_roles(
            db, fkp.id, ["qc"],
            "FKP Jalur Approval RSM — Investigasi Paralel",
            f"FKP {fkp.nomor_fkp} sudah punya resolusi dari Admin HO dan menunggu "
            f"approval RSM. Silakan isi catatan investigasi paralel — tidak menahan "
            f"proses approval.",
            TipeNotifikasi.NEED_ACTION,
        )

    await db.commit()
    return await _load_fkp_detail(fkp.id, db)

async def teruskan_ke_warehouse(fkp_id, data: "TeruskanWarehouseRequest", user, kode_role, db):
    """
    Handoff eksplisit Admin HO -> Warehouse untuk resolusi tukar_barang.
    Permission "warehouse.surat_jalan.create" DICABUT dari admin_ho (lihat
    seed permission) — admin_ho hanya bisa sampai di sini, tidak bisa
    create_surat_jalan() sendiri.

    Tidak mengubah fkp.status — murni menyalakan flag di FkpResolution.
    Sekali true, qty_disetujui terkunci (lihat guard di buat_resolusi()
    Fase 2 tukar_barang) dan create_surat_jalan() baru bisa dipanggil
    (lihat guard di warehouse_service.py).
    """
    await require_permission(kode_role, "fkp.teruskan_ke_warehouse", db)

    fkp = await _get_or_404(fkp_id, db, for_update=True)
    if fkp.status not in (FkpStatus.ACCEPTED, FkpStatus.IN_PROCESS):
        raise HTTPException(
            status_code=400,
            detail=f"FKP harus berstatus 'accepted' atau 'in_process', bukan '{fkp.status}'.",
        )

    r = await db.execute(select(FkpResolution).where(FkpResolution.fkp_id == fkp_id))
    resolusi = r.scalar_one_or_none()
    if not resolusi:
        raise HTTPException(status_code=400, detail="Resolusi belum dibuat untuk FKP ini.")
    if resolusi.tipe_resolusi != TipeResolusi.TUKAR_BARANG:
        raise HTTPException(
            status_code=400,
            detail="Teruskan ke Warehouse hanya berlaku untuk resolusi tukar_barang.",
        )
    if resolusi.diteruskan_ke_warehouse:
        raise HTTPException(status_code=400, detail="FKP ini sudah diteruskan ke Warehouse sebelumnya.")

    # Reuse validasi yang sama dengan buat_resolusi() — pastikan SEMUA item
    # 'diterima' sudah punya qty_disetujui. Dipanggil dengan None supaya
    # masuk cabang validasi-saja (tidak menyimpan apa pun). Ini satu-satunya
    # titik yang MEWAJIBKAN qty_disetujui terisi (di Fase 1 masih opsional).
    await _validasi_dan_simpan_qty_disetujui(fkp_id, None, db)

    r_items = await db.execute(select(FkpItem).where(FkpItem.fkp_id == fkp_id))
    ada_item_layak = any(
        i.status_item == StatusItem.DITERIMA and (i.qty_disetujui or 0) > 0
        for i in r_items.scalars().all()
    )
    if not ada_item_layak:
        raise HTTPException(
            status_code=400,
            detail=("Tidak ada item yang disetujui untuk dikirim (semua item ditolak "
                    "atau qty_disetujui = 0). Tidak ada yang perlu diteruskan ke Warehouse."),
        )

    resolusi.diteruskan_ke_warehouse = True
    resolusi.tanggal_diteruskan_ke_warehouse = datetime.now(timezone.utc)
    resolusi.diteruskan_oleh = user.id
    db.add(resolusi)

    # Bukan transisi status (status_lama == status_baru), tapi tetap
    # dicatat di timeline supaya jejak "siapa & kapan meneruskan" terlihat
    # di Riwayat Status FE.
    await _log(db, fkp.id, fkp.status, fkp.status, user.id,
               data.catatan or "Diteruskan ke Warehouse untuk pembuatan Surat Jalan.")

    from app.services.notification_service import notify_roles, TipeNotifikasi
    await notify_roles(
        db, fkp.id, ["warehouse", "superadmin"],
        "FKP siap dibuatkan Surat Jalan",
        f"FKP {fkp.nomor_fkp} sudah diteruskan Admin HO — silakan buat Surat Jalan.",
        TipeNotifikasi.WAREHOUSE_SJ,
    )

    await db.commit()
    return await _load_fkp_detail(fkp.id, db)

async def proses_finance(fkp_id, catatan_finance, user, kode_role, db):
    """
    Finance konfirmasi pembayaran cashback potong_tagihan SUDAH ditransfer.

    Parameter `nilai_nota_penjualan` TIDAK diterima di sini. nilai_nota_penjualan
    & nilai_cashback HANYA dihitung sekali, di terbitkan_invoice() saat
    invoice pertama kali diterbitkan. proses_finance() murni konfirmasi
    pembayaran sudah ditransfer (langkah terpisah dari penerbitan invoice).
    Signature ini harus tetap cocok dengan pemanggilnya di
    api/endpoints/fkp.py (endpoint /finance/proses).
    """
    await require_permission(kode_role, "fkp.finance.process", db)

    fkp = await _get_or_404(fkp_id, db, for_update=True)

    if fkp.status != FkpStatus.IN_PROCESS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Proses finance hanya bisa dilakukan saat status 'in_process' "
                f"(invoice harus diterbitkan lebih dulu lewat POST "
                f".../finance/invoice). Status saat ini: '{fkp.status}'."
            ),
        )

    r = await db.execute(select(FkpResolution).where(FkpResolution.fkp_id == fkp_id))
    resolusi = r.scalar_one_or_none()
    if not resolusi:
        raise HTTPException(status_code=404, detail="Resolusi belum dibuat untuk FKP ini.")

    if resolusi.tipe_resolusi != TipeResolusi.POTONG_TAGIHAN:
        raise HTTPException(
            status_code=400,
            detail="Proses finance hanya berlaku untuk resolusi tipe 'potong_tagihan'.",
        )

    if resolusi.diproses_finance:
        raise HTTPException(
            status_code=400,
            detail="Pembayaran cashback FKP ini sudah dikonfirmasi Finance sebelumnya.",
        )

    # nilai_nota_penjualan & nilai_cashback seharusnya sudah diisi oleh
    # terbitkan_invoice() sebelum FKP bisa mencapai status in_process untuk
    # resolusi potong_tagihan. Guard ini jaga-jaga kalau ada data
    # lama/tidak konsisten, bukan jalur normal.
    if resolusi.nilai_cashback is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "nilai_cashback belum tersedia pada resolusi ini. Invoice harus "
                "diterbitkan terlebih dahulu lewat POST .../finance/invoice."
            ),
        )

    resolusi.catatan_finance        = catatan_finance
    resolusi.diproses_finance       = True
    resolusi.tanggal_proses_finance = datetime.now(timezone.utc)
    resolusi.finance_user_id        = user.id

    db.add(resolusi)
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    # Bukan transisi status, tapi dicatat di timeline supaya jejak
    # "siapa & kapan Finance mengonfirmasi" terlihat (sama seperti teruskan_ke_warehouse).
    await _log(db, fkp.id, fkp.status, fkp.status, user.id,
               catatan_finance or "Pembayaran cashback dikonfirmasi Finance.")
    await db.commit()
    return await _load_fkp_detail(fkp.id, db)

async def terbitkan_invoice(fkp_id, nomor_invoice, nilai_nota_penjualan, catatan, user, kode_role, db):
    """
    Trigger accepted → in_process khusus resolusi potong_tagihan. Generate
    PDF invoice via WeasyPrint, simpan sebagai FkpDocument (bukan
    FkpAttachment — dokumen formal).

    nomor_invoice input MANUAL (sama seperti nomor_surat_jalan/
    nomor_tanda_terima, tidak ada auto-generate).

    nilai_nota_penjualan WAJIB diisi di sini. nilai_cashback dihitung &
    disimpan ke resolusi SEBELUM PDF digenerate (supaya PDF & notifikasi
    menampilkan angka yang benar), dengan rumus:
    nilai_nota_penjualan × (persentase_kompensasi_disetujui / 100).

    Langkah berikutnya SETELAH ini adalah proses_finance() untuk konfirmasi
    pembayaran benar-benar sudah ditransfer (hanya valid saat in_process).
    """
    await require_permission(kode_role, "fkp.finance.invoice", db)

    fkp = await _get_or_404(fkp_id, db, for_update=True)
    if fkp.status != FkpStatus.ACCEPTED:
        raise HTTPException(
            status_code=400,
            detail=f"FKP harus berstatus 'accepted', bukan '{fkp.status}'.",
        )

    r = await db.execute(select(FkpResolution).where(FkpResolution.fkp_id == fkp_id))
    resolusi = r.scalar_one_or_none()
    if not resolusi:
        raise HTTPException(status_code=400, detail="Resolusi belum dibuat untuk FKP ini.")

    if resolusi.tipe_resolusi != TipeResolusi.POTONG_TAGIHAN:
        raise HTTPException(
            status_code=400,
            detail="Endpoint ini hanya untuk resolusi bertipe 'potong_tagihan'.",
        )

    if not resolusi.persentase_kompensasi_disetujui:
        raise HTTPException(
            status_code=400,
            detail="persentase_kompensasi_disetujui belum diisi pada resolusi.",
        )
    
    kurang = [f for f in ("nama_bank", "nomor_rekening", "atas_nama")
              if not getattr(resolusi, f, None)]
    if kurang:
        raise HTTPException(
            400,
            f"Data rekening belum lengkap: {', '.join(kurang)}. Lengkapi lewat resolusi (status accepted) sebelum menerbitkan invoice.",
        )

    # nilai_nota_penjualan wajib > 0 (sudah divalidasi juga di schema
    # InvoiceCreateRequest, dicek ulang di sini karena fungsi service bisa
    # dipanggil dari jalur lain di luar endpoint HTTP).
    if nilai_nota_penjualan is None or nilai_nota_penjualan <= 0:
        raise HTTPException(status_code=400, detail="nilai_nota_penjualan harus lebih dari 0.")

    if not nomor_invoice or not nomor_invoice.strip():
        raise HTTPException(status_code=400, detail="nomor_invoice wajib diisi.")

    r_dup = await db.execute(
        select(FkpDocument).where(
            FkpDocument.tipe_dokumen == TipeDokumen.INVOICE_POTONG_TAGIHAN,
            FkpDocument.nomor_dokumen == nomor_invoice,
        )
    )
    if r_dup.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Nomor invoice '{nomor_invoice}' sudah digunakan.")

    # Hitung & simpan nilai_nota_penjualan/nilai_cashback SEBELUM PDF
    # digenerate — template invoice (invoice_pdf_service.py) membaca kedua
    # field ini langsung dari objek `resolusi`.
    resolusi.nilai_nota_penjualan = nilai_nota_penjualan
    resolusi.nilai_cashback = (
        Decimal(str(nilai_nota_penjualan)) *
        resolusi.persentase_kompensasi_disetujui / 100
    ).quantize(Decimal("0.01"))
    
    db.add(resolusi)
    await db.flush()

    invoice_doc = FkpDocument(
        fkp_id=fkp_id,
        tipe_dokumen=TipeDokumen.INVOICE_POTONG_TAGIHAN,
        nomor_dokumen=nomor_invoice,
        tanggal_dokumen=datetime.now(timezone.utc).date(),
        url_file="pending",  # diisi setelah PDF berhasil digenerate
        dibuat_oleh=user.id,
    )
    db.add(invoice_doc)
    await db.flush()

    from app.services.invoice_pdf_service import generate_and_save_invoice_pdf
    url_file = await generate_and_save_invoice_pdf(fkp, resolusi, invoice_doc, user, db)
    invoice_doc.url_file = url_file
    db.add(invoice_doc)

    lama = fkp.status
    fkp.status = FkpStatus.IN_PROCESS
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await _log(db, fkp.id, lama, FkpStatus.IN_PROCESS, user.id,
               catatan or f"Invoice {nomor_invoice} diterbitkan, menunggu konfirmasi pembayaran.")
    await kirim_notifikasi_transisi(db, fkp, lama, FkpStatus.IN_PROCESS, user)

    # Notifikasi invoice diterbitkan: admin_ho, rsm
    from app.services.notification_service import notify_roles, TipeNotifikasi
    await notify_roles(
        db, fkp.id, ["admin_ho", "rsm"],
        "Invoice diterbitkan",
        f"Invoice potong tagihan FKP {fkp.nomor_fkp} diterbitkan. Nilai: {resolusi.nilai_cashback}",
        TipeNotifikasi.INVOICE,
    )

    await db.commit()
    await db.refresh(invoice_doc)

    # Kembalikan dict eksplisit (bukan menempelkan atribut baru ke instance
    # FkpDocument) supaya FE langsung dapat nilai_cashback tanpa request
    # tambahan — lihat InvoiceResponse di schemas/finance.py. Dict biasa
    # lebih aman divalidasi Pydantic dibanding menambah atribut ad-hoc ke
    # object model SQLAlchemy/SQLModel.
    return {
        "id": invoice_doc.id,
        "fkp_id": invoice_doc.fkp_id,
        "tipe_dokumen": invoice_doc.tipe_dokumen,
        "nomor_dokumen": invoice_doc.nomor_dokumen,
        "tanggal_dokumen": invoice_doc.tanggal_dokumen,
        "url_file": invoice_doc.url_file,
        "dibuat_oleh": invoice_doc.dibuat_oleh,
        "created_at": invoice_doc.created_at,
        "nilai_nota_penjualan": resolusi.nilai_nota_penjualan,
        "nilai_cashback": resolusi.nilai_cashback,
    }
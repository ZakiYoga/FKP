"""
FKP Service — state machine engine.

Alur status lengkap:
  draft
    → submitted                   (distributor/outlet/sc_spv/apsm)
    → apsm_reviewed               (apsm)           ← bisa minta revisi ke submitted
    → rsm_approval_investigasi    (admin_ho)        ← bisa minta revisi ke submitted
    → in_investigation            (rsm approve)     ← rsm bisa revisi ke apsm_reviewed
    → investigated                (qc)
    → rsm_approval_resolusi       (admin_ho)        ← rsm bisa revisi ke investigated
    → direktur_approval           (rsm approve)
    → accepted                    (direktur approve)
    → in_process                  (admin_ho — tukar_barang / potong_tagihan)
                                   atau langsung closed (pemusnahan)
    → closed                      (admin_ho)

  Need revision — mundur 1 langkah ke pihak yang bertanggung jawab:
    apsm_reviewed            → need_revision → kembali ke submitted
    rsm_approval_investigasi → need_revision → kembali ke submitted (Admin HO)
    rsm_approval_investigasi → kembali ke apsm_reviewed (RSM minta ke APSM)
    rsm_approval_resolusi    → need_revision → kembali ke investigated

── RBAC dinamis (migrasi) ─────────────────────────────────────────────────
Permission per role TIDAK lagi hardcode sebagai dict Python di sini.
Dua lapis akses, jangan dicampur:
  1. Action/Feature Permission → tabel `permissions` + `role_permissions`,
     dicek lewat require_permission(). Bisa diatur lewat dashboard admin.
  2. Data Scope / Row-level & Ownership → TETAP di kode (fungsi list_fkp,
     list_fkp_penerbitan, get_fkp_detail, validate_fkp_formulir_access, dan
     _check_ownership() untuk WRITE). Tidak masuk dashboard karena butuh
     JOIN/perbandingan data, bukan sekadar boolean role.

VALID_TRANSITIONS dan REVISION_TARGETS tetap hardcode — itu business
workflow (urutan status), bukan soal "siapa boleh apa".

── PERBAIKAN LANJUTAN (audit keamanan) ────────────────────────────────────
  - REVISION_TARGETS: ditambah (APSM_REVIEWED, "admin_ho") -> SUBMITTED.
    Sebelumnya admin_ho tidak punya jalur mengembalikan FKP ke APSM saat
    status masih apsm_reviewed (hanya apsm sendiri/superadmin yang bisa).
  - apsm_review(): ditambah _check_apsm_area_scope() — sebelumnya apsm bisa
    mereview FKP distributor mana pun (di luar area-nya) selama punya
    permission "fkp.apsm_review", karena tidak ada pengecekan data-scope
    sama sekali di fungsi ini (berbeda dengan list_fkp/get_fkp_detail yang
    sudah dibatasi per-area).
"""
import uuid
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException
from sqlmodel import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.services.authz_helpers import is_superadmin

from app.models.fkp import (
    FkpComplaint, FkpItem, FkpStatus,
    FkpStatusLog, FkpResolution, FkpAttachment,
    FkpDocument,
    TipeResolusi, MetodePenangananFisik, TipeDokumen,
)
from app.models.distributor import Distributor, DistributorUser
from app.models.outlet import Outlet
from app.models.sc_spv import ScSpvDistributor
from app.models.user import User
from app.schemas.fkp import (
    FkpCreate, FkpUpdate,
    FkpItemCreate, FkpItemUpdate,
    ApsmReviewRequest, AdminHoReviewRequest,
    RsmApproveRequest, DirekturApproveRequest,
    InvestigasiQcRequest, RejectRequest, RevisionRequest,
    UpdatePengirimanRequest,
)
from app.utils.fkp_number import generate_nomor_fkp
from app.services.notification_service import kirim_notifikasi_transisi
from app.services.email_trigger_service import trigger_email_after_transition
from app.services.permission_service import require_permission
from app.services.authz_helpers import get_apsm_distributor_ids

# ─── DATA SCOPE (Lapis 2) — TETAP DI KODE, TIDAK MASUK DASHBOARD ─────────────
# Dipakai oleh list_fkp, list_fkp_penerbitan, get_fkp_detail,
# validate_fkp_formulir_access — JANGAN DIUBAH, scope baca hierarki ini
# sudah benar dan terpisah dari RBAC action permission.
# [FIX BUG KRITIS #3 — audit modul Sample Shipment/Warehouse] "warehouse"
# ditambahkan ke sini. Sebelumnya role ini TIDAK termasuk data-scope global
# padahal §1.6 dokumen rencana modul mendefinisikan scope warehouse sebagai
# GLOBAL (single entity 1 HO, tidak dibatasi per lokasi gudang). Akibat
# sebelumnya: list_fkp()/list_fkp_penerbitan() selalu return [] untuk
# warehouse, dan validate_fkp_formulir_access() 403. get_fkp_detail()
# kebetulan tetap lolos (tidak ada else-raise di situ) — perilaku sekarang
# dibuat konsisten & eksplisit lewat baris ini, bukan lagi kebetulan.
_ROLE_GLOBAL_ACCESS = {"admin_ho", "qc", "rsm", "direktur", "superadmin", "finance", "warehouse"}
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


# ─── STATE MACHINE ────────────────────────────────────────────────────────────

VALID_TRANSITIONS = {
    FkpStatus.DRAFT:                    [FkpStatus.SUBMITTED],
    FkpStatus.SUBMITTED:                [FkpStatus.APSM_REVIEWED, FkpStatus.NEED_REVISION],
    FkpStatus.APSM_REVIEWED:            [
        FkpStatus.RSM_APPROVAL_INVESTIGASI,
        FkpStatus.NEED_REVISION,
        FkpStatus.REJECTED,
    ],
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
    FkpStatus.RSM_APPROVAL_RESOLUSI:    [
        FkpStatus.DIREKTUR_APPROVAL,
        FkpStatus.INVESTIGATED,
        FkpStatus.REJECTED,
    ],
    FkpStatus.DIREKTUR_APPROVAL:        [FkpStatus.ACCEPTED, FkpStatus.REJECTED],
    FkpStatus.ACCEPTED:                 [FkpStatus.IN_PROCESS],
    FkpStatus.IN_PROCESS:               [FkpStatus.CLOSED],
    FkpStatus.NEED_REVISION:            [FkpStatus.SUBMITTED],
    FkpStatus.REJECTED:                 [],
    FkpStatus.CLOSED:                   [],
}

# Mapping status tujuan -> permission code. Dicek via require_permission()
# di _validate_transition(). VALID_TRANSITIONS (alur status) TETAP hardcode
# karena itu business flow/urutan kerja, BUKAN soal "siapa boleh apa".
STATUS_TO_PERMISSION = {
    FkpStatus.SUBMITTED:                "fkp.submit",
    FkpStatus.APSM_REVIEWED:            "fkp.apsm_review",
    FkpStatus.RSM_APPROVAL_INVESTIGASI: "fkp.admin_ho_review",
    FkpStatus.IN_INVESTIGATION:         "fkp.rsm_approve_investigasi",
    FkpStatus.INVESTIGATED:             "fkp.qc_investigasi",
    FkpStatus.RSM_APPROVAL_RESOLUSI:    "fkp.admin_ho_request_resolusi_approval",
    FkpStatus.DIREKTUR_APPROVAL:        "fkp.rsm_approve_resolusi",
    FkpStatus.ACCEPTED:                 "fkp.direktur_approve",
    FkpStatus.IN_PROCESS:               "fkp.resolution.manage",
    FkpStatus.NEED_REVISION:            "fkp.request_revision",
    FkpStatus.REJECTED:                 "fkp.reject",
    FkpStatus.CLOSED:                   "fkp.close",
}

# Format: { (status_asal, kode_role): status_tujuan }
# Business logic mundur (request_revision) — TETAP hardcode, bukan permission.
REVISION_TARGETS = {
    (FkpStatus.SUBMITTED,                "apsm"):       FkpStatus.DRAFT,
    (FkpStatus.APSM_REVIEWED,            "apsm"):       FkpStatus.SUBMITTED,
    (FkpStatus.APSM_REVIEWED,            "admin_ho"):   FkpStatus.SUBMITTED,
    (FkpStatus.APSM_REVIEWED,            "superadmin"): FkpStatus.SUBMITTED,
    (FkpStatus.RSM_APPROVAL_INVESTIGASI, "admin_ho"):   FkpStatus.SUBMITTED,
    (FkpStatus.RSM_APPROVAL_INVESTIGASI, "rsm"):        FkpStatus.APSM_REVIEWED,
    (FkpStatus.RSM_APPROVAL_INVESTIGASI, "superadmin"): FkpStatus.SUBMITTED,
    (FkpStatus.RSM_APPROVAL_RESOLUSI,    "rsm"):        FkpStatus.INVESTIGATED,
    (FkpStatus.RSM_APPROVAL_RESOLUSI,    "admin_ho"):   FkpStatus.INVESTIGATED,
    (FkpStatus.RSM_APPROVAL_RESOLUSI,    "superadmin"): FkpStatus.INVESTIGATED,
}


# ─── HELPERS ──────────────────────────────────────────────────────────────────

async def _validate_transition(fkp: FkpComplaint, new_status: str, kode_role: str, db: AsyncSession):
    allowed_next = VALID_TRANSITIONS.get(fkp.status, [])
    if new_status not in allowed_next:
        raise HTTPException(
            status_code=400,
            detail=f"Transisi dari '{fkp.status}' ke '{new_status}' tidak diizinkan.",
        )

    permission_code = STATUS_TO_PERMISSION.get(new_status)
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
    PERBAIKAN: apsm_review() sebelumnya hanya dijaga oleh permission action
    ("fkp.apsm_review") tanpa pengecekan data-scope, sehingga apsm bisa
    mereview FKP distributor mana pun di luar area-nya selama dia punya
    permission tersebut. list_fkp/get_fkp_detail/create_fkp sudah membatasi
    apsm ke distributor dalam area-nya — fungsi ini menutup gap yang sama
    untuk aksi tulis apsm_review, memakai resolver scope terpusat di
    authz_helpers (sama yang dipakai upload_service & outlet_register_service)
    supaya tidak ada logic scope APSM yang berbeda-beda di tempat lain.
    """
    if kode_role != "apsm":
        return
    dist_ids = await get_apsm_distributor_ids(user.id, db)
    if fkp.distributor_id not in dist_ids:
        raise HTTPException(
            status_code=403,
            detail="FKP ini di luar area yang Anda tangani.",
        )


async def _log(db, fkp_id, status_lama, status_baru, changed_by, catatan=None):
    db.add(FkpStatusLog(
        fkp_id=fkp_id, status_lama=status_lama, status_baru=status_baru,
        catatan=catatan, changed_by=changed_by,
    ))


async def _get_or_404(fkp_id, db) -> FkpComplaint:
    r = await db.execute(select(FkpComplaint).where(FkpComplaint.id == fkp_id))
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
            selectinload(FkpComplaint.distributor),
            selectinload(FkpComplaint.outlet),
            selectinload(FkpComplaint.status_logs),
            selectinload(FkpComplaint.resolution),
            selectinload(FkpComplaint.attachments),
            selectinload(FkpComplaint.documents),
        )
    )
    return r.scalar_one()


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
    TIDAK DIUBAH — ownership check existing ini sudah benar, bukan
    permission RBAC biasa (pembuat dokumen tidak ditentukan oleh role).

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

    is_super = await is_superadmin(user, db)  # ← baru dicek setelah dokumen confirmed ada
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
    """
    from app.models.fkp import TipeResolusi

    if not tipe_resolusi_baru:
        return

    MAPPING = {
        "ganti_barang":       TipeResolusi.TUKAR_BARANG,
        "potong_tagihan":     TipeResolusi.POTONG_TAGIHAN,
        "musnahkan":          TipeResolusi.TIDAK_ADA_KOMPENSASI,
        "jual_pakan_ternak":  TipeResolusi.TIDAK_ADA_KOMPENSASI,
        "kirim_ke_ho":        TipeResolusi.TIDAK_ADA_KOMPENSASI,
    }

    r = await db.execute(select(FkpItem).where(FkpItem.fkp_id == fkp_id))
    items = r.scalars().all()

    tipe_dari_rekomendasi = {
        MAPPING[i.rekomendasi_kompensasi_admin_ho]
        for i in items
        if i.rekomendasi_kompensasi_admin_ho in MAPPING
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


async def _validasi_dan_simpan_qty_disetujui(fkp_id, item_qty_list, db):
    """
    Validasi dan simpan qty_disetujui per item untuk resolusi tukar_barang.
    Wajib dipanggil saat fase accepted.
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
        item.updated_at = datetime.now(timezone.utc)
        db.add(item)


# ─── LIST & DETAIL ────────────────────────────────────────────────────────────
# JANGAN DIUBAH — data-scope/hierarchy logic (Lapis 2), bukan action permission.

async def list_fkp(db, user, kode_role, status_filter=None, prioritas_filter=None):
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
        r = await db.execute(
            select(FkpResolution.fkp_id).where(
                FkpResolution.tipe_resolusi == "potong_tagihan"
            )
        )
        fkp_ids = r.scalars().all()
        if not fkp_ids:
            return []
        query = query.where(FkpComplaint.id.in_(fkp_ids))

        if status_filter and status_filter not in FkpStatus.FINANCE_VISIBLE:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Finance hanya bisa memfilter status: {FkpStatus.FINANCE_VISIBLE}. "
                    f"Status '{status_filter}' tidak relevan dengan role finance."
                ),
            )
    
    elif kode_role not in _ROLE_GLOBAL_ACCESS:
        return []

    if status_filter:
        query = query.where(FkpComplaint.status == status_filter)
    if prioritas_filter:
        query = query.where(FkpComplaint.prioritas == prioritas_filter)

    result = await db.execute(
        query
        .options(
            selectinload(FkpComplaint.distributor),
            selectinload(FkpComplaint.outlet),
        )
        .order_by(FkpComplaint.created_at.desc())
    )
    return result.scalars().all()

# ─── PENERBITAN FORMULIR ──────────────────────────────────────────────────────
# JANGAN DIUBAH — data-scope/hierarchy logic (Lapis 2).

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
    from app.models.fkp import FkpStatus

    DOWNLOADABLE = {
        FkpStatus.SUBMITTED, FkpStatus.APSM_REVIEWED,
        FkpStatus.RSM_APPROVAL_INVESTIGASI, FkpStatus.IN_INVESTIGATION,
        FkpStatus.INVESTIGATED, FkpStatus.RSM_APPROVAL_RESOLUSI,
        FkpStatus.DIREKTUR_APPROVAL, FkpStatus.ACCEPTED,
        FkpStatus.IN_PROCESS, FkpStatus.CLOSED, FkpStatus.REJECTED,
    }

    fkp = await _get_or_404(fkp_id, db)

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
    if kode_role in _ROLE_GLOBAL_ACCESS:
        return fkp  # akses penuh, tidak perlu cek lebih lanjut

    if kode_role == "outlet":
        r = await db.execute(
            select(Outlet).where(
                Outlet.pic_user_id == user.id,
                Outlet.id == fkp.outlet_id,
            )
        )
        if not r.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Akses ditolak.")

    elif kode_role == "distributor":
        r = await db.execute(
            select(DistributorUser).where(
                DistributorUser.user_id == user.id,
                DistributorUser.distributor_id == fkp.distributor_id,
            )
        )
        if not r.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Akses ditolak.")

    elif kode_role == "sc_spv":
        r = await db.execute(
            select(ScSpvDistributor).where(
                ScSpvDistributor.sc_spv_user_id == user.id,
                ScSpvDistributor.distributor_id == fkp.distributor_id,
            )
        )
        if not r.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Akses ditolak.")

    elif kode_role == "apsm":
        from app.models.area import Area
        # Single JOIN query — tidak ada N+1
        r = await db.execute(
            select(Distributor)
            .join(Area, Distributor.area_id == Area.id)
            .where(
                Area.pic_user_id == user.id,
                Distributor.id == fkp.distributor_id,
            )
        )
        if not r.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Akses ditolak.")

    else:
        raise HTTPException(status_code=403, detail="Akses ditolak.")

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
    JANGAN DIUBAH — data-scope/hierarchy logic (Lapis 2).
    """

    DOWNLOADABLE_STATUSES = [
        FkpStatus.SUBMITTED, FkpStatus.APSM_REVIEWED,
        FkpStatus.RSM_APPROVAL_INVESTIGASI, FkpStatus.IN_INVESTIGATION,
        FkpStatus.INVESTIGATED, FkpStatus.RSM_APPROVAL_RESOLUSI,
        FkpStatus.DIREKTUR_APPROVAL, FkpStatus.ACCEPTED,
        FkpStatus.IN_PROCESS, FkpStatus.CLOSED, FkpStatus.REJECTED,
    ]

    query = (
        select(FkpComplaint)
        .options(
            selectinload(FkpComplaint.distributor),
            selectinload(FkpComplaint.outlet),
        )
        .where(FkpComplaint.status.in_(DOWNLOADABLE_STATUSES))
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
        
        else:
            return []

    # ── Filter tambahan ────────────────────────────────────────────────────
    if status_filter:
        if status_filter not in DOWNLOADABLE_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Status '{status_filter}' tidak valid untuk halaman penerbitan."
            )
        query = query.where(FkpComplaint.status == status_filter)

    if tanggal_dari:
        try:
            d = date.fromisoformat(tanggal_dari)
            query = query.where(FkpComplaint.tanggal_pengajuan >= d)
        except ValueError:
            raise HTTPException(status_code=400, detail="Format tanggal_dari tidak valid (YYYY-MM-DD).")

    if tanggal_sampai:
        try:
            d = date.fromisoformat(tanggal_sampai)
            query = query.where(FkpComplaint.tanggal_pengajuan <= d)
        except ValueError:
            raise HTTPException(status_code=400, detail="Format tanggal_sampai tidak valid (YYYY-MM-DD).")

    query = query.order_by(FkpComplaint.tanggal_pengajuan.desc().nullslast(), FkpComplaint.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


# [FIX GAP #6 — Sample Shipment] Role yang TIDAK BOLEH melihat dokumen
# hasil pemeriksaan QC. Konsisten dengan sample_service._sanitize_for_external()
# yang sudah menyaring field narasi `hasil_pemeriksaan` — helper di bawah ini
# menutup celah yang sama untuk FILE-nya (FkpAttachment tipe hasil_pemeriksaan_qc),
# yang sebelumnya ikut terbawa apa adanya lewat _load_fkp_detail().
ROLE_HASIL_QC_HIDDEN = ("outlet", "distributor", "sc_spv")


def _filter_internal_documents(fkp: FkpComplaint, kode_role: str) -> FkpComplaint:
    """Buang attachment bertipe HASIL_PEMERIKSAAN_QC dari fkp.attachments
    sebelum diserialisasi ke response, khusus untuk role eksternal."""
    if kode_role in ROLE_HASIL_QC_HIDDEN:
        fkp.attachments = [
            a for a in fkp.attachments
            if a.tipe_dokumen != TipeDokumen.HASIL_PEMERIKSAAN_QC
        ]
    return fkp


async def get_fkp_detail(fkp_id, db, user, kode_role):
    fkp = await _get_or_404(fkp_id, db)

    if kode_role in _ROLE_GLOBAL_ACCESS:
        pass  # akses penuh

    elif kode_role == "outlet":
        r = await db.execute(
            select(Outlet.id).where(Outlet.pic_user_id == user.id)
        )
        outlet_ids_milik_user = set(r.scalars().all())
        if fkp.outlet_id not in outlet_ids_milik_user:
            raise HTTPException(status_code=403, detail="Akses ditolak.")

    elif kode_role == "distributor":
        r = await db.execute(select(DistributorUser).where(
            DistributorUser.user_id == user.id,
            DistributorUser.distributor_id == fkp.distributor_id,
        ))
        if not r.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Akses ditolak.")

    elif kode_role == "sc_spv":
        r = await db.execute(select(ScSpvDistributor).where(
            ScSpvDistributor.sc_spv_user_id == user.id,
            ScSpvDistributor.distributor_id == fkp.distributor_id,
        ))
        if not r.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Akses ditolak.")

    elif kode_role == "apsm":
        from app.models.area import Area
        r = await db.execute(
            select(Distributor)
            .join(Area, Distributor.area_id == Area.id)
            .where(
                Area.pic_user_id == user.id,
                Distributor.id == fkp.distributor_id,
            )
        )
        if not r.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Akses ditolak.")

    elif kode_role == "finance":
        r = await db.execute(select(FkpResolution).where(
            FkpResolution.fkp_id == fkp.id,
            FkpResolution.tipe_resolusi == "potong_tagihan",
        ))
        if not r.scalar_one_or_none():
            raise HTTPException(
                status_code=403,
                detail="Akses ditolak. Finance hanya bisa mengakses FKP dengan resolusi potong_tagihan.",
            )

    fkp_detail = await _load_fkp_detail(fkp.id, db)
    return _filter_internal_documents(fkp_detail, kode_role)


# ─── CRUD ─────────────────────────────────────────────────────────────────────

async def create_fkp(data: FkpCreate, user: User, kode_role: str, db) -> FkpComplaint:
    """Buat FKP baru dengan multi-item sekaligus."""
    await require_permission(kode_role, "fkp.create", db)

    if data.outlet_id:
        r = await db.execute(select(Outlet).where(Outlet.id == data.outlet_id))
        outlet = r.scalar_one_or_none()
        if not outlet:
            raise HTTPException(status_code=404, detail="Outlet tidak ditemukan.")
        if getattr(outlet, "status", None) not in (None, "aktif"):
            raise HTTPException(
                status_code=400,
                detail=f"Outlet '{outlet.nama_toko}' tidak aktif (status: {outlet.status}). "
                       "FKP hanya bisa dibuat untuk outlet dengan status aktif."
            )

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
            # FE mengirim outlet_id eksplisit -> wajib salah satu milik user ini.
            if data.outlet_id not in outlet_ids_milik_user:
                raise HTTPException(
                    status_code=403,
                    detail="Outlet yang dipilih bukan outlet Anda.",
                )
        elif len(outlets_milik_user) == 1:
            # Hanya 1 kandidat -> aman untuk auto-fill seperti behavior lama.
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

    nomor_fkp = await generate_nomor_fkp(db)
    fkp = FkpComplaint(
        nomor_fkp=nomor_fkp,
        distributor_id=data.distributor_id,
        outlet_id=data.outlet_id,
        submitted_by=user.id,
        prioritas=data.prioritas,
        catatan_distributor=data.catatan_distributor,
        status=FkpStatus.DRAFT,
        lokasi_pembelian=data.lokasi_pembelian,
    )
    db.add(fkp)
    await db.flush()

    for item_data in data.items:
        item = FkpItem(
            fkp_id=fkp.id,
            **item_data.model_dump(exclude_none=True),
        )
        db.add(item)

    await _log(db, fkp.id, None, FkpStatus.DRAFT, user.id, "FKP dibuat")
    await db.commit()
    return await _load_fkp_detail(fkp.id, db)

async def update_fkp(fkp_id, data: FkpUpdate, user, kode_role, db):
    fkp = await _get_or_404(fkp_id, db)

    await require_permission(kode_role, "fkp.update_header", db)
    _check_ownership(fkp, user, kode_role)

    if fkp.status not in FkpStatus.EDITABLE:
        raise HTTPException(status_code=400, detail=f"FKP status '{fkp.status}' tidak bisa diedit.")

    if kode_role == "outlet" and data.outlet_id is not None:
        r = await db.execute(select(Outlet).where(
            Outlet.id == data.outlet_id,
            Outlet.pic_user_id == user.id,
        ))
        outlet_baru = r.scalar_one_or_none()
        if not outlet_baru:
            raise HTTPException(status_code=403, detail="Outlet yang dipilih bukan outlet Anda.")
        # Pastikan outlet baru tetap di distributor yang sama dengan FKP
        if outlet_baru.distributor_id != fkp.distributor_id:
            raise HTTPException(
                status_code=400,
                detail="Outlet yang dipilih harus berada di distributor yang sama dengan FKP ini.",
            )

    for k, v in data.model_dump(exclude_none=True).items():
        setattr(fkp, k, v)
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await db.commit()
    return await _load_fkp_detail(fkp_id, db)


# ─── CRUD FKP ITEMS ───────────────────────────────────────────────────────────

async def add_fkp_item(fkp_id, item_data: dict, user, kode_role, db) -> FkpItem:
    fkp = await _get_or_404(fkp_id, db)

    await require_permission(kode_role, "fkp.item.create", db)
    _check_ownership(fkp, user, kode_role)

    if fkp.status not in FkpStatus.EDITABLE:
        raise HTTPException(status_code=400, detail="Item hanya bisa ditambah saat status draft atau need_revision.")
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
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(item, k, v)
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
    """Draft / Need Revision → Submitted."""
    fkp = await _get_or_404(fkp_id, db)

    # Ownership check — selain permission fkp.submit (dicek di _validate_transition),
    # user lain dari distributor/sc_spv/apsm yang sama tidak bisa submit draft
    # yang bukan buatannya.
    _check_ownership(fkp, user, kode_role)

    await _validate_transition(fkp, FkpStatus.SUBMITTED, kode_role, db)

    r = await db.execute(select(FkpAttachment).where(FkpAttachment.fkp_id == fkp_id))
    if not r.scalars().first():
        raise HTTPException(status_code=400, detail="Minimal 1 foto bukti wajib diupload sebelum submit.")

    r2 = await db.execute(select(FkpItem).where(FkpItem.fkp_id == fkp_id))
    if not r2.scalars().first():
        raise HTTPException(status_code=400, detail="FKP harus memiliki minimal 1 item produk.")

    lama = fkp.status
    fkp.status = FkpStatus.SUBMITTED
    if lama == FkpStatus.DRAFT:
        fkp.tanggal_pengajuan = datetime.now(timezone.utc)
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await _log(db, fkp.id, lama, FkpStatus.SUBMITTED, user.id)
    await kirim_notifikasi_transisi(db, fkp, lama, FkpStatus.SUBMITTED, user)
    
    await db.commit()
    await trigger_email_after_transition(db, fkp, lama, FkpStatus.SUBMITTED, user)
    return await _load_fkp_detail(fkp.id, db)


async def apsm_review(fkp_id, data: ApsmReviewRequest, user, kode_role, db):
    """Submitted → Apsm Reviewed."""
    fkp = await _get_or_404(fkp_id, db)
    await _validate_transition(fkp, FkpStatus.APSM_REVIEWED, kode_role, db)
    await _check_apsm_area_scope(fkp, user, kode_role, db)

    if data.item_reviews:
        for review in data.item_reviews:
            r = await db.execute(select(FkpItem).where(
                FkpItem.id == review.item_id,
                FkpItem.fkp_id == fkp_id,
            ))
            item = r.scalar_one_or_none()
            if item:
                # PERUBAHAN: gunakan field baru rekomendasi_penanganan_apsm & rekomendasi_kompensasi_apsm
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


async def admin_ho_review(fkp_id, data: AdminHoReviewRequest, user, kode_role, db):
    """Apsm Reviewed → Rsm Approval Investigasi."""
    fkp = await _get_or_404(fkp_id, db)
    await _validate_transition(fkp, FkpStatus.RSM_APPROVAL_INVESTIGASI, kode_role, db)

    if data.item_reviews:
        for review in data.item_reviews:
            r = await db.execute(select(FkpItem).where(
                FkpItem.id == review.item_id,
                FkpItem.fkp_id == fkp_id,
            ))
            item = r.scalar_one_or_none()
            if item:
                # PERUBAHAN: gunakan field baru rekomendasi_penanganan_admin_ho & rekomendasi_kompensasi_admin_ho
                if review.rekomendasi_penanganan_admin_ho is not None:
                    item.rekomendasi_penanganan_admin_ho = review.rekomendasi_penanganan_admin_ho
                if review.rekomendasi_kompensasi_admin_ho is not None:
                    item.rekomendasi_kompensasi_admin_ho = review.rekomendasi_kompensasi_admin_ho
                if review.catatan_admin_ho is not None:
                    item.catatan_admin_ho = review.catatan_admin_ho
                if review.persentase_disetujui_admin_ho is not None:
                    item.persentase_disetujui_admin_ho = review.persentase_disetujui_admin_ho
                item.updated_at = datetime.now(timezone.utc)
                db.add(item)

    lama = fkp.status
    fkp.status = FkpStatus.RSM_APPROVAL_INVESTIGASI
    fkp.catatan_admin = data.catatan_admin
    fkp.handled_by = user.id
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await _log(db, fkp.id, lama, FkpStatus.RSM_APPROVAL_INVESTIGASI, user.id, data.catatan_admin)
    await kirim_notifikasi_transisi(db, fkp, lama, FkpStatus.RSM_APPROVAL_INVESTIGASI, user)
    await db.commit()
    return await _load_fkp_detail(fkp.id, db)


async def rsm_approve_investigasi(fkp_id, data: RsmApproveRequest, user, kode_role, db):
    """RSM approve → In Investigation / tolak → Rejected."""
    fkp = await _get_or_404(fkp_id, db)
    new_status = FkpStatus.IN_INVESTIGATION if data.disetujui else FkpStatus.REJECTED
    await _validate_transition(fkp, new_status, kode_role, db)
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
    """QC selesai investigasi → Investigated."""
    fkp = await _get_or_404(fkp_id, db)
    await _validate_transition(fkp, FkpStatus.INVESTIGATED, kode_role, db)

    # [BARU — Modul Sample Shipment, Phase 4] Gate: tolak transisi ke
    # INVESTIGATED kalau masih ada sample yang belum selesai diperiksa
    # (status di luar SampleStatus.TERMINAL — examined/cancelled).
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

    if data.item_results:
        for result in data.item_results:
            r = await db.execute(select(FkpItem).where(
                FkpItem.id == result.item_id,
                FkpItem.fkp_id == fkp_id,
            ))
            item = r.scalar_one_or_none()
            if item:
                item.status_item = result.status_item
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


async def admin_ho_request_resolusi_approval(fkp_id, catatan, user, kode_role, db):
    """Investigated → Rsm Approval Resolusi."""
    fkp = await _get_or_404(fkp_id, db)
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
    """RSM approve → Direktur Approval / tolak → Rejected."""
    fkp = await _get_or_404(fkp_id, db)
    new_status = FkpStatus.DIREKTUR_APPROVAL if data.disetujui else FkpStatus.REJECTED
    await _validate_transition(fkp, new_status, kode_role, db)
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
    """Direktur Approval → Accepted / Rejected."""
    fkp = await _get_or_404(fkp_id, db)
    new_status = FkpStatus.ACCEPTED if data.disetujui else FkpStatus.REJECTED
    await _validate_transition(fkp, new_status, kode_role, db)
    lama = fkp.status
    fkp.status = new_status
    fkp.catatan_direktur = data.catatan
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
    """Minta revisi — tujuan mundur ditentukan otomatis dari REVISION_TARGETS."""
    await require_permission(kode_role, "fkp.request_revision", db)

    if not data.catatan:
        raise HTTPException(status_code=400, detail="Catatan alasan revisi wajib diisi.")
    fkp = await _get_or_404(fkp_id, db)

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
    """Tolak FKP dari status mana pun yang diizinkan."""
    if not data.catatan:
        raise HTTPException(status_code=400, detail="Alasan penolakan wajib diisi.")
    fkp = await _get_or_404(fkp_id, db)
    await _validate_transition(fkp, FkpStatus.REJECTED, kode_role, db)
    lama = fkp.status
    fkp.status = FkpStatus.REJECTED
    fkp.tanggal_selesai = datetime.now(timezone.utc)
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await _log(db, fkp.id, lama, FkpStatus.REJECTED, user.id, data.catatan)
    await kirim_notifikasi_transisi(db, fkp, lama, FkpStatus.REJECTED, user)
   
    await db.commit()
    await trigger_email_after_transition(db, fkp, lama, FkpStatus.REJECTED, user, data.catatan)
    return await _load_fkp_detail(fkp.id, db)


async def input_surat_jalan(fkp_id, nomor_surat_jalan, user, kode_role, db):
    """
    Admin HO input/update nomor surat jalan kapan pun.
    Sebelumnya GAP KEAMANAN — tidak ada cek role sama sekali. Sekarang
    ditambal dengan fkp.surat_jalan.input. Endpoint pemanggil fungsi ini
    juga perlu diupdate untuk meneruskan kode_role.
    """
    await require_permission(kode_role, "fkp.surat_jalan.input", db)

    fkp = await _get_or_404(fkp_id, db)
    fkp.nomor_surat_jalan = nomor_surat_jalan
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await db.commit()
    return await _load_fkp_detail(fkp_id, db)


async def close_fkp(fkp_id, catatan, user, kode_role, db):
    """In Process → Closed."""
    fkp = await _get_or_404(fkp_id, db)

    if fkp.status != FkpStatus.IN_PROCESS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"FKP tidak bisa ditutup dari status '{fkp.status}'. "
                f"Status harus 'in_process' sebelum bisa ditutup."
            )
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
    Satu fungsi, dua fase — dikontrol oleh status FKP.

    [DIUBAH — Modul Sample Shipment, Phase 2] Fungsi ini SEKARANG HANYA
    menyimpan data resolusi, TIDAK PERNAH mengubah fkp.status lagi — bahkan
    di Fase 2 (status 'accepted'). Transisi accepted → in_process sudah
    dipindah ke 3 endpoint terpisah sesuai tipe_resolusi:
      - tukar_barang                    → create_surat_jalan() (Phase 6)
      - potong_tagihan                  → terbitkan_invoice() (Phase 7)
      - pemusnahan / tidak_ada_kompensasi → confirm_resolusi() (Phase 5)

    FASE 1 — status 'investigated':
      Wajib: tipe_resolusi + metode_penanganan_fisik
      Boleh: lokasi_pemusnahan (wajib jika dimusnahkan), tanggal_pemusnahan, keterangan
      TIDAK boleh: field eksekusi (nomor_do, rekening, dll)

    FASE 2 — status 'accepted':
      Wajib: detail eksekusi sesuai tipe_resolusi
      TIDAK boleh ubah: tipe_resolusi, metode_penanganan_fisik
      Simpan data saja — TIDAK men-trigger status apa pun (lihat catatan di atas).

    EDIT TIPE — status 'rsm_approval_resolusi':
      Sama seperti Fase 1, hanya boleh ubah tipe/metode
    """
    await require_permission(kode_role, "fkp.resolution.manage", db)

    fkp = await _get_or_404(fkp_id, db)

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
    FASE_2_TUKAR_BARANG = {
        "nomor_do", "ekspedisi", "resi_pengiriman",
        "nomor_surat_jalan", "tanggal_pengiriman", "keterangan",
    }
    FASE_2_POTONG_TAGIHAN = {
        "nilai_cashback", "nama_bank", "nomor_rekening",
        "atas_nama", "nomor_nota_retur", "keterangan",
    }
    FASE_2_TIDAK_ADA = {"keterangan"}

    # ── Tentukan field_diizinkan berdasarkan status ───────────────────────
    if fkp.status in [FkpStatus.INVESTIGATED, FkpStatus.RSM_APPROVAL_RESOLUSI]:
        field_diizinkan = FASE_1_FIELDS

    elif fkp.status == FkpStatus.ACCEPTED:
        if not resolusi_existing:
            raise HTTPException(
                status_code=400,
                detail="Resolusi belum dibuat. Buat resolusi dulu saat status 'investigated'."
            )
        tipe = resolusi_existing.tipe_resolusi
        if tipe == TipeResolusi.TUKAR_BARANG:
            field_diizinkan = FASE_2_TUKAR_BARANG
        elif tipe == TipeResolusi.POTONG_TAGIHAN:
            field_diizinkan = FASE_2_POTONG_TAGIHAN
        else:
            field_diizinkan = FASE_2_TIDAK_ADA

    else:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Resolusi tidak bisa diubah pada status '{fkp.status}'. "
                f"Gunakan status 'investigated' untuk membuat resolusi, "
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
    if fkp.status in [FkpStatus.INVESTIGATED, FkpStatus.RSM_APPROVAL_RESOLUSI]:

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
            await _validasi_dan_simpan_qty_disetujui(
                fkp_id, data.item_qty_disetujui, db
            )

    # ── Simpan resolusi ke DB ─────────────────────────────────────────────
    FIELDS_FKP_COMPLAINT = {"nomor_surat_jalan"}
 
    data_untuk_resolusi = {
        k: v for k, v in data_tersaring.items()
        if k not in FIELDS_FKP_COMPLAINT
    }
 
    # ── Simpan resolusi ke DB ─────────────────────────────────────────────
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
 
    # ── [FIX Phase 2 — Modul Sample Shipment] ───────────────────────────────
    # SEBELUM: mengisi field eksekusi Fase 2 (selagi status ACCEPTED) otomatis
    # men-trigger transisi ke IN_PROCESS, untuk SEMUA tipe_resolusi sekaligus.
    #
    # SESUDAH: buat_resolusi() HANYA menyimpan data resolusi. Transisi
    # accepted → in_process sekarang jadi tanggung jawab 3 endpoint terpisah,
    # sesuai tipe_resolusi:
    #   - tukar_barang                    → POST /warehouse/surat-jalan
    #                                        (create_surat_jalan, Phase 6)
    #   - potong_tagihan                  → POST /fkp/{id}/finance/invoice
    #                                        (terbitkan_invoice, Phase 7)
    #   - pemusnahan / tidak_ada_kompensasi → POST /fkp/{id}/confirm-resolusi
    #                                        (confirm_resolusi, Phase 5)
    #
    # nomor_surat_jalan di fkp_complaints dipertahankan diisi (kalau dikirim)
    # untuk backward-compat FE lama — field otoritatif baru ada di
    # WarehouseSuratJalan.nomor_surat_jalan (Phase 6). Rencana deprecation
    # kolom ini mengikuti §8–§9 dokumen rencana modul.
    if "nomor_surat_jalan" in data_tersaring:
        fkp.nomor_surat_jalan = data_tersaring["nomor_surat_jalan"]

    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)

    await db.commit()
    return await _load_fkp_detail(fkp.id, db)


def _resolusi_terkunci(fkp_status: str) -> bool:
    """
    Kembalikan True jika resolusi sudah melewati tahap RSM approval
    dan tidak boleh diubah lagi.
    """
    STATUS_TERKUNCI = {
        FkpStatus.DIREKTUR_APPROVAL,
        FkpStatus.ACCEPTED,
        FkpStatus.IN_PROCESS,
        FkpStatus.CLOSED,
        FkpStatus.REJECTED,
    }
    return fkp_status in STATUS_TERKUNCI

async def proses_finance(fkp_id, catatan_finance, user, kode_role, db):
    """
    Finance konfirmasi pembayaran cashback potong_tagihan SUDAH ditransfer.

    [FIX BUG KRITIS #2 — audit modul Sample Shipment] Parameter
    `nilai_nota_penjualan` DIHAPUS dari signature fungsi ini. Endpoint
    (api/endpoints/fkp.py) sudah lebih dulu diubah untuk TIDAK mengirim
    argumen ini lagi (lihat komentar "[FIX] nilai_nota_penjualan TIDAK LAGI
    diterima di sini" di endpoint), tapi signature fungsi ini sebelumnya
    belum ikut disesuaikan — akibatnya jumlah/urutan argumen saat dipanggil
    dari endpoint tidak cocok lagi dengan signature lama dan selalu
    menyebabkan TypeError setiap kali endpoint /finance/proses dipanggil.

    nilai_nota_penjualan & nilai_cashback sekarang HANYA dihitung sekali,
    di terbitkan_invoice() saat invoice pertama kali diterbitkan.
    proses_finance() murni konfirmasi pembayaran sudah ditransfer, sesuai
    keputusan user (#1: langkah konfirmasi transfer terpisah dari
    penerbitan invoice).
    """
    await require_permission(kode_role, "fkp.finance.process", db)

    fkp = await _get_or_404(fkp_id, db)

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

    if resolusi.tipe_resolusi != "potong_tagihan":
        raise HTTPException(
            status_code=400,
            detail="Proses finance hanya berlaku untuk resolusi tipe 'potong_tagihan'.",
        )

    # [FIX BUG KRITIS #2] nilai_nota_penjualan & nilai_cashback seharusnya
    # sudah diisi oleh terbitkan_invoice() sebelum FKP bisa mencapai status
    # in_process untuk resolusi potong_tagihan. Guard ini jaga-jaga kalau
    # ada data lama/tidak konsisten, bukan jalur normal.
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
    await db.commit()
    return await _load_fkp_detail(fkp.id, db)


# ═════════════════════════════════════════════════════════════════════════════
# MODUL SAMPLE SHIPMENT — Phase 5
# ═════════════════════════════════════════════════════════════════════════════

async def confirm_resolusi(fkp_id, catatan, user, kode_role, db):
    """
    Trigger accepted → in_process untuk resolusi SELAIN tukar_barang dan
    potong_tagihan — yaitu pemusnahan (tidak_ada_kompensasi + metode
    dimusnahkan) dan tidak_ada_kompensasi murni tanpa pemusnahan.

    [KEPUTUSAN — hasil diskusi Kontradiksi A & B]
    Dispatch di sini SENGAJA composite, BUKAN match/case eksklusif satu
    field: tipe_resolusi (tukar_barang/potong_tagihan/tidak_ada_kompensasi)
    dan metode_penanganan_fisik (dimusnahkan/dst) adalah dua kolom
    independen yang BISA berlaku bersamaan — misal barang berkutu/menjamur:
    tipe_resolusi=tukar_barang + metode=dimusnahkan (kasus ini TIDAK lewat
    endpoint ini, lihat penolakan di bawah — lewat create_surat_jalan(),
    Phase 6). Endpoint ini menangani kombinasi:
      - tipe_resolusi=tidak_ada_kompensasi, metode=apa pun (termasuk dimusnahkan)
    Gate metode=dimusnahkan & gate tipe=tidak_ada_kompensasi dicek TERPISAH
    dan bisa berlaku BERSAMAAN, bukan salah satu.
    """
    await require_permission(kode_role, "fkp.confirm_resolusi", db)

    fkp = await _get_or_404(fkp_id, db)
    if fkp.status != FkpStatus.ACCEPTED:
        raise HTTPException(
            status_code=400,
            detail=f"FKP harus berstatus 'accepted', bukan '{fkp.status}'.",
        )

    r = await db.execute(select(FkpResolution).where(FkpResolution.fkp_id == fkp_id))
    resolusi = r.scalar_one_or_none()
    if not resolusi:
        raise HTTPException(status_code=400, detail="Resolusi belum dibuat untuk FKP ini.")

    # tukar_barang & potong_tagihan TIDAK lewat endpoint ini — masing-masing
    # sudah punya jalur trigger sendiri (Phase 6 & 7).
    if resolusi.tipe_resolusi == TipeResolusi.TUKAR_BARANG:
        raise HTTPException(
            status_code=400,
            detail=(
                "Resolusi tukar_barang diproses lewat pembuatan Surat Jalan "
                "(POST /fkp/{fkp_id}/warehouse/surat-jalan), bukan endpoint ini."
            ),
        )
    if resolusi.tipe_resolusi == TipeResolusi.POTONG_TAGIHAN:
        raise HTTPException(
            status_code=400,
            detail="Resolusi potong_tagihan diproses lewat POST /fkp/{fkp_id}/finance/invoice.",
        )

    # ── Gate composite #1: metode_penanganan_fisik == DIMUSNAHKAN ──────────
    # [KEPUTUSAN] Hard gate — wajib upload "Berita Acara Pemusnahan dan
    # Tukar Barang" dulu, TERLEPAS dari tipe_resolusi-nya (di endpoint ini
    # tipe_resolusi sudah pasti tidak_ada_kompensasi setelah 2 pengecekan
    # di atas, tapi gate ditulis generik terhadap metode agar konsisten
    # kalau nanti ada tipe_resolusi baru).
    if resolusi.metode_penanganan_fisik == MetodePenangananFisik.DIMUSNAHKAN:
        r_bukti = await db.execute(
            select(FkpAttachment).where(
                FkpAttachment.fkp_id == fkp_id,
                FkpAttachment.tipe_dokumen == TipeDokumen.BERITA_ACARA_PEMUSNAHAN_TUKAR_BARANG,
            )
        )
        if not r_bukti.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=(
                    "Upload dokumen 'Berita Acara Pemusnahan dan Tukar Barang' "
                    "terlebih dahulu sebelum melanjutkan."
                ),
            )

    # ── Gate composite #2: tipe_resolusi == TIDAK_ADA_KOMPENSASI ───────────
    if resolusi.tipe_resolusi == TipeResolusi.TIDAK_ADA_KOMPENSASI:
        if not catatan or not catatan.strip():
            raise HTTPException(
                status_code=400,
                detail="Catatan wajib diisi untuk resolusi tidak_ada_kompensasi.",
            )

    lama = fkp.status
    fkp.status = FkpStatus.IN_PROCESS
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await _log(db, fkp.id, lama, FkpStatus.IN_PROCESS, user.id,
               catatan or "Resolusi dikonfirmasi, proses dimulai.")
    await kirim_notifikasi_transisi(db, fkp, lama, FkpStatus.IN_PROCESS, user)
    await db.commit()
    return await _load_fkp_detail(fkp.id, db)


async def terbitkan_invoice(fkp_id, nomor_invoice, nilai_nota_penjualan, catatan, user, kode_role, db):
    """
    [BARU — Modul Sample Shipment, Phase 7] Trigger accepted → in_process
    khusus resolusi potong_tagihan. Generate PDF invoice via WeasyPrint,
    simpan sebagai FkpDocument (bukan FkpAttachment — dokumen formal).

    nomor_invoice input MANUAL (sesuai keputusan user — sama seperti
    nomor_surat_jalan/nomor_tanda_terima, tidak ada auto-generate).

    [FIX BUG KRITIS #1 — audit modul Sample Shipment] Parameter
    `nilai_nota_penjualan` sebelumnya TIDAK ADA di signature fungsi ini
    sama sekali, padahal endpoint & docstring ini sendiri sudah
    mengasumsikan nilai itu diisi di sini ("nilai_nota_penjualan WAJIB
    diisi di sini") dan notifikasi di bawah sudah membaca
    `resolusi.nilai_cashback` seolah-olah sudah dihitung. Sekarang
    nilai_nota_penjualan diterima, nilai_cashback dihitung & disimpan ke
    resolusi SEBELUM PDF digenerate (supaya PDF & notifikasi menampilkan
    angka yang benar), dengan rumus yang sama seperti proses_finance()
    versi lama: nilai_nota_penjualan × (persentase_kompensasi_disetujui / 100).

    Langkah berikutnya SETELAH ini tetap proses_finance() untuk konfirmasi
    pembayaran benar-benar sudah ditransfer (keputusan user #1) — lihat
    guard proses_finance() yang diperketat jadi in_process-only di bawah.
    """
    await require_permission(kode_role, "fkp.finance.invoice", db)

    fkp = await _get_or_404(fkp_id, db)
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

    # [FIX BUG KRITIS #1] nilai_nota_penjualan wajib > 0 (sudah divalidasi
    # juga di schema InvoiceCreateRequest, dicek ulang di sini karena fungsi
    # service bisa dipanggil dari jalur lain di luar endpoint HTTP).
    if nilai_nota_penjualan is None or nilai_nota_penjualan <= 0:
        raise HTTPException(status_code=400, detail="nilai_nota_penjualan harus lebih dari 0.")

    # [KONSISTENSI dengan confirm_resolusi() & create_surat_jalan() —
    # dijanjikan di Phase 5] metode_penanganan_fisik == DIMUSNAHKAN adalah
    # hard gate independen dari tipe_resolusi — barang bisa dimusnahkan
    # SEKALIGUS distributor tetap dapat potongan tagihan sebagai kompensasi.
    if resolusi.metode_penanganan_fisik == MetodePenangananFisik.DIMUSNAHKAN:
        r_bukti = await db.execute(
            select(FkpAttachment).where(
                FkpAttachment.fkp_id == fkp_id,
                FkpAttachment.tipe_dokumen == TipeDokumen.BERITA_ACARA_PEMUSNAHAN_TUKAR_BARANG,
            )
        )
        if not r_bukti.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=(
                    "Upload dokumen 'Berita Acara Pemusnahan dan Tukar Barang' "
                    "terlebih dahulu sebelum menerbitkan invoice."
                ),
            )

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

    # [FIX BUG KRITIS #1] Hitung & simpan nilai_nota_penjualan/nilai_cashback
    # SEBELUM PDF digenerate — template invoice (invoice_pdf_service.py)
    # membaca kedua field ini langsung dari objek `resolusi`.
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

    # [Phase 8 — Notifikasi §12.1] Invoice diterbitkan: admin_ho, rsm
    from app.services.notification_service import notify_roles, TipeNotifikasi
    await notify_roles(
        db, fkp.id, ["admin_ho", "rsm"],
        "Invoice diterbitkan",
        f"Invoice potong tagihan FKP {fkp.nomor_fkp} diterbitkan. Nilai: {resolusi.nilai_cashback}",
        TipeNotifikasi.INVOICE,
    )

    await db.commit()
    await db.refresh(invoice_doc)

    # [FIX BUG KRITIS #1] Kembalikan dict eksplisit (bukan menempelkan
    # atribut baru ke instance FkpDocument) supaya FE langsung dapat
    # nilai_cashback tanpa request tambahan — lihat InvoiceResponse di
    # schemas/finance.py. Dict biasa lebih aman divalidasi Pydantic
    # dibanding menambah atribut ad-hoc ke object model SQLAlchemy/SQLModel.
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
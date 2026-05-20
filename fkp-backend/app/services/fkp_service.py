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
"""
from unittest import result
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.fkp import (
    FkpComplaint, FkpItem, FkpStatus,
    FkpStatusLog, FkpResolution, FkpAttachment,
    FkpDocument,
    TipeResolusi, MetodePenangananFisik,
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

TRANSITION_ROLES = {
    FkpStatus.SUBMITTED:                ["outlet", "distributor", "sc_spv", "apsm", "superadmin"],
    FkpStatus.APSM_REVIEWED:            ["apsm", "superadmin"],
    FkpStatus.RSM_APPROVAL_INVESTIGASI: ["admin_ho", "superadmin"],
    FkpStatus.IN_INVESTIGATION:         ["rsm", "superadmin"],
    FkpStatus.INVESTIGATED:             ["qc", "superadmin"],
    FkpStatus.RSM_APPROVAL_RESOLUSI:    ["admin_ho", "superadmin"],
    FkpStatus.DIREKTUR_APPROVAL:        ["rsm", "superadmin"],
    FkpStatus.ACCEPTED:                 ["direktur", "superadmin"],
    FkpStatus.IN_PROCESS:               ["admin_ho", "superadmin"],
    FkpStatus.NEED_REVISION:            ["apsm", "admin_ho", "rsm", "superadmin"],
    FkpStatus.REJECTED:                 ["apsm", "admin_ho", "rsm", "direktur", "qc", "superadmin"],
    FkpStatus.CLOSED:                   ["admin_ho", "superadmin"],
}

# Format: { (status_asal, kode_role): status_tujuan }
REVISION_TARGETS = {
    (FkpStatus.SUBMITTED,                "apsm"):       FkpStatus.DRAFT,
    (FkpStatus.APSM_REVIEWED,            "apsm"):       FkpStatus.SUBMITTED,
    (FkpStatus.APSM_REVIEWED,            "superadmin"): FkpStatus.SUBMITTED,
    (FkpStatus.RSM_APPROVAL_INVESTIGASI, "admin_ho"):   FkpStatus.SUBMITTED,
    (FkpStatus.RSM_APPROVAL_INVESTIGASI, "rsm"):        FkpStatus.APSM_REVIEWED,
    (FkpStatus.RSM_APPROVAL_INVESTIGASI, "superadmin"): FkpStatus.SUBMITTED,
    (FkpStatus.RSM_APPROVAL_RESOLUSI,    "rsm"):        FkpStatus.INVESTIGATED,
    (FkpStatus.RSM_APPROVAL_RESOLUSI,    "admin_ho"):   FkpStatus.INVESTIGATED,
    (FkpStatus.RSM_APPROVAL_RESOLUSI,    "superadmin"): FkpStatus.INVESTIGATED,
}


# ─── HELPERS ──────────────────────────────────────────────────────────────────

async def _validate_transition(fkp: FkpComplaint, new_status: str, kode_role: str):
    allowed_next = VALID_TRANSITIONS.get(fkp.status, [])
    if new_status not in allowed_next:
        raise HTTPException(
            status_code=400,
            detail=f"Transisi dari '{fkp.status}' ke '{new_status}' tidak diizinkan.",
        )
    if kode_role not in TRANSITION_ROLES.get(new_status, []):
        raise HTTPException(
            status_code=403,
            detail=f"Role '{kode_role}' tidak bisa mengubah status ke '{new_status}'.",
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
    """Admin HO / superadmin menambahkan dokumen formal ke FKP."""
    if kode_role not in ("admin_ho", "superadmin"):
        raise HTTPException(status_code=403, detail="Hanya Admin HO yang bisa menambah dokumen.")

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
    """Hapus dokumen — hanya oleh pembuatnya atau superadmin."""
    r = await db.execute(
        select(FkpDocument).where(
            FkpDocument.id == dokumen_id,
            FkpDocument.fkp_id == fkp_id,
        )
    )
    dokumen = r.scalar_one_or_none()
    if not dokumen:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan.")
    if kode_role != "superadmin" and dokumen.dibuat_oleh != user.id:
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


async def get_fkp_detail(fkp_id, db, user, kode_role):
    fkp = await _get_or_404(fkp_id, db)
    if kode_role == "outlet":
        r = await db.execute(select(Outlet).where(
            Outlet.pic_user_id == user.id,
            Outlet.distributor_id == fkp.distributor_id,
        ))
        if not r.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Akses ditolak.")
    elif kode_role == "distributor":
        r = await db.execute(select(DistributorUser).where(
            DistributorUser.user_id == user.id,
            DistributorUser.distributor_id == fkp.distributor_id,
        ))
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
    return await _load_fkp_detail(fkp.id, db)


# ─── CRUD ─────────────────────────────────────────────────────────────────────

async def create_fkp(data: FkpCreate, user: User, kode_role: str, db) -> FkpComplaint:
    """Buat FKP baru dengan multi-item sekaligus."""
    if kode_role == "outlet":
        r = await db.execute(select(Outlet).where(
            Outlet.pic_user_id == user.id,
            Outlet.distributor_id == data.distributor_id,
        ))
        outlet_milik_user = r.scalar_one_or_none()
        if not outlet_milik_user:
            raise HTTPException(status_code=403, detail="Distributor tidak sesuai dengan outlet Anda.")
        if not data.outlet_id:
            data.outlet_id = outlet_milik_user.id

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
    """Update header FKP — hanya saat draft/need_revision."""
    fkp = await _get_or_404(fkp_id, db)
    if fkp.status not in FkpStatus.EDITABLE:
        raise HTTPException(status_code=400, detail=f"FKP status '{fkp.status}' tidak bisa diedit.")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(fkp, k, v)
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await db.commit()
    return await _load_fkp_detail(fkp_id, db)


# ─── CRUD FKP ITEMS ───────────────────────────────────────────────────────────

async def add_fkp_item(fkp_id, item_data: dict, user, db) -> FkpItem:
    fkp = await _get_or_404(fkp_id, db)
    if fkp.status not in FkpStatus.EDITABLE:
        raise HTTPException(status_code=400, detail="Item hanya bisa ditambah saat status draft atau need_revision.")
    item = FkpItem(fkp_id=fkp_id, **item_data)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_fkp_item(fkp_id, item_id, data: FkpItemUpdate, user, db) -> FkpItem:
    fkp = await _get_or_404(fkp_id, db)
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


async def delete_fkp_item(fkp_id, item_id, user, db):
    fkp = await _get_or_404(fkp_id, db)
    if fkp.status not in FkpStatus.EDITABLE:
        raise HTTPException(status_code=400, detail="Item hanya bisa dihapus saat status draft atau need_revision.")
    r = await db.execute(select(FkpItem).where(FkpItem.id == item_id, FkpItem.fkp_id == fkp_id))
    item = r.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item tidak ditemukan.")
    r2 = await db.execute(select(FkpItem).where(FkpItem.fkp_id == fkp_id))
    if len(r2.scalars().all()) <= 1:
        raise HTTPException(status_code=400, detail="FKP harus memiliki minimal 1 item. Hapus FKP-nya jika tidak diperlukan.")
    await db.delete(item)
    await db.commit()
    return {"detail": "Item berhasil dihapus."}


# ─── TRANSISI STATUS ──────────────────────────────────────────────────────────

async def submit_fkp(fkp_id, user, kode_role, db):
    """Draft / Need Revision → Submitted."""
    fkp = await _get_or_404(fkp_id, db)
    await _validate_transition(fkp, FkpStatus.SUBMITTED, kode_role)

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
    return await _load_fkp_detail(fkp.id, db)


async def apsm_review(fkp_id, data: ApsmReviewRequest, user, kode_role, db):
    """Submitted → Apsm Reviewed."""
    fkp = await _get_or_404(fkp_id, db)
    await _validate_transition(fkp, FkpStatus.APSM_REVIEWED, kode_role)

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
    await _validate_transition(fkp, FkpStatus.RSM_APPROVAL_INVESTIGASI, kode_role)

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
    await _validate_transition(fkp, new_status, kode_role)
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
    await _validate_transition(fkp, FkpStatus.INVESTIGATED, kode_role)

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
    await _validate_transition(fkp, FkpStatus.RSM_APPROVAL_RESOLUSI, kode_role)
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
    await _validate_transition(fkp, new_status, kode_role)
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
    await _validate_transition(fkp, new_status, kode_role)
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
    return await _load_fkp_detail(fkp.id, db)


async def reject_fkp(fkp_id, data: RejectRequest, user, kode_role, db):
    """Tolak FKP dari status mana pun yang diizinkan."""
    if not data.catatan:
        raise HTTPException(status_code=400, detail="Alasan penolakan wajib diisi.")
    fkp = await _get_or_404(fkp_id, db)
    await _validate_transition(fkp, FkpStatus.REJECTED, kode_role)
    lama = fkp.status
    fkp.status = FkpStatus.REJECTED
    fkp.tanggal_selesai = datetime.now(timezone.utc)
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await _log(db, fkp.id, lama, FkpStatus.REJECTED, user.id, data.catatan)
    await kirim_notifikasi_transisi(db, fkp, lama, FkpStatus.REJECTED, user)
    await db.commit()
    return await _load_fkp_detail(fkp.id, db)


async def input_surat_jalan(fkp_id, nomor_surat_jalan, user, db):
    """Admin HO input/update nomor surat jalan kapan pun."""
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

    await _validate_transition(fkp, FkpStatus.CLOSED, kode_role)
    lama = fkp.status
    fkp.status = FkpStatus.CLOSED
    fkp.tanggal_selesai = datetime.now(timezone.utc)
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await _log(db, fkp.id, lama, FkpStatus.CLOSED, user.id, catatan or "FKP ditutup.")
    await kirim_notifikasi_transisi(db, fkp, lama, FkpStatus.CLOSED, user)
    await db.commit()
    return await _load_fkp_detail(fkp.id, db)

async def buat_resolusi(fkp_id, data, user, kode_role, db):
    """
    Satu fungsi, dua fase — dikontrol oleh status FKP:

    FASE 1 — status 'investigated':
      Wajib: tipe_resolusi + metode_penanganan_fisik
      Boleh: lokasi_pemusnahan (wajib jika dimusnahkan), tanggal_pemusnahan, keterangan
      TIDAK boleh: field eksekusi (nomor_do, rekening, dll)

    FASE 2 — status 'accepted':
      Wajib: detail eksekusi sesuai tipe_resolusi
      TIDAK boleh ubah: tipe_resolusi, metode_penanganan_fisik
      Setelah simpan → otomatis transisi ke in_process

    EDIT TIPE — status 'rsm_approval_resolusi':
      Sama seperti Fase 1, hanya boleh ubah tipe/metode
    """
    fkp = await _get_or_404(fkp_id, db)

    if kode_role not in ["admin_ho", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Hanya Admin HO yang bisa membuat atau mengupdate resolusi."
        )

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
 
    # ── Fase 2: transisi ke in_process ───────────────────────────────────
    if fkp.status == FkpStatus.ACCEPTED:
        if "nomor_surat_jalan" in data_tersaring:  
            fkp.nomor_surat_jalan = data_tersaring["nomor_surat_jalan"]

        lama = fkp.status
        fkp.status = FkpStatus.IN_PROCESS
        fkp.updated_at = datetime.now(timezone.utc)
        db.add(fkp)

        log_catatan = data_tersaring.get("keterangan") or \
            f"Detail resolusi '{resolusi_existing.tipe_resolusi}' diisi, proses dimulai."
        await _log(db, fkp.id, lama, FkpStatus.IN_PROCESS, user.id, log_catatan)
        await kirim_notifikasi_transisi(db, fkp, lama, FkpStatus.IN_PROCESS, user)
    else:
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

async def proses_finance(fkp_id, catatan_finance, nilai_nota_penjualan, user, kode_role, db):
    """
    Finance memproses pembayaran cashback potong_tagihan.
    Kalkulasi otomatis: nilai_nota × persentase_kompensasi_disetujui / 100 = nilai_cashback
    """
    if kode_role not in ("finance", "admin_ho", "superadmin"):
        raise HTTPException(status_code=403, detail="Hanya role finance yang bisa memproses keuangan.")

    fkp = await _get_or_404(fkp_id, db)

    if fkp.status not in [FkpStatus.ACCEPTED, FkpStatus.IN_PROCESS]:
        raise HTTPException(
            status_code=400,
            detail=f"Proses finance hanya bisa dilakukan saat status accepted/in_process. "
                   f"Status saat ini: '{fkp.status}'.",
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

    if not resolusi.persentase_kompensasi_disetujui:
        raise HTTPException(
            status_code=400,
            detail="persentase_kompensasi_disetujui belum diisi pada resolusi. "
                   "Admin HO harus melengkapi resolusi terlebih dahulu."
        )

    # Simpan nilai nota
    if nilai_nota_penjualan:
        resolusi.nilai_nota_penjualan = nilai_nota_penjualan
        # Auto-kalkulasi nilai_cashback
        resolusi.nilai_cashback = (
            Decimal(str(nilai_nota_penjualan)) *
            resolusi.persentase_kompensasi_disetujui / 100
        ).quantize(Decimal("0.01"))

    resolusi.catatan_finance        = catatan_finance
    resolusi.diproses_finance       = True
    resolusi.tanggal_proses_finance = datetime.now(timezone.utc)
    resolusi.finance_user_id        = user.id

    db.add(resolusi)
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await db.commit()
    return await _load_fkp_detail(fkp.id, db)
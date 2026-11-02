"""
Sample Service — state machine untuk tracking sample fisik yang dikirim ke
QC pusat (modul Sample Shipment, rencana_modul_sample_shipment_v3.md §4).

State machine (lihat models/fkp.py SampleStatus):
  shipped → delivered → received_by_warehouse → forwarded_to_qc
          → under_qc_review → examined
  (bisa CANCELLED dari status non-terminal manapun, lihat cancel_sample())

Independen dari FkpStatus — hanya dipakai sebagai GATE agar qc_investigasi()
tidak bisa dijalankan selama masih ada sample yang belum selesai diperiksa
(lihat all_samples_examined_or_cancelled(), dipakai ulang di Phase 4).
"""
import math
import uuid
from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlmodel import select, func
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.distributor import Distributor
from app.models.fkp import FkpAttachment, FkpComplaint, FkpItem, FkpStatus, SampleStatus
from app.models.outlet import Outlet
from app.models.product import ProductCatalog
from app.models.sample import SampleShipment, SampleStatusLog
from app.models.user import User
from app.schemas.sample import SampleInboxItem, SampleResponse
from app.services.permission_service import require_permission
from app.services.fkp_service import _get_or_404, _check_ownership, OWNERSHIP_SCOPED_ROLES
from app.services.notification_service import _buat_notif, _get_users_by_role, notify_roles, notify_user, TipeNotifikasi


ALLOWED_FKP_STATUS_FOR_SAMPLE = [
    FkpStatus.SUBMITTED,
    FkpStatus.APSM_REVIEWED,
    FkpStatus.RSM_APPROVAL_INVESTIGASI,
    FkpStatus.IN_INVESTIGATION,
]

# Role yang, saat men-cancel, dibatasi ke sample yang mereka kirim sendiri
# DAN hanya di status awal (shipped/delivered) — lihat cancel_sample().
SENDER_ROLES = {"outlet", "distributor", "sc_spv", "apsm"}


# ─── HELPERS ────────────────────────────────────────────────────────────────

async def _get_sample_or_404(sample_id: uuid.UUID, fkp_id: uuid.UUID, db: AsyncSession) -> SampleShipment:
    r = await db.execute(
        select(SampleShipment).where(
            SampleShipment.id == sample_id,
            SampleShipment.fkp_id == fkp_id,
        )
    )
    sample = r.scalar_one_or_none()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample shipment tidak ditemukan.")
    return sample


async def _log_transisi(db, sample_id, fkp_id, status_lama, status_baru, changed_by, catatan=None):
    db.add(SampleStatusLog(
        sample_id=sample_id, fkp_id=fkp_id,
        status_lama=status_lama, status_baru=status_baru,
        catatan=catatan, changed_by=changed_by,
    ))


def _sanitize_for_external(sample: SampleShipment, kode_role: str) -> SampleShipment:
    """
    [KEPUTUSAN BISNIS] hasil_pemeriksaan HANYA untuk role internal. Untuk
    outlet/distributor/sc_spv, field ini disaring jadi None sebelum
    diserialisasi ke response — bukan cuma disembunyikan di frontend, karena
    payload API tidak boleh membawa data itu sama sekali ke luar sistem
    internal.
    """
    if kode_role in ("outlet", "distributor", "sc_spv"):
        sample.hasil_pemeriksaan = None
    return sample


async def all_samples_examined_or_cancelled(fkp_id: uuid.UUID, db: AsyncSession) -> bool:
    """
    True jika TIDAK ADA sample aktif (non-terminal) tersisa untuk FKP ini.
    Dipakai sebagai:
      1. Side-effect notifikasi di examine_sample() (bagian bawah file ini)
      2. Gate qc_investigasi() di fkp_service.py — Phase 4
    """
    r = await db.execute(
        select(func.count(SampleShipment.id)).where(
            SampleShipment.fkp_id == fkp_id,
            SampleShipment.status.not_in(SampleStatus.TERMINAL),
        )
    )
    return r.scalar_one() == 0


# ─── CREATE ─────────────────────────────────────────────────────────────────

async def _get_item_nama_produk(fkp_item_id: uuid.UUID, db: AsyncSession) -> str:
    r = await db.execute(select(FkpItem).where(FkpItem.id == fkp_item_id))
    item = r.scalar_one_or_none()
    if not item:
        return "Produk"
    from app.models.product import ProductCatalog
    rp = await db.execute(select(ProductCatalog).where(ProductCatalog.id == item.product_id))
    product = rp.scalar_one_or_none()
    return product.nama_produk if product else "Produk"


async def create_sample_shipment(
    fkp_id: uuid.UUID, data, user: User, kode_role: str, db: AsyncSession
) -> SampleShipment:
    await require_permission(kode_role, "sample.create", db)

    fkp = await _get_or_404(fkp_id, db)
    _check_ownership(fkp, user, kode_role)  # no-op untuk admin_ho/superadmin

    if fkp.status not in ALLOWED_FKP_STATUS_FOR_SAMPLE:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Sample tidak dapat didaftarkan. FKP sudah berada di status "
                f"'{fkp.status}'. Sample hanya bisa didaftarkan sebelum "
                "investigasi selesai."
            ),
        )

    r_item = await db.execute(
        select(FkpItem).where(FkpItem.id == data.fkp_item_id, FkpItem.fkp_id == fkp_id)
    )
    if not r_item.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Item tidak ditemukan atau tidak termasuk dalam FKP ini.")

    sample = SampleShipment(
        fkp_id=fkp_id,
        fkp_item_id=data.fkp_item_id,
        sender_id=user.id,
        ekspedisi=data.ekspedisi,
        nomor_resi=data.nomor_resi,
        tanggal_kirim=data.tanggal_kirim,
        catatan_pengirim=data.catatan_pengirim,
        qty_sample=data.qty_sample,
    )
    db.add(sample)
    await db.flush()  # butuh sample.id untuk log

    await _log_transisi(db, sample.id, fkp_id, None, sample.status, user.id, "Sample didaftarkan untuk dikirim.")

    # [Phase 8 — Notifikasi §12.1] Sample baru (shipped) → admin_ho
    nama_produk = await _get_item_nama_produk(data.fkp_item_id, db)
    judul = "Sample baru didaftarkan"
    pesan = f"Sample FKP {fkp.nomor_fkp} — {nama_produk} didaftarkan. Resi: {data.nomor_resi or '—'}"
    for admin_user in await _get_users_by_role(db, "admin_ho"):
        await _buat_notif(db, admin_user.id, fkp_id, judul, pesan, TipeNotifikasi.SAMPLE)

    await db.commit()
    await db.refresh(sample)
    return sample


# ─── READ ───────────────────────────────────────────────────────────────────

async def list_samples_by_fkp(
    fkp_id: uuid.UUID, user: User, kode_role: str, db: AsyncSession
) -> List[SampleShipment]:
    # Scope gate — reuse logic get_fkp_detail() (raise 403/404 kalau di luar
    # jangkauan), konsisten dengan pola fix IDOR testimoni sebelumnya.
    from app.services.fkp_service import get_fkp_detail
    await get_fkp_detail(fkp_id, db, user, kode_role)

    r = await db.execute(
        select(SampleShipment)
        .where(SampleShipment.fkp_id == fkp_id)
        .order_by(SampleShipment.created_at.desc())
    )
    samples = r.scalars().all()
    return [_sanitize_for_external(s, kode_role) for s in samples]


async def get_sample_detail(
    fkp_id: uuid.UUID, sample_id: uuid.UUID, user: User, kode_role: str, db: AsyncSession
) -> SampleShipment:
    from app.services.fkp_service import get_fkp_detail
    await get_fkp_detail(fkp_id, db, user, kode_role)

    sample = await _get_sample_or_404(sample_id, fkp_id, db)
    return _sanitize_for_external(sample, kode_role)


# ─── TRANSISI ───────────────────────────────────────────────────────────────

async def confirm_delivery(
    fkp_id: uuid.UUID, sample_id: uuid.UUID, user: User, kode_role: str, db: AsyncSession
) -> SampleShipment:
    await require_permission(kode_role, "sample.deliver_confirm", db)
    sample = await _get_sample_or_404(sample_id, fkp_id, db)

    if sample.status != "shipped":
        raise HTTPException(status_code=400, detail=f"Sample harus berstatus 'shipped', bukan '{sample.status}'.")

    if kode_role not in ("admin_ho", "superadmin") and sample.sender_id != user.id:
        raise HTTPException(status_code=403, detail="Hanya pengirim sample ini yang bisa konfirmasi terkirim.")

    lama = sample.status
    sample.status = "delivered"
    sample.tanggal_delivered = datetime.now(timezone.utc)
    sample.dikonfirmasi_delivered_oleh = user.id
    sample.updated_at = datetime.now(timezone.utc)
    db.add(sample)
    await _log_transisi(db, sample.id, fkp_id, lama, sample.status, user.id)

    # [Phase 8 — Notifikasi §12.1] shipped → delivered: sender + admin_ho
    r_fkp = await db.execute(select(FkpComplaint).where(FkpComplaint.id == fkp_id))
    fkp = r_fkp.scalar_one()
    await notify_user(db, sample.sender_id, fkp_id,
                       "Sample terkirim", f"Sample FKP {fkp.nomor_fkp} dikonfirmasi terkirim.",
                       TipeNotifikasi.SAMPLE)
    await notify_roles(db, fkp_id, ["admin_ho"],
                        "Sample delivered", f"Sample FKP {fkp.nomor_fkp} tiba, menunggu penerimaan warehouse.",
                        TipeNotifikasi.SAMPLE)

    await db.commit()
    await db.refresh(sample)
    return sample


async def receive_sample(
    fkp_id: uuid.UUID, sample_id: uuid.UUID, data, user: User, kode_role: str, db: AsyncSession
) -> SampleShipment:
    await require_permission(kode_role, "sample.receive", db)
    sample = await _get_sample_or_404(sample_id, fkp_id, db)

    if sample.status != "delivered":
        raise HTTPException(status_code=400, detail=f"Sample harus berstatus 'delivered', bukan '{sample.status}'.")

    lama = sample.status
    sample.status = "received_by_warehouse"
    sample.diterima_oleh = user.id
    sample.nomor_tanda_terima = data.nomor_tanda_terima
    sample.tanggal_diterima = datetime.now(timezone.utc)
    sample.catatan_warehouse = data.catatan_warehouse
    sample.updated_at = datetime.now(timezone.utc)
    db.add(sample)
    await _log_transisi(
        db, sample.id, fkp_id, lama, sample.status, user.id,
        f"Diterima warehouse. No. TT: {data.nomor_tanda_terima}",
    )

    # [Phase 8 — Notifikasi §12.1] delivered → received_by_warehouse: admin_ho, rsm, superadmin
    r_fkp = await db.execute(select(FkpComplaint).where(FkpComplaint.id == fkp_id))
    fkp = r_fkp.scalar_one()
    await notify_roles(
        db, fkp_id, ["admin_ho", "rsm", "superadmin"],
        "Sample diterima warehouse",
        f"Sample FKP {fkp.nomor_fkp} diterima. No. TT: {data.nomor_tanda_terima}",
        TipeNotifikasi.SAMPLE,
    )

    await db.commit()
    await db.refresh(sample)
    return sample


async def forward_to_qc(
    fkp_id: uuid.UUID, sample_id: uuid.UUID, user: User, kode_role: str, db: AsyncSession
) -> SampleShipment:
    await require_permission(kode_role, "sample.forward_qc", db)
    sample = await _get_sample_or_404(sample_id, fkp_id, db)

    if sample.status != "received_by_warehouse":
        raise HTTPException(
            status_code=400,
            detail=f"Sample harus berstatus 'received_by_warehouse', bukan '{sample.status}'.",
        )

    lama = sample.status
    sample.status = "forwarded_to_qc"
    sample.updated_at = datetime.now(timezone.utc)
    db.add(sample)
    await _log_transisi(db, sample.id, fkp_id, lama, sample.status, user.id, "Diserahkan ke QC.")

    # [Phase 8 — Notifikasi §12.1] received_by_warehouse → forwarded_to_qc: semua QC
    r_fkp = await db.execute(select(FkpComplaint).where(FkpComplaint.id == fkp_id))
    fkp = r_fkp.scalar_one()
    nama_produk = await _get_item_nama_produk(sample.fkp_item_id, db)
    await notify_roles(
        db, fkp_id, ["qc"],
        "Sample siap diperiksa",
        f"Sample FKP {fkp.nomor_fkp} — {nama_produk} menunggu pemeriksaan QC.",
        TipeNotifikasi.SAMPLE,
    )

    await db.commit()
    await db.refresh(sample)
    return sample


async def start_review(
    fkp_id: uuid.UUID, sample_id: uuid.UUID, user: User, kode_role: str, db: AsyncSession
) -> SampleShipment:
    await require_permission(kode_role, "sample.examine", db)
    sample = await _get_sample_or_404(sample_id, fkp_id, db)

    if sample.status != "forwarded_to_qc":
        raise HTTPException(
            status_code=400,
            detail=f"Sample harus berstatus 'forwarded_to_qc', bukan '{sample.status}'.",
        )

    lama = sample.status
    sample.status = "under_qc_review"
    sample.diperiksa_oleh = user.id
    sample.tanggal_mulai_periksa = datetime.now(timezone.utc)
    sample.updated_at = datetime.now(timezone.utc)
    db.add(sample)
    await _log_transisi(db, sample.id, fkp_id, lama, sample.status, user.id, "QC mulai memeriksa.")
    await db.commit()
    await db.refresh(sample)
    return sample


async def examine_sample(
    fkp_id: uuid.UUID, sample_id: uuid.UUID, data, user: User, kode_role: str, db: AsyncSession
) -> SampleShipment:
    await require_permission(kode_role, "sample.examine", db)
    sample = await _get_sample_or_404(sample_id, fkp_id, db)

    if sample.status != "under_qc_review":
        raise HTTPException(
            status_code=400,
            detail=f"Sample harus berstatus 'under_qc_review', bukan '{sample.status}'.",
        )

    lama = sample.status
    sample.status = "examined"
    sample.hasil_pemeriksaan = data.hasil_pemeriksaan
    sample.tanggal_selesai_periksa = datetime.now(timezone.utc)
    sample.updated_at = datetime.now(timezone.utc)
    db.add(sample)
    await _log_transisi(db, sample.id, fkp_id, lama, sample.status, user.id, "Pemeriksaan selesai.")
    await db.flush()

    # Side-effect: kalau semua sample aktif FKP ini sudah examined/cancelled,
    # beri tahu QC + Admin HO bahwa investigasi bisa dilanjutkan/ditutup.
    if await all_samples_examined_or_cancelled(fkp_id, db):
        r_fkp = await db.execute(select(FkpComplaint).where(FkpComplaint.id == fkp_id))
        fkp = r_fkp.scalar_one()
        judul = f"Semua sample FKP {fkp.nomor_fkp} selesai diperiksa"
        pesan = f"Seluruh sample untuk FKP {fkp.nomor_fkp} sudah selesai diperiksa QC. Investigasi dapat dilanjutkan."
        await notify_roles(db, fkp_id, ["qc", "admin_ho"], judul, pesan, TipeNotifikasi.SAMPLE)

    await db.commit()
    await db.refresh(sample)
    return sample


async def cancel_sample(
    fkp_id: uuid.UUID, sample_id: uuid.UUID, data, user: User, kode_role: str, db: AsyncSession
) -> SampleShipment:
    await require_permission(kode_role, "sample.cancel", db)
    sample = await _get_sample_or_404(sample_id, fkp_id, db)

    if sample.status in SampleStatus.TERMINAL:
        raise HTTPException(status_code=400, detail=f"Sample sudah berstatus terminal ('{sample.status}').")

    # Guard ownership & status sesuai peran — persis §4.4 dokumen rencana.
    if kode_role in ("admin_ho", "superadmin"):
        pass  # bisa cancel dari status non-terminal manapun
    elif kode_role == "warehouse":
        if sample.status != "received_by_warehouse":
            raise HTTPException(
                status_code=403,
                detail=(
                    "Warehouse hanya bisa membatalkan sample yang belum "
                    "diserahkan ke QC (status: received_by_warehouse)."
                ),
            )
    else:
        # outlet/distributor/sc_spv/apsm — hanya milik sendiri, hanya early stage
        if sample.sender_id != user.id:
            raise HTTPException(status_code=403, detail="Anda hanya bisa membatalkan sample yang Anda kirim.")
        if sample.status not in ("shipped", "delivered"):
            raise HTTPException(status_code=400, detail="Tidak bisa dibatalkan — sample sudah diterima warehouse.")

    lama = sample.status
    sample.status = "cancelled"
    sample.alasan_batal = data.alasan_batal
    sample.dibatalkan_oleh = user.id
    sample.tanggal_batal = datetime.now(timezone.utc)
    sample.updated_at = datetime.now(timezone.utc)
    db.add(sample)
    await _log_transisi(db, sample.id, fkp_id, lama, sample.status, user.id, data.alasan_batal)

    # [Phase 8 — Notifikasi §12.1] → cancelled: admin_ho + sender
    r_fkp = await db.execute(select(FkpComplaint).where(FkpComplaint.id == fkp_id))
    fkp = r_fkp.scalar_one()
    judul = "Sample dibatalkan"
    pesan = f"Sample FKP {fkp.nomor_fkp} dibatalkan. Alasan: {data.alasan_batal}"
    await notify_roles(db, fkp_id, ["admin_ho"], judul, pesan, TipeNotifikasi.SAMPLE)
    if sample.sender_id != user.id:  # hindari notif dobel kalau yang cancel adalah sender itu sendiri
        await notify_user(db, sample.sender_id, fkp_id, judul, pesan, TipeNotifikasi.SAMPLE)

    await db.commit()
    await db.refresh(sample)
    return sample


# ─── SAMPLE MASUK (list global lintas FKP) ──────────────────────────────────
#
# Endpoint: GET /api/samples dan GET /api/samples/summary (sample_inbox_router).
# Permission: sample.view_all (warehouse, qc, admin_ho; superadmin bypass).
# Scope data: global, tanpa filter area/distributor — sama dengan prinsip
# fkp_service._ROLE_GLOBAL_ACCESS untuk role yang lolos permission ini.

def _escape_like(value: str) -> str:
    """Escape wildcard LIKE (\\, %, _) agar input user dianggap teks biasa."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _parse_status_filter(status: Optional[str]) -> List[str]:
    """'a,b' -> ['a','b']. Nilai tak dikenal -> 400. Kosong/None -> []."""
    if not status:
        return []
    values: List[str] = []
    for raw in status.split(","):
        v = raw.strip()
        if v and v not in values:
            values.append(v)
    invalid = [v for v in values if v not in SampleStatus.ALL]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Status sample tidak valid: {', '.join(invalid)}. "
                f"Status yang diizinkan: {', '.join(SampleStatus.ALL)}."
            ),
        )
    return values


def _apply_inbox_joins(stmt, *, with_sender: bool):
    """
    Join eksplisit untuk query Sample Masuk. Distributor INNER (FK wajib),
    Outlet OUTER (FkpComplaint.outlet_id nullable), User OUTER.
    SampleShipment punya banyak FK ke users.id, jadi onclause User WAJIB
    eksplisit (User.id == SampleShipment.sender_id).
    """
    stmt = (
        stmt.select_from(SampleShipment)
        .join(FkpComplaint, FkpComplaint.id == SampleShipment.fkp_id)
        .join(FkpItem, FkpItem.id == SampleShipment.fkp_item_id)
        .join(ProductCatalog, ProductCatalog.id == FkpItem.product_id)
        .join(Distributor, Distributor.id == FkpComplaint.distributor_id)
        .outerjoin(Outlet, Outlet.id == FkpComplaint.outlet_id)
    )
    if with_sender:
        stmt = stmt.outerjoin(User, User.id == SampleShipment.sender_id)
    return stmt


def _apply_inbox_filters(
    stmt,
    *,
    statuses: List[str],
    search: Optional[str],
    tanggal_dari: Optional[date],
    tanggal_sampai: Optional[date],
):
    if statuses:
        stmt = stmt.where(SampleShipment.status.in_(statuses))

    term = (search or "").strip()
    if term:
        pattern = f"%{_escape_like(term)}%"
        stmt = stmt.where(
            or_(
                FkpComplaint.nomor_fkp.ilike(pattern, escape="\\"),
                ProductCatalog.nama_produk.ilike(pattern, escape="\\"),
                SampleShipment.nomor_resi.ilike(pattern, escape="\\"),
                SampleShipment.nomor_tanda_terima.ilike(pattern, escape="\\"),
                Distributor.nama_perusahaan.ilike(pattern, escape="\\"),
                Outlet.nama_toko.ilike(pattern, escape="\\"),
            )
        )

    # tanggal_kirim bertipe date; kedua batas inklusif.
    if tanggal_dari:
        stmt = stmt.where(SampleShipment.tanggal_kirim >= tanggal_dari)
    if tanggal_sampai:
        stmt = stmt.where(SampleShipment.tanggal_kirim <= tanggal_sampai)
    return stmt


async def list_samples_inbox(
    user: User,
    kode_role: str,
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
    tanggal_dari: Optional[date] = None,
    tanggal_sampai: Optional[date] = None,
) -> dict:
    """
    List sample lintas FKP, berpaginasi. Satu query data (tanpa N+1) + satu
    COUNT dengan join dan filter yang sama.
    """
    await require_permission(kode_role, "sample.view_all", db)

    statuses = _parse_status_filter(status)
    if tanggal_dari and tanggal_sampai and tanggal_dari > tanggal_sampai:
        raise HTTPException(
            status_code=400,
            detail="tanggal_dari tidak boleh lebih besar dari tanggal_sampai.",
        )

    # jumlah_dokumen: correlated scalar subquery (bukan query per baris).
    jumlah_dokumen = (
        select(func.count(FkpAttachment.id))
        .where(FkpAttachment.sample_shipment_id == SampleShipment.id)
        .correlate(SampleShipment)
        .scalar_subquery()
    )

    # ── COUNT ──────────────────────────────────────────────────────────────
    count_stmt = _apply_inbox_filters(
        _apply_inbox_joins(select(func.count(SampleShipment.id)), with_sender=False),
        statuses=statuses, search=search,
        tanggal_dari=tanggal_dari, tanggal_sampai=tanggal_sampai,
    )
    total = (await db.execute(count_stmt)).scalar_one()

    # ── DATA ───────────────────────────────────────────────────────────────
    data_stmt = _apply_inbox_filters(
        _apply_inbox_joins(
            select(
                SampleShipment,
                FkpComplaint.nomor_fkp,
                FkpComplaint.status,
                ProductCatalog.nama_produk,
                FkpItem.jenis_kemasan,
                FkpItem.qty,
                Distributor.nama_perusahaan,
                Distributor.kode_distributor,
                Outlet.nama_toko,
                Outlet.kode_outlet,
                User.first_name,
                User.last_name,
                jumlah_dokumen,
            ),
            with_sender=True,
        ),
        statuses=statuses, search=search,
        tanggal_dari=tanggal_dari, tanggal_sampai=tanggal_sampai,
    ).order_by(SampleShipment.created_at.desc(), SampleShipment.id.desc())
    data_stmt = data_stmt.offset((page - 1) * page_size).limit(page_size)

    rows = (await db.execute(data_stmt)).all()

    items: List[SampleInboxItem] = []
    for (
        sample, nomor_fkp, fkp_status, nama_produk, jenis_kemasan, qty_item,
        dist_nama, dist_kode, outlet_nama, outlet_kode,
        first_name, last_name, n_dokumen,
    ) in rows:
        # User.full_name hanya @property Python (bukan kolom) -> gabung di sini.
        pengirim_nama = None
        if first_name is not None:
            pengirim_nama = f"{first_name} {last_name or ''}".strip()

        base = SampleResponse.model_validate(sample).model_dump()
        items.append(SampleInboxItem(
            **base,
            nomor_fkp=nomor_fkp,
            fkp_status=fkp_status,
            nama_produk=nama_produk,
            jenis_kemasan=jenis_kemasan,
            qty_item_keluhan=qty_item or 0,
            distributor_nama=dist_nama,
            distributor_kode=dist_kode,
            outlet_nama=outlet_nama,
            outlet_kode=outlet_kode,
            pengirim_nama=pengirim_nama,
            jumlah_dokumen=n_dokumen or 0,
        ))

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


async def get_samples_summary(user: User, kode_role: str, db: AsyncSession) -> dict:
    """Jumlah sample per status (GROUP BY). `counts` memuat semua status, default 0."""
    await require_permission(kode_role, "sample.view_all", db)

    rows = (
        await db.execute(
            select(SampleShipment.status, func.count(SampleShipment.id))
            .group_by(SampleShipment.status)
        )
    ).all()

    counts = {s: 0 for s in SampleStatus.ALL}
    for st, n in rows:
        counts[st] = counts.get(st, 0) + n
    return {"counts": counts, "total": sum(counts.values())}
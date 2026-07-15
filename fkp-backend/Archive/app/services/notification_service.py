"""
Notification Service — logika bisnis notifikasi FKP SaktiFood.

Notifikasi dibuat otomatis saat terjadi transisi status FKP.
Setiap peran menerima notifikasi yang relevan dengan tugasnya.

Pemetaan notifikasi per transisi (sinkron dengan fkp_service.py):
  DRAFT → SUBMITTED                    → APSM (area distributor) + Admin HO
  SUBMITTED → APSM_REVIEWED            → Submitter + Admin HO (need action)
  APSM_REVIEWED → RSM_APPROVAL_INVESTIGASI → Submitter + RSM area (need action)
  RSM_APPROVAL_INVESTIGASI → IN_INVESTIGATION → Submitter + QC (need action)
  IN_INVESTIGATION → INVESTIGATED      → Admin HO + RSM area
  INVESTIGATED → RSM_APPROVAL_RESOLUSI → RSM area (need action)
  RSM_APPROVAL_RESOLUSI → DIREKTUR_APPROVAL → Direktur (need action)
  DIREKTUR_APPROVAL → ACCEPTED         → Admin HO + Submitter + QC
  ACCEPTED → IN_PROCESS                → Submitter + Admin HO
  IN_PROCESS → CLOSED                  → Semua pihak terkait
  * → NEED_REVISION                    → Submitter (need action)
  * → REJECTED                         → Submitter + Admin HO
  ACCEPTED → CLOSED (pemusnahan)       → Semua pihak terkait
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.fkp import FkpComplaint, FkpStatus
from app.models.user import User
from app.models.distributor import Distributor, DistributorUser
from app.models.outlet import Outlet
from app.models.sc_spv import ScSpvDistributor, ApsmScSpv, RsmApsm
from app.schemas.notification import NotificationResponse, NotificationListResponse, NotificationSummary


# ─── TIPE NOTIFIKASI ─────────────────────────────────────────────────────────
class TipeNotifikasi:
    STATUS_CHANGE = "status_change"   # Informasi perubahan status
    NEED_ACTION   = "need_action"     # Perlu tindakan dari penerima
    INFO          = "info"            # Informasi umum
    # [BARU — Modul Sample Shipment, §12.2 dokumen]
    SAMPLE        = "sample"          # Notifikasi sample shipment
    WAREHOUSE_SJ  = "warehouse_sj"    # Notifikasi surat jalan
    INVOICE       = "invoice"         # Notifikasi invoice finance


# ─── HELPER: BUAT NOTIFIKASI ─────────────────────────────────────────────────

async def _buat_notif(
    db: AsyncSession,
    user_id: uuid.UUID,
    fkp_id: uuid.UUID,
    judul: str,
    pesan: str,
    tipe: str,
):
    """Insert satu notifikasi ke DB — dengan dedup guard 5 menit.

    Jika dalam 5 menit terakhir sudah ada notifikasi dengan user_id + fkp_id + judul
    yang sama, skip insert untuk mencegah duplikat akibat double-click atau retry.
    """
    from datetime import timedelta
    from sqlalchemy import and_
    window_start = datetime.now(timezone.utc) - timedelta(minutes=5)
    existing = await db.execute(
        select(Notification).where(
            and_(
                Notification.user_id == user_id,
                Notification.fkp_id  == fkp_id,
                Notification.judul   == judul,
                Notification.created_at >= window_start,
            )
        ).limit(1)
    )
    if existing.scalar_one_or_none():
        return  # skip duplikat

    notif = Notification(
        user_id=user_id,
        fkp_id=fkp_id,
        judul=judul,
        pesan=pesan,
        tipe=tipe,
    )
    db.add(notif)


async def _get_users_by_role(db: AsyncSession, kode_role: str) -> List[User]:
    """Ambil semua user aktif dengan kode_role tertentu."""
    from app.models.role import Role
    result = await db.execute(
        select(User)
        .join(Role, User.role_id == Role.id)
        .where(Role.kode_role == kode_role, User.is_active == True)
    )
    return result.scalars().all()


async def notify_roles(
    db: AsyncSession, fkp_id: uuid.UUID, roles: List[str],
    judul: str, pesan: str, tipe: str = TipeNotifikasi.INFO,
):
    """
    [BARU — Modul Sample Shipment, Phase 8] Helper generik: kirim notifikasi
    yang sama ke semua user aktif pada daftar role tertentu. Dipakai oleh
    sample_service.py & warehouse_service.py agar tidak menduplikasi pola
    "loop role -> loop user -> _buat_notif" di banyak tempat.
    """
    for kode_role in roles:
        for u in await _get_users_by_role(db, kode_role):
            await _buat_notif(db, u.id, fkp_id, judul, pesan, tipe)


async def notify_user(
    db: AsyncSession, user_id: uuid.UUID, fkp_id: uuid.UUID,
    judul: str, pesan: str, tipe: str = TipeNotifikasi.INFO,
):
    """Helper generik: kirim notifikasi ke satu user spesifik (mis. sender sample)."""
    await _buat_notif(db, user_id, fkp_id, judul, pesan, tipe)


async def _get_apsm_for_distributor(db: AsyncSession, distributor_id: uuid.UUID) -> List[uuid.UUID]:
    """Cari APSM yang bertanggung jawab atas distributor ini (via SC/SPV → APSM chain)."""
    # Distributor → SC/SPV
    r = await db.execute(
        select(ScSpvDistributor).where(ScSpvDistributor.distributor_id == distributor_id)
    )
    sc_spv_map = r.scalar_one_or_none()
    if not sc_spv_map:
        return []

    # SC/SPV → APSM
    r2 = await db.execute(
        select(ApsmScSpv).where(ApsmScSpv.sc_spv_user_id == sc_spv_map.sc_spv_user_id)
    )
    apsm_map = r2.scalar_one_or_none()
    if not apsm_map:
        return []

    return [apsm_map.apsm_user_id]


async def _get_rsm_for_distributor(db: AsyncSession, distributor_id: uuid.UUID) -> List[uuid.UUID]:
    """Cari RSM yang bertanggung jawab atas distributor ini (via SC/SPV → APSM → RSM chain)."""
    apsm_ids = await _get_apsm_for_distributor(db, distributor_id)
    if not apsm_ids:
        return []

    rsm_ids = []
    for apsm_id in apsm_ids:
        r = await db.execute(
            select(RsmApsm).where(RsmApsm.apsm_user_id == apsm_id)
        )
        rsm_map = r.scalar_one_or_none()
        if rsm_map:
            rsm_ids.append(rsm_map.rsm_user_id)

    return rsm_ids


# ─── DISPATCH NOTIFIKASI PER TRANSISI ────────────────────────────────────────

async def kirim_notifikasi_transisi(
    db: AsyncSession,
    fkp: FkpComplaint,
    status_lama: str,
    status_baru: str,
    aktor: User,
):
    """
    Dipanggil setelah setiap transisi status FKP.
    Menentukan siapa yang harus menerima notifikasi dan jenis notifnya.

    Semua konstanta status mengacu pada FkpStatus di fkp_service.py:
      SUBMITTED, APSM_REVIEWED, RSM_APPROVAL_INVESTIGASI, IN_INVESTIGATION,
      INVESTIGATED, RSM_APPROVAL_RESOLUSI, DIREKTUR_APPROVAL, ACCEPTED,
      IN_PROCESS, NEED_REVISION, REJECTED, CLOSED
    """
    nomor  = fkp.nomor_fkp
    fkp_id = fkp.id
    dist_id = fkp.distributor_id

    # ── DRAFT → SUBMITTED ────────────────────────────────────────────────────
    if status_baru == FkpStatus.SUBMITTED:
        # Notify APSM area distributor — perlu action
        apsm_ids = await _get_apsm_for_distributor(db, dist_id)
        for uid in apsm_ids:
            await _buat_notif(db, uid, fkp_id,
                judul=f"FKP Baru Menunggu Review: {nomor}",
                pesan=(
                    f"FKP {nomor} telah disubmit oleh {aktor.nama} dan menunggu "
                    f"review APSM sebelum diteruskan ke Admin HO."
                ),
                tipe=TipeNotifikasi.NEED_ACTION,
            )
        # Notify Admin HO — info saja
        for u in await _get_users_by_role(db, "admin_ho"):
            await _buat_notif(db, u.id, fkp_id,
                judul=f"FKP Baru Masuk: {nomor}",
                pesan=(
                    f"FKP {nomor} telah disubmit oleh {aktor.nama} "
                    f"dan sedang menunggu review APSM."
                ),
                tipe=TipeNotifikasi.INFO,
            )

    # ── SUBMITTED → APSM_REVIEWED ────────────────────────────────────────────
    elif status_baru == FkpStatus.APSM_REVIEWED:
        if status_lama == FkpStatus.RSM_APPROVAL_INVESTIGASI:
            # RSM minta revisi → notify APSM
            apsm_ids = await _get_apsm_for_distributor(db, dist_id)
            for uid in apsm_ids:
                await _buat_notif(db, uid, fkp_id,
                    judul=f"FKP Dikembalikan RSM untuk Revisi: {nomor}",
                    pesan=(
                        f"RSM {aktor.nama} meminta revisi pada FKP {nomor}. "
                        f"Silakan perbaiki dan teruskan kembali ke Admin HO."
                    ),
                    tipe=TipeNotifikasi.NEED_ACTION,
                )
        else:
            # SUBMITTED → APSM_REVIEWED normal
            await _buat_notif(db, fkp.submitted_by, fkp_id,
                judul=f"FKP Anda Sedang Direview APSM: {nomor}",
                pesan=(
                    f"FKP {nomor} telah direview oleh APSM ({aktor.nama}) "
                    f"dan diteruskan ke Admin HO."
                ),
                tipe=TipeNotifikasi.STATUS_CHANGE,
            )
            for u in await _get_users_by_role(db, "admin_ho"):
                await _buat_notif(db, u.id, fkp_id,
                    judul=f"FKP Siap Direview Admin HO: {nomor}",
                    pesan=(
                        f"APSM {aktor.nama} telah meneruskan FKP {nomor} "
                        f"untuk review Admin HO."
                    ),
                    tipe=TipeNotifikasi.NEED_ACTION,
                )

    # ── APSM_REVIEWED → RSM_APPROVAL_INVESTIGASI ─────────────────────────────
    elif status_baru == FkpStatus.RSM_APPROVAL_INVESTIGASI:
        # Notify submitter — info
        await _buat_notif(db, fkp.submitted_by, fkp_id,
            judul=f"FKP Menunggu Persetujuan RSM: {nomor}",
            pesan=(
                f"FKP {nomor} telah disetujui Admin HO ({aktor.nama}) "
                f"dan menunggu persetujuan RSM untuk investigasi."
            ),
            tipe=TipeNotifikasi.STATUS_CHANGE,
        )
        # Notify RSM area — perlu action
        rsm_ids = await _get_rsm_for_distributor(db, dist_id)
        for uid in rsm_ids:
            await _buat_notif(db, uid, fkp_id,
                judul=f"FKP Menunggu Persetujuan Anda (Investigasi): {nomor}",
                pesan=(
                    f"Admin HO telah meneruskan FKP {nomor} untuk persetujuan "
                    f"investigasi. Silakan review dan berikan keputusan."
                ),
                tipe=TipeNotifikasi.NEED_ACTION,
            )

    # ── RSM_APPROVAL_INVESTIGASI → IN_INVESTIGATION ──────────────────────────
    elif status_baru == FkpStatus.IN_INVESTIGATION:
        # Notify submitter — info
        await _buat_notif(db, fkp.submitted_by, fkp_id,
            judul=f"FKP Sedang Diinvestigasi: {nomor}",
            pesan=(
                f"FKP {nomor} telah disetujui RSM ({aktor.nama}) "
                f"dan sedang dalam proses investigasi oleh tim QC."
            ),
            tipe=TipeNotifikasi.STATUS_CHANGE,
        )
        # Notify QC — perlu action
        for u in await _get_users_by_role(db, "qc"):
            await _buat_notif(db, u.id, fkp_id,
                judul=f"FKP Menunggu Investigasi QC: {nomor}",
                pesan=(
                    f"FKP {nomor} telah disetujui RSM dan siap untuk investigasi QC. "
                    f"Silakan lakukan investigasi dan input hasilnya."
                ),
                tipe=TipeNotifikasi.NEED_ACTION,
            )

    # ── IN_INVESTIGATION → INVESTIGATED ──────────────────────────────────────
    elif status_baru == FkpStatus.INVESTIGATED:
        if status_lama == FkpStatus.RSM_APPROVAL_RESOLUSI:
            # RSM minta revisi resolusi → notify Admin HO
            for u in await _get_users_by_role(db, "admin_ho"):
                await _buat_notif(db, u.id, fkp_id,
                    judul=f"FKP Dikembalikan RSM — Perlu Perbaikan Resolusi: {nomor}",
                    pesan=(
                        f"RSM {aktor.nama} meminta revisi pada FKP {nomor}. "
                        f"Silakan perbaiki dan teruskan kembali untuk persetujuan RSM."
                    ),
                    tipe=TipeNotifikasi.NEED_ACTION,
                )
        else:
            # IN_INVESTIGATION → INVESTIGATED normal
            for u in await _get_users_by_role(db, "admin_ho"):
                await _buat_notif(db, u.id, fkp_id,
                    judul=f"Investigasi Selesai: {nomor}",
                    pesan=(
                        f"QC {aktor.nama} telah menyelesaikan investigasi FKP {nomor}. "
                        f"Menunggu proses persetujuan resolusi RSM."
                    ),
                    tipe=TipeNotifikasi.INFO,
                )
            rsm_ids = await _get_rsm_for_distributor(db, dist_id)
            for uid in rsm_ids:
                await _buat_notif(db, uid, fkp_id,
                    judul=f"Investigasi FKP Selesai: {nomor}",
                    pesan=(
                        f"Tim QC telah menyelesaikan investigasi FKP {nomor}. "
                        f"Menunggu Admin HO meneruskan untuk persetujuan resolusi."
                    ),
                    tipe=TipeNotifikasi.INFO,
                )
            await _buat_notif(db, fkp.submitted_by, fkp_id,
                judul=f"Investigasi FKP Selesai: {nomor}",
                pesan=f"Investigasi FKP {nomor} telah selesai dilakukan oleh tim QC.",
                tipe=TipeNotifikasi.STATUS_CHANGE,
            )

    # ── INVESTIGATED → RSM_APPROVAL_RESOLUSI ─────────────────────────────────
    elif status_baru == FkpStatus.RSM_APPROVAL_RESOLUSI:
        # Notify RSM area — perlu action
        rsm_ids = await _get_rsm_for_distributor(db, dist_id)
        for uid in rsm_ids:
            await _buat_notif(db, uid, fkp_id,
                judul=f"FKP Menunggu Persetujuan Anda (Resolusi): {nomor}",
                pesan=(
                    f"Admin HO telah meneruskan FKP {nomor} untuk persetujuan resolusi. "
                    f"Silakan review hasil investigasi dan berikan keputusan."
                ),
                tipe=TipeNotifikasi.NEED_ACTION,
            )
        # Notify submitter — info
        await _buat_notif(db, fkp.submitted_by, fkp_id,
            judul=f"FKP Menunggu Persetujuan RSM (Resolusi): {nomor}",
            pesan=f"FKP {nomor} sedang dalam proses persetujuan resolusi oleh RSM.",
            tipe=TipeNotifikasi.STATUS_CHANGE,
        )

    # ── RSM_APPROVAL_RESOLUSI → DIREKTUR_APPROVAL ────────────────────────────
    elif status_baru == FkpStatus.DIREKTUR_APPROVAL:
        # Notify Direktur — perlu action
        for u in await _get_users_by_role(db, "direktur"):
            await _buat_notif(db, u.id, fkp_id,
                judul=f"FKP Menunggu Keputusan Anda: {nomor}",
                pesan=(
                    f"RSM {aktor.nama} telah menyetujui FKP {nomor} "
                    f"dan meneruskan untuk keputusan final Direktur."
                ),
                tipe=TipeNotifikasi.NEED_ACTION,
            )
        # Notify submitter — info
        await _buat_notif(db, fkp.submitted_by, fkp_id,
            judul=f"FKP Menunggu Persetujuan Direktur: {nomor}",
            pesan=f"FKP {nomor} telah disetujui RSM dan menunggu keputusan Direktur.",
            tipe=TipeNotifikasi.STATUS_CHANGE,
        )

    # ── DIREKTUR_APPROVAL → ACCEPTED ─────────────────────────────────────────
    elif status_baru == FkpStatus.ACCEPTED:
        # Notify submitter — info
        await _buat_notif(db, fkp.submitted_by, fkp_id,
            judul=f"FKP Diterima ✅: {nomor}",
            pesan=(
                f"FKP {nomor} telah disetujui Direktur. "
                f"Proses resolusi akan segera dilakukan."
            ),
            tipe=TipeNotifikasi.STATUS_CHANGE,
        )
        # Notify Admin HO — perlu action (buat resolusi)
        for u in await _get_users_by_role(db, "admin_ho"):
            await _buat_notif(db, u.id, fkp_id,
                judul=f"FKP Diterima — Buat Resolusi: {nomor}",
                pesan=(
                    f"Direktur telah menyetujui FKP {nomor}. "
                    f"Silakan buat resolusi (tukar barang / potong tagihan / pemusnahan)."
                ),
                tipe=TipeNotifikasi.NEED_ACTION,
            )
        # Notify QC — perlu action (input resolusi)
        for u in await _get_users_by_role(db, "qc"):
            await _buat_notif(db, u.id, fkp_id,
                judul=f"FKP Diterima — Input Resolusi: {nomor}",
                pesan=f"FKP {nomor} telah disetujui Direktur. Silakan input resolusi.",
                tipe=TipeNotifikasi.NEED_ACTION,
            )

    # ── ACCEPTED → IN_PROCESS ─────────────────────────────────────────────────
    # Dipanggil dari update_pengiriman untuk tipe tukar_barang / potong_tagihan
    elif status_baru == FkpStatus.IN_PROCESS:
        # Notify submitter — info
        await _buat_notif(db, fkp.submitted_by, fkp_id,
            judul=f"FKP Sedang Diproses: {nomor}",
            pesan=(
                f"Resolusi FKP {nomor} sedang dalam proses oleh Admin HO. "
                f"Anda akan diberitahu saat proses selesai."
            ),
            tipe=TipeNotifikasi.STATUS_CHANGE,
        )
        # Notify Admin HO — reminder selesaikan proses
        for u in await _get_users_by_role(db, "admin_ho"):
            await _buat_notif(db, u.id, fkp_id,
                judul=f"FKP In Process — Tutup Jika Selesai: {nomor}",
                pesan=(
                    f"FKP {nomor} sedang diproses. "
                    f"Tutup FKP setelah proses resolusi benar-benar selesai."
                ),
                tipe=TipeNotifikasi.NEED_ACTION,
            )

    # ── * → NEED_REVISION ────────────────────────────────────────────────────
    elif status_baru == FkpStatus.NEED_REVISION:
        await _buat_notif(db, fkp.submitted_by, fkp_id,
            judul=f"FKP Perlu Revisi: {nomor}",
            pesan=(
                f"FKP {nomor} dikembalikan oleh {aktor.nama} untuk diperbaiki. "
                f"Silakan periksa catatan dan lengkapi data yang dibutuhkan."
            ),
            tipe=TipeNotifikasi.NEED_ACTION,
        )

    # ── * → REJECTED ─────────────────────────────────────────────────────────
    elif status_baru == FkpStatus.REJECTED:
        # Notify submitter
        await _buat_notif(db, fkp.submitted_by, fkp_id,
            judul=f"FKP Ditolak ❌: {nomor}",
            pesan=(
                f"FKP {nomor} ditolak oleh {aktor.nama}. "
                f"Silakan periksa catatan untuk alasan penolakan."
            ),
            tipe=TipeNotifikasi.STATUS_CHANGE,
        )
        # Notify Admin HO — info
        for u in await _get_users_by_role(db, "admin_ho"):
            await _buat_notif(db, u.id, fkp_id,
                judul=f"FKP Ditolak: {nomor}",
                pesan=(
                    f"FKP {nomor} telah ditolak oleh {aktor.nama} "
                    f"(dari status: {status_lama})."
                ),
                tipe=TipeNotifikasi.INFO,
            )

    # ── IN_PROCESS / ACCEPTED (pemusnahan) → CLOSED ──────────────────────────
    elif status_baru == FkpStatus.CLOSED:
        # Kumpulkan semua pihak terkait
        recipients = set()
        recipients.add(fkp.submitted_by)
        if fkp.handled_by:
            recipients.add(fkp.handled_by)
        apsm_ids = await _get_apsm_for_distributor(db, dist_id)
        recipients.update(apsm_ids)

        for uid in recipients:
            await _buat_notif(db, uid, fkp_id,
                judul=f"FKP Ditutup: {nomor}",
                pesan=(
                    f"FKP {nomor} telah resmi ditutup oleh {aktor.nama}. "
                    f"Proses selesai."
                ),
                tipe=TipeNotifikasi.INFO,
            )
        # Notify Admin HO juga jika belum termasuk
        for u in await _get_users_by_role(db, "admin_ho"):
            if u.id not in recipients:
                await _buat_notif(db, u.id, fkp_id,
                    judul=f"FKP Ditutup: {nomor}",
                    pesan=f"FKP {nomor} telah resmi ditutup oleh {aktor.nama}.",
                    tipe=TipeNotifikasi.INFO,
                )


# ─── QUERY NOTIFIKASI ────────────────────────────────────────────────────────

async def get_notifications(
    db: AsyncSession,
    user: User,
    hanya_belum_dibaca: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> NotificationListResponse:
    """Ambil daftar notifikasi untuk user yang sedang login."""
    from sqlalchemy import func, select as sa_select

    # ── Total & unread count dalam satu query ────────────────────────────
    count_r = await db.execute(
        sa_select(
            func.count().label("total"),
            func.count().filter(Notification.is_read == False).label("unread"),
        ).where(Notification.user_id == user.id)
    )
    counts = count_r.one()
    total, unread_count = counts.total, counts.unread

    # ── Fetch notifikasi dengan pagination ───────────────────────────────
    base_query = (
        select(Notification)
        .where(Notification.user_id == user.id)
    )
    if hanya_belum_dibaca:
        base_query = base_query.where(Notification.is_read == False)

    data_q = base_query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(data_q)
    notifs = result.scalars().all()

    # ── Batch fetch FKP — satu query untuk semua fkp_id ─────────────────
    fkp_ids = {n.fkp_id for n in notifs if n.fkp_id}
    fkp_map: dict[uuid.UUID, FkpComplaint] = {}
    if fkp_ids:
        fkp_r = await db.execute(
            select(FkpComplaint).where(FkpComplaint.id.in_(fkp_ids))
        )
        fkp_map = {fkp.id: fkp for fkp in fkp_r.scalars().all()}

    # ── Enrich dari map — zero query di loop ────────────────────────────
    items = []
    for n in notifs:
        fkp = fkp_map.get(n.fkp_id) if n.fkp_id else None
        items.append(NotificationResponse(
            id=n.id,
            user_id=n.user_id,
            fkp_id=n.fkp_id,
            judul=n.judul,
            pesan=n.pesan,
            tipe=n.tipe,
            is_read=n.is_read,
            created_at=n.created_at,
            read_at=n.read_at,
            nomor_fkp=fkp.nomor_fkp if fkp else None,
            fkp_status=fkp.status if fkp else None,
        ))

    return NotificationListResponse(
        notifications=items,
        total=total,
        unread_count=unread_count,
    )

async def get_unread_count(db: AsyncSession, user: User) -> NotificationSummary:
    """Hanya unread count — untuk badge / polling ringan."""
    from sqlalchemy import func, select as sa_select
    q = sa_select(func.count()).select_from(
        select(Notification).where(
            Notification.user_id == user.id,
            Notification.is_read == False,
        ).subquery()
    )
    r = await db.execute(q)
    return NotificationSummary(unread_count=r.scalar_one())


async def mark_as_read(
    db: AsyncSession,
    user: User,
    notification_ids: List[uuid.UUID],
) -> dict:
    """Tandai notifikasi sebagai sudah dibaca."""
    if not notification_ids:
        return {"updated": 0}

    now = datetime.now(timezone.utc)

    # ── Fetch semua sekaligus — satu query ──────────────────────────────
    r = await db.execute(
        select(Notification).where(
            Notification.id.in_(notification_ids),
            Notification.user_id == user.id,
            Notification.is_read == False,
        )
    )
    notifs = r.scalars().all()

    # ── Update in-memory, satu commit ───────────────────────────────────
    for notif in notifs:
        notif.is_read = True
        notif.read_at = now
        db.add(notif)

    await db.commit()
    return {"updated": len(notifs)}


async def mark_all_as_read(db: AsyncSession, user: User) -> dict:
    """Tandai semua notifikasi user sebagai dibaca."""
    from sqlalchemy import update
    now = datetime.now(timezone.utc)
    stmt = (
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read == False)
        .values(is_read=True, read_at=now)
    )
    result = await db.execute(stmt)
    await db.commit()
    return {"updated": result.rowcount}


async def delete_notification(
    db: AsyncSession,
    user: User,
    notification_id: uuid.UUID,
) -> bool:
    """Hapus satu notifikasi milik user."""
    r = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    )
    notif = r.scalar_one_or_none()
    if not notif:
        return False
    await db.delete(notif)
    await db.commit()
    return True
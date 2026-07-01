"""
Dipanggil dari fkp_service setelah commit — resolve user dari DB
lalu fire email di background (tidak memblokir response API).
"""
import asyncio
import logging
from typing import Optional

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fkp import FkpComplaint, FkpStatus
from app.models.user import User
from app.services import email_service

logger = logging.getLogger(__name__)


async def _get_user(db: AsyncSession, user_id) -> Optional[User]:
    if not user_id:
        return None
    r = await db.execute(select(User).where(User.id == user_id))
    return r.scalar_one_or_none()


def _nama(user: Optional[User]) -> str:
    """Ambil nama terbaik dari user, fallback ke 'Pengguna'."""
    if not user:
        return "Pengguna"
    # Sesuaikan nama field dengan model User Anda
    return (
        getattr(user, "nama_lengkap", None)
        or getattr(user, "nama", None)
        or getattr(user, "full_name", None)
        or user.email.split("@")[0]
    )


async def trigger_email_after_transition(
    db: AsyncSession,
    fkp: FkpComplaint,
    status_lama: str,
    status_baru: str,
    actor: User,
    catatan: Optional[str] = None,
) -> None:
    """
    Entry point — panggil setelah db.commit() di setiap fungsi transisi.
    Menjalankan pengiriman email sebagai asyncio background task
    sehingga tidak memperlambat response API.
    """
    # Resolve submitter
    submitter = await _get_user(db, fkp.submitted_by)
    if not submitter or not getattr(submitter, "email", None):
        logger.warning("[EMAIL-TRIGGER] FKP %s: email submitter kosong, skip.", fkp.nomor_fkp)
        return

    to_email      = submitter.email
    nama_penerima = _nama(submitter)
    actor_nama    = _nama(actor)
    fkp_id        = str(fkp.id)

    # Pilih fungsi email berdasarkan status baru
    if status_baru == FkpStatus.SUBMITTED:
        coro = email_service.kirim_email_fkp_submitted(
            to_email=to_email, nama_penerima=nama_penerima,
            nomor_fkp=fkp.nomor_fkp, fkp_id=fkp_id,
            prioritas=fkp.prioritas,
        )

    elif status_baru == FkpStatus.NEED_REVISION:
        coro = email_service.kirim_email_fkp_need_revision(
            to_email=to_email, nama_penerima=nama_penerima,
            nomor_fkp=fkp.nomor_fkp, fkp_id=fkp_id,
            catatan_revisi=catatan, direview_oleh=actor_nama,
        )

    elif status_baru == FkpStatus.REJECTED:
        coro = email_service.kirim_email_fkp_rejected(
            to_email=to_email, nama_penerima=nama_penerima,
            nomor_fkp=fkp.nomor_fkp, fkp_id=fkp_id,
            alasan_penolakan=catatan or "Tidak ada keterangan.",
            ditolak_oleh=actor_nama,
        )

    elif status_baru == FkpStatus.CLOSED:
        tipe = fkp.resolution.tipe_resolusi if fkp.resolution else None
        coro = email_service.kirim_email_fkp_closed(
            to_email=to_email, nama_penerima=nama_penerima,
            nomor_fkp=fkp.nomor_fkp, fkp_id=fkp_id,
            tipe_resolusi=tipe,
        )

    else:
        # Status lain tidak memerlukan notifikasi email ke submitter
        return

    # Fire-and-forget — tidak await langsung agar response API tidak tertahan
    asyncio.create_task(coro)
    logger.info("[EMAIL-TRIGGER] Task email dibuat: %s → %s", status_baru, to_email)
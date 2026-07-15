"""
Public Tracking Endpoint — app/api/endpoints/public_tracking.py

Letakkan file ini di: app/api/endpoints/public_tracking.py
(sejajar dengan auth.py, fkp.py, users.py, dst.)

Daftarkan di main.py:
    from app.api.endpoints import public_tracking
    app.include_router(
        public_tracking.router,
        prefix="/api/public/fkp",
        tags=["Public Tracking"],
    )

Endpoint yang tersedia:
    GET /api/public/fkp/{fkp_id}  — tracking publik tanpa login
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select
from pydantic import BaseModel

from app.core.dependencies import get_db
from app.models.fkp import FkpComplaint, FkpStatus

router = APIRouter()


# ─── Response Schemas (non-sensitif) ─────────────────────────────────────────

class TrackingStage(BaseModel):
    label: str
    timestamp: Optional[datetime] = None   # None = tahap belum dicapai
    is_current: bool
    is_completed: bool


class PublicTrackingResponse(BaseModel):
    fkp_id: str
    nomor_fkp: str
    nama_distributor: Optional[str] = None
    nama_outlet: Optional[str] = None
    status: str
    status_label: str
    prioritas: str
    tanggal_pengajuan: Optional[datetime] = None
    tanggal_selesai: Optional[datetime] = None
    timeline: List[TrackingStage]
    is_closed: bool
    is_rejected: bool


# ─── Label publik ─────────────────────────────────────────────────────────────

PUBLIC_STATUS_LABELS = {
    FkpStatus.DRAFT:                    "Formulir Sedang Disiapkan",
    FkpStatus.SUBMITTED:                "Keluhan Diterima — Menunggu Verifikasi Lapangan",
    FkpStatus.APSM_REVIEWED:            "Terverifikasi Lapangan — Menunggu Review Internal",
    FkpStatus.RSM_APPROVAL_INVESTIGASI: "Menunggu Persetujuan Investigasi",
    FkpStatus.IN_INVESTIGATION:         "Sedang Diinvestigasi",
    FkpStatus.INVESTIGATED:             "Investigasi Selesai — Menyusun Resolusi",
    FkpStatus.RSM_APPROVAL_RESOLUSI:    "Menunggu Persetujuan Resolusi",
    FkpStatus.DIREKTUR_APPROVAL:        "Menunggu Persetujuan Final",
    FkpStatus.ACCEPTED:                 "Disetujui — Sedang Diproses",
    FkpStatus.IN_PROCESS:               "Dalam Proses Penyelesaian",
    FkpStatus.NEED_REVISION:            "Dikembalikan untuk Perbaikan",
    FkpStatus.REJECTED:                 "Keluhan Tidak Dapat Diproses",
    FkpStatus.CLOSED:                   "Selesai",
}

# Urutan maju (tidak termasuk need_revision / rejected / draft)
STAGE_ORDER = [
    FkpStatus.SUBMITTED,
    FkpStatus.APSM_REVIEWED,
    FkpStatus.RSM_APPROVAL_INVESTIGASI,
    FkpStatus.IN_INVESTIGATION,
    FkpStatus.INVESTIGATED,
    FkpStatus.RSM_APPROVAL_RESOLUSI,
    FkpStatus.DIREKTUR_APPROVAL,
    FkpStatus.ACCEPTED,
    FkpStatus.IN_PROCESS,
    FkpStatus.CLOSED,
]


# ─── Helper ───────────────────────────────────────────────────────────────────

def _build_timeline(current_status: str, status_logs: list) -> List[TrackingStage]:
    """
    Bangun timeline publik.

    Aturan:
    - Hanya status dalam STAGE_ORDER yang masuk timeline
    - Timestamp diambil dari log aktual (pertama kali status dicapai)
    - Tahap yang belum dicapai: timestamp=None, is_completed=False, is_current=False
    - Tampilkan satu tahap ke depan (next step) agar user tahu akan ke mana
    - need_revision / rejected ditambahkan di akhir jika itu status saat ini
    """
    # Lookup: status → waktu pertama kali dicapai
    status_timestamps: dict = {}
    for log in sorted(status_logs, key=lambda l: l.changed_at):
        if log.status_baru not in status_timestamps:
            status_timestamps[log.status_baru] = log.changed_at

    try:
        current_idx = STAGE_ORDER.index(current_status)
    except ValueError:
        current_idx = -1  # rejected / need_revision / draft

    timeline: List[TrackingStage] = []
    for stage in STAGE_ORDER:
        stage_idx = STAGE_ORDER.index(stage)
        ts = status_timestamps.get(stage)

        is_completed = stage_idx < current_idx if current_idx >= 0 else False
        is_current = stage == current_status

        # Lewati tahap yang belum dicapai kecuali satu "next step"
        if ts is None and not is_current:
            if stage_idx != current_idx + 1:
                continue  # sembunyikan tahap jauh ke depan

        timeline.append(TrackingStage(
            label=PUBLIC_STATUS_LABELS.get(stage, stage),
            timestamp=ts,            # None jika belum dicapai
            is_current=is_current,
            is_completed=is_completed,
        ))

    # Tambahkan need_revision / rejected di akhir jika itu status aktif
    if current_status in (FkpStatus.REJECTED, FkpStatus.NEED_REVISION):
        ts = status_timestamps.get(current_status)
        timeline.append(TrackingStage(
            label=PUBLIC_STATUS_LABELS.get(current_status, current_status),
            timestamp=ts,
            is_current=True,
            is_completed=False,
        ))

    return timeline


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.get(
    "/{fkp_id}",
    response_model=PublicTrackingResponse,
    summary="Tracking publik FKP — tanpa autentikasi",
    responses={
        200: {"description": "Data tracking FKP"},
        404: {"description": "FKP tidak ditemukan"},
    },
)
async def track_fkp(
    fkp_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint publik — tidak memerlukan Bearer token.

    Hanya mengembalikan informasi tracking (status + timeline).
    Data sensitif (rekening, cashback, nama staff internal) tidak disertakan.
    """
    r = await db.execute(
        select(FkpComplaint)
        .where(FkpComplaint.id == fkp_id)
        .options(
            selectinload(FkpComplaint.status_logs),
            selectinload(FkpComplaint.distributor),
            selectinload(FkpComplaint.outlet),
        )
    )
    fkp = r.scalar_one_or_none()

    if not fkp:
        raise HTTPException(
            status_code=404,
            detail="FKP tidak ditemukan. Pastikan UUID yang Anda masukkan sudah benar.",
        )

    timeline = _build_timeline(fkp.status, fkp.status_logs or [])

    return PublicTrackingResponse(
        fkp_id=str(fkp.id),
        nomor_fkp=fkp.nomor_fkp,
        # Sesuai model Distributor: field nama_perusahaan
        # Sesuai model Outlet: field nama_toko
        nama_distributor=fkp.distributor.nama_perusahaan if fkp.distributor else None,
        nama_outlet=fkp.outlet.nama_toko if fkp.outlet else None,
        status=fkp.status,
        status_label=PUBLIC_STATUS_LABELS.get(fkp.status, fkp.status),
        prioritas=fkp.prioritas,
        tanggal_pengajuan=fkp.tanggal_pengajuan,
        tanggal_selesai=fkp.tanggal_selesai,
        timeline=timeline,
        is_closed=fkp.status == FkpStatus.CLOSED,
        is_rejected=fkp.status == FkpStatus.REJECTED,
    )
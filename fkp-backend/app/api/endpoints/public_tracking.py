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
from typing import Optional, List, Literal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select
from pydantic import BaseModel

from app.core.dependencies import get_db
from app.models.fkp import (
    BATAS_QTY_DIREKTUR, FkpComplaint, FkpItem, FkpStatus, JenisKeluhan,
)
from app.models.distributor import Distributor


router = APIRouter()


# ─── Response Schemas (non-sensitif) ─────────────────────────────────────────

StepState = Literal["done", "current", "pending", "rejected"]


class TrackingStep(BaseModel):
    key: str
    label: str
    state: StepState
    timestamp: Optional[datetime] = None

class TrackingItem(BaseModel):
    nama_produk: str
    jenis_kemasan: Optional[str] = None
    qty: int
    jenis_keluhan: str
    jenis_keluhan_label: str
    deskripsi_keluhan: Optional[str] = None

class TrackingPhase(BaseModel):
    key: str
    label: str
    state: StepState
    timestamp: Optional[datetime] = None
    steps: List[TrackingStep]


class PublicTrackingResponse(BaseModel):
    fkp_id: str
    nomor_fkp: str
    nama_distributor: Optional[str] = None
    nama_outlet: Optional[str] = None
    area: Optional[str] = None                 # BARU
    status: str
    status_label: str
    prioritas: str
    tanggal_pengajuan: Optional[datetime] = None
    tanggal_selesai: Optional[datetime] = None
    catatan_pembuat: Optional[str] = None
    items: List[TrackingItem] = []
    phases: List[TrackingPhase]
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
    FkpStatus.RSM_APPROVAL_FINAL:       "Menunggu Persetujuan Akhir",
    FkpStatus.ACCEPTED:                 "Disetujui — Sedang Diproses",
    FkpStatus.IN_PROCESS:               "Dalam Proses Penyelesaian",
    FkpStatus.NEED_REVISION:            "Dikembalikan untuk Perbaikan",
    FkpStatus.REJECTED:                 "Keluhan Tidak Dapat Diproses",
    FkpStatus.CLOSED:                   "Selesai",
}

STEP_ORDER = [
    "submitted", "apsm_review", "ho_review",
    "pemeriksaan", "approval", "pengiriman", "selesai",
]

STEP_LABELS = {
    "submitted":   "Keluhan diajukan",
    "apsm_review": "Review APSM",
    "ho_review":   "Masuk ke HO",
    "pemeriksaan": "Pemeriksaan & penyusunan resolusi",
    "approval":    "Proses approval",
    "pengiriman":  "Proses pengiriman",
    "selesai":     "Selesai",
}

PHASES = [
    ("submitted",  "Diajukan",               ["submitted"]),
    ("review",     "Review APSM & Admin HO", ["apsm_review", "ho_review", "pemeriksaan"]),
    ("approval",   "Proses Approval",        ["approval"]),
    ("pengiriman", "Proses Pengiriman",      ["pengiriman", "selesai"]),
]

# Status FKP saat ini -> langkah yang SEDANG berjalan
STATUS_TO_STEP = {
    FkpStatus.SUBMITTED:                "apsm_review",
    FkpStatus.APSM_REVIEWED:            "ho_review",
    FkpStatus.RSM_APPROVAL_INVESTIGASI: "pemeriksaan",
    FkpStatus.IN_INVESTIGATION:         "pemeriksaan",
    FkpStatus.INVESTIGATED:             "pemeriksaan",
    FkpStatus.RSM_APPROVAL_RESOLUSI:    "approval",
    FkpStatus.DIREKTUR_APPROVAL:        "approval",
    FkpStatus.ACCEPTED:                 "pengiriman",
    FkpStatus.IN_PROCESS:               "pengiriman",
}

# Sebuah langkah dianggap SELESAI saat FKP masuk ke salah satu status ini
STEP_DONE_AT = {
    "submitted":   [FkpStatus.SUBMITTED],
    "apsm_review": [FkpStatus.APSM_REVIEWED],
    "ho_review":   [FkpStatus.RSM_APPROVAL_INVESTIGASI, FkpStatus.RSM_APPROVAL_FINAL],
    "pemeriksaan": [FkpStatus.RSM_APPROVAL_RESOLUSI],   # jalur cepat: resolution.created_at
    "approval":    [FkpStatus.ACCEPTED],
    "pengiriman":  [FkpStatus.CLOSED],
    "selesai":     [FkpStatus.CLOSED],
}



def _step_for_status(status: Optional[str], has_resolution: bool) -> Optional[str]:
    if status == FkpStatus.RSM_APPROVAL_FINAL:
        # Jalur cepat: Admin HO membuat resolusi SAAT status ini, baru RSM approve.
        # Ini hanya membaca status, bukan menentukan jalur.
        return "approval" if has_resolution else "pemeriksaan"
    return STATUS_TO_STEP.get(status)

def _build_phases(fkp: FkpComplaint) -> List[TrackingPhase]:
    logs = sorted(fkp.status_logs or [], key=lambda l: l.changed_at)

    # status -> waktu TERAKHIR FKP masuk status itu. Log tanpa perpindahan
    # (status_lama == status_baru, mis. "diteruskan ke Warehouse") bukan transisi.
    ts_by_status: dict = {}
    for log in logs:
        if log.status_lama != log.status_baru:
            ts_by_status[log.status_baru] = log.changed_at

    resolution = fkp.resolution
    has_resolution = resolution is not None

    # Posisi FKP: langkah sebelum marker = done, marker = current/rejected,
    # sesudahnya = pending.
    if fkp.status == FkpStatus.CLOSED:
        marker_idx, marker_state = len(STEP_ORDER), "done"     # semua selesai
    elif fkp.status == FkpStatus.REJECTED:
        lama = next(
            (l.status_lama for l in reversed(logs) if l.status_baru == FkpStatus.REJECTED),
            None,
        )
        key = _step_for_status(lama, has_resolution) or "ho_review"  # fallback jika log hilang
        marker_idx, marker_state = STEP_ORDER.index(key), "rejected"
    else:
        key = _step_for_status(fkp.status, has_resolution)
        marker_idx = STEP_ORDER.index(key) if key else -1      # draft / need_revision
        marker_state = "current"

    def done_at(key: str) -> Optional[datetime]:
        times = [ts_by_status[s] for s in STEP_DONE_AT[key] if s in ts_by_status]
        if not times and key == "pemeriksaan" and resolution:
            return resolution.created_at    # jalur cepat: tidak ada status khusus
        return max(times) if times else None

    steps: List[TrackingStep] = []
    prev_ts: Optional[datetime] = None
    for idx, key in enumerate(STEP_ORDER):
        if idx < marker_idx:
            state = "done"
        elif idx == marker_idx:
            state = marker_state
        else:
            state = "pending"

        if fkp.status == FkpStatus.REJECTED and state == "pending":
            continue  # FKP ditolak: tahap setelahnya tidak relevan

        if state == "done":
            ts = done_at(key)
        elif state == "current":
            ts = prev_ts          # "sejak" = langkah sebelumnya selesai
        elif state == "rejected":
            ts = ts_by_status.get(FkpStatus.REJECTED)
        else:
            ts = None

        steps.append(TrackingStep(key=key, label=STEP_LABELS[key], state=state, timestamp=ts))
        prev_ts = ts

    by_key = {s.key: s for s in steps}
    phases: List[TrackingPhase] = []
    for pkey, plabel, keys in PHASES:
        p_steps = [by_key[k] for k in keys if k in by_key]
        if not p_steps:
            continue
        states = [s.state for s in p_steps]
        if all(st == "done" for st in states):
            pstate = "done"
        elif "rejected" in states:
            pstate = "rejected"
        elif all(st == "pending" for st in states):
            pstate = "pending"
        else:
            pstate = "current"

        if pstate == "done":
            pts = p_steps[-1].timestamp
        elif pstate in ("current", "rejected"):
            pts = next((s.timestamp for s in p_steps if s.state in ("current", "rejected")), None)
        else:
            pts = None

        phases.append(TrackingPhase(
            key=pkey, label=plabel, state=pstate, timestamp=pts, steps=p_steps,
        ))
    return phases

def _resolve_area(fkp: FkpComplaint) -> Optional[str]:
    if fkp.distributor and fkp.distributor.area:
        return fkp.distributor.area.nama_area
    return None


def _build_items(fkp: FkpComplaint) -> List[TrackingItem]:
    items = sorted(fkp.items or [], key=lambda i: i.created_at)
    return [
        TrackingItem(
            nama_produk=i.product.nama_produk if i.product else "-",  # GANTI jika beda
            jenis_kemasan=i.jenis_kemasan,
            qty=i.qty,
            jenis_keluhan=i.jenis_keluhan,
            jenis_keluhan_label=JenisKeluhan.LABELS.get(i.jenis_keluhan, i.jenis_keluhan),
            deskripsi_keluhan=i.deskripsi_keluhan,
        )
        for i in items
    ]


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
            selectinload(FkpComplaint.distributor).selectinload(Distributor.area),
            selectinload(FkpComplaint.outlet),
            selectinload(FkpComplaint.items).selectinload(FkpItem.product),
            selectinload(FkpComplaint.resolution),
        )
    )
    fkp = r.scalar_one_or_none()

    if not fkp:
        raise HTTPException(
            status_code=404,
            detail="FKP tidak ditemukan. Pastikan UUID yang Anda masukkan sudah benar.",
        )

    phases = _build_phases(fkp)
    
    return PublicTrackingResponse(
        fkp_id=str(fkp.id),
        nomor_fkp=fkp.nomor_fkp,
        nama_distributor=fkp.distributor.nama_perusahaan if fkp.distributor else None,
        nama_outlet=fkp.outlet.nama_toko if fkp.outlet else None,
        area=_resolve_area(fkp),
        status=fkp.status,
        status_label=PUBLIC_STATUS_LABELS.get(fkp.status, fkp.status),
        prioritas=fkp.prioritas,
        tanggal_pengajuan=fkp.tanggal_pengajuan,
        tanggal_selesai=fkp.tanggal_selesai,
        catatan_pembuat=fkp.catatan_distributor,
        items=_build_items(fkp),
        phases=phases,
        is_closed=fkp.status == FkpStatus.CLOSED,
        is_rejected=fkp.status == FkpStatus.REJECTED,
    )
"""
Model Testimoni — pendapat/ulasan pelanggan setelah FKP ditutup (closed).

Testimoni hanya bisa diberikan ketika FKP sudah berstatus 'closed'.
Mencakup dua dimensi penilaian:
  1. Penanganan keluhan  — rating keseluruhan + per aspek (kecepatan, komunikasi, solusi)
  2. Aplikasi FKP        — rating tunggal + kritik/saran terpisah untuk tim dan aplikasi

Tipe responden: distributor | outlet
"""
import uuid
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import DateTime, Column
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .fkp import FkpComplaint
    from .user import User


class FkpTestimoni(SQLModel, table=True):
    """
    Testimoni pelanggan terhadap penanganan FKP.

    Aturan bisnis:
    - Hanya bisa dibuat ketika FKP sudah berstatus 'closed'
    - Satu FKP hanya boleh punya satu testimoni per user (unique fkp_id + user_id)
    - Hanya bisa dibuat oleh user yang terkait dengan FKP (distributor/outlet)
    - Bisa diupdate oleh user yang sama
    - Rating keseluruhan 1–5 (wajib)
    - Rating aplikasi 1–5 (opsional)
    - Komentar, kritik_saran_tim, kritik_saran_app opsional (masing-masing max 1000 karakter)
    """
    __tablename__ = "fkp_testimoni"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    fkp_id: uuid.UUID = Field(
        foreign_key="fkp_complaints.id",
        index=True,
        description="FKP yang ditestimoni"
    )
    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        index=True,
        description="User pemberi testimoni (distributor/outlet)"
    )

    # ── Rating utama ──────────────────────────────────────────────────────
    rating_keseluruhan: int = Field(
        ge=1, le=5,
        description="Rating keseluruhan 1–5 bintang"
    )

    # ── Rating per aspek penanganan (wajib) ───────────────────────────────
    rating_kecepatan: int = Field(
        ge=1, le=5,
        description="Kecepatan penanganan keluhan"
    )
    rating_komunikasi: int = Field(
        ge=1, le=5,
        description="Kualitas komunikasi dari tim"
    )
    rating_solusi: int = Field(
        ge=1, le=5,
        description="Kepuasan terhadap solusi yang diberikan"
    )

    # ── Rating aplikasi (wajib) ───────────────────────────────────────────
    rating_aplikasi: int = Field(
        ge=1, le=5,
        description="Rating pengalaman penggunaan aplikasi FKP"
    )

    # ── Teks penanganan & masukan aplikasi ───────────────────────────────
    komentar: Optional[str] = Field(
        default=None, max_length=1000,
        description="Ulasan bebas tentang penanganan keluhan secara keseluruhan"
    )
    kritik_saran_tim: Optional[str] = Field(
        default=None, max_length=1000,
        description="Kritik dan saran khusus untuk tim penanganan (APSM, Admin HO, QC, dll)"
    )
    kritik_saran_app: Optional[str] = Field(
        default=None, max_length=1000,
        description="Kritik dan saran khusus untuk aplikasi FKP"
    )

    # ── Tipe responden ────────────────────────────────────────────────────
    tipe_responden: str = Field(
        max_length=20,
        description="'distributor' | 'outlet'"
    )

    # ── Visibilitas ───────────────────────────────────────────────────────
    is_public: bool = Field(
        default=True,
        description="Apakah testimoni boleh ditampilkan ke publik internal"
    )

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    # ── Relasi ────────────────────────────────────────────────────────────
    fkp: Optional["FkpComplaint"] = Relationship(back_populates="testimoni")
    user: Optional["User"] = Relationship(back_populates="fkp_testimoni")
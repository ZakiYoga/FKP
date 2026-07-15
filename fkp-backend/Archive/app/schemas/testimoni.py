"""
Schema Pydantic untuk fitur Testimoni FKP.
"""
import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, field_validator, model_validator


# ─── REQUEST ──────────────────────────────────────────────────────────────────

class TestimoniCreate(BaseModel):
    """
    Body request untuk membuat testimoni baru.

    Wajib   : semua rating (keseluruhan, kecepatan, komunikasi, solusi, aplikasi)
    Opsional: komentar, kritik_saran_tim, kritik_saran_app
    """
    rating_keseluruhan: int
    rating_kecepatan: int
    rating_komunikasi: int
    rating_solusi: int
    rating_aplikasi: int
    komentar: Optional[str] = None
    kritik_saran_tim: Optional[str] = None
    kritik_saran_app: Optional[str] = None
    is_public: bool = True

    @field_validator(
        "rating_keseluruhan", "rating_kecepatan",
        "rating_komunikasi", "rating_solusi", "rating_aplikasi",
    )
    @classmethod
    def rating_valid(cls, v):
        if not (1 <= v <= 5):
            raise ValueError("Rating harus antara 1 dan 5")
        return v

    @field_validator("komentar", "kritik_saran_tim", "kritik_saran_app")
    @classmethod
    def teks_max(cls, v):
        if v is not None and len(v) > 1000:
            raise ValueError("Teks maksimal 1000 karakter")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "rating_keseluruhan": 4,
                "rating_kecepatan": 5,
                "rating_komunikasi": 4,
                "rating_solusi": 3,
                "rating_aplikasi": 4,
                "komentar": "Penanganan cukup baik, namun solusi akhir kurang memuaskan.",
                "kritik_saran_tim": "Mohon respon lebih cepat saat status investigasi.",
                "kritik_saran_app": "Fitur tracking status sudah bagus, notifikasi perlu ditingkatkan.",
                "is_public": True
            }
        }


class TestimoniUpdate(BaseModel):
    """
    Update testimoni — field teks opsional, rating jika dikirim tidak boleh null.
    Minimal satu field harus diisi.
    """
    rating_keseluruhan: Optional[int] = None
    rating_kecepatan: Optional[int] = None
    rating_komunikasi: Optional[int] = None
    rating_solusi: Optional[int] = None
    rating_aplikasi: Optional[int] = None
    komentar: Optional[str] = None
    kritik_saran_tim: Optional[str] = None
    kritik_saran_app: Optional[str] = None
    is_public: Optional[bool] = None

    @field_validator(
        "rating_keseluruhan", "rating_kecepatan",
        "rating_komunikasi", "rating_solusi", "rating_aplikasi",
    )
    @classmethod
    def rating_valid(cls, v):
        if v is not None and not (1 <= v <= 5):
            raise ValueError("Rating harus antara 1 dan 5")
        return v

    @field_validator("komentar", "kritik_saran_tim", "kritik_saran_app")
    @classmethod
    def teks_max(cls, v):
        if v is not None and len(v) > 1000:
            raise ValueError("Teks maksimal 1000 karakter")
        return v


# ─── RESPONSE ─────────────────────────────────────────────────────────────────

class TestimoniResponse(BaseModel):
    """Response lengkap satu testimoni."""
    id: uuid.UUID
    fkp_id: uuid.UUID
    user_id: uuid.UUID
    nama_pemberi: Optional[str] = None
    # Penanganan keluhan
    rating_keseluruhan: int
    rating_kecepatan: int
    rating_komunikasi: int
    rating_solusi: int
    komentar: Optional[str]
    kritik_saran_tim: Optional[str]
    # Aplikasi
    rating_aplikasi: int
    kritik_saran_app: Optional[str]
    # Meta
    tipe_responden: str
    is_public: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TestimoniRingkasanResponse(BaseModel):
    """
    Ringkasan/statistik testimoni untuk satu FKP atau agregat semua FKP.
    Digunakan untuk dashboard atau header halaman detail FKP.
    """
    total_testimoni: int
    # Penanganan keluhan
    rata_rata_keseluruhan: Optional[float]
    rata_rata_kecepatan: Optional[float]
    rata_rata_komunikasi: Optional[float]
    rata_rata_solusi: Optional[float]
    distribusi_rating: dict        # { "1": 0, "2": 1, "3": 3, "4": 5, "5": 2 }
    # Aplikasi
    rata_rata_aplikasi: Optional[float]
    distribusi_rating_aplikasi: dict   # { "1": 0, "2": 0, "3": 1, "4": 3, "5": 2 }
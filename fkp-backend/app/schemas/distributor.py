import re
import uuid
from typing import Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from app.schemas.wilayah import WilayahLengkap


# ─── KOORDINAT (dipakai bersama) ──────────────────────────────────────────────

class _GeoFields(BaseModel):
    """
    Koordinat lokasi dari peta. latitude & longitude harus diisi bersamaan
    atau dikosongkan bersamaan (tidak boleh hanya salah satu), supaya data di DB
    tidak pernah berisi titik setengah jadi.
    """
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def _coords_together(self):
        sent = self.model_fields_set
        if (("latitude" in sent) != ("longitude" in sent)) or ((self.latitude is None) != (self.longitude is None)):
            raise ValueError("latitude dan longitude harus diisi bersamaan.")
        return self


# ─── DISTRIBUTOR ──────────────────────────────────────────────────────────────

class DistributorCreate(_GeoFields):
    area_id: uuid.UUID
    kelurahan_id: Optional[int] = None
    kode_distributor: str
    nama_perusahaan: str
    pemilik: str
    no_telepon: Optional[str] = None
    email_perusahaan: Optional[EmailStr] = None
    alamat_lengkap: Optional[str] = None
    npwp: Optional[str] = None

    @field_validator("npwp")
    @classmethod
    def validate_npwp(cls, v):
        if v is None or v == "":
            return None
        digits = re.sub(r"\D", "", v)
        if len(digits) not in (15, 16):
            raise ValueError("NPWP harus 15 atau 16 digit")
        return digits

    class Config:
        json_schema_extra = {
            "example": {
                "area_id": "uuid-area",
                "kode_distributor": "DIST-001",
                "nama_perusahaan": "PT Maju Sejahtera",
                "pemilik": "Budi Santoso",
                "no_telepon": "08123456789",
                "email_perusahaan": "budi@majusejahtera.com",
                "alamat_lengkap": "Jl. Contoh No. 1",
                "kelurahan_id": 35502,
                "latitude": -7.558496,
                "longitude": 110.887668,
            }
        }


class DistributorUpdate(_GeoFields):
    area_id: Optional[uuid.UUID] = None
    kelurahan_id: Optional[int] = None
    nama_perusahaan: Optional[str] = None
    pemilik: Optional[str] = None
    no_telepon: Optional[str] = None
    email_perusahaan: Optional[EmailStr] = None
    alamat_lengkap: Optional[str] = None
    status: Optional[str] = None
    npwp: Optional[str] = None

    @field_validator("npwp")
    @classmethod
    def validate_npwp(cls, v):
        if v is None or v == "":
            return None
        digits = re.sub(r"\D", "", v)
        if len(digits) not in (15, 16):
            raise ValueError("NPWP harus 15 atau 16 digit")
        return digits


class DistributorResponse(BaseModel):
    id: uuid.UUID
    area_id: uuid.UUID
    kelurahan_id: Optional[int]
    wilayah: Optional[WilayahLengkap] = None  # kode pos ada di wilayah.kelurahan.kode_pos
    kode_distributor: str
    nama_perusahaan: str
    pemilik: str
    no_telepon: Optional[str]
    email_perusahaan: Optional[str]
    alamat_lengkap: Optional[str]
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    npwp: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DistributorSelfUpdate(_GeoFields):
    """
    Field yang boleh diubah user primary dari halaman profile.
    Sengaja TANPA: area_id (mengubah scope APSM), kode_distributor, status.
    extra="forbid" → field terlarang ditolak 422, bukan diabaikan diam-diam.

    latitude/longitude: kirim keduanya untuk mengubah, atau keduanya null untuk menghapus titik.
    """
    model_config = ConfigDict(extra="forbid")

    nama_perusahaan: Optional[str] = None
    pemilik: Optional[str] = None
    no_telepon: Optional[str] = None
    email_perusahaan: Optional[EmailStr] = None
    alamat_lengkap: Optional[str] = None
    kelurahan_id: Optional[int] = None
    npwp: Optional[str] = None

    @field_validator("npwp")
    @classmethod
    def validate_npwp(cls, v):
        if v is None or v == "":
            return None
        digits = re.sub(r"\D", "", v)
        if len(digits) not in (15, 16):
            raise ValueError("NPWP harus 15 atau 16 digit")
        return digits


class DistributorDetailResponse(DistributorResponse):
    """DistributorResponse + hak edit untuk user yang sedang login."""
    can_edit: bool
    edit_blocked_reason: Optional[str] = None
    is_primary: bool = False
    jabatan: Optional[str] = None

# ─── PAGINATION ───────────────────────────────────────────────────────────────

class DistributorListPage(BaseModel):
    """Response berpagination untuk GET /api/distributors/page."""
    items: List[DistributorResponse]
    total: int          # total baris yang cocok filter (bukan hanya halaman ini)
    page: int           # halaman aktif, mulai dari 1
    page_size: int
    total_pages: int    # 0 jika tidak ada data


class DistributorStatusSummary(BaseModel):
    """
    Jumlah distributor per status (mengikuti scope role + filter area).
    Contoh: {"counts": {"aktif": 40, "nonaktif": 3}, "total": 43}
    """
    counts: Dict[str, int]
    total: int


# ─── DISTRIBUTOR USER (mapping user ke distributor) ───────────────────────────

class DistributorUserAdd(BaseModel):
    user_id: uuid.UUID
    jabatan: Optional[str] = None
    is_primary: bool = False


class DistributorUserResponse(BaseModel):
    id: uuid.UUID
    distributor_id: uuid.UUID
    user_id: uuid.UUID
    jabatan: Optional[str]
    is_primary: bool
    created_at: datetime

    class Config:
        from_attributes = True
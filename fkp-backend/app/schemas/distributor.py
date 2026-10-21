import uuid
from typing import Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr


# ─── DISTRIBUTOR ──────────────────────────────────────────────────────────────

class DistributorCreate(BaseModel):
    area_id: uuid.UUID
    kelurahan_id: Optional[int] = None
    kode_distributor: str
    nama_perusahaan: str
    pemilik: str
    no_telepon: Optional[str] = None
    email_perusahaan: Optional[EmailStr] = None
    alamat_lengkap: Optional[str] = None
    kode_pos: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "area_id": "uuid-area",
                "kode_distributor": "DIST-001",
                "nama_perusahaan": "PT Maju Sejahtera",
                "pemilik": "Budi Santoso",
                "no_telepon": "08123456789",
                "email_perusahaan": "budi@majusejahtera.com",
                "alamat_lengkap": "Jl. Contoh No. 1, Jakarta",
                "kode_pos": "12345"
            }
        }


class DistributorUpdate(BaseModel):
    area_id: Optional[uuid.UUID] = None
    kelurahan_id: Optional[int] = None
    nama_perusahaan: Optional[str] = None
    pemilik: Optional[str] = None
    no_telepon: Optional[str] = None
    email_perusahaan: Optional[EmailStr] = None
    alamat_lengkap: Optional[str] = None
    kode_pos: Optional[str] = None
    status: Optional[str] = None


class DistributorResponse(BaseModel):
    id: uuid.UUID
    area_id: uuid.UUID
    kelurahan_id: Optional[int]
    kode_distributor: str
    nama_perusahaan: str
    pemilik: str
    no_telepon: Optional[str]
    email_perusahaan: Optional[str]
    alamat_lengkap: Optional[str]
    kode_pos: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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
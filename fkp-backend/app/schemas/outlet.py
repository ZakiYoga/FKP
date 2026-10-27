import uuid
from typing import Dict, List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr
from app.schemas.wilayah import WilayahLengkap
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


TipeToko = Literal["retail_tradisional","retail_modern","grosir","horeca","umkm",
                   "tobaku","bakery","catering","reseller","online_shop","lainnya"]

def _norm_kode_pos(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip()
    if not v:
        return None
    if not v.isdigit() or len(v) > 10:
        raise ValueError("Kode pos harus berupa angka (maks 10 digit)")
    return v

class OutletCreate(BaseModel):
    distributor_id: uuid.UUID
    kode_outlet: str
    nama_toko: str
    pemilik_toko: str
    tipe_toko: TipeToko
    no_hp: Optional[str] = None
    email: Optional[EmailStr] = None
    kelurahan_id: Optional[int] = None
    alamat_lengkap: Optional[str] = None
    kode_pos: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    foto_url: Optional[str] = None
    pic_user_id: Optional[uuid.UUID] = None

    class Config:
        json_schema_extra = {
            "example": {
                "distributor_id": "uuid-distributor",
                "kode_outlet": "OTL-001",
                "nama_toko": "Toko Maju Jaya",
                "pemilik_toko": "Budi Santoso",
                "tipe_toko": "retail",
                "no_hp": "08123456789",
                "alamat_lengkap": "Jl. Contoh No. 1",
                "latitude": -7.250445,
                "longitude": 112.768845
            }
        }

    @field_validator("kode_pos")
    @classmethod
    def _validate_kode_pos(cls, v):
        return _norm_kode_pos(v)


class OutletUpdate(BaseModel):
    nama_toko: Optional[str] = None
    pemilik_toko: Optional[str] = None
    tipe_toko: Optional[TipeToko] = None
    no_hp: Optional[str] = None
    email: Optional[EmailStr] = None
    kelurahan_id: Optional[int] = None
    alamat_lengkap: Optional[str] = None
    kode_pos: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    foto_url: Optional[str] = None
    pic_user_id: Optional[uuid.UUID] = None
    status: Optional[str] = None

    @field_validator("kode_pos")
    @classmethod
    def _validate_kode_pos(cls, v):
        return _norm_kode_pos(v)

class OutletResponse(BaseModel):
    id: uuid.UUID
    distributor_id: uuid.UUID
    kode_outlet: str
    nama_toko: str
    pemilik_toko: str
    tipe_toko: str
    no_hp: Optional[str]
    email: Optional[str]
    kelurahan_id: Optional[int]
    wilayah: Optional[WilayahLengkap] = None
    alamat_lengkap: Optional[str]
    kode_pos: Optional[str] = None
    latitude: Optional[float]
    longitude: Optional[float]
    foto_url: Optional[str]
    pic_user_id: Optional[uuid.UUID]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OutletSelfUpdate(BaseModel):
    """
    Field yang boleh diubah PIC dari halaman profile.
    Sengaja TANPA: distributor_id, kode_outlet, status, pic_user_id.
    extra="forbid" → kalau FE mengirim field terlarang, ditolak 422
    (bukan diam-diam diabaikan).
    """
    model_config = ConfigDict(extra="forbid")
    nama_toko: Optional[str] = None
    pemilik_toko: Optional[str] = None
    tipe_toko: Optional[TipeToko] = None
    alamat_lengkap: Optional[str] = None
    kode_pos: Optional[str] = None
    no_hp: Optional[str] = None
    email: Optional[EmailStr] = None
    kelurahan_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    foto_url: Optional[str] = None

    @field_validator("kode_pos")
    @classmethod
    def _validate_kode_pos(cls, v):
        return _norm_kode_pos(v)

class OutletDetailResponse(OutletResponse):
    """OutletResponse + penanda hak edit untuk user yang sedang login."""
    can_edit: bool
    edit_blocked_reason: Optional[str] = None

# ─── PAGINATION ───────────────────────────────────────────────────────────────

class OutletListPage(BaseModel):
    """Response berpagination untuk GET /api/outlets/page."""
    items: List[OutletResponse]
    total: int          # total baris yang cocok filter (bukan hanya halaman ini)
    page: int           # halaman aktif, mulai dari 1
    page_size: int
    total_pages: int    # 0 jika tidak ada data


class OutletStatusSummary(BaseModel):
    """
    Jumlah outlet per status (mengikuti scope role + filter distributor).
    Dipakai FE untuk badge "N menunggu persetujuan" tanpa memuat seluruh list.
    Contoh: {"counts": {"aktif": 120, "pending": 7, "nonaktif": 3}, "total": 130}
    """
    counts: Dict[str, int]
    total: int
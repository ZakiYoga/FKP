import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr


class OutletCreate(BaseModel):
    distributor_id: uuid.UUID
    kode_outlet: str
    nama_toko: str
    pemilik_toko: str
    tipe_toko: str              # "retail" | "grosir" | "horeka"
    no_hp: Optional[str] = None
    email: Optional[EmailStr] = None
    kelurahan_id: Optional[int] = None
    alamat_lengkap: Optional[str] = None
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


class OutletUpdate(BaseModel):
    nama_toko: Optional[str] = None
    pemilik_toko: Optional[str] = None
    tipe_toko: Optional[str] = None
    no_hp: Optional[str] = None
    email: Optional[EmailStr] = None
    kelurahan_id: Optional[int] = None
    alamat_lengkap: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    foto_url: Optional[str] = None
    pic_user_id: Optional[uuid.UUID] = None
    status: Optional[str] = None


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
    alamat_lengkap: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    foto_url: Optional[str]
    pic_user_id: Optional[uuid.UUID]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

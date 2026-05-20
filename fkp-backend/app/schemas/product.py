import uuid
from typing import Optional
from pydantic import BaseModel


class ProductCreate(BaseModel):
    kode_produk: str
    nama_produk: str
    jenis_kemasan: str      # "zak" | "karton" | "renceng" | "ball" | "pcs"
    berat_gr: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "kode_produk": "PRD-ZAK-003",
                "nama_produk": "Garam Baru Cap Saktifood",
                "jenis_kemasan": "zak",
                "berat_gr": 10000
            }
        }


class ProductUpdate(BaseModel):
    nama_produk: Optional[str] = None
    jenis_kemasan: Optional[str] = None
    berat_gr: Optional[int] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    id: uuid.UUID
    kode_produk: str
    nama_produk: str
    jenis_kemasan: str
    berat_gr: Optional[int]
    is_active: bool

    class Config:
        from_attributes = True

"""
Schema Pydantic untuk modul Warehouse Surat Jalan (barang pengganti outbound).
"""
import uuid
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, field_validator


# ─── REQUEST ──────────────────────────────────────────────────────────────────

class SuratJalanItemCreate(BaseModel):
    fkp_item_id: Optional[uuid.UUID] = None
    nama_produk: str
    qty: int
    satuan: str
    keterangan: Optional[str] = None

    @field_validator("qty")
    @classmethod
    def qty_positif(cls, v):
        if v < 1:
            raise ValueError("qty minimal 1")
        return v

    @field_validator("nama_produk", "satuan")
    @classmethod
    def wajib_diisi(cls, v):
        if not v or not v.strip():
            raise ValueError("Field ini wajib diisi")
        return v


class SuratJalanCreate(BaseModel):
    nomor_surat_jalan: str
    tanggal_surat_jalan: date
    nama_penerima: str
    alamat_penerima: str
    telepon_penerima: Optional[str] = None
    ekspedisi: Optional[str] = None
    nomor_resi: Optional[str] = None
    tanggal_kirim: Optional[date] = None
    catatan: Optional[str] = None
    items: List[SuratJalanItemCreate]

    @field_validator("nomor_surat_jalan", "nama_penerima", "alamat_penerima")
    @classmethod
    def wajib_diisi(cls, v):
        if not v or not v.strip():
            raise ValueError("Field ini wajib diisi")
        return v

    @field_validator("items")
    @classmethod
    def minimal_satu_item(cls, v):
        if not v or len(v) < 1:
            raise ValueError("Minimal 1 item pengiriman wajib diisi")
        return v


class SuratJalanUpdate(BaseModel):
    """Hanya untuk SJ berstatus draft — semua field opsional (partial update)."""
    nomor_surat_jalan: Optional[str] = None
    tanggal_surat_jalan: Optional[date] = None
    nama_penerima: Optional[str] = None
    alamat_penerima: Optional[str] = None
    telepon_penerima: Optional[str] = None
    ekspedisi: Optional[str] = None
    nomor_resi: Optional[str] = None
    tanggal_kirim: Optional[date] = None
    catatan: Optional[str] = None


class SuratJalanShipRequest(BaseModel):
    ekspedisi: Optional[str] = None
    nomor_resi: Optional[str] = None
    tanggal_kirim: Optional[date] = None


# ─── RESPONSE ─────────────────────────────────────────────────────────────────

class SuratJalanItemResponse(BaseModel):
    id: uuid.UUID
    fkp_item_id: Optional[uuid.UUID] = None
    nama_produk: str
    qty: int
    satuan: str
    keterangan: Optional[str] = None

    model_config = {"from_attributes": True}


class SuratJalanResponse(BaseModel):
    id: uuid.UUID
    fkp_id: uuid.UUID
    nomor_surat_jalan: str
    tanggal_surat_jalan: date
    status: str

    nama_penerima: str
    alamat_penerima: str
    telepon_penerima: Optional[str] = None

    ekspedisi: Optional[str] = None
    nomor_resi: Optional[str] = None
    tanggal_kirim: Optional[date] = None
    tanggal_delivered: Optional[datetime] = None

    url_pdf: Optional[str] = None
    catatan: Optional[str] = None

    dibuat_oleh: uuid.UUID
    created_at: datetime
    updated_at: datetime

    items: List[SuratJalanItemResponse] = []

    model_config = {"from_attributes": True}
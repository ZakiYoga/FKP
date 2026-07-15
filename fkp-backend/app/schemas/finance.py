"""
Schema Pydantic untuk modul Finance Invoice (resolusi potong_tagihan).
"""
import uuid
from typing import Optional
from decimal import Decimal
from datetime import datetime, date
from pydantic import BaseModel, field_validator


class InvoiceCreateRequest(BaseModel):
    nomor_invoice: str

    # [FIX BUG KRITIS #1] Field ini sebelumnya TIDAK ADA di schema padahal
    # endpoint (api/endpoints/fkp.py) sudah mengakses `data.nilai_nota_penjualan`
    # -> AttributeError setiap kali endpoint dipanggil. Wajib diisi di sini
    # (bukan di /finance/proses) karena nilai_cashback harus final & tercetak
    # di PDF invoice saat endpoint ini dipanggil — lihat
    # fkp_service.terbitkan_invoice().
    nilai_nota_penjualan: Decimal

    catatan: Optional[str] = None

    @field_validator("nomor_invoice")
    @classmethod
    def wajib_diisi(cls, v):
        if not v or not v.strip():
            raise ValueError("nomor_invoice wajib diisi")
        return v

    @field_validator("nilai_nota_penjualan")
    @classmethod
    def nilai_positif(cls, v):
        if v is None or v <= 0:
            raise ValueError("nilai_nota_penjualan harus lebih dari 0")
        return v


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    fkp_id: uuid.UUID
    tipe_dokumen: str
    nomor_dokumen: Optional[str] = None
    tanggal_dokumen: Optional[date] = None
    url_file: str
    dibuat_oleh: uuid.UUID
    created_at: datetime

    # [FIX BUG KRITIS #1] Nilai yang baru dihitung, dikembalikan langsung
    # supaya FE tidak perlu request terpisah untuk menampilkan hasil kalkulasi
    # cashback setelah invoice diterbitkan.
    nilai_nota_penjualan: Optional[Decimal] = None
    nilai_cashback: Optional[Decimal] = None

    model_config = {"from_attributes": True}
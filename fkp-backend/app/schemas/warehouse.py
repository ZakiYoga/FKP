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

# ─── SURAT JALAN INBOX (halaman "Surat Jalan" warehouse — list lintas FKP) ───
#
# Dipakai GET /api/warehouse/surat-jalan, /summary, dan /pending-fkp
# (warehouse_inbox_router). Hanya tambahan — schema di atas tidak berubah.

class SuratJalanInboxItem(SuratJalanResponse):
    nomor_fkp: str
    fkp_status: str
    distributor_nama: Optional[str] = None
    outlet_nama: Optional[str] = None
    jumlah_item: int = 0
    total_qty: int = 0

    model_config = {"from_attributes": False}


class SuratJalanInboxPage(BaseModel):
    """Bentuk sama dengan tipe frontend Paginated<T>."""
    items: List[SuratJalanInboxItem]
    total: int
    page: int
    page_size: int
    total_pages: int  # minimal 1, walau data kosong


class SuratJalanSummary(BaseModel):
    counts: dict[str, int]   # semua status SJ, default 0
    total: int               # jumlah semua SJ
    perlu_dibuat: int        # jumlah FKP di antrean "Perlu Dibuat"


class PendingSjItem(BaseModel):
    fkp_item_id: uuid.UUID
    nama_produk: str
    jenis_kemasan: Optional[str] = None
    satuan_default: str
    qty_keluhan: int
    qty_disetujui: int
    qty_terkirim: int
    sisa_kuota: int


class PenerimaDefault(BaseModel):
    nama: Optional[str] = None
    alamat: Optional[str] = None
    telepon: Optional[str] = None


class PendingSjFkp(BaseModel):
    fkp_id: uuid.UUID
    nomor_fkp: str
    fkp_status: str
    tanggal_diteruskan_ke_warehouse: Optional[datetime] = None
    distributor_nama: Optional[str] = None
    distributor_kode: Optional[str] = None
    outlet_nama: Optional[str] = None
    outlet_kode: Optional[str] = None
    penerima_default: PenerimaDefault
    items: List[PendingSjItem]
    jumlah_sj_terbit: int = 0   # jumlah SJ yang sudah dibuat (semua status; menghabiskan kuota)


class PendingSjPage(BaseModel):
    items: List[PendingSjFkp]
    total: int
    page: int
    page_size: int
    total_pages: int
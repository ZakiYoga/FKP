"""
Schema Pydantic untuk modul Sample Shipment.

CATATAN KEAMANAN: `hasil_pemeriksaan` adalah INTERNAL ONLY (keputusan bisnis
eksplisit — outlet/distributor tidak boleh melihat narasi hasil QC). Field ini
tetap ada di SampleResponse (dipakai role internal), tapi service layer WAJIB
menyaringnya jadi None sebelum response dikirim ke role outlet/distributor/
sc_spv — lihat `sample_service._sanitize_for_external()`.
"""
import uuid
from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel, field_validator


# ─── REQUEST ──────────────────────────────────────────────────────────────────

class SampleCreate(BaseModel):
    fkp_item_id: uuid.UUID
    ekspedisi: Optional[str] = None
    nomor_resi: Optional[str] = None
    tanggal_kirim: Optional[date] = None
    catatan_pengirim: Optional[str] = None
    qty_sample: int = 1

    @field_validator("qty_sample")
    @classmethod
    def qty_positif(cls, v):
        if v < 1:
            raise ValueError("qty_sample minimal 1")
        return v


class SampleReceiveRequest(BaseModel):
    nomor_tanda_terima: str
    catatan_warehouse: Optional[str] = None

    @field_validator("nomor_tanda_terima")
    @classmethod
    def wajib_diisi(cls, v):
        if not v or not v.strip():
            raise ValueError("nomor_tanda_terima wajib diisi")
        return v


class SampleExamineRequest(BaseModel):
    hasil_pemeriksaan: str

    @field_validator("hasil_pemeriksaan")
    @classmethod
    def wajib_diisi(cls, v):
        if not v or not v.strip():
            raise ValueError("hasil_pemeriksaan wajib diisi")
        return v


class SampleCancelRequest(BaseModel):
    alasan_batal: str

    @field_validator("alasan_batal")
    @classmethod
    def wajib_diisi(cls, v):
        if not v or not v.strip():
            raise ValueError("alasan_batal wajib diisi")
        return v


# ─── RESPONSE ─────────────────────────────────────────────────────────────────

class SampleResponse(BaseModel):
    id: uuid.UUID
    fkp_id: uuid.UUID
    fkp_item_id: uuid.UUID
    status: str

    sender_id: uuid.UUID
    ekspedisi: Optional[str] = None
    nomor_resi: Optional[str] = None
    tanggal_kirim: Optional[date] = None
    catatan_pengirim: Optional[str] = None
    qty_sample: int

    tanggal_delivered: Optional[datetime] = None
    dikonfirmasi_delivered_oleh: Optional[uuid.UUID] = None

    diterima_oleh: Optional[uuid.UUID] = None
    nomor_tanda_terima: Optional[str] = None
    tanggal_diterima: Optional[datetime] = None
    catatan_warehouse: Optional[str] = None

    diperiksa_oleh: Optional[uuid.UUID] = None
    tanggal_mulai_periksa: Optional[datetime] = None
    tanggal_selesai_periksa: Optional[datetime] = None
    # INTERNAL ONLY — disaring ke None oleh service layer untuk role eksternal
    hasil_pemeriksaan: Optional[str] = None

    alasan_batal: Optional[str] = None
    dibatalkan_oleh: Optional[uuid.UUID] = None
    tanggal_batal: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SampleStatusLogResponse(BaseModel):
    id: uuid.UUID
    status_lama: Optional[str] = None
    status_baru: str
    catatan: Optional[str] = None
    changed_by: uuid.UUID
    changed_at: datetime

    model_config = {"from_attributes": True}

# ─── SAMPLE MASUK (list global lintas FKP) ───────────────────────────────────
#
# Dipakai halaman "Sample Masuk" (GET /api/samples). Hanya role internal HO
# (permission sample.view_all), jadi hasil_pemeriksaan boleh ikut dikembalikan.
# Dibangun eksplisit dari baris hasil join (bukan dari ORM object), maka
# from_attributes dimatikan.

class SampleInboxItem(SampleResponse):
    nomor_fkp: str
    fkp_status: str
    nama_produk: str
    jenis_kemasan: Optional[str] = None
    qty_item_keluhan: int
    distributor_nama: Optional[str] = None
    distributor_kode: Optional[str] = None
    outlet_nama: Optional[str] = None
    outlet_kode: Optional[str] = None
    pengirim_nama: Optional[str] = None
    jumlah_dokumen: int = 0

    model_config = {"from_attributes": False}


class SampleInboxPage(BaseModel):
    """Bentuk sama dengan tipe frontend Paginated<T>."""
    items: list[SampleInboxItem]
    total: int          # total baris yang cocok filter (bukan hanya halaman ini)
    page: int           # halaman aktif, mulai dari 1
    page_size: int
    total_pages: int    # minimal 1, walau data kosong


class SampleStatusSummary(BaseModel):
    """
    Jumlah sample per status. `counts` selalu memuat semua status (default 0).
    Contoh: {"counts": {"shipped": 2, "delivered": 5, ...}, "total": 36}
    """
    counts: dict[str, int]
    total: int
"""
app/schemas/bapkp.py

Schema request/response untuk BAPKP (Berita Acara Pemeriksaan Keluhan
Pelanggan, SPP/QC/FORM/25).

CATATAN PENAMAAN: project ini SUDAH punya app/schemas/berita_acara.py
untuk dokumen BEDA (Berita Acara Pemusnahan, SPP/QC/FORM 26). Modul ini
sengaja dinamai "bapkp" (bukan "berita_acara") supaya tidak menimpa /
membingungkan dengan file yang sudah ada.

── ALUR PEMAKAIAN DARI FE ──────────────────────────────────────────────────
  1. GET  /api/fkp/{fkp_id}/bapkp/draft
        -> BapkpDraftResponse: semua data yang SUDAH ADA di FKP (outlet,
           distributor, per-item nama/kemasan/batch/qty/deskripsi keluhan/
           kondisi_sample) + saran nomor_ba. FE render form dengan data
           ini sbg prefill, sisanya (field BAPKP-only) dikosongkan.
  2. POST /api/fkp/{fkp_id}/bapkp
        body: BapkpCreate -> HANYA field yang tidak bisa auto-fill.
  3. PATCH /api/fkp/{fkp_id}/bapkp
        body: BapkpUpdate -> sama seperti create tapi semua opsional.
  4. GET  /api/fkp/{fkp_id}/bapkp
        -> BapkpResponse: versi FULL (gabungan FKP + BAPKP) utk preview.
  5. GET  /api/fkp/{fkp_id}/bapkp/pdf
        -> file PDF.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ─── INPUT (dikirim FE) ─────────────────────────────────────────────────────

class BapkpItemInput(BaseModel):
    """
    Field BAPKP-only per item + kondisi_sample.

    kondisi_sample ditulis LANGSUNG ke FkpItem.kondisi_sample (kolom yang
    sudah ada di model FkpItem tapi belum pernah diisi lewat schema mana
    pun) -- BUKAN disimpan di tabel bapkp. Lihat catatan di
    app/models/bapkp.py ASUMSI #3.
    """
    fkp_item_id: UUID

    tanggal_kadaluarsa: Optional[date] = None
    umur_produk: Optional[str] = Field(default=None, max_length=50)
    tanggal_dikirim: Optional[date] = None
    lama_di_gudang_spp: Optional[str] = Field(default=None, max_length=50)
    kondisi_sample: Optional[str] = Field(default=None, max_length=20)  # "utuh" | "terbuka" | custom


class BapkpCreate(BaseModel):
    """Payload pembuatan BAPKP baru untuk sebuah FKP (fkp_id dari path param)."""

    nomor_ba: Optional[str] = Field(default=None, max_length=100)

    hari_pemeriksaan: Optional[str] = Field(default=None, max_length=20)
    tanggal_pemeriksaan: Optional[date] = None
    tanggal_diterima_qc: Optional[date] = None
    catatan_pemeriksaan: Optional[str] = None

    # Wajib mencakup SEMUA item milik FKP ini -- divalidasi di service.
    items: List[BapkpItemInput]

    @field_validator("items")
    @classmethod
    def items_tidak_boleh_kosong(cls, v):
        if not v:
            raise ValueError("Minimal 1 item wajib diisi untuk membuat BAPKP.")
        return v


class BapkpUpdate(BaseModel):
    """Sama seperti create, tapi semua field opsional (partial update)."""

    hari_pemeriksaan: Optional[str] = Field(default=None, max_length=20)
    tanggal_pemeriksaan: Optional[date] = None
    tanggal_diterima_qc: Optional[date] = None
    catatan_pemeriksaan: Optional[str] = None
    items: Optional[List[BapkpItemInput]] = None


# ─── OUTPUT: DRAFT (auto-fill preview sebelum create) ──────────────────────

class BapkpDraftItem(BaseModel):
    """Data 1 produk yang sudah tersedia dari FkpItem, ditampilkan
    read-only di form FE sebelum QC mengisi field BAPKP-only-nya."""
    fkp_item_id: UUID
    nama_produk: str
    jenis_kemasan: Optional[str] = None
    batch_number: Optional[str] = None
    qty: Optional[int] = None
    expired_date: Optional[date] = None   # dari FkpItem -> saran default tanggal_kadaluarsa
    deskripsi_keluhan: Optional[str] = None
    ada_sample_keluhan: Optional[str] = None
    kondisi_sample: Optional[str] = None  # dari FkpItem.kondisi_sample, kalau sudah pernah diisi


class BapkpDraftResponse(BaseModel):
    """Response GET .../bapkp/draft -- auto-fill context untuk form FE."""
    fkp_id: UUID
    nomor_fkp: str
    tanggal_pengajuan: Optional[date] = None
    prioritas: Optional[str] = None

    outlet_nama: Optional[str] = None
    outlet_alamat: Optional[str] = None
    outlet_no_hp: Optional[str] = None
    outlet_email: Optional[str] = None
    distributor_nama: Optional[str] = None

    items: List[BapkpDraftItem]

    nomor_ba_disarankan: str
    sudah_ada_bapkp: bool   # True kalau FKP ini sudah pernah dibuatkan BAPKP


# ─── OUTPUT: FULL DETAIL (gabungan FKP + BAPKP) ────────────────────────────

class BapkpItemDetail(BaseModel):
    fkp_item_id: UUID
    nama_produk: str
    jenis_kemasan: Optional[str] = None
    batch_number: Optional[str] = None
    qty: Optional[int] = None
    deskripsi_keluhan: Optional[str] = None
    ada_sample_keluhan: Optional[str] = None
    kondisi_sample: Optional[str] = None

    tanggal_kadaluarsa: Optional[date] = None
    umur_produk: Optional[str] = None
    tanggal_dikirim: Optional[date] = None
    lama_di_gudang_spp: Optional[str] = None


class BapkpResponse(BaseModel):
    id: UUID
    fkp_id: UUID
    nomor_fkp: str
    nomor_ba: str

    hari_pemeriksaan: Optional[str] = None
    tanggal_pemeriksaan: Optional[date] = None
    tanggal_diterima_qc: Optional[date] = None
    tenggat_terpenuhi: Optional[bool] = None   # DIHITUNG, bukan disimpan
    catatan_pemeriksaan: Optional[str] = None

    outlet_nama: Optional[str] = None
    distributor_nama: Optional[str] = None

    items: List[BapkpItemDetail]

    dibuat_oleh: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
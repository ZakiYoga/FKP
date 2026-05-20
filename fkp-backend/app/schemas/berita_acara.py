"""
app/schemas/berita_acara.py

Request / Response schema untuk endpoint Berita Acara Pemusnahan.
Dipakai oleh:
  - POST /fkp/{fkp_id}/berita-acara   (skenario A — auto dari FKP)
  - POST /berita-acara                 (skenario B — manual)
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ─── Shared sub-models ────────────────────────────────────────────────────────

class ItemBarangRequest(BaseModel):
    """Satu baris di tabel A (Informasi Keseluruhan)."""
    nama_barang:  str             = Field(..., description="Nama produk / barang")
    batch_no_ed:  Optional[str]   = Field(None, description="Batch No / Tanggal ED")
    jumlah:       Optional[str]   = Field(None, description="Jumlah, mis. '12 pcs'")
    keterangan:   Optional[str]   = Field(None, description="Kondisi / keterangan barang")


# ─── Skenario A — override opsional dari FKP ─────────────────────────────────

class BeritaAcaraFromFkpRequest(BaseModel):
    """
    Body opsional saat generate BA dari FKP (POST /fkp/{fkp_id}/berita-acara).
    Semua field opsional — jika kosong, nilai diambil otomatis dari FkpResolution.
    Isi hanya field yang perlu di-override.
    """
    metode_pemusnahan:    Optional[str]  = Field(
        None,
        description="Override metode: 'dibakar' | 'dihancurkan' | 'dikembalikan_ho' | teks bebas"
    )
    pihak_pelaksana:      Optional[str]  = Field(None, description="Override pihak pelaksana")
    nama_saksi_eksternal: Optional[str]  = Field(None, description="Override nama saksi eksternal")
    nama_penyetuju:       Optional[str]  = Field(None, description="Override nama penyetuju / marketing")
    catatan_tambahan:     Optional[str]  = Field(None, description="Catatan tambahan di dokumen")


# ─── Skenario B — manual penuh ────────────────────────────────────────────────

class BeritaAcaraManualRequest(BaseModel):
    """
    Body lengkap untuk generate BA manual
    (POST /berita-acara).
    Tidak memerlukan FKP yang sudah ada.
    Jika fkp_id diisi, dokumen akan disimpan ke FkpDocument milik FKP tersebut.
    """

    # ── Referensi FKP (opsional) ──────────────────────────────────────────────
    fkp_id: Optional[UUID] = Field(
        None,
        description="Isi jika BA ini terkait FKP tertentu (akan disimpan ke FkpDocument)"
    )

    # ── Kalimat pembuka ───────────────────────────────────────────────────────
    hari:                Optional[str]  = Field(None, description="Mis. 'Senin'")
    tanggal_pelaksanaan: Optional[date] = Field(None)
    lokasi_pelaksanaan:  Optional[str]  = Field(None)

    # ── Seksi A — tabel barang ────────────────────────────────────────────────
    items: List[ItemBarangRequest] = Field(
        default_factory=list,
        description="Daftar barang yang dimusnahkan"
    )

    # ── Seksi B — metode & pelaksanaan ────────────────────────────────────────
    metode_pemusnahan:     Optional[str]  = Field(
        None,
        description="'dibakar' | 'dihancurkan' | 'dikembalikan_ho' | teks bebas"
    )
    lokasi_pemusnahan:     Optional[str]  = Field(None)
    pihak_pelaksana:       Optional[str]  = Field(None)
    dokumentasi_lampiran:  Optional[str]  = Field(
        None, description="Deskripsi singkat lampiran, mis. 'Foto 1–5 terlampir'"
    )
    tindak_lanjut:         Optional[str]  = Field(
        None,
        description="'penukaran_barang' | 'potong_tagihan'"
    )

    # ── Tanda tangan ─────────────────────────────────────────────────────────
    nama_pengaju:          Optional[str]  = Field(None, description="Nama pelanggan / distributor")
    nama_saksi_internal:   Optional[str]  = Field(None, description="Nama saksi internal (APSM)")
    nama_saksi_eksternal:  Optional[str]  = Field(None, description="Nama saksi eksternal")
    nama_penyetuju:        Optional[str]  = Field(None, description="Nama marketing / penyetuju")


# ─── Response ─────────────────────────────────────────────────────────────────

class BeritaAcaraGenerateResponse(BaseModel):
    """
    Response setelah generate BA berhasil.
    PDF tersedia di url_download selama sesi aktif (atau dari FkpDocument jika disimpan).
    """
    message:       str
    nomor_dokumen: str
    fkp_id:        Optional[UUID]  = None
    doc_id:        Optional[UUID]  = None   # FkpDocument.id jika disimpan ke DB
    url_download:  Optional[str]   = None   # endpoint download
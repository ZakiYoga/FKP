"""
app/models/bapkp.py

Model untuk BAPKP (Berita Acara Pemeriksaan Keluhan Pelanggan) — dokumen
SPP/QC/FORM/25.

── PENTING: JANGAN disamakan dengan modul "Berita Acara" yang SUDAH ADA ───
Project ini SUDAH punya modul terpisah untuk "Berita Acara Pemusnahan dan
Tukar Barang" (SPP/QC/FORM 26) di:
    app/schemas/berita_acara.py
    app/services/berita_acara_pdf_service.py
    app/templates/BA/berita_acara_pemusnahan.html
    permission: fkp.berita_acara.read / fkp.berita_acara.manual
    route: /api/fkp/{fkp_id}/berita-acara, /api/fkp/{fkp_id}/berita-acara/pdf,
           /api/fkp/berita-acara/manual

Itu dokumen BEDA (laporan pemusnahan barang, dibuat pasca-resolusi) dari
BAPKP di modul ini (laporan hasil pemeriksaan QC, dibuat pasca-investigasi,
SPP/QC/FORM/25). Supaya tidak bentrok nama file/route/permission dengan
modul yang sudah ada, SEMUA penamaan di modul ini sengaja pakai kata kunci
"bapkp", BUKAN "berita_acara".

Relasi:
    FkpComplaint (1) ── (0..1) FkpBapkp ── (1..N) FkpBapkpItem

── ASUMSI DESAIN ────────────────────────────────────────────────────────
1. 1 FKP : 1 BAPKP (unique fkp_id). Kalau nanti perlu re-inspeksi/versi
   baru, unique constraint ini yang perlu dilonggarkan lebih dulu.
2. FkpBapkpItem berelasi 1:1 ke FkpItem (fkp_item_id). Field yang SUDAH
   ADA di FkpItem (nama_produk, jenis_kemasan, batch_number, qty,
   deskripsi_keluhan, ada_sample_keluhan) TIDAK diduplikasi ke sini.
3. `kondisi_sample` SENGAJA TIDAK dibuat sebagai kolom baru di
   FkpBapkpItem — kolom itu SUDAH ADA di FkpItem.kondisi_sample tapi
   tidak pernah diisi lewat schema mana pun saat ini (FkpItemCreate tidak
   punya field ini, qc_investigasi() juga tidak mengisinya). BAPKP jadi
   titik pengisian resminya: bapkp_service akan MENULIS ke
   FkpItem.kondisi_sample langsung saat create/update BAPKP, bukan
   menyimpan salinannya di tabel ini — supaya tidak ada 2 sumber
   kebenaran untuk field yang sama.
"""

import uuid
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, Field, Relationship

# PENTING: JANGAN tambahkan `from __future__ import annotations` di file
# ini. Semua app/models/*.py di project ini (fkp.py, outlet.py,
# distributor.py, user.py, dst) SENGAJA tidak memakainya, karena
# kombinasi `from __future__ import annotations` + `List["ForwardRef"]`
# di Relationship() membuat SQLAlchemy gagal resolve type saat
# configure_mappers() (annotation jadi string literal "List['X']" yang
# tidak dikenali class registry). Sudah diverifikasi: model ini error
# saat configure_mappers() ketika future-annotations dipakai, dan normal
# setelah dihapus -- konsisten dengan pola seluruh model lain di project.

if TYPE_CHECKING:
    from app.models.fkp import FkpItem  # noqa: F401


class FkpBapkp(SQLModel, table=True):
    """Header BAPKP — 1 baris per FKP yang sudah diperiksa QC."""
    __tablename__ = "fkp_bapkp"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    fkp_id: uuid.UUID = Field(foreign_key="fkp_complaints.id", unique=True, index=True)

    nomor_ba: str = Field(unique=True, index=True)

    # ── Field yang WAJIB diisi manual oleh QC lewat form ──────────────────
    hari_pemeriksaan: Optional[str] = None        # contoh: "Senin"
    tanggal_pemeriksaan: Optional[date] = None
    tanggal_diterima_qc: Optional[date] = None     # dipakai hitung tenggat_terpenuhi

    catatan_pemeriksaan: Optional[str] = None

    # ── Audit ───────────────────────────────────────────────────────────
    # sa_column=Column(DateTime(timezone=True)) WAJIB disamakan dgn pola
    # SELURUH created_at/updated_at di app/models/fkp.py (FkpComplaint,
    # FkpItem, FkpDocument, dst) -- tanpa ini, kolom jadi
    # TIMESTAMP WITHOUT TIME ZONE (default SQLModel), padahal seluruh
    # service di project ini konsisten memakai datetime.now(timezone.utc)
    # (timezone-aware). Sudah diverifikasi: tanpa baris ini, DDL yang
    # dihasilkan berbeda dari seluruh tabel FKP lain.
    dibuat_oleh: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )

    # ── Relasi ──────────────────────────────────────────────────────────
    items: List["FkpBapkpItem"] = Relationship(
        back_populates="bapkp",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class FkpBapkpItem(SQLModel, table=True):
    """
    Detail per-produk BAPKP. 1 baris per FkpItem yang diperiksa.

    TIDAK ada kolom kondisi_sample di sini — lihat ASUMSI #3 di docstring
    modul. Field lain di sini murni BAPKP-only, tidak ada padanannya di
    FkpItem.
    """
    __tablename__ = "fkp_bapkp_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    bapkp_id: uuid.UUID = Field(foreign_key="fkp_bapkp.id", index=True)
    fkp_item_id: uuid.UUID = Field(foreign_key="fkp_items.id", index=True)

    tanggal_kadaluarsa: Optional[date] = None
    umur_produk: Optional[str] = None              # contoh: "3 bulan"
    tanggal_dikirim: Optional[date] = None
    lama_di_gudang_spp: Optional[str] = None        # contoh: "5 hari"

    bapkp: Optional[FkpBapkp] = Relationship(back_populates="items")
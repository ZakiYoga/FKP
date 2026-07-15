import uuid
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime, date, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import DateTime, Column

from app.models.fkp import SuratJalanStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.fkp import FkpComplaint, FkpItem


# ─── WAREHOUSE SURAT JALAN (barang pengganti outbound — resolusi tukar_barang) ─
#
# [KEPUTUSAN — lihat diskusi Kontradiksi A] SJ bisa dibuat SELAGI FKP masih
# berstatus ACCEPTED, dan trigger transisi accepted → in_process LANGSUNG
# saat dibuat (bukan menunggu status → issued). Karena itu, kolom
# `disetujui_oleh` / `tanggal_disetujui` dari draf awal dokumen DIHAPUS —
# tidak ada lagi langkah approval terpisah dari Admin HO setelah SJ dibuat;
# siapa yang membuat SJ sudah cukup tercatat lewat `dibuat_oleh`.
#
# Bisa lebih dari 1 SJ per FKP (pengiriman bertahap karena stok kurang) —
# hanya SJ PERTAMA yang memicu transisi status; SJ berikutnya murni
# administratif.

class WarehouseSuratJalan(SQLModel, table=True):
    __tablename__ = "warehouse_surat_jalan"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    fkp_id: uuid.UUID = Field(
        foreign_key="fkp_complaints.id", index=True,
        description=(
            "FK utama — satu arah dari SJ ke FKP. "
            "Tidak ada FK balik di fkp_complaints atau fkp_resolutions. "
            "Admin HO/Warehouse melihat SJ via query WHERE fkp_id = :fkp_id."
        )
    )

    # ── Identitas Dokumen — nomor input MANUAL oleh warehouse ────────────────
    nomor_surat_jalan: str = Field(max_length=50, unique=True, index=True)
    tanggal_surat_jalan: date = Field()
    status: str = Field(
        default=SuratJalanStatus.DRAFT, max_length=20, index=True
    )

    # ── Penerima ───────────────────────────────────────────────────────────
    nama_penerima: str = Field(max_length=200)
    alamat_penerima: str = Field(max_length=500)
    telepon_penerima: Optional[str] = Field(default=None, max_length=20)

    # ── Pengiriman ─────────────────────────────────────────────────────────
    ekspedisi: Optional[str] = Field(default=None, max_length=100)
    nomor_resi: Optional[str] = Field(default=None, max_length=100)
    tanggal_kirim: Optional[date] = Field(default=None)
    tanggal_delivered: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # ── PDF ────────────────────────────────────────────────────────────────
    url_pdf: Optional[str] = Field(
        default=None, max_length=500,
        description=(
            "Path relatif ke file PDF hasil generate WeasyPrint saat status → issued. "
            "TIDAK disajikan lewat static mount publik — download HARUS lewat "
            "endpoint terautentikasi (GET /warehouse/surat-jalan/{id}/pdf) yang "
            "melalui scope check, konsisten dengan pola fix keamanan attachment FKP."
        )
    )
    catatan: Optional[str] = Field(default=None)

    # ── Audit ──────────────────────────────────────────────────────────────
    dibuat_oleh: uuid.UUID = Field(
        foreign_key="users.id",
        description="Warehouse (atau admin_ho/superadmin) user yang membuat SJ ini"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    fkp: Optional["FkpComplaint"] = Relationship(back_populates="warehouse_surat_jalan")
    items: List["WarehouseSuratJalanItem"] = Relationship(back_populates="surat_jalan")
    dibuat_oleh_user: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[WarehouseSuratJalan.dibuat_oleh]"}
    )


# ─── WAREHOUSE SURAT JALAN ITEM ────────────────────────────────────────────────

class WarehouseSuratJalanItem(SQLModel, table=True):
    __tablename__ = "warehouse_surat_jalan_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    surat_jalan_id: uuid.UUID = Field(
        foreign_key="warehouse_surat_jalan.id", index=True
    )
    fkp_item_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="fkp_items.id",
        description=(
            "Link ke FKP item asal — untuk pre-populate qty_disetujui & nama produk. "
            "Opsional: warehouse bisa tambah item manual tanpa link."
        )
    )
    nama_produk: str = Field(max_length=200)
    qty: int
    satuan: str = Field(max_length=20, description="pcs / karton / dus / dll")
    keterangan: Optional[str] = Field(default=None, max_length=255)

    surat_jalan: Optional["WarehouseSuratJalan"] = Relationship(back_populates="items")
    fkp_item: Optional["FkpItem"] = Relationship()
import uuid
from typing import Optional, List, Any
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, field_validator, model_validator

from app.models.fkp import (
    FkpPrioritas, RekomendasiTipe, StatusItem,
    TipeResolusi, JenisKeluhan,
)


# ─── TYPED REVIEW SUB-SCHEMAS ─────────────────────────────────────────────────

class ItemApsmReview(BaseModel):
    """Sub-schema untuk review APSM per item."""
    item_id: uuid.UUID

    # PERUBAHAN: rekomendasi_apsm dipecah menjadi dua field
    rekomendasi_penanganan_apsm: Optional[str] = None   # apa yang dilakukan thd barang fisik
    rekomendasi_kompensasi_apsm: Optional[str] = None   # kompensasi finansial ke distributor

    catatan_apsm: Optional[str] = None
    persentase_disetujui_apsm: Optional[int] = None

    @field_validator("rekomendasi_penanganan_apsm")
    @classmethod
    def validate_rekomendasi_penanganan(cls, v):
        if v is not None and v not in RekomendasiTipe.ALL:
            raise ValueError(
                f"rekomendasi_penanganan_apsm harus salah satu dari: {RekomendasiTipe.ALL}"
            )
        return v

    @field_validator("rekomendasi_kompensasi_apsm")
    @classmethod
    def validate_rekomendasi_kompensasi(cls, v):
        if v is not None and v not in RekomendasiTipe.ALL:
            raise ValueError(
                f"rekomendasi_kompensasi_apsm harus salah satu dari: {RekomendasiTipe.ALL}"
            )
        return v

    @field_validator("persentase_disetujui_apsm")
    @classmethod
    def validate_persentase(cls, v):
        if v is not None and not (0 <= v <= 100):
            raise ValueError("persentase_disetujui_apsm harus antara 0 dan 100")
        return v


class ItemAdminHoReview(BaseModel):
    """Sub-schema untuk review Admin HO per item."""
    item_id: uuid.UUID

    # PERUBAHAN: rekomendasi_admin_ho dipecah menjadi dua field
    rekomendasi_penanganan_admin_ho: Optional[str] = None   # apa yang dilakukan thd barang fisik
    rekomendasi_kompensasi_admin_ho: Optional[str] = None   # kompensasi finansial ke distributor

    catatan_admin_ho: Optional[str] = None
    persentase_disetujui_admin_ho: Optional[int] = None

    @field_validator("rekomendasi_penanganan_admin_ho")
    @classmethod
    def validate_rekomendasi_penanganan(cls, v):
        if v is not None and v not in RekomendasiTipe.ALL:
            raise ValueError(
                f"rekomendasi_penanganan_admin_ho harus salah satu dari: {RekomendasiTipe.ALL}"
            )
        return v

    @field_validator("rekomendasi_kompensasi_admin_ho")
    @classmethod
    def validate_rekomendasi_kompensasi(cls, v):
        if v is not None and v not in RekomendasiTipe.ALL:
            raise ValueError(
                f"rekomendasi_kompensasi_admin_ho harus salah satu dari: {RekomendasiTipe.ALL}"
            )
        return v

    @field_validator("persentase_disetujui_admin_ho")
    @classmethod
    def validate_persentase(cls, v):
        if v is not None and not (0 <= v <= 100):
            raise ValueError("persentase_disetujui_admin_ho harus antara 0 dan 100")
        return v

class ItemQtyDisetujui(BaseModel):
    """Sub-schema untuk mengisi qty_disetujui per item saat fase accepted (tukar_barang)."""
    item_id: uuid.UUID
    qty_disetujui: int

    @field_validator("qty_disetujui")
    @classmethod
    def qty_positif(cls, v):
        if v <= 0:
            raise ValueError("qty_disetujui harus lebih dari 0")
        return v
    
class ItemQcResult(BaseModel):
    """Sub-schema untuk hasil investigasi QC per item."""
    item_id: uuid.UUID
    status_item: str
    catatan_qc: Optional[str] = None
    alasan_penolakan: Optional[str] = None

    @field_validator("status_item")
    @classmethod
    def validate_status(cls, v):
        if v not in StatusItem.ALL:
            raise ValueError(f"status_item harus salah satu dari: {StatusItem.ALL}")
        return v

    @model_validator(mode="after")
    def alasan_wajib_jika_ditolak(self):
        if self.status_item == StatusItem.DITOLAK and not self.alasan_penolakan:
            raise ValueError("alasan_penolakan wajib diisi jika status_item adalah 'ditolak'")
        return self


# ─── FKP ITEM SCHEMAS ─────────────────────────────────────────────────────────

class FkpItemCreate(BaseModel):
    """
    Body untuk menambahkan 1 item produk ke dalam FKP.
    Bisa dipakai saat create FKP (multi-item) atau tambah item belakangan.
    Minimal salah satu dari product_id atau nama_produk_custom harus diisi.
    """
    product_id: Optional[uuid.UUID] = None
    nama_produk_custom: Optional[str] = None
    jenis_kemasan: Optional[str] = None     # "karton" | "renceng" | "ball" | "zak" | "pcs" | None

    qty: int = 1
    batch_number: Optional[str] = None
    expired_date: Optional[date] = None

    ada_sample_keluhan: str = "foto"   # "ada" | "foto"
    ada_foto_sample: bool = False
    tanggal_pembelian: Optional[date] = None
    tanggal_dikonsumsi: Optional[date] = None

    jenis_keluhan: str
    deskripsi_keluhan: Optional[str] = None

    @model_validator(mode="after")
    def produk_harus_diisi(self):
        if not self.product_id and not self.nama_produk_custom:
            raise ValueError("Salah satu dari product_id atau nama_produk_custom wajib diisi")
        return self

    @model_validator(mode="after")
    def qty_minimal_satu(self):
        if self.qty <= 0:
            raise ValueError("Quantity harus lebih dari 0")
        return self

    @field_validator("ada_sample_keluhan")
    @classmethod
    def validate_sample(cls, v):
        if v not in ("ada", "foto", "tidak_ada"):
            raise ValueError("ada_sample_keluhan harus 'ada' atau 'foto keluhan'")
        return v

    @field_validator("jenis_kemasan")
    @classmethod
    def validate_kemasan(cls, v):
        if v is not None and v not in ("karton", "renceng", "ball", "zak", "pcs"):
            raise ValueError("jenis_kemasan harus salah satu dari: karton, renceng, ball, zak, pcs")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "uuid-produk",
                "qty": 2,
                "batch_number": "BT-2025-001",
                "expired_date": "2026-01-01",
                "ada_sample_keluhan": "foto",
                "ada_foto_sample": False,
                "tanggal_pembelian": "2025-03-15",
                "tanggal_dikonsumsi": "2025-03-16",
                "jenis_keluhan": "produk_rusak_cacat",
                "deskripsi_keluhan": "Kemasan sobek dan isi tumpah"
            }
        }


class FkpItemUpdate(BaseModel):
    """Edit item FKP — hanya boleh saat status draft atau need_revision."""
    product_id: Optional[uuid.UUID] = None
    nama_produk_custom: Optional[str] = None
    jenis_kemasan: Optional[str] = None
    qty: Optional[int] = None
    batch_number: Optional[str] = None
    expired_date: Optional[date] = None
    ada_sample_keluhan: Optional[str] = None
    ada_foto_sample: Optional[bool] = None
    tanggal_pembelian: Optional[date] = None
    tanggal_dikonsumsi: Optional[date] = None
    jenis_keluhan: Optional[str] = None
    deskripsi_keluhan: Optional[str] = None

    @field_validator("ada_sample_keluhan")
    @classmethod
    def validate_sample(cls, v):
        if v is not None and v not in ("ada", "foto", "tidak_ada"):
            raise ValueError("ada_sample_keluhan harus 'ada' atau 'foto keluhan'")
        return v

    @field_validator("jenis_kemasan")
    @classmethod
    def validate_kemasan(cls, v):
        if v is not None and v not in ("karton", "renceng", "ball", "zak", "pcs"):
            raise ValueError("jenis_kemasan harus salah satu dari: karton, renceng, ball, zak, pcs")
        return v


class FkpItemResponse(BaseModel):
    id: uuid.UUID
    fkp_id: uuid.UUID
    product_id: Optional[uuid.UUID]
    nama_produk_custom: Optional[str]
    jenis_kemasan: Optional[str]
    qty: int
    batch_number: Optional[str]
    expired_date: Optional[date]
    ada_sample_keluhan: str
    ada_foto_sample: bool
    tanggal_pembelian: Optional[date]
    tanggal_dikonsumsi: Optional[date]
    jenis_keluhan: str
    deskripsi_keluhan: Optional[str]

    # PERUBAHAN: field lama dihapus, diganti dua field baru masing-masing
    rekomendasi_penanganan_apsm: Optional[str]
    rekomendasi_kompensasi_apsm: Optional[str]
    catatan_apsm: Optional[str]
    persentase_disetujui_apsm: Optional[int]

    rekomendasi_penanganan_admin_ho: Optional[str]
    rekomendasi_kompensasi_admin_ho: Optional[str]
    catatan_admin_ho: Optional[str]
    persentase_disetujui_admin_ho: Optional[int]

    status_item: str
    catatan_qc: Optional[str]
    alasan_penolakan: Optional[str]
    qty_disetujui: Optional[int]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── INFO SCHEMAS Distributor & Outlet ────────────────────────────────────────

class DistributorInfo(BaseModel):
    id: uuid.UUID
    nama_perusahaan: str
    kode_distributor: Optional[str] = None

    class Config:
        from_attributes = True


class OutletInfo(BaseModel):
    id: uuid.UUID
    nama_toko: str
    kode_outlet: Optional[str] = None

    class Config:
        from_attributes = True


# ─── FKP MASTER SCHEMAS ───────────────────────────────────────────────────────

class FkpCreate(BaseModel):
    """
    Body request saat membuat FKP baru (multi-item).
    Header FKP + minimal 1 item.
    """
    distributor_id: uuid.UUID
    outlet_id: Optional[uuid.UUID] = None
    prioritas: str = FkpPrioritas.REGULER
    catatan_distributor: Optional[str] = None
    lokasi_pembelian: Optional[str] = None
    items: List[FkpItemCreate]

    @field_validator("prioritas")
    @classmethod
    def validate_prioritas(cls, v):
        if v not in FkpPrioritas.ALL:
            raise ValueError(f"prioritas harus salah satu dari: {FkpPrioritas.ALL}")
        return v

    @field_validator("items")
    @classmethod
    def items_tidak_kosong(cls, v):
        if not v:
            raise ValueError("FKP harus memiliki minimal 1 item produk")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "distributor_id": "uuid-distributor",
                "outlet_id": "uuid-outlet-opsional",
                "prioritas": "urgent",
                "catatan_distributor": "Ditemukan saat unboxing",
                "items": [
                    {
                        "product_id": "uuid-produk",
                        "qty": 2,
                        "batch_number": "BT-2025-001",
                        "expired_date": "2026-01-01",
                        "ada_sample_keluhan": "foto",
                        "ada_foto_sample": False,
                        "jenis_keluhan": "produk_rusak_cacat",
                        "deskripsi_keluhan": "Kemasan sobek"
                    }
                ]
            }
        }


class FkpUpdate(BaseModel):
    """Update FKP saat status masih draft atau need_revision."""
    outlet_id: Optional[uuid.UUID] = None
    prioritas: Optional[str] = None
    catatan_distributor: Optional[str] = None

    @field_validator("prioritas")
    @classmethod
    def validate_prioritas(cls, v):
        if v is not None and v not in FkpPrioritas.ALL:
            raise ValueError(f"prioritas harus salah satu dari: {FkpPrioritas.ALL}")
        return v


# ─── REVIEW SCHEMAS ───────────────────────────────────────────────────────────

class ApsmReviewRequest(BaseModel):
    """APSM submit review keseluruhan FKP + rekomendasi per item."""
    catatan_apsm: Optional[str] = None
    item_reviews: Optional[List[ItemApsmReview]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "catatan_apsm": "Keluhan valid, item sudah dicek di lapangan.",
                "item_reviews": [
                    {
                        "item_id": "uuid-item",
                        "rekomendasi_penanganan_apsm": "musnahkan",
                        "rekomendasi_kompensasi_apsm": "ganti_barang",
                        "catatan_apsm": "Batch ini memang bermasalah.",
                        "persentase_disetujui_apsm": 100
                    }
                ]
            }
        }


class AdminHoReviewRequest(BaseModel):
    """Admin HO submit review + rekomendasi per item sebelum ke RSM."""
    catatan_admin: Optional[str] = None
    item_reviews: Optional[List[ItemAdminHoReview]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "catatan_admin": "Dokumen lengkap, diteruskan ke RSM.",
                "item_reviews": [
                    {
                        "item_id": "uuid-item",
                        "rekomendasi_penanganan_admin_ho": "musnahkan",
                        "rekomendasi_kompensasi_admin_ho": "ganti_barang",
                        "catatan_admin_ho": "Setuju dengan rekomendasi APSM.",
                        "persentase_disetujui_admin_ho": 100
                    }
                ]
            }
        }


class RsmApproveRequest(BaseModel):
    disetujui: bool
    catatan: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {"disetujui": True, "catatan": "Investigasi disetujui"}
        }


class DirekturApproveRequest(BaseModel):
    disetujui: bool
    catatan: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {"disetujui": True, "catatan": "Disetujui untuk diproses"}
        }


class InvestigasiQcRequest(BaseModel):
    """QC mengisi hasil investigasi + status per item."""
    sumber_ketidaksesuaian: str     # "internal" | "pelanggan"
    catatan_qc: Optional[str] = None
    item_results: Optional[List[ItemQcResult]] = None

    @field_validator("sumber_ketidaksesuaian")
    @classmethod
    def validate_sumber(cls, v):
        if v not in ("internal", "pelanggan"):
            raise ValueError("sumber_ketidaksesuaian harus 'internal' atau 'pelanggan'")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "sumber_ketidaksesuaian": "internal",
                "catatan_qc": "Ditemukan cacat produksi pada batch BT-2025-001",
                "item_results": [
                    {
                        "item_id": "uuid-item",
                        "status_item": "diterima",
                        "catatan_qc": "Cacat terbukti dari sisi produksi"
                    }
                ]
            }
        }


class RejectRequest(BaseModel):
    catatan: str

    class Config:
        json_schema_extra = {"example": {"catatan": "Keluhan tidak terbukti setelah investigasi."}}


class RevisionRequest(BaseModel):
    catatan: str

    class Config:
        json_schema_extra = {"example": {"catatan": "Mohon lengkapi foto kemasan."}}


# ─── UPDATE PENGIRIMAN / PROSES RESOLUSI ──────────────────────────────────────

class UpdatePengirimanRequest(BaseModel):
    """
    Admin HO mengupdate progres pengiriman atau proses potong tagihan
    setelah Direktur menyetujui FKP.
    """
    resi_pengiriman: Optional[str] = None
    ekspedisi: Optional[str] = None
    nomor_surat_jalan: Optional[str] = None
    catatan: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "resi_pengiriman": "JNE-20250423-001",
                "ekspedisi": "JNE",
                "nomor_surat_jalan": "SJ-2025-0042",
                "catatan": "Barang sudah di-pickup ekspedisi."
            }
        }


# ─── RESOLUSI ─────────────────────────────────────────────────────────────────

class ResolusiCreate(BaseModel):
    """
    Satu schema untuk dua fase:
    - Fase 1 (investigated)  : wajib tipe_resolusi + metode_penanganan_fisik
    - Fase 2 (accepted)      : isi detail eksekusi (nomor_do/rekening/dll)
    Validasi ketat dilakukan di service berdasarkan status FKP saat itu.
    """
    tipe_resolusi: Optional[str] = None
    metode_penanganan_fisik: Optional[str] = None
    detail_penanganan: Optional[str] = None

    # Pemusnahan
    lokasi_pemusnahan: Optional[str] = None
    tanggal_pemusnahan: Optional[date] = None

    # Potong tagihan
    nilai_cashback: Optional[Decimal] = None
    nama_bank: Optional[str] = None
    nomor_rekening: Optional[str] = None
    atas_nama: Optional[str] = None
    nomor_nota_retur: Optional[str] = None

    # Tukar barang
    nomor_do: Optional[str] = None
    tanggal_pengiriman: Optional[datetime] = None
    ekspedisi: Optional[str] = None
    resi_pengiriman: Optional[str] = None
    nomor_surat_jalan: Optional[str] = None 
    
    persentase_kompensasi_disetujui: Optional[int] = None
    item_qty_disetujui: Optional[List[ItemQtyDisetujui]] = None

    keterangan: Optional[str] = None

    @field_validator("tipe_resolusi")
    @classmethod
    def validate_tipe(cls, v):
        if v is not None and v not in TipeResolusi.ALL:
            raise ValueError(f"tipe_resolusi harus salah satu dari: {TipeResolusi.ALL}")
        return v

    @field_validator("metode_penanganan_fisik")
    @classmethod
    def validate_metode(cls, v):
        from app.models.fkp import MetodePenangananFisik
        if v is not None and v not in MetodePenangananFisik.ALL:
            raise ValueError(f"metode_penanganan_fisik harus salah satu dari: {MetodePenangananFisik.ALL}")
        return v
    
    @field_validator("persentase_kompensasi_disetujui")
    @classmethod
    def validate_persentase(cls, v):
        if v is not None and not (1 <= v <= 100):
            raise ValueError("persentase_kompensasi_disetujui harus antara 1 dan 100")
        return v


class SuratJalanRequest(BaseModel):
    """Admin/HO mengisi nomor surat jalan (untuk resolusi tukar_barang)."""
    nomor_surat_jalan: str

    class Config:
        json_schema_extra = {"example": {"nomor_surat_jalan": "SJ-2025-0042"}}


# ─── RESPONSE ─────────────────────────────────────────────────────────────────

class StatusLogResponse(BaseModel):
    id: uuid.UUID
    status_lama: Optional[str]
    status_baru: str
    catatan: Optional[str]
    changed_by: uuid.UUID
    changed_at: datetime

    class Config:
        from_attributes = True


class ResolusiResponse(BaseModel):
    id: uuid.UUID
    fkp_id: uuid.UUID
    tipe_resolusi: str
    metode_penanganan_fisik: Optional[str] = None
    detail_penanganan: Optional[str] = None
    nilai_cashback: Optional[Decimal]
    nama_bank: Optional[str]
    nomor_rekening: Optional[str]
    atas_nama: Optional[str]
    nomor_nota_retur: Optional[str]
    nomor_do: Optional[str]
    tanggal_pengiriman: Optional[datetime]
    ekspedisi: Optional[str]
    resi_pengiriman: Optional[str]
    tanggal_pemusnahan: Optional[date]
    lokasi_pemusnahan: Optional[str]
    keterangan: Optional[str]
    persentase_kompensasi_disetujui: Optional[int] = None
    nilai_nota_penjualan: Optional[Decimal] = None
    dibuat_oleh: uuid.UUID
    created_at: datetime
    catatan_finance: Optional[str] = None
    diproses_finance: Optional[bool] = None
    tanggal_proses_finance: Optional[datetime] = None
    finance_user_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True


class AttachmentResponse(BaseModel):
    id: uuid.UUID
    fkp_id: uuid.UUID
    fkp_item_id: Optional[uuid.UUID]
    tipe_file: str
    nama_file: str
    url: str
    ukuran_bytes: Optional[int]
    uploaded_by: uuid.UUID
    uploaded_at: datetime
    tipe_dokumen: Optional[str] = None
    keterangan: Optional[str] = None

    class Config:
        from_attributes = True


class FkpDocumentResponse(BaseModel):
    id: uuid.UUID
    fkp_id: uuid.UUID
    tipe_dokumen: str
    nomor_dokumen: Optional[str]
    tanggal_dokumen: Optional[date]
    url_file: str
    dibuat_oleh: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class FkpDetailResponse(BaseModel):
    id: uuid.UUID
    nomor_fkp: str
    outlet_id: Optional[uuid.UUID]
    distributor_id: uuid.UUID
    distributor_info: Optional[DistributorInfo] = None
    outlet_info: Optional[OutletInfo] = None
    submitted_by: uuid.UUID
    handled_by: Optional[uuid.UUID]
    prioritas: str
    status: str
    catatan_distributor: Optional[str]
    catatan_sc_spv: Optional[str]
    catatan_apsm: Optional[str]
    catatan_admin: Optional[str]
    catatan_qc: Optional[str]
    catatan_rsm_investigasi: Optional[str]
    catatan_rsm_resolusi: Optional[str]
    catatan_direktur: Optional[str]
    lokasi_pembelian: Optional[str]
    nomor_surat_jalan: Optional[str]
    tanggal_pengajuan: Optional[datetime]
    tanggal_selesai: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    items: List[FkpItemResponse] = []
    status_logs: List[StatusLogResponse] = []
    resolution: Optional[ResolusiResponse] = None
    attachments: List[AttachmentResponse] = []
    documents: List[FkpDocumentResponse] = []

    @model_validator(mode='before')
    @classmethod
    def extract_nested(cls, data):
        if hasattr(data, '__class__') and hasattr(data, 'distributor'):
            if data.distributor:
                data.__dict__['distributor_info'] = data.distributor
            if data.outlet:
                data.__dict__['outlet_info'] = data.outlet
        return data

    class Config:
        from_attributes = True


class TipeDokumenInfo(BaseModel):
    value: str
    label: str
    kelompok: str   # "keluhan" | "investigasi" | "resolusi" | "dokumen"


class FkpListResponse(BaseModel):
    """Response ringkas untuk list FKP."""
    id: uuid.UUID
    nomor_fkp: str
    outlet_id: Optional[uuid.UUID]
    distributor_id: uuid.UUID
    distributor_info: Optional[DistributorInfo] = None
    outlet_info: Optional[OutletInfo] = None
    prioritas: str
    status: str
    tanggal_pengajuan: Optional[datetime]
    created_at: datetime
    item_count: Optional[int] = None

    class Config:
        from_attributes = True


class FkpDocumentCreate(BaseModel):
    tipe_dokumen: str
    nomor_dokumen: Optional[str] = None
    tanggal_dokumen: Optional[date] = None
    url_file: str

    @field_validator("tipe_dokumen")
    @classmethod
    def validate_tipe(cls, v):
        from app.models.fkp import TipeDokumen
        if v not in TipeDokumen.ALL:
            raise ValueError(f"tipe_dokumen harus salah satu dari: {TipeDokumen.ALL}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "tipe_dokumen": "berita_acara_penukaran",
                "nomor_dokumen": "BA-2025-0042",
                "tanggal_dokumen": "2025-04-20",
                "url_file": "https://storage.example.com/fkp/ba-2025-0042.pdf",
            }
        }
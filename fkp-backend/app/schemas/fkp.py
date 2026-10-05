import uuid
from typing import Optional, List, Any
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, model_validator, computed_field
from app.utils.durasi import hitung_durasi_detik, format_durasi

from app.models.fkp import (
    FkpPrioritas, JenisKemasan, RekomendasiTipe, StatusItem,
    TipeResolusi, JenisKeluhan,
    AdaSampleKeluhan, KondisiSample,
)


# ─── TYPED REVIEW SUB-SCHEMAS ─────────────────────────────────────────────────
class AreaInfo(BaseModel):
    id: uuid.UUID
    nama_area: str                     
    kode_area: Optional[str] = None

    class Config:
        from_attributes = True

class ItemApsmReview(BaseModel):
    """Sub-schema untuk review APSM per item."""
    item_id: uuid.UUID

    # Rekomendasi dipecah menjadi dua field
    rekomendasi_penanganan_apsm: Optional[str] = None   # apa yang dilakukan thd barang fisik
    rekomendasi_kompensasi_apsm: Optional[str] = None   # kompensasi finansial ke distributor

    catatan_apsm: Optional[str] = None
    persentase_disetujui_apsm: Optional[int] = None

    @field_validator("rekomendasi_penanganan_apsm")
    @classmethod
    def validate_rekomendasi_penanganan(cls, v):
        if v is not None and v not in RekomendasiTipe.PENANGANAN:
            raise ValueError(
                f"rekomendasi_penanganan_apsm harus salah satu dari: {RekomendasiTipe.PENANGANAN}"
            )
        return v

    @field_validator("rekomendasi_kompensasi_apsm")
    @classmethod
    def validate_rekomendasi_kompensasi(cls, v):
        if v is not None and v not in RekomendasiTipe.KOMPENSASI:
            raise ValueError(
                f"rekomendasi_kompensasi_apsm harus salah satu dari: {RekomendasiTipe.KOMPENSASI}"
            )
        return v

    @field_validator("persentase_disetujui_apsm")
    @classmethod
    def validate_persentase(cls, v):
        if v is not None and not (0 <= v <= 100):
            raise ValueError("persentase_disetujui_apsm harus antara 0 dan 100")
        return v


# CATATAN: tidak ada ItemAdminHoReview. Admin HO tidak mengisi rekomendasi per
# item (rekomendasi_penanganan_admin_ho / rekomendasi_kompensasi_admin_ho) —
# Admin HO hanya meneruskan FKP dari apsm_reviewed ke RSM (lihat
# AdminHoReviewRequest di bawah). Kolom DB terkait tetap ada (backward compat /
# data historis), hanya berhenti diisi.

class ItemQtyDisetujui(BaseModel):
    """
    Sub-schema untuk mengisi qty_disetujui per item, khusus resolusi
    tukar_barang. Diisi Admin HO bersamaan dengan pembuatan resolusi di Fase 1
    (status investigated / rsm_approval_resolusi / rsm_approval_final), dan
    masih boleh dikoreksi di Fase 2 (accepted) selama belum diteruskan ke
    Warehouse.

    DIUBAH: qty_disetujui = 0 sekarang berarti item DITOLAK — status_item
    langsung berubah jadi 'ditolak' saat ini juga (bukan menunggu approval
    terakhir), dan alasan_penolakan WAJIB diisi. qty_disetujui > 0 berarti
    item DISETUJUI — status_item langsung 'diterima'. Di FE, ini dipetakan
    ke dropdown "Setujui item ini?" per item: pilih "Ya" → field qty_disetujui
    muncul (nilai > 0); pilih "Tidak" → qty_disetujui dikirim 0 dan field qty
    disembunyikan, alasan_penolakan yang diminta sebagai gantinya.

    qty_disetujui dipakai untuk pengiriman barang pengganti. Nilai ini TIDAK
    menentukan jalur approval maupun keterlibatan Direktur — itu murni dari
    total qty klaim saat pengajuan (FkpItem.qty).
    """
    item_id: uuid.UUID
    qty_disetujui: int
    alasan_penolakan: Optional[str] = None


    @field_validator("qty_disetujui")
    @classmethod
    def qty_tidak_negatif(cls, v):
        if v < 0:
            raise ValueError("qty_disetujui tidak boleh negatif (0 = item ditolak)")
        return v

    @model_validator(mode="after")
    def alasan_wajib_jika_ditolak(self):
        if self.qty_disetujui == 0 and not self.alasan_penolakan:
            raise ValueError("alasan_penolakan wajib diisi jika qty_disetujui = 0 (item ditolak)")
        return self
    
class ItemQcResult(BaseModel):
    """
    Sub-schema untuk hasil investigasi QC per item.

    QC TIDAK mengubah status_item (diterima/ditolak) secara langsung —
    keputusan final itu otomatis dari approval terakhir (rsm_approve_final()
    di jalur cepat, direktur_approve() di jalur reguler; lihat
    _tandai_item_diterima_setelah_approval_final() di fkp_service.py).
    QC hanya memberi rekomendasi berupa persentase_disetujui_qc per item —
    setara persentase_disetujui_apsm tapi dari sisi hasil pemeriksaan QC —
    murni insight untuk pertimbangan Admin HO/RSM, tidak mengikat resolusi.
    """
    item_id: uuid.UUID
    persentase_disetujui_qc: Optional[int] = None
    catatan_qc: Optional[str] = None
    alasan_penolakan: Optional[str] = None

    @field_validator("persentase_disetujui_qc")
    @classmethod
    def validate_persentase(cls, v):
        if v is not None and not (0 <= v <= 100):
            raise ValueError("persentase_disetujui_qc harus antara 0 dan 100")
        return v


# ─── FKP ITEM SCHEMAS ─────────────────────────────────────────────────────────

class FkpItemCreate(BaseModel):
    """
    Body untuk menambahkan 1 item produk ke dalam FKP.
    Bisa dipakai saat create FKP (multi-item) atau tambah item belakangan.
    product_id WAJIB — setiap item harus merujuk produk yang terdaftar di
    ProductCatalog (kemampuan item custom dihapus total).

    `qty` dan `jenis_kemasan` menentukan jalur approval FKP (cepat/reguler)
    lewat total qty klaim saat pengajuan — lihat BATAS_QTY_DIREKTUR di
    models/fkp.py.
    """
    product_id: uuid.UUID
    jenis_kemasan: Optional[str] = None

    qty: int = 1
    batch_number: Optional[str] = None
    expired_date: Optional[date] = None

    ada_sample_keluhan: str = AdaSampleKeluhan.FOTO   # "ada" | "foto"
    ada_foto_sample: bool = False
    tanggal_pembelian: Optional[date] = None
    tanggal_dikonsumsi: Optional[date] = None
    kondisi_sample: Optional[str] = None
    kondisi_sample_lainnya: Optional[str] = Field(default=None, max_length=100)
    jenis_keluhan: str
    deskripsi_keluhan: Optional[str] = None

    @model_validator(mode="after")
    def qty_minimal_satu(self):
        if self.qty <= 0:
            raise ValueError("Quantity harus lebih dari 0")
        return self

    @field_validator("ada_sample_keluhan")
    @classmethod
    def validate_sample(cls, v):
        if v not in AdaSampleKeluhan.ALL:
            raise ValueError(f"ada_sample_keluhan harus salah satu dari: {AdaSampleKeluhan.ALL}")
        return v

    @field_validator("kondisi_sample")
    @classmethod
    def validate_kondisi(cls, v):
        if v is not None and v not in KondisiSample.ALL:
            raise ValueError(f"kondisi_sample harus salah satu dari: {KondisiSample.ALL}")
        return v

    @field_validator("jenis_kemasan")
    @classmethod
    def validate_kemasan(cls, v):
        if v is not None and v not in JenisKemasan.ALL:
            raise ValueError(f"jenis_kemasan harus salah satu dari: {JenisKemasan.ALL}")
        return v

    @model_validator(mode="after")
    def normalisasi_kondisi_sample(self):
        if self.ada_sample_keluhan == AdaSampleKeluhan.ADA:
            if not self.kondisi_sample:
                raise ValueError("kondisi_sample wajib diisi jika ada_sample_keluhan = 'ada'")
            if self.kondisi_sample == KondisiSample.LAINNYA:
                if not (self.kondisi_sample_lainnya or "").strip():
                    raise ValueError("kondisi_sample_lainnya wajib diisi jika kondisi_sample = 'lainnya'")
            else:
                self.kondisi_sample_lainnya = None
        else:
            self.kondisi_sample = None
            self.kondisi_sample_lainnya = None
        return self

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
    jenis_kemasan: Optional[str] = None
    qty: Optional[int] = None
    batch_number: Optional[str] = None
    expired_date: Optional[date] = None
    ada_sample_keluhan: Optional[str] = None
    ada_foto_sample: Optional[bool] = None
    kondisi_sample: Optional[str] = None
    kondisi_sample_lainnya: Optional[str] = Field(default=None, max_length=100)
    tanggal_pembelian: Optional[date] = None
    tanggal_dikonsumsi: Optional[date] = None
    jenis_keluhan: Optional[str] = None
    deskripsi_keluhan: Optional[str] = None

    @field_validator("qty")
    @classmethod
    def validate_qty(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Quantity harus lebih dari 0")
        return v

    @field_validator("ada_sample_keluhan")
    @classmethod
    def validate_sample(cls, v):
        if v is not None and v not in AdaSampleKeluhan.ALL:
            raise ValueError(f"ada_sample_keluhan harus salah satu dari: {AdaSampleKeluhan.ALL}")
        return v

    @field_validator("kondisi_sample")
    @classmethod
    def validate_kondisi(cls, v):
        if v is not None and v not in KondisiSample.ALL:
            raise ValueError(f"kondisi_sample harus salah satu dari: {KondisiSample.ALL}")
        return v

    @field_validator("jenis_kemasan")
    @classmethod
    def validate_kemasan(cls, v):
        if v is not None and v not in JenisKemasan.ALL:
            raise ValueError(f"jenis_kemasan harus salah satu dari: {JenisKemasan.ALL}")
        return v


class FkpItemResponse(BaseModel):
    id: uuid.UUID
    fkp_id: uuid.UUID
    product_id: uuid.UUID
    jenis_kemasan: Optional[str] = None
    qty: int
    batch_number: Optional[str] = None
    expired_date: Optional[date] = None
    ada_sample_keluhan: str
    ada_foto_sample: bool
    kondisi_sample: Optional[str] = None
    kondisi_sample_lainnya: Optional[str] = None
    tanggal_pembelian: Optional[date] = None
    tanggal_dikonsumsi: Optional[date] = None
    jenis_keluhan: str
    deskripsi_keluhan: Optional[str] = None

    rekomendasi_penanganan_apsm: Optional[str] = None
    rekomendasi_kompensasi_apsm: Optional[str] = None
    catatan_apsm: Optional[str] = None
    persentase_disetujui_apsm: Optional[int] = None

    # DEPRECATED: tidak lagi diisi untuk FKP baru (data historis saja)
    rekomendasi_penanganan_admin_ho: Optional[str] = None
    rekomendasi_kompensasi_admin_ho: Optional[str] = None
    catatan_admin_ho: Optional[str] = None
    persentase_disetujui_admin_ho: Optional[int] = None

    status_item: str
    catatan_qc: Optional[str] = None
    alasan_penolakan: Optional[str] = None
    persentase_disetujui_qc: Optional[int] = None
    qty_disetujui: Optional[int] = None

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
    """
    Update header FKP saat draft/need_revision. Field yang tidak dikirim tidak
    berubah; null pada catatan_distributor / lokasi_pembelian = dikosongkan.
    """
    outlet_id: Optional[uuid.UUID] = None
    prioritas: Optional[str] = None
    catatan_distributor: Optional[str] = None
    lokasi_pembelian: Optional[str] = None

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
    """
    Admin HO meneruskan FKP ke MSM (dari apsm_reviewed). Tujuan status
    ditentukan otomatis di admin_ho_review() dari total qty klaim saat
    pengajuan, BUKAN dari input request ini:
      - total qty ≤ BATAS_QTY_DIREKTUR → rsm_approval_final (jalur cepat)
      - total qty >  BATAS_QTY_DIREKTUR → rsm_approval_investigasi (jalur reguler)

    Admin HO tidak mengisi rekomendasi per item — rekomendasi yang dipakai
    untuk validasi konsistensi resolusi (lihat _validasi_konsistensi_rekomendasi
    di fkp_service.py) bersumber dari rekomendasi APSM
    (rekomendasi_kompensasi_apsm).
    """
    catatan_admin: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "catatan_admin": "Dokumen lengkap, diteruskan ke RSM.",
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
    """
    QC mengisi hasil investigasi + rekomendasi persentase per item.
    item_results tidak membawa status_item (lihat ItemQcResult) — QC hanya
    memberi persentase_disetujui_qc sebagai rekomendasi/insight.

    Dipakai oleh dua endpoint dengan skema yang sama:
      - qc_investigasi()                  : jalur reguler, mengubah status
                                            → investigated
      - qc_catatan_investigasi_paralel()  : jalur cepat, tidak mengubah status
    """
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
                        "persentase_disetujui_qc": 100,
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
    DEPRECATED — dipakai stub update_pengiriman() yang meneruskan ke
    buat_resolusi(). Progres pengiriman tukar_barang sekarang lewat modul
    Warehouse Surat Jalan; potong_tagihan lewat terbitkan_invoice().
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
    Satu schema untuk dua fase (field yang dipakai difilter di service
    berdasarkan status FKP saat itu — lihat buat_resolusi()):

    - Fase 1 (investigated / rsm_approval_resolusi / rsm_approval_final —
      SEBELUM approval final): wajib tipe_resolusi + metode_penanganan_fisik.
      item_qty_disetujui (khusus tukar_barang) juga diisi di fase ini, 1 form
      dengan resolusi — dan LANGSUNG memutuskan status_item per item
      (0 = ditolak, >0 = diterima, lihat ItemQtyDisetujui).
    - Fase 2 (accepted): isi detail eksekusi (nomor_do/rekening/dll).
      item_qty_disetujui masih boleh dikoreksi di sini selama belum
      diteruskan ke Warehouse.

    tipe_resolusi dan item_qty_disetujui TIDAK mempengaruhi jalur approval
    maupun keterlibatan Direktur (penentunya hanya total qty klaim saat
    pengajuan). Validasi ketat dilakukan di service.
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
    diteruskan_ke_warehouse: bool = False
    tanggal_diteruskan_ke_warehouse: Optional[datetime] = None
    diteruskan_oleh: Optional[uuid.UUID] = None

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

    @model_validator(mode="after")
    def _rewrite_url_ke_endpoint_terautentikasi(self):
        """
        Kolom `url` di DB masih path lama (mis. "/uploads/fkp/{fkp_id}/{file}")
        dari sebelum static mount publik dihapus — path itu sekarang 404.
        File HANYA bisa diambil lewat endpoint terautentikasi & scope-checked
        GET /api/fkp/{fkp_id}/attachments/{attachment_id}/file — jadi `url`
        ditimpa di sini supaya frontend selalu dapat URL yang berfungsi.
        """
        self.url = f"/api/fkp/{self.fkp_id}/attachments/{self.id}/file"
        return self

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
    area_info: Optional[AreaInfo] = None
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

    @computed_field  # type: ignore[misc]
    @property
    def masa_penyelesaian_detik(self) -> Optional[int]:
        return hitung_durasi_detik(self.tanggal_pengajuan, self.tanggal_selesai)

    @computed_field  # type: ignore[misc]
    @property
    def masa_penyelesaian_label(self) -> Optional[str]:
        detik = self.masa_penyelesaian_detik
        return format_durasi(detik) if detik is not None else None
    
    @model_validator(mode='before')
    @classmethod
    def extract_nested(cls, data):
        if hasattr(data, '__class__') and hasattr(data, 'distributor'):
            if data.distributor:
                data.__dict__['distributor_info'] = data.distributor
                area = getattr(data.distributor, 'area', None)   # ← BARU
                if area:
                    data.__dict__['area_info'] = area
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

    @model_validator(mode='before')
    @classmethod
    def extract_nested(cls, data):
        if hasattr(data, 'distributor'):
            if data.distributor:
                data.__dict__['distributor_info'] = data.distributor
            if data.outlet:
                data.__dict__['outlet_info'] = data.outlet
        return data

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

class TeruskanWarehouseRequest(BaseModel):
    catatan: Optional[str] = None
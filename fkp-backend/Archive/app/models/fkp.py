import uuid
from typing import TYPE_CHECKING, Optional, List, Any
from datetime import datetime, date, timezone
from decimal import Decimal
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import DateTime, Column, JSON, Integer

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.distributor import Distributor
    from app.models.outlet import Outlet
    from app.models.notification import Notification
    from app.models.product import ProductCatalog
    from app.models.testimoni import FkpTestimoni
    from app.models.sample import SampleShipment
    from app.models.warehouse import WarehouseSuratJalan


# ─── KONSTANTA ────────────────────────────────────────────────────────────────

class FkpStatus:
    DRAFT                    = "draft"
    SUBMITTED                = "submitted"
    APSM_REVIEWED            = "apsm_reviewed"
    RSM_APPROVAL_INVESTIGASI = "rsm_approval_investigasi"
    IN_INVESTIGATION         = "in_investigation"
    INVESTIGATED             = "investigated"
    RSM_APPROVAL_RESOLUSI    = "rsm_approval_resolusi"
    DIREKTUR_APPROVAL        = "direktur_approval"
    ACCEPTED                 = "accepted"
    IN_PROCESS               = "in_process"
    NEED_REVISION            = "need_revision"
    REJECTED                 = "rejected"
    CLOSED                   = "closed"

    ALL = [
        DRAFT, SUBMITTED, APSM_REVIEWED,
        RSM_APPROVAL_INVESTIGASI, IN_INVESTIGATION, INVESTIGATED,
        RSM_APPROVAL_RESOLUSI, DIREKTUR_APPROVAL,
        ACCEPTED, IN_PROCESS,
        NEED_REVISION, REJECTED, CLOSED,
    ]

    LABELS = {
        DRAFT:                    "Draft",
        SUBMITTED:                "Menunggu Review APSM",
        APSM_REVIEWED:            "Direview APSM — Menunggu Admin HO",
        RSM_APPROVAL_INVESTIGASI: "Menunggu Persetujuan RSM",
        IN_INVESTIGATION:         "Sedang Diinvestigasi QC",
        INVESTIGATED:             "Investigasi Selesai",
        RSM_APPROVAL_RESOLUSI:    "Menunggu Persetujuan RSM (Resolusi)",
        DIREKTUR_APPROVAL:        "Menunggu Persetujuan Direktur",
        ACCEPTED:                 "Disetujui — Menunggu Proses Resolusi",
        IN_PROCESS:               "Sedang Diproses (Pengiriman / Potong Tagihan)",
        NEED_REVISION:            "Perlu Revisi",
        REJECTED:                 "Ditolak",
        CLOSED:                   "Selesai / Ditutup",
    }

    # Status di mana FKP masih bisa diedit oleh distributor/outlet
    EDITABLE = [DRAFT, NEED_REVISION]

    # Status terminal — tidak bisa transisi lagi
    TERMINAL = [REJECTED, CLOSED]
    
    FINANCE_VISIBLE = [ACCEPTED, IN_PROCESS, CLOSED]


class FkpPrioritas:
    TOP_URGENT = "top_urgent"
    URGENT     = "urgent"
    REGULER    = "reguler"
    LOW        = "low"

    ALL = [TOP_URGENT, URGENT, REGULER, LOW]


class RekomendasiTipe:
    """Pilihan dropdown rekomendasi — sama untuk APSM dan Admin HO."""
    MUSNAHKAN         = "musnahkan"
    JUAL_PAKAN_TERNAK = "jual_pakan_ternak"
    KIRIM_KE_HO       = "kirim_ke_ho"
    GANTI_BARANG      = "ganti_barang"
    POTONG_TAGIHAN    = "potong_tagihan"

    ALL = [MUSNAHKAN, JUAL_PAKAN_TERNAK, KIRIM_KE_HO, GANTI_BARANG, POTONG_TAGIHAN]

    LABELS = {
        MUSNAHKAN:         "Dimusnahkan",
        JUAL_PAKAN_TERNAK: "Dijual sebagai pakan ternak",
        KIRIM_KE_HO:       "Dikirim kembali ke HO",
        GANTI_BARANG:      "Ganti barang baru",
        POTONG_TAGIHAN:    "Potong tagihan (cashback)",
    }


class StatusItem:
    PENDING  = "pending"
    DITERIMA = "diterima"
    DITOLAK  = "ditolak"

    ALL = [PENDING, DITERIMA, DITOLAK]


class TipeResolusi:
    TUKAR_BARANG   = "tukar_barang"
    POTONG_TAGIHAN = "potong_tagihan"
    TIDAK_ADA_KOMPENSASI = "tidak_ada_kompensasi"

    ALL = [TUKAR_BARANG, POTONG_TAGIHAN, TIDAK_ADA_KOMPENSASI]

class MetodePenangananFisik:
    """
    Apa yang secara fisik dilakukan terhadap barang bermasalah.
    Ini TERPISAH dari tipe_resolusi (kompensasi finansial).
    
    Contoh: barang berkutu → metode=dimusnahkan, tipe_resolusi=tukar_barang
    """
    DIMUSNAHKAN          = "dimusnahkan"         # dibakar, dikubur, insinerator
    DIJUAL_PAKAN_TERNAK  = "dijual_pakan_ternak"
    DIKIRIM_KE_HO        = "dikirim_ke_ho"
    DISIMPAN_DISTRIBUTOR = "disimpan_distributor"
    DI_REPACK_OLEH_PIHAK_INTERNAL = "di_repack_oleh_pihak_internal"

    ALL = [DIMUSNAHKAN, DIJUAL_PAKAN_TERNAK, DIKIRIM_KE_HO, DISIMPAN_DISTRIBUTOR, DI_REPACK_OLEH_PIHAK_INTERNAL]

    LABELS = {
        DIMUSNAHKAN:          "Dimusnahkan (dibakar/dikubur)",
        DIJUAL_PAKAN_TERNAK:  "Dijual sebagai pakan ternak",
        DIKIRIM_KE_HO:        "Dikirim kembali ke Head Office",
        DISIMPAN_DISTRIBUTOR: "Disimpan sementara oleh distributor",
        DI_REPACK_OLEH_PIHAK_INTERNAL: "Di Repack oleh pihak internal",
    }

class TipeDokumen:
    """
    Enum tipe dokumen/lampiran FKP.
    Gunakan `ALL` untuk validasi di service/schema.
    Tambahkan nilai baru di sini jika ada kebutuhan tipe baru.
 
    Pengelompokan:
      KELUHAN     → lampiran saat pengajuan keluhan
      INVESTIGASI → lampiran saat proses investigasi QC
      RESOLUSI    → bukti setelah proses resolusi dijalankan
      DOKUMEN     → dokumen formal (BA, surat, invoice)
      SAMPLE      → dokumen terkait modul Sample Shipment (BARU)
      LAINNYA     → catch-all
    """
    # ── Keluhan & Investigasi ─────────────────────────────
    FOTO_KELUHAN        = "foto_keluhan"         # foto produk bermasalah saat pengajuan
    FOTO_SAMPLE         = "foto_sample"          # foto sample yang dikirim ke QC
    FOTO_INVESTIGASI    = "foto_investigasi"     # foto hasil investigasi QC
    FOTO_EXPIRED        = "foto_expired"         # foto produk yang sudah kadaluarsa
    FOTO_KODE_PRODUKSI  = "foto_kode_produksi"   # foto kode produksi / BTN
    
 
    # ── Resolusi — tukar barang ───────────────────────────
    SURAT_JALAN             = "surat_jalan"          # surat jalan pengiriman barang pengganti
    FOTO_SERAH_TERIMA       = "foto_serah_terima"    # foto serah terima barang
    BERITA_ACARA_PENUKARAN  = "berita_acara_penukaran"
 
    # ── Resolusi — potong tagihan ─────────────────────────
    INVOICE_TERPOTONG   = "invoice_terpotong"    # invoice yang sudah dipotong tagihan
    BUKTI_TRANSFER      = "bukti_transfer"       # bukti transfer cashback ke rekening
    NOTA_RETUR          = "nota_retur"           # nota retur produk
 
    # ── Resolusi — pemusnahan ─────────────────────────────
    FOTO_PEMUSNAHAN         = "foto_pemusnahan"      # foto dokumentasi proses pemusnahan
    BERITA_ACARA_PEMUSNAHAN = "berita_acara_pemusnahan"

    # ── Resolusi — pemusnahan SEKALIGUS tukar barang — BARU ──────
    # Wajib diupload sebelum confirm_resolusi()/create_surat_jalan() saat
    # metode_penanganan_fisik == DIMUSNAHKAN. Sengaja dipisah dari
    # BERITA_ACARA_PEMUSNAHAN (yang dipakai murni untuk kasus pemusnahan
    # TANPA barang pengganti) — dua dokumen berbeda konteks meski serupa.
    BERITA_ACARA_PEMUSNAHAN_TUKAR_BARANG = "berita_acara_pemusnahan_tukar_barang"

    # ── Sample Shipment — BARU ─────────────────────────────────────────
    TANDA_TERIMA_SAMPLE  = "tanda_terima_sample"   # tanda terima fisik warehouse
    FOTO_KONDISI_MASUK   = "foto_kondisi_masuk"    # kondisi sample saat diterima
    HASIL_PEMERIKSAAN_QC = "hasil_pemeriksaan_qc"  # laporan/sertifikat hasil QC
 
    # ── Dokumen umum ─────────────────────────────────────
    BA_PEMERIKSAAN      = "ba_pemeriksaan"       # berita acara pemeriksaan produk
    SURAT_PERNYATAAN    = "surat_pernyataan"     # surat pernyataan dari distributor/outlet
    DOKUMEN_LAINNYA     = "dokumen_lainnya"      # catch-all untuk dokumen lain

    # ── Dokumen formal (disimpan di FkpDocument, bukan FkpAttachment) ─────
    INVOICE_POTONG_TAGIHAN = "invoice_potong_tagihan"
 
    ALL = [
        FOTO_KELUHAN, FOTO_SAMPLE, FOTO_INVESTIGASI, FOTO_EXPIRED, FOTO_KODE_PRODUKSI,
        SURAT_JALAN, FOTO_SERAH_TERIMA, BERITA_ACARA_PENUKARAN,
        INVOICE_TERPOTONG, BUKTI_TRANSFER, NOTA_RETUR,
        FOTO_PEMUSNAHAN, BERITA_ACARA_PEMUSNAHAN, BERITA_ACARA_PEMUSNAHAN_TUKAR_BARANG,
        TANDA_TERIMA_SAMPLE, FOTO_KONDISI_MASUK, HASIL_PEMERIKSAAN_QC,
        BA_PEMERIKSAAN, SURAT_PERNYATAAN, DOKUMEN_LAINNYA,
    ]
 
    # Shortcut per tipe resolusi — untuk FE filter/suggestions
    UNTUK_TUKAR_BARANG   = [SURAT_JALAN, FOTO_SERAH_TERIMA, BERITA_ACARA_PENUKARAN, NOTA_RETUR]
    UNTUK_POTONG_TAGIHAN = [INVOICE_TERPOTONG, BUKTI_TRANSFER, NOTA_RETUR]
    UNTUK_PEMUSNAHAN     = [FOTO_PEMUSNAHAN, BERITA_ACARA_PEMUSNAHAN]
    UNTUK_SAMPLE_INBOUND = [TANDA_TERIMA_SAMPLE, FOTO_KONDISI_MASUK]
    UNTUK_SAMPLE_QC      = [HASIL_PEMERIKSAAN_QC, FOTO_INVESTIGASI]


class SampleStatus:
    """State machine modul Sample Shipment (tracking sample fisik ke QC)."""
    SHIPPED               = "shipped"
    DELIVERED             = "delivered"
    RECEIVED_BY_WAREHOUSE = "received_by_warehouse"
    FORWARDED_TO_QC       = "forwarded_to_qc"
    UNDER_QC_REVIEW       = "under_qc_review"
    EXAMINED              = "examined"
    CANCELLED             = "cancelled"

    ALL = [
        SHIPPED, DELIVERED, RECEIVED_BY_WAREHOUSE,
        FORWARDED_TO_QC, UNDER_QC_REVIEW, EXAMINED, CANCELLED,
    ]
    TERMINAL = [EXAMINED, CANCELLED]

    LABELS = {
        SHIPPED:               "Dikirim oleh Pengirim",
        DELIVERED:             "Terkirim ke Tujuan",
        RECEIVED_BY_WAREHOUSE: "Diterima Warehouse",
        FORWARDED_TO_QC:       "Diserahkan ke QC",
        UNDER_QC_REVIEW:       "Sedang Diperiksa QC",
        EXAMINED:              "Pemeriksaan Selesai",
        CANCELLED:             "Dibatalkan",
    }


class SuratJalanStatus:
    """State machine modul Warehouse Surat Jalan (barang pengganti outbound)."""
    DRAFT     = "draft"      # sedang disiapkan warehouse
    ISSUED    = "issued"     # diterbitkan — PDF di-generate, siap cetak
    SHIPPED   = "shipped"    # barang diserahkan ke ekspedisi
    DELIVERED = "delivered"  # dikonfirmasi diterima outlet/distributor

    ALL      = [DRAFT, ISSUED, SHIPPED, DELIVERED]
    TERMINAL = [DELIVERED]


class JenisKeluhan:
    """Standarisasi jenis keluhan agar konsisten antara FE dan BE."""
    PRODUK_RUSAK_CACAT    = "produk_rusak_cacat"
    EXPIRED               = "expired"
    BENDA_ASING           = "benda_asing"
    KEMASAN_BOCOR         = "kemasan_bocor"
    SALAH_PRODUK          = "salah_produk"
    KUALITAS_TIDAK_SESUAI = "kualitas_tidak_sesuai"
    LAINNYA               = "lainnya"

    ALL = [
        PRODUK_RUSAK_CACAT, EXPIRED, BENDA_ASING,
        KEMASAN_BOCOR, SALAH_PRODUK, KUALITAS_TIDAK_SESUAI, LAINNYA,
    ]

    LABELS = {
        PRODUK_RUSAK_CACAT:    "Produk rusak / cacat fisik",
        EXPIRED:               "Produk kadaluarsa",
        BENDA_ASING:           "Ditemukan benda asing",
        KEMASAN_BOCOR:         "Kemasan bocor / rusak",
        SALAH_PRODUK:          "Produk tidak sesuai pesanan",
        KUALITAS_TIDAK_SESUAI: "Kualitas tidak sesuai standar",
        LAINNYA:               "Lainnya",
    }


# ─── FKP COMPLAINTS (master) ──────────────────────────────────────────────────

class FkpComplaint(SQLModel, table=True):
    __tablename__ = "fkp_complaints"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    nomor_fkp: str = Field(max_length=30, unique=True, index=True)

    # Sumber FKP
    outlet_id: Optional[uuid.UUID] = Field(default=None, foreign_key="outlets.id", index=True)
    distributor_id: uuid.UUID = Field(foreign_key="distributors.id", index=True)
    submitted_by: uuid.UUID = Field(foreign_key="users.id")
    handled_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")

    # Info level FKP
    prioritas: str = Field(default=FkpPrioritas.REGULER, max_length=20)
    status: str = Field(default=FkpStatus.DRAFT, max_length=40, index=True)

    lokasi_pembelian: Optional[str] = Field(default=None, max_length=255)
    
    # Catatan level FKP (ringkasan, bukan per item)
    catatan_distributor: Optional[str] = Field(default=None)
    catatan_sc_spv: Optional[str] = Field(default=None)
    catatan_apsm: Optional[str] = Field(default=None)
    catatan_admin: Optional[str] = Field(default=None)
    catatan_qc: Optional[str] = Field(default=None)
    catatan_rsm_investigasi: Optional[str] = Field(default=None)
    catatan_rsm_resolusi: Optional[str] = Field(default=None)
    catatan_direktur: Optional[str] = Field(default=None)

    # Nomor surat jalan (Admin HO input manual)
    nomor_surat_jalan: Optional[str] = Field(default=None, max_length=50)
    
    approved_by_marketing: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    approved_by_direktur: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")

    # Timestamp
    tanggal_pengajuan: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    tanggal_selesai: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    # Relasi
    outlet: Optional["Outlet"] = Relationship(back_populates="fkp_complaints")
    distributor: Optional["Distributor"] = Relationship(back_populates="fkp_complaints")
    submitted_by_user: Optional["User"] = Relationship(
        back_populates="fkp_submitted",
        sa_relationship_kwargs={"foreign_keys": "[FkpComplaint.submitted_by]"},
    )
    handled_by_user: Optional["User"] = Relationship(
        back_populates="fkp_handled",
        sa_relationship_kwargs={"foreign_keys": "[FkpComplaint.handled_by]"},
    )
    
    
    marketing_approver: Optional["User"] = Relationship(
        back_populates="fkp_approved_as_marketing",
        sa_relationship_kwargs={"foreign_keys": "[FkpComplaint.approved_by_marketing]"},
    )
    direktur_approver: Optional["User"] = Relationship(
        back_populates="fkp_approved_as_direktur",
        sa_relationship_kwargs={"foreign_keys": "[FkpComplaint.approved_by_direktur]"},
    )
    items: List["FkpItem"] = Relationship(back_populates="fkp")
    status_logs: List["FkpStatusLog"] = Relationship(back_populates="fkp")
    resolution: Optional["FkpResolution"] = Relationship(back_populates="fkp")
    attachments: List["FkpAttachment"] = Relationship(back_populates="fkp")
    documents: List["FkpDocument"] = Relationship(back_populates="fkp")
    notifications: List["Notification"] = Relationship(back_populates="fkp")
    testimoni: List["FkpTestimoni"] = Relationship(back_populates="fkp")
    # [BARU — Sample Shipment]
    sample_shipments: List["SampleShipment"] = Relationship(back_populates="fkp")
    warehouse_surat_jalan: List["WarehouseSuratJalan"] = Relationship(back_populates="fkp")


# ─── FKP ITEMS (per produk dalam 1 FKP) ──────────────────────────────────────

class FkpItem(SQLModel, table=True):
    __tablename__ = "fkp_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    fkp_id: uuid.UUID = Field(foreign_key="fkp_complaints.id", index=True)
    product_id: Optional[uuid.UUID] = Field(default=None, foreign_key="product_catalog.id")

    # Detail produk per item
    nama_produk_custom: Optional[str] = Field(default=None, max_length=200)

    # jenis_kemasan OPSIONAL — override dari ProductCatalog.jenis_kemasan.
    # Jika None → frontend/service fallback ke ProductCatalog.jenis_kemasan.
    jenis_kemasan: Optional[str] = Field(default=None, max_length=20)

    qty: int = Field(default=0) 
    batch_number: Optional[str] = Field(default=None, max_length=50)
    expired_date: Optional[date] = Field(default=None)

    # Detail keluhan
    ada_sample_keluhan: str = Field(default="tidak_ada", max_length=20)
    ada_foto_sample: bool = Field(default=False)
    kondisi_sample: Optional[str] = Field(default=None, max_length=20)  # "utuh" | "terbuka" | custom
    tanggal_pembelian: Optional[date] = Field(default=None)
    tanggal_dikonsumsi: Optional[date] = Field(default=None)

    jenis_keluhan: str = Field(max_length=100)
    deskripsi_keluhan: Optional[str] = Field(default=None)

    # Rekomendasi APSM (per item)
    # rekomendasi_apsm: Optional[str] = Field(default=None, max_length=30)
    rekomendasi_penanganan_apsm: Optional[str]
    rekomendasi_kompensasi_apsm: Optional[str]
    catatan_apsm: Optional[str] = Field(default=None)
    persentase_disetujui_apsm: Optional[int] = Field(default=None)

    # Rekomendasi Admin HO (per item)
    # rekomendasi_admin_ho: Optional[str] = Field(default=None, max_length=30)
    rekomendasi_penanganan_admin_ho: Optional[str]
    rekomendasi_kompensasi_admin_ho: Optional[str]
    catatan_admin_ho: Optional[str] = Field(default=None)
    persentase_disetujui_admin_ho: Optional[int] = Field(default=None)

    # Hasil QC per item
    status_item: str = Field(default=StatusItem.PENDING, max_length=20)
    catatan_qc: Optional[str] = Field(default=None)
    alasan_penolakan: Optional[str] = Field(default=None)
    
    qty_disetujui: Optional[int] = Field(
        default=None,
        description=(
            "Jumlah unit final yang disetujui untuk diganti. "
            "Khusus resolusi tukar_barang. "
            "Diisi Admin HO saat fase accepted, wajib untuk item berstatus diterima."
        )
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    # Relasi
    fkp: Optional[FkpComplaint] = Relationship(back_populates="items")
    product: Optional["ProductCatalog"] = Relationship(back_populates="fkp_items")
    attachments: List["FkpAttachment"] = Relationship(back_populates="fkp_item")
    # [BARU — Sample Shipment] 1 item bisa punya beberapa sample terkirim
    # (misal dikirim ulang kalau sample pertama rusak di jalan)
    sample_shipments: List["SampleShipment"] = Relationship(back_populates="fkp_item")


# ─── FKP STATUS LOGS ──────────────────────────────────────────────────────────

class FkpStatusLog(SQLModel, table=True):
    __tablename__ = "fkp_status_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    fkp_id: uuid.UUID = Field(foreign_key="fkp_complaints.id", index=True)
    status_lama: Optional[str] = Field(default=None, max_length=40)
    status_baru: str = Field(max_length=40)
    catatan: Optional[str] = Field(default=None)
    changed_by: uuid.UUID = Field(foreign_key="users.id")
    changed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    fkp: Optional[FkpComplaint] = Relationship(back_populates="status_logs")
    changed_by_user: Optional["User"] = Relationship(back_populates="fkp_status_logs")


# ─── FKP RESOLUTIONS (1 per FKP, level master) ───────────────────────────────

class FkpResolution(SQLModel, table=True):
    __tablename__ = "fkp_resolutions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    fkp_id: uuid.UUID = Field(foreign_key="fkp_complaints.id", unique=True, index=True)
    tipe_resolusi: str = Field(max_length=20)

    persentase_kompensasi_disetujui: Optional[int] = Field(
        default=None,
        description=(
            "Persentase potongan/cashback yang disetujui (0–100). "
            "Ditentukan Admin HO saat fase investigated, "
            "berdasarkan rekomendasi APSM & Admin HO per item. "
            "Digunakan Finance untuk menghitung nilai_cashback dari nota penjualan."
        )
    )
    
    nilai_nota_penjualan: Optional[Decimal] = Field(
        default=None, decimal_places=2, max_digits=15,
        description=(
            "Nilai nota penjualan aktual dari distributor. "
            "Diisi Finance saat memproses pembayaran cashback."
        )
    )

    # Potong tagihan
    nilai_cashback: Optional[Decimal] = Field(
        default=None, decimal_places=2, max_digits=15,
        description=(
            "Nominal cashback final yang dibayarkan. "
            "Hasil: nilai_nota_penjualan × (persentase_kompensasi_disetujui / 100). "
            "Bisa diisi manual oleh Finance jika ada penyesuaian."
        )
    )
    
    nama_bank: Optional[str] = Field(default=None, max_length=100)
    nomor_rekening: Optional[str] = Field(default=None, max_length=50)
    atas_nama: Optional[str] = Field(default=None, max_length=150)
    nomor_nota_retur: Optional[str] = Field(default=None, max_length=50)

    # Tukar barang
    nomor_do: Optional[str] = Field(default=None, max_length=50)
    tanggal_pengiriman: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    ekspedisi: Optional[str] = Field(default=None, max_length=100)
    resi_pengiriman: Optional[str] = Field(default=None, max_length=100)

    metode_penanganan_fisik: Optional[str] = Field(default=None, max_length=30)
    detail_penanganan: Optional[str] = Field(default=None, max_length=255)

    # Pemusnahan
    tanggal_pemusnahan: Optional[date] = Field(default=None)
    lokasi_pemusnahan: Optional[str] = Field(default=None, max_length=255)

    keterangan: Optional[str] = Field(default=None)
    
    catatan_finance: Optional[str] = Field(default=None)
    diproses_finance: bool = Field(default=False)
    tanggal_proses_finance: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    finance_user_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="users.id", nullable=True
    )
    
    dibuat_oleh: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    fkp: Optional[FkpComplaint] = Relationship(back_populates="resolution")
    finance_user: Optional["User"] = Relationship(
        back_populates="fkp_resolutions_as_finance",
        sa_relationship_kwargs={"foreign_keys": "[FkpResolution.finance_user_id]"},
    )
    dibuat_oleh_user: Optional["User"] = Relationship(
        back_populates="fkp_resolutions_created",
        sa_relationship_kwargs={"foreign_keys": "[FkpResolution.dibuat_oleh]"},
    )


# ─── FKP ATTACHMENTS ──────────────────────────────────────────────────────────

class FkpAttachment(SQLModel, table=True):
    __tablename__ = "fkp_attachments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    fkp_id: uuid.UUID = Field(foreign_key="fkp_complaints.id", index=True)

    fkp_item_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="fkp_items.id", index=True
    )

    # [BARU — Sample Shipment] Opsional — diisi kalau attachment ini terkait
    # dengan pengiriman sample tertentu (tanda terima, foto kondisi masuk,
    # hasil pemeriksaan QC), bukan lampiran FKP level umum.
    sample_shipment_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="sample_shipments.id", index=True
    )

    tipe_dokumen: str = Field(max_length=50)
    
    nama_file: str = Field(max_length=255)
    url: str = Field(max_length=500)
    ukuran_bytes: Optional[int] = Field(default=None)
    tipe_file: str = Field(max_length=20)
    
    keterangan: Optional[str] = Field(default=None, max_length=255)
    
    uploaded_by: uuid.UUID = Field(foreign_key="users.id")
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    fkp: Optional[FkpComplaint] = Relationship(back_populates="attachments")
    fkp_item: Optional["FkpItem"] = Relationship(back_populates="attachments")
    sample_shipment: Optional["SampleShipment"] = Relationship(back_populates="documents")


# ─── FKP DOCUMENTS ────────────────────────────────────────────────────────────

class FkpDocument(SQLModel, table=True):
    __tablename__ = "fkp_documents"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    fkp_id: uuid.UUID = Field(foreign_key="fkp_complaints.id", index=True)
    tipe_dokumen: str = Field(max_length=30)
    nomor_dokumen: Optional[str] = Field(default=None, max_length=50)
    tanggal_dokumen: Optional[date] = Field(default=None)
    url_file: str = Field(max_length=500)
    dibuat_oleh: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    fkp: Optional[FkpComplaint] = Relationship(back_populates="documents")
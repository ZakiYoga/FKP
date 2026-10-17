import uuid
from typing import Optional, List
from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field, Relationship

from app.models.fkp import FkpItem


class JenisKemasan:
    """
    Daftar nilai jenis kemasan yang dikenal sistem. Sumber tunggal untuk model,
    schema, dan validator. Urutan di ALL = urutan tampil di dropdown.

    KEMASAN_DIHITUNG_JALUR dan KEMASAN_PCS di models/fkp.py harus MEMBAGI ALL tanpa
    irisan: zak/ball/karton dihitung ke jalur approval, pcs ditangani langsung APSM.
    Jaga sinkron lewat test (juga dengan JenisKemasan di models/fkp.py).
    """
    ZAK     = "zak"
    BALL    = "ball"
    KARTON  = "karton"
    PCS     = "pcs"

    ALL = [ZAK, BALL, KARTON, PCS]

    LABELS = {
        ZAK:     "Zak",
        BALL:    "Ball",
        KARTON:  "Karton",
        PCS:     "Pcs",
    }


class ProductCatalog(SQLModel, table=True):
    """
    Katalog produk: SATU baris = SATU SKU.

    kode_produk mengacu pada kode SKU resmi yang ditetapkan perusahaan. Jangan
    menambah baris katalog hanya untuk membedakan kemasan (ball / pcs / karton).
    Kemasan berbeda dari SKU yang sama didaftarkan di ProductKemasan, dan itulah
    sumber dropdown jenis kemasan di form FKP.
    """
    __tablename__ = "product_catalog"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    kode_produk: str = Field(
        max_length=30, unique=True, index=True,
        description=(
            "Kode SKU resmi produk sesuai penetapan perusahaan. "
            "Satu SKU = satu produk; kemasan diatur di ProductKemasan."
        ),
    )
    nama_produk: str = Field(max_length=200)
    jenis_kemasan: str = Field(
        max_length=20,
        description=(
            "DEPRECATED, hanya untuk masa transisi. Sumber kemasan sekarang "
            "ProductKemasan (lihat get_kemasan() di product_service). Masih dibaca "
            "_hitung_total_qty_jalur() sebagai fallback untuk item FKP lama yang "
            "snapshot jenis_kemasan-nya NULL. Diisi dengan kemasan utama produk "
            "sampai kolom ini dihapus."
        ),
    )
    berat_gr: Optional[int] = Field(default=None)
    foto_url: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    qty_per_kemasan: Optional[int] = Field(default=None)

    fkp_items: List["FkpItem"] = Relationship(back_populates="product")
    # Jangan diakses langsung di kode async tanpa selectinload (lazy load =
    # MissingGreenlet). Untuk membaca kemasan, pakai get_kemasan().
    kemasan_list: List["ProductKemasan"] = Relationship(back_populates="product")


class ProductKemasan(SQLModel, table=True):
    """
    Kemasan yang tersedia untuk satu produk (satu SKU).

    Bentuk jual berbeda dari SKU yang sama (mis. ball utuh dan pcs/ecer)
    didaftarkan di sini, BUKAN dengan menambah baris di ProductCatalog.
      - 2 kemasan terdaftar (ball, pcs) → dropdown FKP berisi 2 pilihan.
      - 1 kemasan terdaftar (zak)       → terisi otomatis dan tidak bisa diganti.
      - 0 kemasan                       → produk belum bisa dipakai di FKP.
    jenis_kemasan yang dipilih user di FKP divalidasi terhadap tabel ini
    (set_jenis_kemasan di fkp_service), karena menentukan jalur approval.
    """
    __tablename__ = "product_kemasan"
    __table_args__ = (
        UniqueConstraint("product_id", "jenis_kemasan", name="uq_product_kemasan"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    product_id: uuid.UUID = Field(foreign_key="product_catalog.id", index=True)
    jenis_kemasan: str = Field(
        max_length=20,
        description="Salah satu nilai JenisKemasan.ALL.",
    )

    product: Optional[ProductCatalog] = Relationship(back_populates="kemasan_list")
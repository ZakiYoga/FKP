import uuid
from typing import Optional, List
from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field, Relationship

from app.models.fkp import FkpItem


class JenisKemasan:
    """
    Daftar nilai jenis kemasan yang dikenal sistem. Sumber tunggal untuk model,
    schema, dan validator. Urutan di ALL = urutan tampil di dropdown DAN
    penentu kemasan utama (yang pertama menurut ALL).

    KEMASAN_BESAR = kemasan yang isinya "banyak pcs": zak, ball, karton. Satu SKU
    boleh punya MAKSIMAL SATU kemasan besar; pcs boleh menyertai.
    ISI_TETAP = kemasan besar yang isinya pasti (zak = 1). Kemasan besar lain
    (ball, karton) wajib diisi qty_per_kemasan-nya oleh admin.

    KEMASAN_BESAR harus SAMA dengan KEMASAN_DIHITUNG_JALUR di models/fkp.py, dan
    KEMASAN_DIHITUNG_JALUR + KEMASAN_PCS di sana harus MEMBAGI ALL tanpa irisan:
    zak/ball/karton dihitung ke jalur approval, pcs ditangani langsung APSM.
    Jaga sinkron lewat test (juga dengan JenisKemasan di models/fkp.py).
    Menambah kemasan baru (mis. renceng kelak) cukup menambah ke ALL, LABELS,
    dan KEMASAN_BESAR; logika di tentukan_qty_per_kemasan() digerakkan konstanta.
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

    KEMASAN_BESAR = [ZAK, BALL, KARTON]
    ISI_TETAP = {ZAK: 1}


def tentukan_qty_per_kemasan(kemasan_urut: list[str], qty: int | None) -> int:
    """
    Menentukan nilai qty_per_kemasan (isi kemasan besar, dalam pcs) dari daftar
    kemasan SKU dan qty kiriman klien. Fungsi murni, dipakai schema, service, dan
    seeder supaya aturannya satu tempat.

      - Lebih dari satu kemasan besar      -> ValueError
      - Tidak ada kemasan besar (pcs saja) -> 1
      - Kemasan besar berisi tetap (zak)   -> nilai tetap (qty kiriman diabaikan)
      - Kemasan besar lain (ball/karton)   -> qty wajib bilangan bulat >= 2

    ValueError dibiarkan lolos; pemanggil mengubahnya menjadi 422 (schema) atau
    400 (service).
    """
    besar = list(dict.fromkeys(k for k in kemasan_urut if k in JenisKemasan.KEMASAN_BESAR))
    if len(besar) > 1:
        raise ValueError("Satu SKU hanya boleh punya satu kemasan besar (zak/ball/karton).")
    if not besar:
        return 1
    if besar[0] in JenisKemasan.ISI_TETAP:
        return JenisKemasan.ISI_TETAP[besar[0]]
    if qty is None or qty < 2:
        label = JenisKemasan.LABELS.get(besar[0], besar[0]).lower()
        raise ValueError(f"Isi per {label} wajib diisi (minimal 2 pcs).")
    return qty


class ProductCatalog(SQLModel, table=True):
    """
    Katalog produk: SATU baris = SATU SKU.

    kode_produk mengacu pada kode SKU resmi yang ditetapkan perusahaan. Jangan
    menambah baris katalog hanya untuk membedakan kemasan (ball / pcs / karton).
    Kemasan berbeda dari SKU yang sama didaftarkan di ProductKemasan, dan itulah
    sumber dropdown jenis kemasan di form FKP. Varian gramasi berbeda
    (mis. Laskar MIX 12 kg vs 10 kg) = SKU baru dengan kode_produk baru.

    Semantik berat dan isi:
      - berat_gr         = berat per SATUAN TERKECIL: per zak untuk kemasan zak,
                           per pcs untuk ball/karton/pcs.
      - qty_per_kemasan  = isi kemasan besar dalam pcs. Zak dan produk pcs-saja = 1.
      - Berat kemasan    = qty_per_kemasan x berat_gr (dihitung, TIDAK disimpan).

    Rumus analitik FKP per produk (belum diimplementasi, dokumentasi):
        berat_item_gr = jumlah_item x isi x berat_gr
        isi = qty_per_kemasan bila jenis item adalah kemasan besar, 1 bila pcs.
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
    berat_gr: Optional[int] = Field(
        default=None,
        description=(
            "Berat per satuan terkecil: per zak untuk zak, per pcs untuk kemasan "
            "lain, dalam gram."
        ),
    )
    foto_url: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    qty_per_kemasan: Optional[int] = Field(
        default=None,
        description="Isi kemasan besar dalam pcs. Zak dan produk pcs-saja = 1.",
    )

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
    Satu SKU maksimal punya satu kemasan besar (zak/ball/karton), lihat
    tentukan_qty_per_kemasan().
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
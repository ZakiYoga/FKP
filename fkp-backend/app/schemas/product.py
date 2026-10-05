import uuid
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.product import JenisKemasan


def _strip(v):
    return v.strip() if isinstance(v, str) else v


def _kosong_jadi_none(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


class ProductCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "kode_produk": "PRD-BALL-003",
                "nama_produk": "Garam Baru Cap Saktifood 1kg",
                "kemasan": ["ball", "pcs"],
                "berat_gr": 1000,
                "qty_per_kemasan": 20,
            }
        }
    )

    kode_produk: str = Field(
        min_length=1, max_length=30,
        description="Kode SKU resmi produk sesuai penetapan perusahaan. Satu SKU = satu produk.",
    )
    nama_produk: str = Field(min_length=1, max_length=200)

    kemasan: Optional[List[str]] = Field(
        default=None,
        description=(
            "Kemasan yang tersedia untuk SKU ini, mis. ['ball', 'pcs']. "
            "Wajib minimal satu (kecuali memakai jenis_kemasan lama)."
        ),
    )
    jenis_kemasan: Optional[str] = Field(
        default=None,
        description="DEPRECATED. Dipakai hanya bila 'kemasan' tidak diisi (setara kemasan=[nilai ini]).",
    )

    berat_gr: Optional[int] = Field(default=None, gt=0)
    qty_per_kemasan: Optional[int] = Field(
        default=None, gt=0,
        description="Isi per kemasan utama (mis. 20 pcs per ball). Kosongkan bila tidak relevan.",
    )
    foto_url: Optional[str] = Field(
        default=None,
        description="URL foto produk. Diisi otomatis oleh POST /api/products/{id}/foto.",
    )

    @field_validator("kode_produk", "nama_produk", mode="before")
    @classmethod
    def _rapikan_teks(cls, v):
        return _strip(v)

    @field_validator("foto_url", mode="before")
    @classmethod
    def _rapikan_foto(cls, v):
        return _kosong_jadi_none(v)

    @model_validator(mode="after")
    def _normalisasi_kemasan(self):
        daftar = self.kemasan or ([self.jenis_kemasan] if self.jenis_kemasan else [])
        if not daftar:
            raise ValueError("Minimal satu kemasan harus dipilih (field 'kemasan').")
        tidak_dikenal = [k for k in daftar if k not in JenisKemasan.ALL]
        if tidak_dikenal:
            raise ValueError(
                f"Kemasan tidak dikenal: {tidak_dikenal}. Pilihan: {JenisKemasan.ALL}."
            )
        urut = sorted(set(daftar), key=JenisKemasan.ALL.index)
        self.kemasan = urut
        self.jenis_kemasan = urut[0]  # kemasan utama (kolom lama ProductCatalog.jenis_kemasan)
        return self


class ProductUpdate(BaseModel):
    """
    Update data dasar produk. Field yang tidak dikirim tidak berubah; null
    mengosongkan field (kecuali nama_produk dan is_active). Kemasan TIDAK
    diubah di sini (PUT /{id}/kemasan); field jenis_kemasan atau kemasan dari
    klien diabaikan.
    """
    nama_produk: Optional[str] = Field(default=None, min_length=1, max_length=200)
    berat_gr: Optional[int] = Field(default=None, gt=0)
    is_active: Optional[bool] = None
    qty_per_kemasan: Optional[int] = Field(default=None, gt=0)
    foto_url: Optional[str] = None

    @field_validator("nama_produk", mode="before")
    @classmethod
    def _rapikan_nama(cls, v):
        return _strip(v)

    @field_validator("foto_url", mode="before")
    @classmethod
    def _rapikan_foto(cls, v):
        return _kosong_jadi_none(v)


class KemasanUpdate(BaseModel):
    kemasan: List[str] = Field(
        description="Daftar lengkap kemasan produk (menggantikan daftar lama), mis. ['ball', 'pcs']."
    )

    @field_validator("kemasan")
    @classmethod
    def _validasi_kemasan(cls, v):
        if not v:
            raise ValueError("Minimal satu kemasan harus dipilih.")
        tidak_dikenal = [k for k in v if k not in JenisKemasan.ALL]
        if tidak_dikenal:
            raise ValueError(
                f"Kemasan tidak dikenal: {tidak_dikenal}. Pilihan: {JenisKemasan.ALL}."
            )
        return list(dict.fromkeys(v))  # buang duplikat, urutan input dipertahankan


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kode_produk: str
    nama_produk: str
    qty_per_kemasan: Optional[int] = None
    foto_url: Optional[str] = None
    jenis_kemasan: str = Field(description="DEPRECATED: kemasan utama. FE memakai kemasan_tersedia.")
    kemasan_tersedia: List[str] = Field(
        default_factory=list,
        description="Kemasan yang tersedia untuk produk ini; sumber dropdown jenis kemasan di FKP.",
    )
    berat_gr: Optional[int] = None
    is_active: bool
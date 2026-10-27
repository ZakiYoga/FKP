from typing import Optional, List, Literal
from pydantic import BaseModel, ConfigDict


class ProvinsiOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kode: str
    nama: str


class KabupatenKotaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kode: str
    nama: str


class KecamatanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kode: str
    nama: str


class KelurahanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kode: str
    nama: str
    kode_pos: Optional[str] = None


class WilayahLengkap(BaseModel):
    """Hasil resolve kelurahan_id → seluruh parent."""
    kelurahan: KelurahanOut
    kecamatan: KecamatanOut
    kabupaten_kota: KabupatenKotaOut
    provinsi: ProvinsiOut
    label: str  # "Gawanan, Colomadu, Karanganyar, Jawa Tengah"


class WilayahSearchItem(BaseModel):
    kelurahan_id: int
    label: str
    kode_pos: Optional[str] = None

class WilayahReverseOut(BaseModel):
    status: Literal["matched", "ambiguous", "not_found"]
    candidates: List[WilayahLengkap] = []
    display_name: Optional[str] = None
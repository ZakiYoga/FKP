from typing import TYPE_CHECKING, Optional, List
from sqlmodel import SQLModel, Field, Relationship
if TYPE_CHECKING:
    from .area import AreaProvince
    from .outlet import Outlet
    from .area import Area
    from .distributor import Distributor

class Provinsi(SQLModel, table=True):
    __tablename__ = "provinsi"

    id: Optional[int] = Field(default=None, primary_key=True)
    kode: str = Field(max_length=10, unique=True, index=True)
    nama_provinsi: str = Field(max_length=100, index=True)

    kabupaten_kota: List["KabupatenKota"] = Relationship(back_populates="provinsi")
    area_provinces: List["AreaProvince"] = Relationship(back_populates="provinsi")


class KabupatenKota(SQLModel, table=True):
    __tablename__ = "kabupaten_kota"

    id: Optional[int] = Field(default=None, primary_key=True)
    kode: str = Field(max_length=10, unique=True, index=True)     
    provinsi_id: int = Field(foreign_key="provinsi.id", index=True)
    nama: str = Field(max_length=100)

    # Relasi
    provinsi: Optional[Provinsi] = Relationship(back_populates="kabupaten_kota")
    kecamatan: List["Kecamatan"] = Relationship(back_populates="kabupaten_kota")


class Kecamatan(SQLModel, table=True):
    __tablename__ = "kecamatan"

    id: Optional[int] = Field(default=None, primary_key=True)
    kode: str = Field(max_length=10, unique=True, index=True) 
    kabupaten_kota_id: int = Field(foreign_key="kabupaten_kota.id", index=True)
    nama: str = Field(max_length=100)

    # Relasi
    kabupaten_kota: Optional[KabupatenKota] = Relationship(back_populates="kecamatan")
    kelurahan: List["Kelurahan"] = Relationship(back_populates="kecamatan")


class Kelurahan(SQLModel, table=True):
    __tablename__ = "kelurahan"

    id: Optional[int] = Field(default=None, primary_key=True)
    kode: str = Field(max_length=10, unique=True, index=True)
    kecamatan_id: int = Field(foreign_key="kecamatan.id", index=True)
    nama: str = Field(max_length=100)
    kode_pos: Optional[str] = Field(default=None, max_length=10)

    # Relasi
    kecamatan: Optional[Kecamatan] = Relationship(back_populates="kelurahan")
    distributors: List["Distributor"] = Relationship(back_populates="kelurahan")
    outlets: List["Outlet"] = Relationship(back_populates="kelurahan")
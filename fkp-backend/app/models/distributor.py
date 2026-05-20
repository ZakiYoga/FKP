import uuid
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import DateTime, Column
from sqlmodel import SQLModel, Field, Relationship


class Distributor(SQLModel, table=True):
    __tablename__ = "distributors"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    area_id: uuid.UUID = Field(foreign_key="areas.id", index=True)
    kelurahan_id: Optional[int] = Field(default=None, foreign_key="kelurahan.id")
    kode_distributor: str = Field(max_length=30, unique=True, index=True)
    nama_perusahaan: str = Field(max_length=200)
    pemilik: str = Field(max_length=150)
    no_telepon: Optional[str] = Field(default=None, max_length=20)
    email_perusahaan: Optional[str] = Field(default=None, max_length=150)
    alamat_lengkap: Optional[str] = Field(default=None)
    kode_pos: Optional[str] = Field(default=None, max_length=10)
    status: str = Field(default="aktif", max_length=20)  # "aktif" | "nonaktif"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    # Relasi
    area: Optional["Area"] = Relationship(back_populates="distributors")
    kelurahan: Optional["Kelurahan"] = Relationship(back_populates="distributors")
    outlets: List["Outlet"] = Relationship(back_populates="distributor")    
    distributor_users: List["DistributorUser"] = Relationship(back_populates="distributor")
    fkp_complaints: List["FkpComplaint"] = Relationship(back_populates="distributor")


class DistributorUser(SQLModel, table=True):
    """
    Many-to-many: satu user (pemilik) bisa terdaftar di beberapa distributor.
    Dipakai untuk akses monitoring — bukan untuk SC/SPV (pakai ScSpvDistributor).
    """
    __tablename__ = "distributor_users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    distributor_id: uuid.UUID = Field(foreign_key="distributors.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    jabatan: Optional[str] = Field(default=None, max_length=100)
    is_primary: bool = Field(default=False)  # True = kontak utama distributor
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    # Relasi
    distributor: Optional[Distributor] = Relationship(back_populates="distributor_users")
    user: Optional["User"] = Relationship(back_populates="distributor_users")

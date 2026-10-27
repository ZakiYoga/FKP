import uuid
import re
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime, timezone
from pydantic import field_validator
from sqlalchemy import DateTime, Column, Float
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.area import Area
    from app.models.wilayah import Kelurahan
    from app.models.outlet import Outlet
    from app.models.fkp import FkpComplaint
    from app.models.user import User
    
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
    latitude: Optional[float] = Field(default=None, sa_column=Column(Float(53), nullable=True))
    longitude: Optional[float] = Field(default=None, sa_column=Column(Float(53), nullable=True))
    status: str = Field(default="aktif", max_length=20)  # "aktif" | "nonaktif"
    npwp: Optional[str] = Field(default=None, max_length=20, index=True)
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

    @field_validator("npwp")
    def validate_npwp(cls, v):
        if v is None:
            return v
        digits = re.sub(r"\D", "", v)
        if len(digits) not in (15, 16):
            raise ValueError("NPWP harus 15 atau 16 digit")
        return digits


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

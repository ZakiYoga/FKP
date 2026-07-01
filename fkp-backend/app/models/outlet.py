import uuid
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime, timezone
from sqlalchemy import DateTime, Column, Numeric
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .distributor import Distributor
    from .user import User
    from .fkp import FkpComplaint
    from .wilayah import Kelurahan


class Outlet(SQLModel, table=True):
    __tablename__ = "outlets"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    distributor_id: uuid.UUID = Field(foreign_key="distributors.id", index=True)
    kode_outlet: str = Field(max_length=30, unique=True, index=True)
    nama_toko: str = Field(max_length=200)
    pemilik_toko: str = Field(max_length=150)
    tipe_toko: str = Field(max_length=50) 
    no_hp: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=150)

    # Lokasi
    kelurahan_id: Optional[int] = Field(default=None, foreign_key="kelurahan.id")
    alamat_lengkap: Optional[str] = Field(default=None)
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)

    # Foto & PIC
    foto_url: Optional[str] = Field(default=None, max_length=500)
    pic_user_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="users.id",
        description="User pemilik / PIC utama toko ini"
    )

    status: str = Field(default="pending", max_length=20)   # "aktif" | "nonaktif" | "pending"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    # Relasi
    distributor: Optional["Distributor"] = Relationship(back_populates="outlets")
    pic_user: Optional["User"] = Relationship(back_populates="outlets_as_pic")
    kelurahan: Optional["Kelurahan"] = Relationship(back_populates="outlets")
    fkp_complaints: List["FkpComplaint"] = Relationship(back_populates="outlet")

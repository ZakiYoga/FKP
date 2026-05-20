import uuid
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import DateTime, Column
from sqlmodel import SQLModel, Field, Relationship


class Area(SQLModel, table=True):
    __tablename__ = "areas"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    kode_area: str = Field(max_length=20, unique=True, index=True)
    nama_area: str = Field(max_length=100)
    pic_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
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
    pic_user: Optional["User"] = Relationship(back_populates="areas_as_pic")
    area_provinces: List["AreaProvince"] = Relationship(back_populates="area")
    distributors: List["Distributor"] = Relationship(back_populates="area")


class AreaProvince(SQLModel, table=True):
    __tablename__ = "area_provinces"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    area_id: uuid.UUID = Field(foreign_key="areas.id", index=True)
    provinsi_id: int = Field(foreign_key="provinsi.id", index=True)

    # Relasi
    area: Optional[Area] = Relationship(back_populates="area_provinces")
    provinsi: Optional["Provinsi"] = Relationship(back_populates="area_provinces")

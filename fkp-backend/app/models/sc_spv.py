import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import DateTime, Column
from sqlmodel import SQLModel, Field, Relationship


class ScSpvDistributor(SQLModel, table=True):
    """
    Mapping SC/SPV ke Distributor yang dia handle.
    Constraint: distributor harus berada di area yang sama
    dengan APSM atasan SC/SPV ini.
    1 distributor hanya bisa di-handle oleh 1 SC/SPV.
    1 SC/SPV bisa handle banyak distributor (di area APSM atasannya).
    """
    __tablename__ = "sc_spv_distributors"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sc_spv_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    distributor_id: uuid.UUID = Field(
        foreign_key="distributors.id",
        unique=True,   # 1 distributor hanya 1 SC/SPV
        index=True
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )


class ApsmScSpv(SQLModel, table=True):
    """
    Mapping APSM ke SC/SPV bawahannya, plus area yang dipegang SC/SPV.
    1 SC/SPV hanya bisa punya 1 APSM atasan dan 1 area.
    1 APSM bisa punya banyak SC/SPV.
    Aturan: area harus aktif dan Area.pic_user_id == apsm_user_id (dicek di service).
    """
    __tablename__ = "apsm_sc_spv"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    apsm_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    sc_spv_user_id: uuid.UUID = Field(foreign_key="users.id", unique=True, index=True)
    # Nullable sementara untuk backfill; jadikan NOT NULL di migrasi kedua
    area_id: Optional[uuid.UUID] = Field(default=None, foreign_key="areas.id", index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )


class RsmApsm(SQLModel, table=True):
    """
    Mapping RSM ke APSM bawahannya.
    1 APSM hanya bisa punya 1 RSM atasan.
    1 RSM bisa punya banyak APSM.
    """
    __tablename__ = "rsm_apsm"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    rsm_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    apsm_user_id: uuid.UUID = Field(
        foreign_key="users.id",
        unique=True,   # 1 APSM hanya 1 RSM atasan
        index=True
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

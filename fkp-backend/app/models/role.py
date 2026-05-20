import uuid
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import DateTime, Column
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .user import User


class Role(SQLModel, table=True):
    __tablename__ = "roles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    kode_role: str = Field(max_length=50, unique=True, index=True)
    nama_role: str = Field(max_length=100)
    deskripsi: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )
    # Relasi
    permissions: List["RolePermission"] = Relationship(back_populates="role")
    users: List["User"] = Relationship(back_populates="role")


class RolePermission(SQLModel, table=True):
    __tablename__ = "role_permissions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    role_id: uuid.UUID = Field(foreign_key="roles.id", index=True)
    permission_code: str = Field(max_length=100)
    keterangan: Optional[str] = Field(default=None, max_length=255)

    # Relasi
    role: Optional[Role] = Relationship(back_populates="permissions")

import uuid
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime, timezone
from sqlalchemy import DateTime, Column
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .role import RolePermission


class Permission(SQLModel, table=True):
    """
    Katalog permission/action yang bisa diatur per role lewat dashboard RBAC.

    Konvensi `code`: "module.nama_fungsi_service" — 1:1 dengan nama fungsi
    di fkp_service.py (contoh: "fkp.submit", "fkp.apsm_review").
    """
    __tablename__ = "permissions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    code: str = Field(max_length=100, unique=True, index=True)
    module: str = Field(max_length=50, index=True)
    action: str = Field(max_length=50)
    label: str = Field(max_length=150)
    deskripsi: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    # Relasi
    roles: List["RolePermission"] = Relationship(back_populates="permission")

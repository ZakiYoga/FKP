"""Schemas untuk endpoint dashboard admin RBAC (matrix role-permission)."""
import uuid
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class PermissionOut(BaseModel):
    id: uuid.UUID
    code: str
    module: str
    action: str
    label: str
    deskripsi: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class RoleOut(BaseModel):
    id: uuid.UUID
    kode_role: str
    nama_role: str
    deskripsi: Optional[str] = None
    is_active: bool
    is_superadmin: bool

    class Config:
        from_attributes = True


class RolePermissionsUpdate(BaseModel):
    permission_ids: List[uuid.UUID]

"""
Role Endpoints:
  GET /api/roles/  → List semua role (untuk dropdown form pembuatan user)
"""
from typing import List
import uuid
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.core.dependencies import require_roles

router = APIRouter()


class RoleResponse(BaseModel):
    id: uuid.UUID
    kode_role: str
    nama_role: str
    deskripsi: str | None
    is_active: bool

    class Config:
        from_attributes = True


@router.get(
    "/",
    response_model=List[RoleResponse],
    summary="List semua role",
    description="Dipakai untuk mengisi dropdown saat membuat user baru.",
)
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user : User = Depends(require_roles("superadmin")),
):
    from app.models.role import Role
    result = await db.execute(
        select(Role).where(Role.is_active == True).order_by(Role.nama_role)
    )
    return result.scalars().all()

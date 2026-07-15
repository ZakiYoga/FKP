"""
User Management Endpoints (hanya SuperAdmin):
  GET    /api/users/          → List semua user
  POST   /api/users/          → Buat user baru
  GET    /api/users/{id}      → Detail user
  PUT    /api/users/{id}      → Update user
  DELETE /api/users/{id}      → Nonaktifkan user (soft delete)
"""
import uuid
from typing import List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission_dep
from app.core.security import hash_password
from app.models.user import User
from app.models.role import Role
from app.schemas.user import UserCreate, UserUpdate, UserResponse

router = APIRouter()


@router.get(
    "/",
    response_model=List[UserResponse],
    summary="List semua user",
)
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission_dep("user.manage")),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Buat user baru",
)
async def create_user(
    request: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission_dep("user.manage")),
):
    # Cek email sudah dipakai atau belum
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{request.email}' sudah digunakan.",
        )

    # Validasi role_id ada di DB
    result = await db.execute(select(Role).where(Role.id == request.role_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role tidak ditemukan.",
        )

    user = User(
        role_id=request.role_id,
        nama=request.nama,
        email=request.email,
        password_hash=hash_password(request.password),
        no_telepon=request.no_telepon,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Detail user",
)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission_dep("user.manage")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")
    return user


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
)
async def update_user(
    user_id: uuid.UUID,
    request: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission_dep("user.manage")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")

    # Update hanya field yang dikirim (tidak None)
    update_data = request.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    user.updated_at = datetime.now(timezone.utc)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete(
    "/{user_id}",
    summary="Nonaktifkan user (soft delete)",
    description="User tidak dihapus dari DB, hanya dinonaktifkan (is_active = False).",
)
async def deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission_dep("user.manage")),
):
    # Cegah superadmin menonaktifkan dirinya sendiri
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak bisa menonaktifkan akun sendiri.",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")

    user.is_active = False
    user.updated_at = datetime.now(timezone.utc)
    db.add(user)
    await db.commit()

    return {"message": f"User '{user.nama}' berhasil dinonaktifkan."}
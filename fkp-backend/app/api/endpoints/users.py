"""
User Management Endpoints (hanya SuperAdmin):
  GET    /api/users/          → List semua user
  POST   /api/users/          → Buat user baru
  GET    /api/users/{id}      → Detail user
  PUT    /api/users/{id}      → Update user
  DELETE /api/users/{id}      → Nonaktifkan user (soft delete)
"""
import uuid
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status, File, UploadFile
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission_dep
from app.core.security import hash_password, normalize_email
from app.models.user import User
from app.models.role import Role
from app.schemas.auth import MessageResponse
from app.schemas.user import UserCreate, UserSelfUpdate, UserUpdate, UserResponse, UserListPage, AdminResetPassword

from app.services import account_security_service as account_svc
from app.services import user_service
from app.services import avatar_service

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
    email_norm = normalize_email(request.email)
    result = await db.execute(select(User).where(func.lower(User.email) == email_norm))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{email_norm}' sudah digunakan.",
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
        first_name=request.first_name, 
        last_name=request.last_name, 
        gender=request.gender,
        email=email_norm,
        password_hash=hash_password(request.password),
        no_telepon=request.no_telepon,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.get("/page", response_model=UserListPage, summary="List user berpagination")
async def list_users_paginated(
    page: int = Query(default=1, ge=1, description="Halaman, mulai dari 1"),
    page_size: int = Query(default=10, ge=1, le=100, description="Jumlah item per halaman (maks 100)"),
    role: Optional[str] = Query(default=None, description="Filter by kode_role"),
    is_active: Optional[bool] = Query(default=None, description="Filter status aktif"),
    search: Optional[str] = Query(
        default=None, max_length=100, description="Cari di nama atau email",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission_dep("user.manage")),
):
    return await user_service.list_users_paginated(
        db, page=page, page_size=page_size,
        role=role, is_active=is_active, search=search,
    )

@router.post("/me/avatar", response_model=UserResponse)
async def upload_my_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    old_path = current_user.avatar_path
    current_user.avatar_path = await avatar_service.save_avatar(file, current_user.id)
    current_user.updated_at = datetime.now(timezone.utc)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    avatar_service.delete_avatar(old_path)
    return current_user


@router.delete("/me/avatar", response_model=UserResponse)
def remove_my_avatar(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    old_path = current_user.avatar_path
    current_user.avatar_path = None
    current_user.updated_at = datetime.now(timezone.utc)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    avatar_service.delete_avatar(old_path)
    return current_user

@router.put(
    "/me",
    response_model=UserResponse,
    summary="Ubah profil sendiri",
)
async def update_my_profile(
    request: UserSelfUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    update_data = request.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)

    current_user.updated_at = datetime.now(timezone.utc)
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user

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


@router.post(
    "/{user_id}/reset-password",
    response_model=MessageResponse,
    summary="Reset password user (oleh admin)",
    description=(
        "Menetapkan password baru untuk user lain dan mencabut semua sesi "
        "loginnya. Akun superadmin hanya bisa direset oleh superadmin."
    ),
)
async def admin_reset_user_password(
    user_id: uuid.UUID,
    request: AdminResetPassword,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission_dep("user.reset_password")),
):
    return MessageResponse(
        **await account_svc.admin_reset_password(
            user_id,
            request.password_baru,
            request.password_baru_konfirmasi,
            current_user,
            db,
            background_tasks,
        )
    )


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

    return {"message": f"User '{user.full_name}' berhasil dinonaktifkan."}
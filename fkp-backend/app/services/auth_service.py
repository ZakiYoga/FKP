"""
Auth Service — business logic untuk login, logout, dan manajemen token.
Dipisah dari endpoint agar mudah di-test dan dipakai ulang.
"""
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import verify_password, create_access_token, hash_password
from app.models.user import User
from app.models.role import Role
from app.schemas.auth import LoginRequest, LoginResponse, UserResponse, RoleInfo


async def login(request: LoginRequest, db: AsyncSession) -> LoginResponse:
    """
    Proses login:
    1. Cari user by email
    2. Verifikasi password
    3. Cek user aktif
    4. Buat JWT token
    5. Update last_login
    6. Return token + data user
    """
    # 1. Cari user berdasarkan email
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    # 2. Cek user ada dan password cocok
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah.",
        )

    # 3. Cek user masih aktif
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun Anda telah dinonaktifkan. Hubungi administrator.",
        )

    # 4. Ambil info role untuk disertakan di token
    result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = result.scalar_one_or_none()

    # 5. Buat JWT token
    # Payload token berisi minimal data yang dibutuhkan untuk autentikasi
    token_data = {
        "sub": str(user.id),          # subject = user id
        "email": user.email,
        "role": role.kode_role if role else "",
        "nama": user.nama,
    }
    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # 6. Update last_login
    user.last_login = datetime.now(timezone.utc)
    db.add(user)

    # 7. Susun response
    role_info = RoleInfo(
        id=role.id,
        kode_role=role.kode_role,
        nama_role=role.nama_role,
    ) if role else None

    user_response = UserResponse(
        id=user.id,
        nama=user.nama,
        email=user.email,
        no_telepon=user.no_telepon,
        is_active=user.is_active,
        last_login=user.last_login,
        created_at=user.created_at,
        role=role_info,
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in_seconds,
        user=user_response,
    )


async def get_me(user: User, db: AsyncSession) -> dict:
    """
    Ambil data user yang sedang login beserta info role-nya.
    """
    result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = result.scalar_one_or_none()

    role_info = RoleInfo(
        id=role.id,
        kode_role=role.kode_role,
        nama_role=role.nama_role,
    ) if role else None

    return {
        "user": UserResponse(
            id=user.id,
            nama=user.nama,
            email=user.email,
            no_telepon=user.no_telepon,
            is_active=user.is_active,
            last_login=user.last_login,
            created_at=user.created_at,
            role=role_info,
        )
    }


async def change_password(
    user: User,
    password_lama: str,
    password_baru: str,
    password_baru_konfirmasi: str,
    db: AsyncSession,
) -> dict:
    """Ganti password user yang sedang login."""

    # Validasi password lama
    if not verify_password(password_lama, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password lama tidak sesuai.",
        )

    # Validasi konfirmasi password baru
    if password_baru != password_baru_konfirmasi:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Konfirmasi password baru tidak cocok.",
        )

    # Minimal 8 karakter
    if len(password_baru) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password baru minimal 8 karakter.",
        )

    user.password_hash = hash_password(password_baru)
    user.updated_at = datetime.now(timezone.utc)
    db.add(user)
    await db.commit()

    return {"message": "Password berhasil diubah."}

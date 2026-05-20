"""
Dependencies FastAPI yang dipakai di endpoint dengan Depends().
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency: pastikan request sudah login dengan token valid.
    Return User object dari DB.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token tidak valid atau sudah kedaluwarsa. Silakan login ulang.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User tidak ditemukan atau sudah dinonaktifkan.",
        )

    return user


def require_roles(*allowed_roles: str):
    """
    Dependency factory: batasi akses endpoint hanya untuk role tertentu.

    Kode role dibaca dari JWT payload field "role" — tidak perlu query DB lagi.

    Cara pakai:
        async def my_endpoint(
            current_user = Depends(require_roles("qc", "superadmin"))
        ):
    """
    async def _check_role(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau sudah kedaluwarsa. Silakan login ulang.",
            headers={"WWW-Authenticate": "Bearer"},
        )

        token = credentials.credentials
        payload = decode_access_token(token)
        if payload is None:
            raise credentials_exception

        user_id: str = payload.get("sub")
        kode_role: str = payload.get("role", "")

        if not user_id:
            raise credentials_exception

        # Cek apakah role ada di daftar yang diizinkan
        if kode_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Akses ditolak. Fitur ini hanya untuk: {', '.join(allowed_roles)}.",
            )

        # Ambil user dari DB
        result = await db.execute(
            select(User).where(User.id == user_id, User.is_active == True)
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User tidak ditemukan atau sudah dinonaktifkan.",
            )

        return user

    return _check_role

async def get_kode_role(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """
    Dependency: ambil kode_role dari JWT payload.
    Tidak query DB — hanya decode token.
    Dipakai bersama get_current_user di router baru.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token tidak valid atau sudah kedaluwarsa. Silakan login ulang.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    return payload.get("role", "")

async def get_current_user_with_role(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> tuple:
    """
    Return (user, kode_role) — dipakai di endpoint yang filter data by role
    tapi tidak membatasi akses.

    Cara pakai:
        async def list_fkp(auth = Depends(get_current_user_with_role)):
            user, kode_role = auth
            if kode_role == "distributor":
                # tampilkan hanya FKP miliknya
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token tidak valid atau sudah kedaluwarsa. Silakan login ulang.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    kode_role: str = payload.get("role", "")

    if not user_id:
        raise credentials_exception

    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User tidak ditemukan atau sudah dinonaktifkan.",
        )

    return user, kode_role

"""
Auth Endpoints:
  POST   /api/auth/login           → Login, dapat token
  GET    /api/auth/me              → Data user yang sedang login
  POST   /api/auth/logout          → Logout (client hapus token)
  POST   /api/auth/change-password → Ganti password
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse
from app.schemas.user import PasswordChange
from app.services import auth_service
from app.schemas.outlet_register import OutletRegisterRequest, OutletRegisterResponse
from app.services.outlet_register_service import register_outlet as register_outlet_service

router = APIRouter()


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login",
    description="Login dengan email dan password. Mengembalikan JWT access token.",
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.login(request, db)


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Data user yang sedang login",
    description="Mengembalikan data lengkap user beserta role-nya. Butuh token.",
)
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.get_me(current_user, db)


@router.post(
    "/logout",
    summary="Logout",
    description=(
        "Logout dari sistem. "
        "Karena JWT adalah stateless, server tidak menyimpan token. "
        "Client (frontend) cukup hapus token dari memory/storage."
    ),
)
async def logout(
    current_user: User = Depends(get_current_user),
):
    # JWT stateless — tidak ada session yang perlu dihapus di server.
    # Frontend yang bertanggung jawab menghapus token dari storage-nya.
    return {
        "message": f"Sampai jumpa, {current_user.nama}! Token telah diinvalidasi di sisi client."
    }


@router.post(
    "/change-password",
    summary="Ganti password",
    description="Ganti password user yang sedang login.",
)
async def change_password(
    request: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.change_password(
        user=current_user,
        password_lama=request.password_lama,
        password_baru=request.password_baru,
        password_baru_konfirmasi=request.password_baru_konfirmasi,
        db=db,
    )

@router.post(
    "/register/outlet",
    response_model=OutletRegisterResponse,
    status_code=201,
    summary="Registrasi akun outlet baru",
    description=(
        "Endpoint publik (tidak butuh token). "
        "Outlet baru akan berstatus 'pending' hingga diapprove oleh admin atau distributor."
    ),
)
async def register_outlet(
    payload: OutletRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await register_outlet_service(payload, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
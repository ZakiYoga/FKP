"""
Auth Endpoints:
  POST   /api/auth/login           → Login, dapat token
  GET    /api/auth/me              → Data user yang sedang login
  POST   /api/auth/logout          → Logout (client hapus token)
  POST   /api/auth/change-password → Ganti password
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest, LoginResponse, MeResponse,
    ChangeEmailRequest, ForgotPasswordRequest, MessageResponse,
    ResendVerificationPublicRequest, ResetPasswordRequest, VerifyEmailRequest,
)
from app.schemas.user import PasswordChange
from app.schemas.outlet_register import OutletRegisterRequest, OutletRegisterResponse
from app.services import auth_service, account_security_service as account_svc
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
        "message": f"Sampai jumpa, {current_user.full_name}! Token telah diinvalidasi di sisi client."
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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await register_outlet_service(payload, db, background_tasks)
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

@router.post("/email/send-verification", response_model=MessageResponse)
async def send_verification_email(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Kirim ulang verifikasi untuk email akun yang sedang login."""
    await account_svc.request_email_verification(current_user, db, background_tasks)
    return MessageResponse(message="Tautan verifikasi telah dikirim ke email Anda.")


@router.post("/email/verify", response_model=MessageResponse)
async def verify_email(body: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    """PUBLIK — hanya butuh token dari tautan email."""
    return MessageResponse(**await account_svc.verify_email(body.token, db))


@router.post("/email/resend-verification", response_model=MessageResponse)
async def resend_verification_public(
    body: ResendVerificationPublicRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """PUBLIK — untuk user yang belum bisa login (mis. outlet pending)."""
    return MessageResponse(
        **await account_svc.resend_verification_public(body.email, db, background_tasks)
    )


@router.post("/email/change", response_model=MessageResponse)
async def change_email(
    body: ChangeEmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return MessageResponse(
        **await account_svc.change_email(
            current_user, body.email_baru, body.password, db, background_tasks
        )
    )


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """PUBLIK — respons selalu sama (anti user enumeration)."""
    return MessageResponse(
        **await account_svc.forgot_password(body.email, db, background_tasks)
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """PUBLIK — token dari tautan email."""
    return MessageResponse(
        **await account_svc.reset_password(
            body.token, body.password_baru, body.password_baru_konfirmasi, db, background_tasks
        )
    )
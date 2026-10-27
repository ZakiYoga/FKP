"""
Schemas untuk Auth endpoint.

Schemas = bentuk data yang masuk (request) dan keluar (response) dari API.
Berbeda dari Model (yang merepresentasikan tabel DB).
"""
from typing import Optional
import uuid
from pydantic import BaseModel, Field
from datetime import datetime

from app.schemas.types import NormalizedEmail


# ─── REQUEST schemas (data yang dikirim user ke server) ──────────────────────

class LoginRequest(BaseModel):
    """Body request untuk POST /api/auth/login"""
    email: NormalizedEmail
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "superadmin@saktipangan.co.id",
                "password": "12345678"
            }
        }


class ForgotPasswordRequest(BaseModel):
    """Body POST /api/auth/forgot-password"""
    email: NormalizedEmail


class ResetPasswordRequest(BaseModel):
    """Body POST /api/auth/reset-password (token dari tautan email)"""
    token: str = Field(min_length=20, max_length=200)
    password_baru: str
    password_baru_konfirmasi: str


class VerifyEmailRequest(BaseModel):
    """Body POST /api/auth/email/verify (token dari tautan email)"""
    token: str = Field(min_length=20, max_length=200)


class ResendVerificationPublicRequest(BaseModel):
    """Body POST /api/auth/email/resend-verification (publik)"""
    email: NormalizedEmail


class ChangeEmailRequest(BaseModel):
    """Body POST /api/auth/email/change"""
    email_baru: NormalizedEmail
    password: str   # password saat ini, untuk konfirmasi


# ─── RESPONSE schemas (data yang dikembalikan server ke user) ─────────────────

class MessageResponse(BaseModel):
    message: str


class RoleInfo(BaseModel):
    """Info role yang disertakan dalam response user"""
    id: uuid.UUID
    kode_role: str
    nama_role: str

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """
    Data user yang aman dikembalikan ke frontend.
    TIDAK menyertakan password_hash!
    """
    id: uuid.UUID
    first_name: str
    last_name: Optional[str] = None
    full_name: str
    gender: Optional[str] = None
    avatar_path: Optional[str] = None
    email: str
    no_telepon: str | None
    is_active: bool
    last_login: datetime | None
    created_at: datetime
    email_verified_at: datetime | None = None   # NULL = belum terverifikasi
    pending_email: str | None = None            # email baru yang menunggu verifikasi
    role: RoleInfo | None = None

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Response dari POST /api/auth/login"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int          # detik sampai expired
    user: UserResponse


class MeResponse(BaseModel):
    """Response dari GET /api/auth/me"""
    user: UserResponse
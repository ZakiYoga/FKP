"""
Schemas untuk Auth endpoint.

Schemas = bentuk data yang masuk (request) dan keluar (response) dari API.
Berbeda dari Model (yang merepresentasikan tabel DB).
"""
import uuid
from pydantic import BaseModel, EmailStr
from datetime import datetime


# ─── REQUEST schemas (data yang dikirim user ke server) ──────────────────────

class LoginRequest(BaseModel):
    """Body request untuk POST /api/auth/login"""
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "superadmin@saktipangan.co.id",
                "password": "12345678"
            }
        }


# ─── RESPONSE schemas (data yang dikembalikan server ke user) ─────────────────

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
    nama: str
    email: str
    no_telepon: str | None
    is_active: bool
    last_login: datetime | None
    created_at: datetime
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

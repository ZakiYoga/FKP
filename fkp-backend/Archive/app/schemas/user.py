import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserCreate(BaseModel):
    """Schema untuk membuat user baru (oleh SuperAdmin)"""
    role_id: uuid.UUID
    nama: str
    email: EmailStr
    password: str
    no_telepon: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "role_id": "uuid-role-disini",
                "nama": "Budi Santoso",
                "email": "budi@saktifood.com",
                "password": "Password123!",
                "no_telepon": "08123456789"
            }
        }


class UserUpdate(BaseModel):
    """Schema untuk update data user"""
    nama: Optional[str] = None
    no_telepon: Optional[str] = None
    is_active: Optional[bool] = None
    role_id: Optional[uuid.UUID] = None


class PasswordChange(BaseModel):
    """Schema untuk ganti password"""
    password_lama: str
    password_baru: str
    password_baru_konfirmasi: str


class UserResponse(BaseModel):
    """
    Response data user (tanpa password).

    [TIDAK ADA PERUBAHAN dari versi awal — dikonfirmasi tetap benar]
    is_active di sini murni status administratif akun (dinonaktifkan admin
    atau tidak). Tidak perlu field tambahan untuk disambiguasi dengan status
    approval outlet, karena status approval outlet sepenuhnya hidup di
    Outlet.status (per-outlet), bukan di User.is_active (per-user) — dan
    keduanya memang TIDAK PERLU disatukan, mengingat 1 user bisa punya
    beberapa outlet dengan status berbeda-beda.
    """
    id: uuid.UUID
    nama: str
    email: str
    no_telepon: Optional[str] = None
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    role_id: uuid.UUID

    class Config:
        from_attributes = True
        
class UserBriefResponse(BaseModel):
    id: uuid.UUID
    nama: str
    email: str
    no_telepon: Optional[str] = None

    class Config:
        from_attributes = True
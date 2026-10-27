import uuid
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

from app.schemas.types import NormalizedEmail

Gender = Literal["male", "female"]


class UserCreate(BaseModel):
    """Schema untuk membuat user baru (oleh SuperAdmin)"""
    role_id: uuid.UUID
    first_name: str = Field(min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    gender: Optional[Gender] = None
    email: NormalizedEmail
    password: str
    no_telepon: Optional[str] = None
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        byte_length = len(value.encode("utf-8"))

        if byte_length < 8:
            raise ValueError("Password minimal 8 bytes")

        if byte_length > 72:
            raise ValueError("Password maksimal 72 bytes")

        return value
    
    class Config:
        json_schema_extra = {
            "example": {
                "role_id": "uuid-role-disini",
                "first_name": "Budi",
                "last_name": "Santoso",
                "gender": "male",
                "email": "budi@saktipangan.co.id",
                "password": "12345678",
                "no_telepon": "08123456789"
            }
        }


class UserUpdate(BaseModel):
    """Schema untuk update data user"""
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    gender: Optional[Gender] = None
    no_telepon: Optional[str] = None
    is_active: Optional[bool] = None
    role_id: Optional[uuid.UUID] = None

class UserSelfUpdate(BaseModel):
    """Schema untuk user mengubah profilnya sendiri (tanpa role_id & is_active)"""
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    gender: Optional[Gender] = None
    no_telepon: Optional[str] = Field(default=None, max_length=20)

class PasswordChange(BaseModel):
    """Schema untuk ganti password"""
    password_lama: str
    password_baru: str
    password_baru_konfirmasi: str

class AdminResetPassword(BaseModel):
    """Body POST /api/users/{id}/reset-password (reset oleh admin)"""
    password_baru: str
    password_baru_konfirmasi: str

class UserResponse(BaseModel):
    """Response data user (tanpa password). is_active = status administratif akun."""
    id: uuid.UUID
    role_id: uuid.UUID
    first_name: str
    last_name: Optional[str] = None
    full_name: str
    gender: Optional[str] = None
    avatar_path: Optional[str] = None
    email: str
    no_telepon: Optional[str] = None
    is_active: bool
    email_verified_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserBriefResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: Optional[str] = None
    full_name: str
    email: str
    no_telepon: Optional[str] = None

    class Config:
        from_attributes = True


# ─── PAGINATION ───────────────────────────────────────────────────────────────

class UserListPage(BaseModel):
    """Response berpagination untuk GET /api/users/page."""
    items: List[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
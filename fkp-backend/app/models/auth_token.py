import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Index, Uuid
from sqlmodel import SQLModel, Field

PURPOSE_VERIFY_EMAIL = "verify_email"
PURPOSE_RESET_PASSWORD = "reset_password"


class AuthToken(SQLModel, table=True):
    """
    Token sekali pakai untuk verifikasi email dan reset password.
    Yang disimpan adalah HASH token (SHA-256), bukan token mentahnya.

    target_email:
      - verify_email   : email yang diverifikasi (bisa email baru saat ganti email)
      - reset_password : alamat tujuan pengiriman; saat dipakai harus sama dengan
                         users.email (kalau email sudah berganti, token tidak sah)

    purpose disimpan sebagai string biasa (bukan enum DB) agar penambahan
    jenis token di masa depan tidak butuh migrasi enum.
    """
    __tablename__ = "auth_tokens"
    __table_args__ = (
        Index("ix_auth_tokens_user_purpose_created", "user_id", "purpose", "created_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # sa_column dipakai karena butuh ON DELETE CASCADE (hapus user -> token ikut terhapus)
    user_id: uuid.UUID = Field(
        sa_column=Column(
            Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        )
    )
    purpose: str = Field(max_length=30)
    token_hash: str = Field(max_length=64, unique=True, index=True)
    target_email: str = Field(max_length=150)
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    used_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
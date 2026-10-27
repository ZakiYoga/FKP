"""
Token sekali pakai untuk verifikasi email & reset password.
Yang disimpan di DB hanya HASH SHA-256; token mentah hanya ada di tautan email.
"""
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.core.security import generate_urlsafe_token, hash_token, normalize_email
from app.models.auth_token import AuthToken, PURPOSE_VERIFY_EMAIL
from app.models.user import User

INVALID_TOKEN_DETAIL = "Tautan tidak valid atau sudah kedaluwarsa. Silakan minta tautan baru."


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def cooldown_remaining(db: AsyncSession, user_id, purpose: str) -> int:
    """Sisa detik cooldown pengiriman ulang (0 = boleh kirim)."""
    result = await db.execute(
        select(AuthToken.created_at)
        .where(AuthToken.user_id == user_id, AuthToken.purpose == purpose)
        .order_by(AuthToken.created_at.desc())
        .limit(1)
    )
    last = result.scalar_one_or_none()
    if last is None:
        return 0
    elapsed = (_now() - last).total_seconds()
    return max(0, math.ceil(settings.AUTH_EMAIL_RESEND_COOLDOWN_SECONDS - elapsed))


async def invalidate_tokens(db: AsyncSession, user_id, purpose: str) -> None:
    """Tandai semua token aktif (belum dipakai) untuk user+purpose sebagai terpakai."""
    await db.execute(
        update(AuthToken)
        .where(
            AuthToken.user_id == user_id,
            AuthToken.purpose == purpose,
            AuthToken.used_at.is_(None),
        )
        .values(used_at=_now())
    )


async def create_token(
    db: AsyncSession,
    user: User,
    purpose: str,
    target_email: str,
    expires_in: timedelta,
) -> str:
    """
    Buat token baru dan batalkan token lama (purpose sama).
    Return token MENTAH (untuk dikirim lewat email). Caller yang commit.
    """
    await invalidate_tokens(db, user.id, purpose)
    raw = generate_urlsafe_token()
    db.add(
        AuthToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_token(raw),
            target_email=normalize_email(target_email),
            expires_at=_now() + expires_in,
        )
    )
    await db.flush()
    return raw


async def consume_token(db: AsyncSession, raw_token: str, purpose: str) -> AuthToken:
    """
    Validasi token lalu tandai terpakai. Caller yang commit.
    Pesan error SENGAJA seragam (tidak membedakan salah/kedaluwarsa/terpakai).
    Baris dikunci (FOR UPDATE) supaya dua request bersamaan tidak bisa
    memakai token yang sama.
    """
    result = await db.execute(
        select(AuthToken)
        .where(AuthToken.token_hash == hash_token(raw_token), AuthToken.purpose == purpose)
        .with_for_update()
    )
    tok = result.scalar_one_or_none()
    now = _now()
    if tok is None or tok.used_at is not None or tok.expires_at <= now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, INVALID_TOKEN_DETAIL)
    tok.used_at = now
    db.add(tok)
    return tok


async def get_pending_email(db: AsyncSession, user: User) -> Optional[str]:
    """Email baru yang masih menunggu verifikasi (untuk ditampilkan di profil)."""
    result = await db.execute(
        select(AuthToken.target_email)
        .where(
            AuthToken.user_id == user.id,
            AuthToken.purpose == PURPOSE_VERIFY_EMAIL,
            AuthToken.used_at.is_(None),
            AuthToken.expires_at > _now(),
        )
        .order_by(AuthToken.created_at.desc())
        .limit(1)
    )
    target = result.scalar_one_or_none()
    if target and normalize_email(target) != normalize_email(user.email):
        return target
    return None
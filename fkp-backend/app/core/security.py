import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

# ─── Password hashing (bcrypt) ────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash password plaintext → bcrypt hash"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifikasi password plaintext vs hash yang tersimpan di DB"""
    return pwd_context.verify(plain_password, hashed_password)


# ─── Email & token acak ───────────────────────────────────────────────────────
def normalize_email(email: str) -> str:
    """Strip + lowercase. Pakai di SEMUA tempat yang membuat/mencari email."""
    return email.strip().lower()


def generate_urlsafe_token(nbytes: int = 32) -> str:
    """Token acak untuk tautan email (±43 karakter)."""
    return secrets.token_urlsafe(nbytes)


def hash_token(raw_token: str) -> str:
    """SHA-256 hex. Yang disimpan di DB adalah hash ini, bukan token mentah."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


# ─── JWT Token ────────────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Buat JWT token.
    data harus berisi: {"sub": user_id, "role": kode_role, "email": email}
    Claim "iat" (waktu terbit) ditambahkan otomatis; dipakai deps.py untuk
    menolak token yang terbit sebelum password terakhir direset.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode JWT token. Return None jika token invalid/expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
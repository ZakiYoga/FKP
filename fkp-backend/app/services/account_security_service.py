"""
Account Security Service — alur verifikasi email, ganti email,
lupa password, dan reset password.

Aturan penting:
- Fungsi kirim_email_* dijadwalkan lewat BackgroundTasks dan TIDAK boleh
  memakai sesi DB. Semua nilai (nama, email, tautan) diambil ke variabel
  SEBELUM add_task, karena sesi sudah ditutup saat task berjalan.
- Respons forgot_password / resend_verification_public SELALU sama, apa pun
  kondisi emailnya (anti user-enumeration).
"""
import logging
from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.core.security import hash_password, normalize_email, verify_password
from app.models.auth_token import PURPOSE_RESET_PASSWORD, PURPOSE_VERIFY_EMAIL
from app.models.outlet import Outlet
from app.models.user import User
from app.services.authz_helpers import is_superadmin
from app.services import auth_token_service as tokens
from app.services.auth_service import validate_password_baru
from app.services.email_service import (
    kirim_email_notifikasi_ganti_email,
    kirim_email_password_diubah,
    kirim_email_reset_password,
    kirim_email_verifikasi,
)
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

GENERIC_FORGOT_MESSAGE = (
    "Jika email terdaftar dan sudah terverifikasi, tautan reset password telah dikirim. "
    "Periksa kotak masuk atau folder spam."
)
GENERIC_RESEND_MESSAGE = (
    "Jika email terdaftar dan belum terverifikasi, tautan verifikasi telah dikirim."
)


def _frontend_url(path: str, token: str) -> str:
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}{path}?token={token}"


async def _email_taken(db: AsyncSession, email: str, exclude_user_id=None) -> bool:
    q = select(User.id).where(func.lower(User.email) == normalize_email(email))
    if exclude_user_id is not None:
        q = q.where(User.id != exclude_user_id)
    result = await db.execute(q.limit(1))
    return result.first() is not None


# ─── Verifikasi email ────────────────────────────────────────────────────────

async def request_email_verification(
    user: User,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    *,
    target_email: str | None = None,
    enforce_cooldown: bool = True,
) -> None:
    """
    Buat token verifikasi + jadwalkan pengiriman email.
    - target_email None  -> verifikasi email akun saat ini
    - target_email diisi -> verifikasi email BARU (ganti email)
    """
    current = normalize_email(user.email)
    target = normalize_email(target_email or user.email)
    is_change = target != current

    if not is_change and user.email_verified_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email Anda sudah terverifikasi.")

    if enforce_cooldown:
        sisa = await tokens.cooldown_remaining(db, user.id, PURPOSE_VERIFY_EMAIL)
        if sisa > 0:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Mohon tunggu {sisa} detik sebelum meminta tautan baru.",
            )

    full_name = user.full_name           # simpan sebelum commit
    hours = settings.VERIFY_EMAIL_TOKEN_EXPIRE_HOURS
    raw = await tokens.create_token(
        db, user, PURPOSE_VERIFY_EMAIL, target, timedelta(hours=hours)
    )
    await db.commit()

    link = _frontend_url("/verify-email", raw)
    background_tasks.add_task(
        kirim_email_verifikasi, target, full_name, link, hours, is_change
    )


async def verify_email(raw_token: str, db: AsyncSession) -> dict:
    """Endpoint publik: hanya butuh token (user bisa saja belum bisa login)."""
    tok = await tokens.consume_token(db, raw_token, PURPOSE_VERIFY_EMAIL)
    user = await db.get(User, tok.user_id)
    if user is None or not user.is_active:
        await db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, tokens.INVALID_TOKEN_DETAIL)

    now = datetime.now(timezone.utc)
    target = normalize_email(tok.target_email)
    email_lama = normalize_email(user.email)

    if target != email_lama:
        # Alur ganti email: cek lagi karena bisa saja sudah dipakai akun lain
        if await _email_taken(db, target, exclude_user_id=user.id):
            await db.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Email tersebut sudah digunakan oleh akun lain."
            )
        # Outlet.email adalah salinan email akun: ikut diperbarui, tetapi hanya
        # outlet milik user ini yang emailnya MASIH sama dengan email lama akun.
        await db.execute(
            update(Outlet)
            .where(
                Outlet.pic_user_id == user.id,
                func.lower(Outlet.email) == email_lama,
            )
            .values(email=target, updated_at=now)
        )
        user.email = target

    user.email_verified_at = now
    user.updated_at = now
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Email tersebut sudah digunakan oleh akun lain."
        )
    return {"message": "Email berhasil diverifikasi."}


async def resend_verification_public(
    email: str, db: AsyncSession, background_tasks: BackgroundTasks
) -> dict:
    """
    Untuk user yang belum bisa login (mis. outlet masih pending) tapi perlu
    kirim ulang verifikasi. Respons selalu generik.
    """
    email = normalize_email(email)
    result = await db.execute(select(User).where(func.lower(User.email) == email))
    user = result.scalar_one_or_none()
    if (
        user
        and user.is_active
        and user.email_verified_at is None
        and await tokens.cooldown_remaining(db, user.id, PURPOSE_VERIFY_EMAIL) == 0
    ):
        await request_email_verification(user, db, background_tasks, enforce_cooldown=False)
    return {"message": GENERIC_RESEND_MESSAGE}


# ─── Ganti email (dari profil) ───────────────────────────────────────────────

async def change_email(
    user: User,
    email_baru: str,
    password: str,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
) -> dict:
    if not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password tidak sesuai.")

    email_baru = normalize_email(email_baru)
    if email_baru == normalize_email(user.email):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Email baru sama dengan email saat ini."
        )
    if await _email_taken(db, email_baru, exclude_user_id=user.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email tersebut sudah digunakan.")

    full_name, email_lama = user.full_name, user.email
    await request_email_verification(user, db, background_tasks, target_email=email_baru)

    # Notifikasi ke email LAMA (peringatan jika akun diambil alih)
    background_tasks.add_task(
        kirim_email_notifikasi_ganti_email, email_lama, full_name, email_baru
    )

    return {
        "message": (
            "Tautan konfirmasi telah dikirim ke email baru. "
            "Email akun Anda berubah setelah tautan tersebut diklik."
        )
    }


# ─── Lupa & reset password ───────────────────────────────────────────────────

async def forgot_password(
    email: str, db: AsyncSession, background_tasks: BackgroundTasks
) -> dict:
    """Respons SELALU sama, apa pun kondisi email-nya (anti user enumeration)."""
    email = normalize_email(email)
    result = await db.execute(select(User).where(func.lower(User.email) == email))
    user = result.scalar_one_or_none()

    if (
        user
        and user.is_active
        and user.email_verified_at is not None
        and await tokens.cooldown_remaining(db, user.id, PURPOSE_RESET_PASSWORD) == 0
    ):
        full_name, target = user.full_name, user.email
        minutes = settings.RESET_PASSWORD_TOKEN_EXPIRE_MINUTES
        raw = await tokens.create_token(
            db, user, PURPOSE_RESET_PASSWORD, target, timedelta(minutes=minutes)
        )
        await db.commit()
        link = _frontend_url("/reset-password", raw)
        background_tasks.add_task(
            kirim_email_reset_password, target, full_name, link, minutes
        )

    return {"message": GENERIC_FORGOT_MESSAGE}


async def reset_password(
    raw_token: str,
    password_baru: str,
    password_baru_konfirmasi: str,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
) -> dict:
    # Validasi password DULU, supaya salah ketik tidak menghabiskan token
    validate_password_baru(password_baru, password_baru_konfirmasi)

    tok = await tokens.consume_token(db, raw_token, PURPOSE_RESET_PASSWORD)
    user = await db.get(User, tok.user_id)
    if (
        user is None
        or not user.is_active
        or user.email_verified_at is None
        or normalize_email(user.email) != normalize_email(tok.target_email)
    ):
        await db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, tokens.INVALID_TOKEN_DETAIL)

    now = datetime.now(timezone.utc)
    full_name, email = user.full_name, user.email
    user.password_hash = hash_password(password_baru)
    user.password_changed_at = now          # dipakai deps.py (langkah 9) untuk mencabut JWT lama
    user.updated_at = now
    db.add(user)
    await tokens.invalidate_tokens(db, user.id, PURPOSE_RESET_PASSWORD)
    await db.commit()

    background_tasks.add_task(kirim_email_password_diubah, email, full_name)
    return {"message": "Password berhasil direset. Silakan login dengan password baru."}


# ─── Reset password oleh admin ───────────────────────────────────────────────

async def admin_reset_password(
    target_user_id,
    password_baru: str,
    password_baru_konfirmasi: str,
    actor: User,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Reset password user oleh admin. Jalur pemulihan untuk user yang tidak bisa
    memakai lupa password (mis. email salah / belum terverifikasi).

    - Hanya superadmin yang boleh mereset akun superadmin (mencegah eskalasi
      hak akses lewat role yang diberi permission ini).
    - Tidak boleh untuk akun sendiri (pakai fitur ganti password).
    - Semua sesi (JWT) lama user target dicabut lewat password_changed_at.
    - Tautan reset password aktif milik user target dibatalkan.
    - Email pemberitahuan hanya dikirim jika email user sudah terverifikasi.
    """
    validate_password_baru(password_baru, password_baru_konfirmasi)

    if target_user_id == actor.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Gunakan fitur ganti password untuk akun Anda sendiri.",
        )

    target = await db.get(User, target_user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User tidak ditemukan.")

    if await is_superadmin(target, db) and not await is_superadmin(actor, db):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Hanya superadmin yang dapat mereset password akun superadmin.",
        )

    now = datetime.now(timezone.utc)
    actor_id = actor.id
    full_name, email = target.full_name, target.email   # simpan sebelum commit
    kirim_notifikasi = target.email_verified_at is not None

    target.password_hash = hash_password(password_baru)
    target.password_changed_at = now        # mencabut JWT lama (deps.py)
    target.updated_at = now
    db.add(target)
    await tokens.invalidate_tokens(db, target.id, PURPOSE_RESET_PASSWORD)
    await db.commit()

    logger.info("[AUTH] Password user %s direset oleh admin %s", target_user_id, actor_id)

    if kirim_notifikasi:
        background_tasks.add_task(kirim_email_password_diubah, email, full_name)

    return {
        "message": (
            f"Password user '{full_name}' berhasil direset. "
            "Semua sesi login user tersebut telah dicabut."
        )
    }
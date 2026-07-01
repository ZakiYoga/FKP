"""
Auth Service — business logic untuk login, logout, dan manajemen token.
Dipisah dari endpoint agar mudah di-test dan dipakai ulang.

[REVISI] Model gate login untuk role 'outlet' diubah total:

  SEBELUM:
    - User.is_active di-set False saat outlet baru register, True saat approve.
    - Login mengambil SATU outlet (scalar_one_or_none) lalu cek status-nya.
    - Asumsi implisit: 1 user = 1 outlet. SALAH — dokumen section 2.3 eksplisit
      bilang 1 user outlet BOLEH pegang banyak outlet (asal distributor sama).
      Kalau user itu punya >1 outlet, scalar_one_or_none() akan melempar
      MultipleResultsFound, bukan None — ini bug laten yang belum ketahuan
      karena belum ada test case user dengan multi-outlet.

  SESUDAH (sesuai arahan):
    - User.is_active SELALU True untuk akun yang valid (tidak lagi dipakai
      sebagai proxy status approval outlet). is_active HANYA berarti
      "akun dinonaktifkan administratif" (admin suspend, dsb).
    - Login untuk role 'outlet' mengambil SEMUA outlet milik user
      (Outlet.pic_user_id == user.id), lalu mengizinkan login jika MINIMAL
      SATU outlet berstatus 'aktif'. Kalau tidak ada satupun yang aktif
      (semua pending/ditolak/nonaktif), login ditolak dengan pesan yang
      mencerminkan kondisi paling relevan.
"""
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import verify_password, create_access_token, hash_password
from app.models.user import User
from app.models.role import Role
from app.models.outlet import Outlet
from app.schemas.auth import LoginRequest, LoginResponse, UserResponse, RoleInfo


async def login(request: LoginRequest, db: AsyncSession) -> LoginResponse:
    """
    Proses login:
    1. Cari user by email
    2. Verifikasi password
    3. Cek user aktif (is_active) — murni status administratif akun
    4. Ambil info role
    5. Khusus role outlet: cek SEMUA outlet miliknya, izinkan jika minimal
       satu berstatus 'aktif'
    6. Buat JWT token
    7. Update last_login
    8. Return token + data user
    """

    # 1. Cari user by email
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    # 2. Cek user ada dan password cocok
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah.",
        )

    # 3. Cek user masih aktif secara administratif
    #    [REVISI] is_active TIDAK LAGI dipakai untuk merepresentasikan status
    #    approval outlet. Outlet pending/ditolak tidak membuat is_active=False;
    #    pengecekan itu sepenuhnya ada di langkah 5.
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun Anda telah dinonaktifkan. Hubungi administrator.",
        )

    # 4. Ambil info role
    result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = result.scalar_one_or_none()

    # 5. Khusus role outlet: cek SEMUA outlet milik user, izinkan login jika
    #    minimal satu berstatus 'aktif'. Ini menggantikan logic lama yang
    #    cuma ambil satu outlet dan akan rusak untuk user multi-outlet.
    if role and role.kode_role == "outlet":
        outlet_result = await db.execute(
            select(Outlet).where(Outlet.pic_user_id == user.id)
        )
        outlets = outlet_result.scalars().all()

        if not outlets:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Data outlet tidak ditemukan.",
            )

        ada_yang_aktif = any(o.status == "aktif" for o in outlets)

        if not ada_yang_aktif:
            # Tidak ada satupun outlet aktif — tentukan pesan paling relevan.
            # Prioritas pesan: pending > ditolak > nonaktif/lainnya, supaya
            # user tahu tindakan apa yang ditunggu/diperlukan.
            statuses = {o.status for o in outlets}

            if "pending" in statuses:
                detail = "Outlet Anda masih menunggu verifikasi dari admin."
            elif statuses == {"ditolak"}:
                detail = "Registrasi outlet Anda ditolak. Hubungi administrator."
            else:
                detail = "Outlet Anda tidak aktif. Hubungi administrator."

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )
        # Jika ada_yang_aktif True -> lanjut, meskipun ada outlet lain yang
        # pending/ditolak/nonaktif. Sesuai aturan: cukup SATU yang aktif.

    # 6. Buat JWT token — payload berisi minimal data yang dibutuhkan untuk autentikasi
    token_data = {
        "sub": str(user.id),          # subject = user id
        "email": user.email,
        "role": role.kode_role if role else "",
        "nama": user.nama,
    }
    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # 7. Update last_login
    user.last_login = datetime.now(timezone.utc)
    db.add(user)
    await db.commit()

    # 8. Susun response
    role_info = RoleInfo(
        id=role.id,
        kode_role=role.kode_role,
        nama_role=role.nama_role,
    ) if role else None

    user_response = UserResponse(
        id=user.id,
        nama=user.nama,
        email=user.email,
        no_telepon=user.no_telepon,
        is_active=user.is_active,
        last_login=user.last_login,
        created_at=user.created_at,
        role=role_info,
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in_seconds,
        user=user_response,
    )


async def get_me(user: User, db: AsyncSession) -> dict:
    """
    Ambil data user yang sedang login beserta info role-nya.
    """
    result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = result.scalar_one_or_none()

    role_info = RoleInfo(
        id=role.id,
        kode_role=role.kode_role,
        nama_role=role.nama_role,
    ) if role else None

    return {
        "user": UserResponse(
            id=user.id,
            nama=user.nama,
            email=user.email,
            no_telepon=user.no_telepon,
            is_active=user.is_active,
            last_login=user.last_login,
            created_at=user.created_at,
            role=role_info,
        )
    }


async def change_password(
    user: User,
    password_lama: str,
    password_baru: str,
    password_baru_konfirmasi: str,
    db: AsyncSession,
) -> dict:
    """Ganti password user yang sedang login."""

    # Validasi password lama
    if not verify_password(password_lama, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password lama tidak sesuai.",
        )

    # Validasi konfirmasi password baru
    if password_baru != password_baru_konfirmasi:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Konfirmasi password baru tidak cocok.",
        )

    # Minimal 8 karakter
    if len(password_baru) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password baru minimal 8 karakter.",
        )

    user.password_hash = hash_password(password_baru)
    user.updated_at = datetime.now(timezone.utc)
    db.add(user)
    await db.commit()

    return {"message": "Password berhasil diubah."}
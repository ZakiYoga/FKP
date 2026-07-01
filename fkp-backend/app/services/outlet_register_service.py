"""
Outlet Register Service — registrasi outlet publik + approval flow.

[REVISI] Keputusan is_active dibalik dari fix sebelumnya, atas pertimbangan
yang lebih tepat: User.is_active SELALU True untuk akun yang valid secara
administratif. is_active TIDAK dipakai sebagai proxy status approval outlet.
Gate "boleh login atau tidak" untuk role outlet sepenuhnya ditentukan oleh
status outlet (lihat auth_service.login()) — bukan oleh is_active.

Alasan: 1 user outlet boleh memiliki LEBIH DARI SATU outlet (asal distributor
sama, lihat dokumen section 2.3). Kalau is_active dipakai sebagai proxy status
approval, maka tidak ada cara merepresentasikan "user dengan 2 outlet: satu
aktif, satu masih pending" — is_active itu milik User, bukan per-Outlet.
Aturan yang benar: izinkan login jika minimal SATU outlet milik user statusnya
'aktif', terlepas dari status outlet lain miliknya. Itu hanya bisa dicek dari
tabel Outlet langsung, bukan dari User.is_active.

[FIX #3] Tidak lagi memakai string "superadmin" untuk cek superadmin.
  Memakai authz_helpers.is_superadmin() yang membaca Role.is_superadmin,
  sesuai dokumen section 3.7. String "superadmin" sebelumnya tidak akan
  pernah match jika kode_role sebenarnya "super_admin" di tabel roles.

[FIX #4] Validasi scope ditambahkan untuk sc_spv & apsm saat approve/reject,
  tidak hanya untuk distributor seperti sebelumnya. Sebelumnya sc_spv/apsm
  bisa approve/reject outlet milik distributor manapun, di luar scope
  mereka — sekarang dibatasi via authz_helpers.assert_distributor_in_scope().
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from passlib.context import CryptContext

from app.models.user import User
from app.models.outlet import Outlet
from app.models.role import Role
from app.models.distributor import Distributor, DistributorUser
from app.schemas.outlet_register import (
    OutletRegisterRequest, 
    OutletRegisterResponse,
    OutletRegistrationDetail,
    OutletRegistrationListResponse,
    OutletApproveRequest,
    OutletApproveResponse,
    OutletRejectRequest,
    OutletRejectResponse,
)
from app.services.authz_helpers import (
    is_superadmin,
    has_global_access,
    get_scoped_distributor_ids,
    assert_distributor_in_scope,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Role yang berhak mengelola registrasi outlet (selain superadmin, yang selalu
# dicek lewat is_superadmin()).
REGISTRATION_MANAGER_ROLES = ("admin_ho", "distributor", "sc_spv", "apsm")


async def _generate_kode_outlet(session: AsyncSession) -> str:
    """Generate kode outlet unik: OTL-YYYYMMDD-XXXX"""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"OTL-{today}-"

    result = await session.execute(
        select(Outlet).where(Outlet.kode_outlet.like(f"{prefix}%"))
    )
    existing = result.scalars().all()
    seq = str(len(existing) + 1).zfill(4)
    return f"{prefix}{seq}"

async def _get_outlet_or_404(outlet_id: uuid.UUID, session: AsyncSession) -> Outlet:
    result = await session.execute(select(Outlet).where(Outlet.id == outlet_id))
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise ValueError(f"Outlet dengan ID '{outlet_id}' tidak ditemukan")
    return outlet


# ─── REGISTRASI (PUBLIK) ─────────────────────────────────────────────────────

async def register_outlet(
    payload: OutletRegisterRequest,
    session: AsyncSession,
) -> OutletRegisterResponse:

    # 1. Cek email sudah terdaftar
    result = await session.execute(
        select(User).where(User.email == payload.email)
    )
    if result.scalar_one_or_none():
        raise ValueError("Email sudah terdaftar")

    # 2. Validasi distributor ada dan aktif
    result = await session.execute(
        select(Distributor).where(Distributor.id == payload.distributor_id)
    )
    distributor = result.scalar_one_or_none()
    if not distributor or distributor.status != "aktif":
        raise ValueError("Distributor tidak ditemukan atau tidak aktif")

    # 3. Ambil role "outlet"
    result = await session.execute(
        select(Role).where(Role.kode_role == "outlet")
    )
    role_outlet = result.scalar_one_or_none()
    if not role_outlet:
        raise RuntimeError("Role 'outlet' belum dikonfigurasi di sistem")

    # 4. Buat User — is_active=True. Status "menunggu approval" direpresentasikan
    #    SEPENUHNYA oleh Outlet.status="pending", bukan oleh User.is_active.
    #    Gate login ada di auth_service.login() yang mengecek status outlet,
    #    bukan di sini.
    new_user = User(
        role_id=role_outlet.id,
        nama=payload.pemilik_toko,
        email=payload.email,
        password_hash=pwd_context.hash(payload.password),
        no_telepon=payload.no_hp,
        is_active=True,
    )
    session.add(new_user)
    await session.flush()   # dapatkan new_user.id sebelum commit

    # 5. Generate kode & buat Outlet (status="pending")
    kode_outlet = await _generate_kode_outlet(session)
    new_outlet = Outlet(
        distributor_id=payload.distributor_id,
        kode_outlet=kode_outlet,
        nama_toko=payload.nama_toko,
        pemilik_toko=payload.pemilik_toko,
        tipe_toko=payload.tipe_toko,
        no_hp=payload.no_hp,
        email=payload.email,
        alamat_lengkap=payload.alamat_lengkap,
        kelurahan_id=payload.kelurahan_id,
        pic_user_id=new_user.id,
        status="pending",
    )
    session.add(new_outlet)
    await session.commit()
    await session.refresh(new_outlet)

    return OutletRegisterResponse(
        message="Registrasi berhasil. Menunggu verifikasi dari admin.",
        outlet_id=new_outlet.id,
        user_id=new_user.id,
        kode_outlet=new_outlet.kode_outlet,
    )
    
# ─── LIST PENDING REGISTRATIONS ──────────────────────────────────────────────
 
async def list_pending_registrations(
    session: AsyncSession,
    requesting_user: User,
    kode_role: str,
    distributor_id: uuid.UUID | None = None,
) -> OutletRegistrationListResponse:
    """
    Kembalikan daftar outlet dengan status 'pending'.
    - superadmin (flag) / admin_ho / qc / rsm / direktur : semua pending outlet
    - distributor : hanya pending outlet di distributornya
    - sc_spv      : hanya pending outlet di distributor yang dia kelola
    - apsm        : hanya pending outlet di distributor pada area yang dia PIC-i
    """
    query = select(Outlet).where(Outlet.status == "pending")

    # [FIX #3] Akses global lewat flag is_superadmin + daftar role HO terpusat,
    # bukan string "superadmin" yang rawan typo / mismatch dengan "super_admin".
    if await has_global_access(requesting_user, kode_role, session):
        pass  # akses penuh, tidak perlu filter distributor

    elif kode_role in ("distributor", "sc_spv", "apsm"):
        # [FIX #1 turunan] dist_ids sekarang dihitung lewat resolver terpusat
        # sehingga APSM ikut mendapat distributor tanpa SC_SPV (scoping via Area).
        dist_ids = await get_scoped_distributor_ids(requesting_user, kode_role, session)
        if not dist_ids:
            return OutletRegistrationListResponse(total=0, items=[])
        query = query.where(Outlet.distributor_id.in_(dist_ids))

    else:
        raise PermissionError(
            f"Role '{kode_role}' tidak diizinkan melihat daftar registrasi outlet."
        )
 
    # Filter opsional by distributor
    if distributor_id:
        query = query.where(Outlet.distributor_id == distributor_id)
 
    query = query.order_by(Outlet.created_at.desc())
    result = await session.execute(query)
    outlets = result.scalars().all()
 
    items = []
    for o in outlets:
        # Ambil email dari User terkait (pic_user_id)
        email = ""
        if o.pic_user_id:
            u_result = await session.execute(
                select(User.email).where(User.id == o.pic_user_id)
            )
            email = u_result.scalar_one_or_none() or (o.email or "")
        else:
            email = o.email or ""
 
        items.append(
            OutletRegistrationDetail(
                outlet_id=o.id,
                user_id=o.pic_user_id,
                kode_outlet=o.kode_outlet,
                nama_toko=o.nama_toko,
                pemilik_toko=o.pemilik_toko,
                tipe_toko=o.tipe_toko,
                no_hp=o.no_hp,
                email=email,
                alamat_lengkap=o.alamat_lengkap,
                distributor_id=o.distributor_id,
                status=o.status,
                created_at=o.created_at,
            )
        )
 
    return OutletRegistrationListResponse(total=len(items), items=items)
 
 
# ─── APPROVE REGISTRASI ──────────────────────────────────────────────────────
 
async def approve_registration(
    outlet_id: uuid.UUID,
    payload: OutletApproveRequest,
    session: AsyncSession,
    requesting_user: User,
    kode_role: str,
) -> OutletApproveResponse:
    """
    Setujui registrasi outlet pending.
    - Outlet.status → 'aktif'
    - User.is_active TIDAK diubah di sini — is_active sudah True sejak
      registrasi dan tidak merepresentasikan status approval outlet.
      Login untuk role outlet digerbang oleh status outlet itu sendiri
      (lihat auth_service.login()), bukan oleh User.is_active.
    """
    outlet = await _get_outlet_or_404(outlet_id, session)
 
    if outlet.status != "pending":
        raise ValueError(
            f"Outlet tidak dalam status 'pending' (status saat ini: '{outlet.status}'). "
            "Hanya outlet berstatus 'pending' yang bisa disetujui."
        )

    superadmin = await is_superadmin(requesting_user, session)

    # [FIX #3] cek role berbasis flag, bukan string "superadmin"
    if not superadmin and kode_role not in REGISTRATION_MANAGER_ROLES:
        raise PermissionError(f"Role '{kode_role}' tidak berhak menyetujui registrasi outlet.")

    # [FIX #4] Validasi scope untuk distributor, sc_spv, DAN apsm.
    # Sebelumnya hanya distributor yang divalidasi; sc_spv & apsm bisa approve
    # outlet milik distributor mana pun. Sekarang semua role non-global wajib
    # lolos assert_distributor_in_scope().
    if not superadmin and kode_role in ("distributor", "sc_spv", "apsm"):
        try:
            await assert_distributor_in_scope(
                outlet.distributor_id,
                requesting_user,
                kode_role,
                session,
                forbidden_message="Anda tidak berhak menyetujui outlet di luar scope Anda.",
            )
        except PermissionError:
            raise PermissionError("Anda tidak berhak menyetujui outlet di luar scope Anda.")

    # Aktifkan outlet. User pemiliknya TIDAK disentuh — is_active-nya
    # sudah True sejak awal dan tetap True di sini.
    outlet.status = "aktif"
    outlet.updated_at = datetime.now(timezone.utc)
    session.add(outlet)

    await session.commit()
    await session.refresh(outlet)

    # Ambil is_active user saat ini untuk response (murni informatif,
    # bukan hasil perubahan oleh fungsi ini).
    user_is_active = True
    if outlet.pic_user_id:
        user_result = await session.execute(
            select(User.is_active).where(User.id == outlet.pic_user_id)
        )
        user_is_active = user_result.scalar_one_or_none()
        if user_is_active is None:
            user_is_active = True

    return OutletApproveResponse(
        message=f"Registrasi outlet '{outlet.nama_toko}' telah disetujui.",
        outlet_id=outlet.id,
        user_id=outlet.pic_user_id,
        kode_outlet=outlet.kode_outlet,
        status=outlet.status,
        user_is_active=user_is_active,
    )
 
 
# ─── REJECT REGISTRASI ───────────────────────────────────────────────────────
 
async def reject_registration(
    outlet_id: uuid.UUID,
    payload: OutletRejectRequest,
    session: AsyncSession,
    requesting_user: User,
    kode_role: str,
) -> OutletRejectResponse:
    """
    Tolak registrasi outlet pending.
    - Outlet.status → 'ditolak'
    - User.is_active TIDAK diubah (tetap True) — yang mencegah user ini
      login bukan is_active, melainkan tidak ada satupun outlet miliknya
      yang berstatus 'aktif' (lihat auth_service.login()). Jika user yang
      sama punya outlet LAIN yang sudah aktif, dia tetap bisa login —
      ini disengaja, sesuai aturan "minimal satu outlet aktif = boleh login".
    """
    outlet = await _get_outlet_or_404(outlet_id, session)
 
    if outlet.status != "pending":
        raise ValueError(
            f"Outlet tidak dalam status 'pending' (status saat ini: '{outlet.status}'). "
            "Hanya outlet berstatus 'pending' yang bisa ditolak."
        )

    superadmin = await is_superadmin(requesting_user, session)

    if not superadmin and kode_role not in REGISTRATION_MANAGER_ROLES:
        raise PermissionError(f"Role '{kode_role}' tidak berhak menolak registrasi outlet.")

    # [FIX #4] Validasi scope juga untuk sc_spv & apsm, sama seperti approve.
    if not superadmin and kode_role in ("distributor", "sc_spv", "apsm"):
        try:
            await assert_distributor_in_scope(
                outlet.distributor_id,
                requesting_user,
                kode_role,
                session,
                forbidden_message="Anda tidak berhak menolak outlet di luar scope Anda.",
            )
        except PermissionError:
            raise PermissionError("Anda tidak berhak menolak outlet di luar scope Anda.")

    # Tandai outlet sebagai ditolak
    outlet.status = "ditolak"
    outlet.updated_at = datetime.now(timezone.utc)
    session.add(outlet)
 
    await session.commit()
    await session.refresh(outlet)
 
    return OutletRejectResponse(
        message=f"Registrasi outlet '{outlet.nama_toko}' ditolak. Alasan: {payload.alasan}",
        outlet_id=outlet.id,
        status=outlet.status,
    )
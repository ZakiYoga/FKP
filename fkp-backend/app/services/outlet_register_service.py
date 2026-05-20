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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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

    # 4. Buat User (is_active=False, tunggu approval)
    new_user = User(
        role_id=role_outlet.id,
        nama=payload.pemilik_toko,
        email=payload.email,
        password_hash=pwd_context.hash(payload.password),
        no_telepon=payload.no_hp,
        is_active=True, # Bisa langsung aktif, karena aksesnya dibatasi oleh status outlet
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
    - superadmin / admin_ho : semua pending outlet
    - distributor           : hanya pending outlet di bawah distributornya
    - sc_spv / apsm         : akses melalui hierarki (opsional, bisa dikembangkan)
    """
    query = select(Outlet).where(Outlet.status == "pending")
 
    # Batasi berdasarkan role
    if kode_role in ("superadmin", "admin_ho", "qc", "rsm", "direktur"):
        pass  # akses penuh
 
    elif kode_role == "distributor":
        du_result = await session.execute(
            select(DistributorUser.distributor_id).where(
                DistributorUser.user_id == requesting_user.id
            )
        )
        dist_ids = du_result.scalars().all()
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
    - Outlet.status  → 'aktif'
    - User.is_active → True
    """
    outlet = await _get_outlet_or_404(outlet_id, session)
 
    if outlet.status != "pending":
        raise ValueError(
            f"Outlet tidak dalam status 'pending' (status saat ini: '{outlet.status}'). "
            "Hanya outlet berstatus 'pending' yang bisa disetujui."
        )
 
    # Validasi hak akses berdasarkan role
    if kode_role not in ("superadmin", "admin_ho", "distributor", "sc_spv", "apsm"):
        raise PermissionError(f"Role '{kode_role}' tidak berhak menyetujui registrasi outlet.")
 
    # Untuk role distributor: pastikan outlet berada di bawah distributornya
    if kode_role == "distributor":
        du_result = await session.execute(
            select(DistributorUser.distributor_id).where(
                DistributorUser.user_id == requesting_user.id
            )
        )
        dist_ids = du_result.scalars().all()
        if outlet.distributor_id not in dist_ids:
            raise PermissionError("Anda tidak berhak menyetujui outlet di luar distributor Anda.")
 
    # Aktifkan outlet
    outlet.status = "aktif"
    outlet.updated_at = datetime.now(timezone.utc)
    session.add(outlet)
 
    # Aktifkan user terkait
    if outlet.pic_user_id:
        u_result = await session.execute(
            select(User).where(User.id == outlet.pic_user_id)
        )
        user = u_result.scalar_one_or_none()
        if user:
            user.is_active = True
            user.updated_at = datetime.now(timezone.utc)
            session.add(user)
 
    await session.commit()
    await session.refresh(outlet)
 
    return OutletApproveResponse(
        message=f"Registrasi outlet '{outlet.nama_toko}' telah disetujui.",
        outlet_id=outlet.id,
        user_id=outlet.pic_user_id,
        kode_outlet=outlet.kode_outlet,
        status=outlet.status,
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
    - Outlet.status tetap bisa dicatat sebagai 'ditolak'
    - User tetap is_active=False (tidak bisa login)
    """
    outlet = await _get_outlet_or_404(outlet_id, session)
 
    if outlet.status != "pending":
        raise ValueError(
            f"Outlet tidak dalam status 'pending' (status saat ini: '{outlet.status}'). "
            "Hanya outlet berstatus 'pending' yang bisa ditolak."
        )
 
    if kode_role not in ("superadmin", "admin_ho", "distributor", "sc_spv", "apsm"):
        raise PermissionError(f"Role '{kode_role}' tidak berhak menolak registrasi outlet.")
 
    if kode_role == "distributor":
        du_result = await session.execute(
            select(DistributorUser.distributor_id).where(
                DistributorUser.user_id == requesting_user.id
            )
        )
        dist_ids = du_result.scalars().all()
        if outlet.distributor_id not in dist_ids:
            raise PermissionError("Anda tidak berhak menolak outlet di luar distributor Anda.")
 
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
 
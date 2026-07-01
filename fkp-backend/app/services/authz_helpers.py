"""
Authz Helpers — pusat logic pengecekan superadmin & resolusi scope per role.

Dibuat untuk menghindari duplikasi & inkonsistensi pengecekan role di banyak
service (mis. "superadmin" vs "super_admin", scoping APSM via SC_SPV vs via Area).

PENTING: Jika struktur Role di project Anda berbeda dari asumsi di bawah
(field is_superadmin), sesuaikan fungsi `is_superadmin()` saja — semua
pemanggil lain tidak perlu diubah.
"""
import uuid
from typing import List, Optional

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.role import Role
from app.models.area import Area
from app.models.distributor import Distributor, DistributorUser
from app.models.outlet import Outlet
from app.models.sc_spv import ScSpvDistributor


# ─── SUPERADMIN CHECK ─────────────────────────────────────────────────────────

async def is_superadmin(user: User, db: AsyncSession) -> bool:
    """
    Satu-satunya tempat untuk cek superadmin di seluruh aplikasi.
    Pakai flag Role.is_superadmin, BUKAN string match "superadmin"/"super_admin"
    yang rawan typo dan sudah terbukti inkonsisten di codebase ini.
    """
    result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = result.scalar_one_or_none()
    return bool(role and getattr(role, "is_superadmin", False))


# Role-role HO yang punya akses global tanpa terikat hierarki wilayah
# (section 3.6 dokumen). Superadmin TIDAK dimasukkan di sini — superadmin
# selalu dicek lewat is_superadmin(), bukan lewat daftar string ini.
GLOBAL_ACCESS_ROLES = {"admin_ho", "qc", "rsm", "direktur", "superadmin", "finance"}
# KEPUTUSAN ARSITEKTUR (Kategori E, audit RBAC Juni 2026): RSM RESMI global,
# bukan dibatasi ke bawahannya. Konsisten dengan _ROLE_GLOBAL_ACCESS di
# fkp_service.py yang dipakai di list_fkp/get_fkp_detail/list_fkp_penerbitan/
# validate_fkp_formulir_access, DAN dengan rsm_approve_investigasi()/
# rsm_approve_resolusi() yang juga tidak menerapkan scope per-area untuk RSM.
# get_rsm_distributor_ids() di bawah DISIMPAN (bukan dihapus) sebagai opsi
# jika suatu saat keputusan ini dibalik — TIDAK dipanggil di mana pun saat ini.

async def has_global_access(user: User, kode_role: str, db: AsyncSession) -> bool:
    """True jika user superadmin ATAU role-nya termasuk akses global."""
    if await is_superadmin(user, db):
        return True
    return kode_role in GLOBAL_ACCESS_ROLES


# ─── SCOPE RESOLVERS ──────────────────────────────────────────────────────────
# Setiap fungsi mengembalikan list distributor_id yang boleh diakses user,
# mengikuti aturan scoping section 3 dokumen secara persis. Dipakai bersama
# oleh distributor_service, fkp_service, outlet_register_service, dst supaya
# tidak ada lagi scoping yang menyimpang (seperti APSM via SC_SPV yang salah).

async def get_apsm_distributor_ids(apsm_user_id: uuid.UUID, db: AsyncSession) -> List[uuid.UUID]:
    """
    Scoping APSM — PRIMARY via Area, BUKAN via SC_SPV.
    Distributor yang belum punya SC_SPV tetap masuk (tidak ada blind spot).
    Lihat dokumen section 3.4 & section 7 (Ringkasan Keputusan Desain).
    """
    area_result = await db.execute(
        select(Area.id).where(Area.pic_user_id == apsm_user_id)
    )
    area_ids = area_result.scalars().all()
    if not area_ids:
        return []

    dist_result = await db.execute(
        select(Distributor.id).where(Distributor.area_id.in_(area_ids))
    )
    return list(dist_result.scalars().all())


async def get_sc_spv_distributor_ids(sc_spv_user_id: uuid.UUID, db: AsyncSession) -> List[uuid.UUID]:
    """Scoping SC_SPV — langsung via ScSpvDistributor (section 3.3)."""
    result = await db.execute(
        select(ScSpvDistributor.distributor_id).where(
            ScSpvDistributor.sc_spv_user_id == sc_spv_user_id
        )
    )
    return list(result.scalars().all())


async def get_distributor_user_distributor_ids(user_id: uuid.UUID, db: AsyncSession) -> List[uuid.UUID]:
    """Scoping role distributor — via DistributorUser (section 3.2)."""
    result = await db.execute(
        select(DistributorUser.distributor_id).where(
            DistributorUser.user_id == user_id
        )
    )
    return list(result.scalars().all())


async def get_outlet_distributor_ids(user_id: uuid.UUID, db: AsyncSession) -> List[uuid.UUID]:
    """
    Scoping role outlet — bisa punya lebih dari 1 outlet,
    tapi semua dijamin di distributor yang sama (aturan bisnis).
    Kembalikan list distributor_id unik milik user ini.
    """
    result = await db.execute(
        select(Outlet.distributor_id)
        .where(Outlet.pic_user_id == user_id)
        .distinct()
    )
    return list(result.scalars().all())

async def get_rsm_distributor_ids(rsm_user_id: uuid.UUID, db: AsyncSession) -> List[uuid.UUID]:
    """
    DEAD CODE (disengaja) — lihat keputusan arsitektur di GLOBAL_ACCESS_ROLES.
    Fungsi ini TIDAK dipanggil karena RSM diputuskan global, bukan scoped.
    Disimpan untuk referensi/kebutuhan masa depan jika kebijakan berubah —
    JANGAN dihapus tanpa diskusi ulang, dan JANGAN dipanggil tanpa juga
    mengeluarkan "rsm" dari GLOBAL_ACCESS_ROLES + _ROLE_GLOBAL_ACCESS
    (fkp_service.py) secara bersamaan.
    """
    from app.models.sc_spv import RsmApsm  # local import agar tidak circular dengan modul lain
    apsm_ids_result = await db.execute(
        select(RsmApsm.apsm_user_id).where(RsmApsm.rsm_user_id == rsm_user_id)
    )
    apsm_ids = apsm_ids_result.scalars().all()
    if not apsm_ids:
        return []

    area_result = await db.execute(
        select(Area.id).where(Area.pic_user_id.in_(apsm_ids))
    )
    area_ids = area_result.scalars().all()
    if not area_ids:
        return []

    dist_result = await db.execute(
        select(Distributor.id).where(Distributor.area_id.in_(area_ids))
    )
    return list(dist_result.scalars().all())


async def get_scoped_distributor_ids(
    user: User, kode_role: str, db: AsyncSession
) -> Optional[List[uuid.UUID]]:
    """
    Resolver tunggal: kembalikan list distributor_id yang boleh diakses user
    sesuai role-nya. Return None artinya "akses global, tidak perlu filter".
    Return [] artinya "tidak ada akses sama sekali".

    Dipakai di semua tempat yang butuh tahu "distributor mana saja yang boleh
    dilihat/diaksi oleh user ini" — distributor_service, outlet_register_service,
    upload_service (via fkp), dsb. SATU sumber kebenaran scoping.
    """
    if await has_global_access(user, kode_role, db):
        return None  # akses global

    if kode_role == "apsm":
        return await get_apsm_distributor_ids(user.id, db)

    if kode_role == "sc_spv":
        return await get_sc_spv_distributor_ids(user.id, db)

    if kode_role == "distributor":
        return await get_distributor_user_distributor_ids(user.id, db)

    if kode_role == "outlet":
        return await get_outlet_distributor_ids(user.id, db)

    if kode_role == "rsm":
        return await get_rsm_distributor_ids(user.id, db)

    if kode_role == "finance":
        return None  # finance global, filter status dilakukan di layer lain

    # Role tidak dikenal -> tidak ada akses
    return []


async def assert_distributor_in_scope(
    distributor_id: uuid.UUID,
    user: User,
    kode_role: str,
    db: AsyncSession,
    forbidden_message: str = "Anda tidak berhak mengakses distributor ini.",
) -> None:
    """
    Lempar PermissionError jika distributor_id di luar scope user.
    Dipakai sebelum aksi tulis (approve/reject outlet, upload attachment, dst).
    """
    scoped_ids = await get_scoped_distributor_ids(user, kode_role, db)
    if scoped_ids is None:
        return  # akses global
    if distributor_id not in scoped_ids:
        raise PermissionError(forbidden_message)
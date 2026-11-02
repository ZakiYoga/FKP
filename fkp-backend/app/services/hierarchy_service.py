"""
Hierarchy Service — validasi dan manajemen hierarki sales.
RSM → APSM → SC/SPV → Distributor
"""
from collections import defaultdict
import uuid
from typing import List

from fastapi import HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sc_spv import ScSpvDistributor, ApsmScSpv, RsmApsm
from app.models.distributor import Distributor
from app.models.area import Area
from app.models.user import User
from app.models.role import Role
from app.schemas.hierarchy import (
    ScSpvDistributorAssign, ApsmScSpvAssign, RsmApsmAssign,
    ScSpvDistributorResponse, ApsmScSpvResponse, RsmApsmResponse,
    ScSpvWithDistributors, ApsmWithTeam, RsmWithTeam,
    UserBasicInfo, DistributorBasicInfo, AreaBasicInfo
)

def to_user_basic(u: User) -> UserBasicInfo:
    return UserBasicInfo(
        id=u.id,
        nama=u.full_name,
        email=u.email,
        no_telepon=u.no_telepon,
        avatar_path=u.avatar_path,
    )

async def _get_user_with_role(user_id: uuid.UUID, expected_role: str, db: AsyncSession) -> User:
    """Ambil user dan validasi role-nya."""
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"User tidak ditemukan atau tidak aktif.")

    role_result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = role_result.scalar_one_or_none()
    if not role or role.kode_role != expected_role:
        raise HTTPException(
            status_code=400,
            detail=f"User harus memiliki role '{expected_role}', bukan '{role.kode_role if role else 'unknown'}'.",
        )
    return user


# ─── RSM ↔ APSM ──────────────────────────────────────────────────────────────

async def list_rsm_apsm(rsm_user_id: uuid.UUID, db: AsyncSession) -> List[RsmApsmResponse]:
    result = await db.execute(
        select(RsmApsm).where(RsmApsm.rsm_user_id == rsm_user_id)
    )
    return result.scalars().all()


async def assign_apsm_to_rsm(data: RsmApsmAssign, db: AsyncSession) -> RsmApsmResponse:
    # Validasi role
    await _get_user_with_role(data.rsm_user_id, "rsm", db)
    await _get_user_with_role(data.apsm_user_id, "apsm", db)

    # Cek apakah APSM sudah punya RSM atasan
    existing = await db.execute(
        select(RsmApsm).where(RsmApsm.apsm_user_id == data.apsm_user_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="APSM ini sudah memiliki RSM atasan. Lepas dulu sebelum assign ke RSM baru.",
        )

    mapping = RsmApsm(rsm_user_id=data.rsm_user_id, apsm_user_id=data.apsm_user_id)
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    return mapping


async def remove_apsm_from_rsm(rsm_user_id: uuid.UUID, apsm_user_id: uuid.UUID, db: AsyncSession) -> dict:
    result = await db.execute(
        select(RsmApsm).where(
            RsmApsm.rsm_user_id == rsm_user_id,
            RsmApsm.apsm_user_id == apsm_user_id,
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping RSM-APSM tidak ditemukan.")
    await db.delete(mapping)
    await db.commit()
    return {"message": "APSM berhasil dilepas dari RSM."}


# ─── APSM ↔ SC/SPV ───────────────────────────────────────────────────────────

async def list_apsm_sc_spv(apsm_user_id: uuid.UUID, db: AsyncSession) -> List[ApsmScSpvResponse]:
    result = await db.execute(
        select(ApsmScSpv).where(ApsmScSpv.apsm_user_id == apsm_user_id)
    )
    return result.scalars().all()


async def assign_sc_spv_to_apsm(data: ApsmScSpvAssign, db: AsyncSession) -> ApsmScSpvResponse:
    # Validasi role
    await _get_user_with_role(data.apsm_user_id, "apsm", db)
    await _get_user_with_role(data.sc_spv_user_id, "sc_spv", db)

    # Cek apakah SC/SPV sudah punya APSM atasan
    existing = await db.execute(
        select(ApsmScSpv).where(ApsmScSpv.sc_spv_user_id == data.sc_spv_user_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="SC/SPV ini sudah memiliki APSM atasan. Lepas dulu sebelum assign ke APSM baru.",
        )

    area = await db.get(Area, data.area_id)
    if not area or area.status != "aktif" or area.pic_user_id != data.apsm_user_id:
        raise HTTPException(
            status_code=400,
            detail="Area harus aktif dan dipegang oleh APSM tujuan.",
        )

    mapping = ApsmScSpv(
        apsm_user_id=data.apsm_user_id,
        sc_spv_user_id=data.sc_spv_user_id,
        area_id=data.area_id,
    )
    
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    return mapping


async def remove_sc_spv_from_apsm(apsm_user_id: uuid.UUID, sc_spv_user_id: uuid.UUID, db: AsyncSession) -> dict:
    result = await db.execute(
        select(ApsmScSpv).where(
            ApsmScSpv.apsm_user_id == apsm_user_id,
            ApsmScSpv.sc_spv_user_id == sc_spv_user_id,
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping APSM-SC/SPV tidak ditemukan.")

    has_dist = await db.execute(
        select(ScSpvDistributor.id)
        .where(ScSpvDistributor.sc_spv_user_id == sc_spv_user_id)
        .limit(1)
    )
    if has_dist.first():
        raise HTTPException(
            status_code=400,
            detail="SC/SPV masih meng-handle distributor. Lepas distributornya terlebih dahulu.",
        )
    await db.delete(mapping)
    await db.commit()
    return {"message": "SC/SPV berhasil dilepas dari APSM."}


# ─── SC/SPV ↔ DISTRIBUTOR ────────────────────────────────────────────────────

async def list_sc_spv_distributors(sc_spv_user_id: uuid.UUID, db: AsyncSession) -> List[ScSpvDistributorResponse]:
    result = await db.execute(
        select(ScSpvDistributor).where(ScSpvDistributor.sc_spv_user_id == sc_spv_user_id)
    )
    return result.scalars().all()


async def assign_distributor_to_sc_spv(data: ScSpvDistributorAssign, db: AsyncSession) -> ScSpvDistributorResponse:
    # Validasi role SC/SPV
    await _get_user_with_role(data.sc_spv_user_id, "sc_spv", db)

    # Ambil distributor
    dist_result = await db.execute(
        select(Distributor).where(Distributor.id == data.distributor_id)
    )
    distributor = dist_result.scalar_one_or_none()
    if not distributor:
        raise HTTPException(status_code=404, detail="Distributor tidak ditemukan.")

    # Cek apakah distributor sudah di-handle SC/SPV lain
    existing = await db.execute(
        select(ScSpvDistributor).where(ScSpvDistributor.distributor_id == data.distributor_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Distributor ini sudah di-handle oleh SC/SPV lain. Lepas dulu sebelum assign ke SC/SPV baru.",
        )

        # ─── VALIDASI AREA ────────────────────────────────────────────────────────
    link = (
        await db.execute(
            select(ApsmScSpv).where(ApsmScSpv.sc_spv_user_id == data.sc_spv_user_id)
        )
    ).scalar_one_or_none()

    if not link:
        raise HTTPException(
            status_code=400,
            detail="SC/SPV belum memiliki APSM atasan. Assign SC/SPV ke APSM terlebih dahulu.",
        )

    # Hapus cek ini setelah kolom area_id dijadikan NOT NULL
    if link.area_id is None:
        raise HTTPException(
            status_code=400,
            detail="SC/SPV ini belum memiliki area. Hubungi admin untuk melengkapi data area.",
        )

    if distributor.area_id != link.area_id:
        rows = await db.execute(
            select(Area).where(Area.id.in_([distributor.area_id, link.area_id]))
        )
        names = {a.id: a.nama_area for a in rows.scalars().all()}
        raise HTTPException(
            status_code=400,
            detail=(
                f"Distributor '{distributor.nama_perusahaan}' berada di area "
                f"'{names.get(distributor.area_id, '-')}', sedangkan SC/SPV ini "
                f"memegang area '{names.get(link.area_id, '-')}'."
            ),
        )
    # ─── END VALIDASI AREA ────────────────────────────────────────────────────

    mapping = ScSpvDistributor(
        sc_spv_user_id=data.sc_spv_user_id,
        distributor_id=data.distributor_id,
    )
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    return mapping


async def remove_distributor_from_sc_spv(
    sc_spv_user_id: uuid.UUID, distributor_id: uuid.UUID, db: AsyncSession
) -> dict:
    result = await db.execute(
        select(ScSpvDistributor).where(
            ScSpvDistributor.sc_spv_user_id == sc_spv_user_id,
            ScSpvDistributor.distributor_id == distributor_id,
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping SC/SPV-Distributor tidak ditemukan.")
    await db.delete(mapping)
    await db.commit()
    return {"message": "Distributor berhasil dilepas dari SC/SPV."}


# ─── VIEW HIERARKI ────────────────────────────────────────────────────────────

async def _users_by_ids(ids, db: AsyncSession) -> dict:
    if not ids:
        return {}
    rows = await db.execute(select(User).where(User.id.in_(list(ids))))
    return {u.id: u for u in rows.scalars().all()}


async def get_hierarchy_by_rsm(rsm_user_id: uuid.UUID, db: AsyncSession) -> RsmWithTeam:
    """Tampilkan hierarki lengkap: RSM → APSM → SC/SPV → Distributor (8 query tetap)."""

    # 1) RSM
    rsm_user = (
        await db.execute(select(User).where(User.id == rsm_user_id))
    ).scalar_one_or_none()
    if not rsm_user:
        raise HTTPException(status_code=404, detail="RSM tidak ditemukan.")

    # 2) Mapping RSM → APSM
    apsm_maps = (
        await db.execute(
            select(RsmApsm)
            .where(RsmApsm.rsm_user_id == rsm_user_id)
            .order_by(RsmApsm.created_at, RsmApsm.id)
        )
    ).scalars().all()
    apsm_ids = [m.apsm_user_id for m in apsm_maps]

    # 3) Semua user APSM
    apsm_users = await _users_by_ids(apsm_ids, db)

    # 4) Mapping APSM → SC/SPV untuk semua APSM sekaligus
    sc_maps = []
    if apsm_ids:
        sc_maps = (
            await db.execute(
                select(ApsmScSpv)
                .where(ApsmScSpv.apsm_user_id.in_(apsm_ids))
                .order_by(ApsmScSpv.created_at, ApsmScSpv.id)
            )
        ).scalars().all()
    sc_by_apsm = defaultdict(list)
    for m in sc_maps:
        sc_by_apsm[m.apsm_user_id].append(m)
    sc_ids = [m.sc_spv_user_id for m in sc_maps]

    # 5) Semua user SC/SPV
    sc_users = await _users_by_ids(sc_ids, db)

    # 6) Mapping SC/SPV → distributor untuk semua SC/SPV sekaligus
    dist_maps = []
    if sc_ids:
        dist_maps = (
            await db.execute(
                select(ScSpvDistributor)
                .where(ScSpvDistributor.sc_spv_user_id.in_(sc_ids))
                .order_by(ScSpvDistributor.created_at, ScSpvDistributor.id)
            )
        ).scalars().all()
    dist_ids_by_sc = defaultdict(list)
    for dm in dist_maps:
        dist_ids_by_sc[dm.sc_spv_user_id].append(dm.distributor_id)

    # 7) Semua distributor
    all_dist_ids = {dm.distributor_id for dm in dist_maps}
    dist_by_id = {}
    if all_dist_ids:
        rows = await db.execute(
            select(Distributor).where(Distributor.id.in_(list(all_dist_ids)))
        )
        dist_by_id = {d.id: d for d in rows.scalars().all()}

    # 8) Semua area SC/SPV
    area_ids = {m.area_id for m in sc_maps if m.area_id}
    area_by_id = {}
    if area_ids:
        rows = await db.execute(select(Area).where(Area.id.in_(list(area_ids))))
        area_by_id = {a.id: a for a in rows.scalars().all()}

    # ─── Rangkai di memori (tanpa query) ──────────────────────────────────────
    apsm_list = []
    for apsm_map in apsm_maps:
        apsm_user = apsm_users.get(apsm_map.apsm_user_id)
        if not apsm_user:
            continue

        sc_list = []
        for sc_map in sc_by_apsm.get(apsm_user.id, []):
            sc_user = sc_users.get(sc_map.sc_spv_user_id)
            if not sc_user:
                continue

            dist_list = [
                DistributorBasicInfo(
                    id=d.id,
                    kode_distributor=d.kode_distributor,
                    nama_perusahaan=d.nama_perusahaan,
                    status=d.status,
                )
                for d in (dist_by_id.get(did) for did in dist_ids_by_sc.get(sc_user.id, []))
                if d
            ]

            area = area_by_id.get(sc_map.area_id)
            sc_list.append(ScSpvWithDistributors(
                sc_spv=to_user_basic(sc_user),
                area=AreaBasicInfo.model_validate(area) if area else None,
                distributors=dist_list,
            ))

        apsm_list.append(ApsmWithTeam(apsm=to_user_basic(apsm_user), sc_spv_list=sc_list))

    return RsmWithTeam(rsm=to_user_basic(rsm_user), apsm_list=apsm_list)

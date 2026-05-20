"""
Hierarchy Service — validasi dan manajemen hierarki sales.
RSM → APSM → SC/SPV → Distributor
"""
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
    UserBasicInfo, DistributorBasicInfo,
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


async def _get_apsm_area_ids(apsm_user_id: uuid.UUID, db: AsyncSession) -> List[uuid.UUID]:
    """Ambil semua area_id yang di-handle APSM ini."""
    result = await db.execute(select(Area).where(Area.pic_user_id == apsm_user_id))
    return [a.id for a in result.scalars().all()]


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

    mapping = ApsmScSpv(apsm_user_id=data.apsm_user_id, sc_spv_user_id=data.sc_spv_user_id)
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
    # SC/SPV hanya boleh handle distributor di area APSM atasannya
    apsm_result = await db.execute(
        select(ApsmScSpv).where(ApsmScSpv.sc_spv_user_id == data.sc_spv_user_id)
    )
    apsm_mapping = apsm_result.scalar_one_or_none()

    if not apsm_mapping:
        raise HTTPException(
            status_code=400,
            detail="SC/SPV belum memiliki APSM atasan. Assign SC/SPV ke APSM terlebih dahulu.",
        )

    # Ambil area-area yang di-handle APSM atasan SC/SPV ini
    apsm_area_ids = await _get_apsm_area_ids(apsm_mapping.apsm_user_id, db)

    if not apsm_area_ids:
        raise HTTPException(
            status_code=400,
            detail="APSM atasan SC/SPV ini belum memiliki area yang di-assign.",
        )

    # Validasi: area distributor harus termasuk area APSM atasan
    if distributor.area_id not in apsm_area_ids:
        # Ambil nama area untuk pesan error yang informatif
        area_result = await db.execute(select(Area).where(Area.id == distributor.area_id))
        area = area_result.scalar_one_or_none()
        raise HTTPException(
            status_code=400,
            detail=(
                f"Distributor '{distributor.nama_perusahaan}' berada di area "
                f"'{area.nama_area if area else distributor.area_id}' yang tidak termasuk "
                f"dalam area APSM atasan SC/SPV ini. "
                f"SC/SPV hanya boleh handle distributor di area APSM atasannya."
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

async def get_hierarchy_by_rsm(rsm_user_id: uuid.UUID, db: AsyncSession) -> RsmWithTeam:
    """Tampilkan hierarki lengkap: RSM → APSM → SC/SPV → Distributor."""

    rsm_result = await db.execute(select(User).where(User.id == rsm_user_id))
    rsm_user = rsm_result.scalar_one_or_none()
    if not rsm_user:
        raise HTTPException(status_code=404, detail="RSM tidak ditemukan.")

    rsm_info = UserBasicInfo(
        id=rsm_user.id, nama=rsm_user.nama,
        email=rsm_user.email, no_telepon=rsm_user.no_telepon
    )

    # Ambil semua APSM di bawah RSM ini
    apsm_mappings = await db.execute(
        select(RsmApsm).where(RsmApsm.rsm_user_id == rsm_user_id)
    )
    apsm_list = []

    for apsm_map in apsm_mappings.scalars().all():
        apsm_result = await db.execute(select(User).where(User.id == apsm_map.apsm_user_id))
        apsm_user = apsm_result.scalar_one_or_none()
        if not apsm_user:
            continue

        apsm_info = UserBasicInfo(
            id=apsm_user.id, nama=apsm_user.nama,
            email=apsm_user.email, no_telepon=apsm_user.no_telepon
        )

        # Ambil SC/SPV di bawah APSM ini
        sc_mappings = await db.execute(
            select(ApsmScSpv).where(ApsmScSpv.apsm_user_id == apsm_user.id)
        )
        sc_list = []

        for sc_map in sc_mappings.scalars().all():
            sc_result = await db.execute(select(User).where(User.id == sc_map.sc_spv_user_id))
            sc_user = sc_result.scalar_one_or_none()
            if not sc_user:
                continue

            sc_info = UserBasicInfo(
                id=sc_user.id, nama=sc_user.nama,
                email=sc_user.email, no_telepon=sc_user.no_telepon
            )

            # Ambil distributor yang di-handle SC/SPV ini
            dist_mappings = await db.execute(
                select(ScSpvDistributor).where(ScSpvDistributor.sc_spv_user_id == sc_user.id)
            )
            dist_list = []
            for dm in dist_mappings.scalars().all():
                dist_result = await db.execute(
                    select(Distributor).where(Distributor.id == dm.distributor_id)
                )
                dist = dist_result.scalar_one_or_none()
                if dist:
                    dist_list.append(DistributorBasicInfo(
                        id=dist.id, kode_distributor=dist.kode_distributor,
                        nama_perusahaan=dist.nama_perusahaan, status=dist.status,
                    ))

            sc_list.append(ScSpvWithDistributors(sc_spv=sc_info, distributors=dist_list))

        apsm_list.append(ApsmWithTeam(apsm=apsm_info, sc_spv_list=sc_list))

    return RsmWithTeam(rsm=rsm_info, apsm_list=apsm_list)

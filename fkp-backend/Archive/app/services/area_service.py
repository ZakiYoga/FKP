import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.area import Area, AreaProvince
from app.models.wilayah import Provinsi
from app.schemas.area import AreaCreate, AreaUpdate, AreaResponse, ProvinsiResponse


async def _get_area_with_provinces(area: Area, db: AsyncSession) -> AreaResponse:
    """Helper: ambil area beserta daftar provinsinya."""
    result = await db.execute(
        select(AreaProvince).where(AreaProvince.area_id == area.id)
    )
    area_provinces = result.scalars().all()

    provinsi_list = []
    for ap in area_provinces:
        prov_result = await db.execute(
            select(Provinsi).where(Provinsi.id == ap.provinsi_id)
        )
        prov = prov_result.scalar_one_or_none()
        if prov:
            provinsi_list.append(ProvinsiResponse(
                id=prov.id, nama_provinsi=prov.nama_provinsi
            ))

    return AreaResponse(
        id=area.id,
        kode_area=area.kode_area,
        nama_area=area.nama_area,
        pic_user_id=area.pic_user_id,
        status=area.status,
        created_at=area.created_at,
        updated_at=area.updated_at,
        provinsi=provinsi_list,
    )


async def list_areas(db: AsyncSession) -> List[AreaResponse]:
    result = await db.execute(select(Area).order_by(Area.kode_area))
    areas = result.scalars().all()
    return [await _get_area_with_provinces(a, db) for a in areas]


async def get_area(area_id: uuid.UUID, db: AsyncSession) -> AreaResponse:
    result = await db.execute(select(Area).where(Area.id == area_id))
    area = result.scalar_one_or_none()
    if not area:
        raise HTTPException(status_code=404, detail="Area tidak ditemukan.")
    return await _get_area_with_provinces(area, db)


async def create_area(data: AreaCreate, db: AsyncSession) -> AreaResponse:
    # Cek kode_area unik
    existing = await db.execute(select(Area).where(Area.kode_area == data.kode_area))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Kode area '{data.kode_area}' sudah digunakan.",
        )

    area = Area(
        kode_area=data.kode_area,
        nama_area=data.nama_area,
        pic_user_id=data.pic_user_id,
    )
    db.add(area)
    await db.flush()  # flush agar area.id ter-generate sebelum insert AreaProvince

    # Tambahkan mapping provinsi
    for prov_id in data.provinsi_ids:
        prov_check = await db.execute(select(Provinsi).where(Provinsi.id == prov_id))
        if not prov_check.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Provinsi dengan id {prov_id} tidak ditemukan.",
            )
        db.add(AreaProvince(area_id=area.id, provinsi_id=prov_id))

    await db.commit()
    await db.refresh(area)
    return await _get_area_with_provinces(area, db)


async def update_area(area_id: uuid.UUID, data: AreaUpdate, db: AsyncSession) -> AreaResponse:
    result = await db.execute(select(Area).where(Area.id == area_id))
    area = result.scalar_one_or_none()
    if not area:
        raise HTTPException(status_code=404, detail="Area tidak ditemukan.")

    update_data = data.model_dump(exclude_none=True, exclude={"provinsi_ids"})
    for key, value in update_data.items():
        setattr(area, key, value)
    area.updated_at = datetime.now(timezone.utc)

    # Update mapping provinsi jika dikirim
    if data.provinsi_ids is not None:
        # Hapus semua mapping lama
        old_aps = await db.execute(
            select(AreaProvince).where(AreaProvince.area_id == area_id)
        )
        for ap in old_aps.scalars().all():
            await db.delete(ap)

        # Insert mapping baru
        for prov_id in data.provinsi_ids:
            db.add(AreaProvince(area_id=area.id, provinsi_id=prov_id))

    db.add(area)
    await db.commit()
    await db.refresh(area)
    return await _get_area_with_provinces(area, db)

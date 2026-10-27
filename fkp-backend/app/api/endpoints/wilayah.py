from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services import wilayah_service as svc
from app.schemas.wilayah import *
from app.services.wilayah_reverse import reverse_wilayah


router = APIRouter()


def _cache(response: Response):
    response.headers["Cache-Control"] = "private, max-age=86400"


@router.get("/provinsi", response_model=List[ProvinsiOut], dependencies=[Depends(_cache)])
async def provinsi(db: AsyncSession = Depends(get_db)):
    return [ProvinsiOut(id=p.id, kode=p.kode, nama=p.nama_provinsi) for p in await svc.list_provinsi(db)]

@router.get("/provinsi/{provinsi_id}/kabupaten", response_model=List[KabupatenKotaOut], dependencies=[Depends(_cache)])
async def kabupaten(provinsi_id: int, db: AsyncSession = Depends(get_db)):
    return await svc.list_kabupaten(db, provinsi_id)

@router.get("/kabupaten/{kabupaten_id}/kecamatan", response_model=List[KecamatanOut], dependencies=[Depends(_cache)])
async def kecamatan(kabupaten_id: int, db: AsyncSession = Depends(get_db)):
    return await svc.list_kecamatan(db, kabupaten_id)

@router.get("/kecamatan/{kecamatan_id}/kelurahan", response_model=List[KelurahanOut], dependencies=[Depends(_cache)])
async def kelurahan(kecamatan_id: int, db: AsyncSession = Depends(get_db)):
    return await svc.list_kelurahan(db, kecamatan_id)

@router.get("/search", response_model=List[WilayahSearchItem])
async def search(q: str = Query(..., min_length=3, max_length=100), db: AsyncSession = Depends(get_db)):
    return await svc.search_kelurahan(db, q)

@router.get("/kelurahan/{kelurahan_id}", response_model=WilayahLengkap, dependencies=[Depends(_cache)])
async def detail(kelurahan_id: int, db: AsyncSession = Depends(get_db)):
    w = await svc.get_wilayah_by_kelurahan(db, kelurahan_id)
    if not w:
        raise HTTPException(404, "Kelurahan tidak ditemukan.")
    return w

@router.get(
    "/reverse",
    response_model=WilayahReverseOut,
    dependencies=[Depends(get_current_user)],
)
async def reverse(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    db: AsyncSession = Depends(get_db),
):
    return await reverse_wilayah(db, lat, lng)
from typing import Dict, Iterable, List, Optional
from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.wilayah import Provinsi, KabupatenKota, Kecamatan, Kelurahan
from app.schemas.wilayah import (
    WilayahLengkap, KelurahanOut, KecamatanOut,
    KabupatenKotaOut, ProvinsiOut, WilayahSearchItem,
)

_BASE = (
    select(Kelurahan, Kecamatan, KabupatenKota, Provinsi)
    .join(Kecamatan, Kelurahan.kecamatan_id == Kecamatan.id)
    .join(KabupatenKota, Kecamatan.kabupaten_kota_id == KabupatenKota.id)
    .join(Provinsi, KabupatenKota.provinsi_id == Provinsi.id)
)


def _label(kel, kec, kab, prov) -> str:
    return f"{kel.nama}, {kec.nama}, {kab.nama}, {prov.nama_provinsi}"


def _to_wilayah(kel, kec, kab, prov) -> WilayahLengkap:
    return WilayahLengkap(
        kelurahan=KelurahanOut.model_validate(kel),
        kecamatan=KecamatanOut.model_validate(kec),
        kabupaten_kota=KabupatenKotaOut.model_validate(kab),
        provinsi=ProvinsiOut(id=prov.id, kode=prov.kode, nama=prov.nama_provinsi),
        label=_label(kel, kec, kab, prov),
    )


async def get_wilayah_by_kelurahan(db: AsyncSession, kelurahan_id: int) -> Optional[WilayahLengkap]:
    row = (await db.execute(_BASE.where(Kelurahan.id == kelurahan_id))).first()
    return _to_wilayah(*row) if row else None


async def get_wilayah_map(db: AsyncSession, kelurahan_ids: Iterable[Optional[int]]) -> Dict[int, WilayahLengkap]:
    ids = {i for i in kelurahan_ids if i is not None}
    if not ids:
        return {}
    rows = (await db.execute(_BASE.where(Kelurahan.id.in_(ids)))).all()
    return {r[0].id: _to_wilayah(*r) for r in rows}


async def attach_wilayah(db: AsyncSession, items: list) -> list:
    """Isi 'wilayah' pada item. Item boleh dict (hasil _to_detail) atau objek schema."""
    def kid(i):
        return i.get("kelurahan_id") if isinstance(i, dict) else i.kelurahan_id

    wmap = await get_wilayah_map(db, (kid(i) for i in items))
    for i in items:
        w = wmap.get(kid(i)) if kid(i) else None
        if isinstance(i, dict):
            i["wilayah"] = w
        else:
            i.wilayah = w
    return items


async def ensure_kelurahan(db: AsyncSession, kelurahan_id: Optional[int]) -> None:
    if kelurahan_id is not None and await db.get(Kelurahan, kelurahan_id) is None:
        raise HTTPException(status_code=422, detail="kelurahan_id tidak valid.")


# ── Dropdown berjenjang ──
async def list_provinsi(db: AsyncSession):
    return (await db.execute(select(Provinsi).order_by(Provinsi.nama_provinsi))).scalars().all()

async def list_kabupaten(db: AsyncSession, provinsi_id: int):
    q = select(KabupatenKota).where(KabupatenKota.provinsi_id == provinsi_id).order_by(KabupatenKota.nama)
    return (await db.execute(q)).scalars().all()

async def list_kecamatan(db: AsyncSession, kabupaten_kota_id: int):
    q = select(Kecamatan).where(Kecamatan.kabupaten_kota_id == kabupaten_kota_id).order_by(Kecamatan.nama)
    return (await db.execute(q)).scalars().all()

async def list_kelurahan(db: AsyncSession, kecamatan_id: int):
    q = select(Kelurahan).where(Kelurahan.kecamatan_id == kecamatan_id).order_by(Kelurahan.nama)
    return (await db.execute(q)).scalars().all()


# ── Pencarian ──
async def search_kelurahan(db: AsyncSession, q: str, limit: int = 20) -> List[WilayahSearchItem]:
    like = f"%{q.strip()}%"
    stmt = _BASE.where(or_(
        Kelurahan.nama.ilike(like), Kecamatan.nama.ilike(like), KabupatenKota.nama.ilike(like),
    )).order_by(Kelurahan.nama).limit(limit)
    rows = (await db.execute(stmt)).all()
    return [WilayahSearchItem(kelurahan_id=k.id, kode_pos=k.kode_pos, label=_label(k, kc, kb, p))
            for k, kc, kb, p in rows]
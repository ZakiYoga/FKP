"""Reverse geocoding: koordinat -> kelurahan/kecamatan/kabupaten/provinsi dari tabel wilayah sendiri.

Alur: Nominatim (OSM) dipanggil dari BE -> nama hasilnya dicocokkan ke tabel wilayah ->
kembalikan kandidat WilayahLengkap. Hasil TIDAK dianggap pasti kecuali cocok tunggal.

Letakkan di app/services/wilayah_reverse.py.
"""
import asyncio
import logging
import re
import time
from typing import Dict, Iterable, List, Optional, Tuple

import httpx
from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.wilayah import KabupatenKota, Kelurahan, Provinsi
from app.schemas.wilayah import WilayahReverseOut
from app.services.wilayah_service import _BASE, _to_wilayah

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
# Wajib mengidentifikasi aplikasi (kebijakan Nominatim). GANTI dengan email kontak yang valid.
USER_AGENT = "SaktiPangan-OutletApp/1.0 (kontak@saktipangan.co.id)"

# Key di `address` Nominatim yang mungkin berisi tiap level (nama field di OSM Indonesia tidak konsisten).
KEL_KEYS = ("village", "suburb", "neighbourhood", "quarter")
KEC_KEYS = ("city_district", "district", "subdistrict", "municipality")
KAB_KEYS = ("county", "city", "regency", "state_district", "municipality")

MAX_CANDIDATES = 5

# ── Normalisasi nama ──
_PREFIX = re.compile(
    r"^(kabupaten|kab\.?|kota administrasi|kota adm\.?|kota|kecamatan|kec\.?|kelurahan|kel\.?|desa)\s+"
)
_PROV_ALIAS = {
    "daerah khusus ibukota jakarta": "dki jakarta",
    "daerah khusus ibu kota jakarta": "dki jakarta",
    "daerah istimewa yogyakarta": "di yogyakarta",
}


def norm(s: str) -> str:
    s = _PREFIX.sub("", s.lower().strip())
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_prov(s: str) -> str:
    n = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()
    return _PROV_ALIAS.get(n, n)


def _names(addr: dict, keys: Iterable[str]) -> set:
    return {norm(addr[k]) for k in keys if addr.get(k)}


# ── Panggilan Nominatim: throttle 1 req/detik + cache ──
_lock: Optional[asyncio.Lock] = None  # dibuat lazy agar terikat ke event loop yang berjalan
_last_call = 0.0
_cache: Dict[Tuple[float, float], Tuple[float, dict]] = {}
_CACHE_TTL = 24 * 3600
_CACHE_MAX = 5000


async def _nominatim(lat: float, lng: float) -> dict:
    global _lock, _last_call
    if _lock is None:
        _lock = asyncio.Lock()
    key = (round(lat, 4), round(lng, 4))  # ~11 m
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < _CACHE_TTL:
        return hit[1]

    async with _lock:
        wait = 1.1 - (time.monotonic() - _last_call)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": USER_AGENT}) as client:
                r = await client.get(
                    NOMINATIM_URL,
                    params={
                        "lat": lat,
                        "lon": lng,
                        "format": "jsonv2",
                        "addressdetails": 1,
                        "accept-language": "id",
                        "zoom": 18,
                    },
                )
            r.raise_for_status()
            data = r.json()
        except (httpx.HTTPError, ValueError):
            raise HTTPException(status_code=502, detail="Layanan geocoding tidak tersedia.")
        finally:
            _last_call = time.monotonic()

    if len(_cache) >= _CACHE_MAX:
        _cache.clear()  # sederhana; cukup untuk trafik kecil
    _cache[key] = (time.monotonic(), data)
    return data


# ── Pencocokan ke tabel wilayah ──
async def reverse_wilayah(db: AsyncSession, lat: float, lng: float) -> WilayahReverseOut:
    data = await _nominatim(lat, lng)
    addr: dict = data.get("address") or {}
    display = data.get("display_name")

    def not_found() -> WilayahReverseOut:
        # Log address mentah supaya daftar KEL_KEYS/KAB_KEYS/_PROV_ALIAS bisa disetel dari kasus nyata.
        logger.info("reverse wilayah not_found (%s, %s): address=%s", lat, lng, addr)
        return WilayahReverseOut(status="not_found", candidates=[], display_name=display)

    if addr.get("country_code") not in (None, "id") or not addr.get("state"):
        return not_found()

    kel_names = _names(addr, KEL_KEYS)
    if not kel_names:
        return not_found()

    # 1) Provinsi
    prov_n = norm_prov(addr["state"])
    provs = (await db.execute(select(Provinsi))).scalars().all()
    prov_ids = [p.id for p in provs if norm_prov(p.nama_provinsi) == prov_n]
    if not prov_ids:
        return not_found()

    # 2) Kabupaten/kota di dalam provinsi tsb (boleh tidak cocok -> fallback ke level provinsi)
    kab_names = _names(addr, KAB_KEYS)
    kabs = (
        await db.execute(select(KabupatenKota).where(KabupatenKota.provinsi_id.in_(prov_ids)))
    ).scalars().all()
    kab_ids = [k.id for k in kabs if norm(k.nama) in kab_names]

    # 3) Kelurahan: filter kasar di SQL (ILIKE), verifikasi tepat di Python (setelah normalisasi)
    stmt = _BASE.where(
        Provinsi.id.in_(prov_ids),
        or_(*[Kelurahan.nama.ilike(f"%{n}%") for n in kel_names]),
    )
    if kab_ids:
        stmt = stmt.where(KabupatenKota.id.in_(kab_ids))
    rows = [r for r in (await db.execute(stmt)).all() if norm(r[0].nama) in kel_names]
    if not rows:
        return not_found()

    # 4) Ranking: kode pos dan nama kecamatan (kalau ada) sebagai pembeda
    postcode = addr.get("postcode")
    kec_names = _names(addr, KEC_KEYS)

    def score(row) -> int:
        kel, kec, _kab, _prov = row
        s = 0
        if postcode and kel.kode_pos == postcode:
            s += 2
        if kec_names and norm(kec.nama) in kec_names:
            s += 2
        return s

    ranked = sorted(rows, key=score, reverse=True)
    scores = [score(r) for r in ranked]
    candidates: List = [_to_wilayah(*r) for r in ranked[:MAX_CANDIDATES]]

    # "matched" hanya jika kabupaten/kota ikut cocok DAN kandidat teratas jelas unggul/tunggal.
    unique_top = len(ranked) == 1 or scores[0] > scores[1]
    status = "matched" if (kab_ids and unique_top) else "ambiguous"
    if status == "ambiguous":
        logger.info("reverse wilayah ambiguous (%s, %s): address=%s", lat, lng, addr)
    return WilayahReverseOut(status=status, candidates=candidates, display_name=display)
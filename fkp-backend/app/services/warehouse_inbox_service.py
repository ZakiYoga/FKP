"""
Warehouse Inbox Service — list lintas FKP untuk halaman "Surat Jalan".

Tiga fungsi, semuanya read-only dan memakai permission `warehouse.surat_jalan.view_all`
(warehouse, admin_ho, rsm, direktur; superadmin bypass). Scope data GLOBAL,
tanpa filter area/distributor — sama dengan prinsip fkp_service._ROLE_GLOBAL_ACCESS.

  - list_surat_jalan_inbox : SJ lintas FKP, berpaginasi
  - get_surat_jalan_summary: jumlah SJ per status + jumlah FKP "Perlu Dibuat"
  - list_pending_fkp       : antrean FKP tukar_barang yang menunggu dibuatkan SJ

Definisi "Perlu Dibuat" (cermin guard create_surat_jalan di warehouse_service):
FKP berstatus accepted/in_process, resolusi tukar_barang, sudah diteruskan Admin HO
ke Warehouse, dan masih punya minimal satu item 'diterima' dengan
sisa_kuota = qty_disetujui - SUM(qty di SEMUA SJ untuk item itu) > 0.
SJ berstatus draft ikut menghabiskan kuota (sama seperti validasi di create).
"""
import math
from datetime import date
from typing import List, Optional

from fastapi import HTTPException
from sqlmodel import select, func
from sqlalchemy import or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.distributor import Distributor
from app.models.fkp import (
    FkpComplaint, FkpItem, FkpResolution, FkpStatus, StatusItem,
    SuratJalanStatus, TipeResolusi,
)
from app.models.outlet import Outlet
from app.models.product import ProductCatalog
from app.models.user import User
from app.models.warehouse import WarehouseSuratJalan, WarehouseSuratJalanItem
from app.schemas.warehouse import SuratJalanInboxItem, SuratJalanResponse
from app.services.permission_service import require_permission

PERMISSION = "warehouse.surat_jalan.view_all"


def _escape_like(value: str) -> str:
    """Escape wildcard LIKE (backslash, %, _) agar input user dianggap teks biasa."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _like_pattern(search: Optional[str]) -> Optional[str]:
    term = (search or "").strip()
    return f"%{_escape_like(term)}%" if term else None


def _total_pages(total: int, page_size: int) -> int:
    return max(1, math.ceil(total / page_size))


def _parse_status_filter(status: Optional[str]) -> List[str]:
    if not status:
        return []
    values: List[str] = []
    for raw in status.split(","):
        v = raw.strip()
        if v and v not in values:
            values.append(v)
    invalid = [v for v in values if v not in SuratJalanStatus.ALL]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Status surat jalan tidak valid: {', '.join(invalid)}. "
                f"Status yang diizinkan: {', '.join(SuratJalanStatus.ALL)}."
            ),
        )
    return values


# ─── Antrean "Perlu Dibuat" ─────────────────────────────────────────────────

def _qty_terkirim_subquery():
    """Total qty per fkp_item_id di SEMUA surat jalan (termasuk draft)."""
    return (
        select(
            WarehouseSuratJalanItem.fkp_item_id.label("fkp_item_id"),
            func.sum(WarehouseSuratJalanItem.qty).label("qty_terkirim"),
        )
        .where(WarehouseSuratJalanItem.fkp_item_id.is_not(None))
        .group_by(WarehouseSuratJalanItem.fkp_item_id)
        .subquery()
    )


def _pending_item_filters(terkirim):
    sisa = FkpItem.qty_disetujui - func.coalesce(terkirim.c.qty_terkirim, 0)
    return [
        FkpComplaint.status.in_([FkpStatus.ACCEPTED, FkpStatus.IN_PROCESS]),
        FkpResolution.tipe_resolusi == TipeResolusi.TUKAR_BARANG,
        FkpResolution.diteruskan_ke_warehouse.is_(True),
        FkpItem.status_item == StatusItem.DITERIMA,
        FkpItem.qty_disetujui.is_not(None),
        sisa > 0,
    ]


def _pending_fkp_ids_query(terkirim):
    return (
        select(FkpItem.fkp_id)
        .select_from(FkpItem)
        .join(FkpComplaint, FkpComplaint.id == FkpItem.fkp_id)
        .join(FkpResolution, FkpResolution.fkp_id == FkpComplaint.id)
        .outerjoin(terkirim, terkirim.c.fkp_item_id == FkpItem.id)
        .where(*_pending_item_filters(terkirim))
    )


async def _count_pending_fkp(db: AsyncSession) -> int:
    terkirim = _qty_terkirim_subquery()
    stmt = select(func.count(func.distinct(FkpItem.fkp_id))).select_from(FkpItem) \
        .join(FkpComplaint, FkpComplaint.id == FkpItem.fkp_id) \
        .join(FkpResolution, FkpResolution.fkp_id == FkpComplaint.id) \
        .outerjoin(terkirim, terkirim.c.fkp_item_id == FkpItem.id) \
        .where(*_pending_item_filters(terkirim))
    return (await db.execute(stmt)).scalar_one()


async def list_pending_fkp(
    user: User, kode_role: str, db: AsyncSession,
    *, page: int = 1, page_size: int = 20, search: Optional[str] = None,
) -> dict:
    await require_permission(kode_role, PERMISSION, db)

    terkirim = _qty_terkirim_subquery()
    pattern = _like_pattern(search)

    def apply(stmt):
        stmt = (
            stmt.select_from(FkpComplaint)
            .join(FkpResolution, FkpResolution.fkp_id == FkpComplaint.id)
            .join(Distributor, Distributor.id == FkpComplaint.distributor_id)
            .outerjoin(Outlet, Outlet.id == FkpComplaint.outlet_id)
            .where(FkpComplaint.id.in_(_pending_fkp_ids_query(terkirim)))
        )
        if pattern:
            stmt = stmt.where(or_(
                FkpComplaint.nomor_fkp.ilike(pattern, escape="\\"),
                Distributor.nama_perusahaan.ilike(pattern, escape="\\"),
                Distributor.kode_distributor.ilike(pattern, escape="\\"),
                Outlet.nama_toko.ilike(pattern, escape="\\"),
                Outlet.kode_outlet.ilike(pattern, escape="\\"),
            ))
        return stmt

    total = (await db.execute(apply(select(func.count(FkpComplaint.id))))).scalar_one()

    # Antrean terlama di atas: urut berdasarkan kapan FKP diteruskan ke warehouse.
    rows = (await db.execute(
        apply(select(
            FkpComplaint.id, FkpComplaint.nomor_fkp, FkpComplaint.status,
            FkpResolution.tanggal_diteruskan_ke_warehouse,
            Distributor.nama_perusahaan, Distributor.kode_distributor,
            Distributor.alamat_lengkap, Distributor.no_telepon,
            Outlet.nama_toko, Outlet.kode_outlet, Outlet.alamat_lengkap, Outlet.no_hp,
            Outlet.id,
        ))
        .order_by(
            FkpResolution.tanggal_diteruskan_ke_warehouse.asc().nulls_last(),
            FkpComplaint.created_at.asc(),
            FkpComplaint.id.asc(),
        )
        .offset((page - 1) * page_size).limit(page_size)
    )).all()

    fkp_ids = [r[0] for r in rows]
    items_by_fkp: dict = {fid: [] for fid in fkp_ids}
    sj_count: dict = {}

    if fkp_ids:
        item_rows = (await db.execute(
            select(
                FkpItem.id, FkpItem.fkp_id, ProductCatalog.nama_produk, FkpItem.jenis_kemasan,
                FkpItem.qty, FkpItem.qty_disetujui,
                func.coalesce(terkirim.c.qty_terkirim, 0),
            )
            .select_from(FkpItem)
            .join(FkpComplaint, FkpComplaint.id == FkpItem.fkp_id)
            .join(FkpResolution, FkpResolution.fkp_id == FkpComplaint.id)
            .join(ProductCatalog, ProductCatalog.id == FkpItem.product_id)
            .outerjoin(terkirim, terkirim.c.fkp_item_id == FkpItem.id)
            .where(FkpItem.fkp_id.in_(fkp_ids), *_pending_item_filters(terkirim))
            .order_by(FkpItem.created_at.asc(), FkpItem.id.asc())
        )).all()
        for item_id, fid, nama, kemasan, qty, qty_ok, qty_kirim in item_rows:
            qty_kirim = int(qty_kirim or 0)
            items_by_fkp[fid].append({
                "fkp_item_id": item_id,
                "nama_produk": nama,
                "jenis_kemasan": kemasan,
                "satuan_default": kemasan or "pcs",   # sama dengan form SJ lama di FkpDetailPage
                "qty_keluhan": qty,
                "qty_disetujui": qty_ok,
                "qty_terkirim": qty_kirim,
                "sisa_kuota": qty_ok - qty_kirim,
            })

        for fid, n in (await db.execute(
            select(WarehouseSuratJalan.fkp_id, func.count(WarehouseSuratJalan.id))
            .where(WarehouseSuratJalan.fkp_id.in_(fkp_ids))
            .group_by(WarehouseSuratJalan.fkp_id)
        )).all():
            sj_count[fid] = n

    items = []
    for (fid, nomor, fkp_status, tgl_diteruskan, dist_nama, dist_kode, dist_alamat, dist_telp,
         outlet_nama, outlet_kode, outlet_alamat, outlet_hp, outlet_id) in rows:
        # Penerima default: outlet bila FKP punya outlet, kalau tidak distributor. Bisa diedit di form.
        if outlet_id is not None:
            penerima = {"nama": outlet_nama, "alamat": outlet_alamat, "telepon": outlet_hp}
        else:
            penerima = {"nama": dist_nama, "alamat": dist_alamat, "telepon": dist_telp}
        items.append({
            "fkp_id": fid,
            "nomor_fkp": nomor,
            "fkp_status": fkp_status,
            "tanggal_diteruskan_ke_warehouse": tgl_diteruskan,
            "distributor_nama": dist_nama,
            "distributor_kode": dist_kode,
            "outlet_nama": outlet_nama,
            "outlet_kode": outlet_kode,
            "penerima_default": penerima,
            "items": items_by_fkp.get(fid, []),
            "jumlah_sj_terbit": sj_count.get(fid, 0),
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "total_pages": _total_pages(total, page_size)}


# ─── Surat Jalan lintas FKP ─────────────────────────────────────────────────

async def list_surat_jalan_inbox(
    user: User, kode_role: str, db: AsyncSession,
    *, page: int = 1, page_size: int = 20,
    status: Optional[str] = None, search: Optional[str] = None,
    tanggal_dari: Optional[date] = None, tanggal_sampai: Optional[date] = None,
) -> dict:
    await require_permission(kode_role, PERMISSION, db)

    statuses = _parse_status_filter(status)
    if tanggal_dari and tanggal_sampai and tanggal_dari > tanggal_sampai:
        raise HTTPException(
            status_code=400,
            detail="tanggal_dari tidak boleh lebih besar dari tanggal_sampai.",
        )
    pattern = _like_pattern(search)

    def apply(stmt):
        stmt = (
            stmt.select_from(WarehouseSuratJalan)
            .join(FkpComplaint, FkpComplaint.id == WarehouseSuratJalan.fkp_id)
            .join(Distributor, Distributor.id == FkpComplaint.distributor_id)
            .outerjoin(Outlet, Outlet.id == FkpComplaint.outlet_id)
        )
        if statuses:
            stmt = stmt.where(WarehouseSuratJalan.status.in_(statuses))
        if pattern:
            stmt = stmt.where(or_(
                WarehouseSuratJalan.nomor_surat_jalan.ilike(pattern, escape="\\"),
                FkpComplaint.nomor_fkp.ilike(pattern, escape="\\"),
                WarehouseSuratJalan.nama_penerima.ilike(pattern, escape="\\"),
                WarehouseSuratJalan.nomor_resi.ilike(pattern, escape="\\"),
                Distributor.nama_perusahaan.ilike(pattern, escape="\\"),
                Outlet.nama_toko.ilike(pattern, escape="\\"),
            ))
        if tanggal_dari:
            stmt = stmt.where(WarehouseSuratJalan.tanggal_surat_jalan >= tanggal_dari)
        if tanggal_sampai:
            stmt = stmt.where(WarehouseSuratJalan.tanggal_surat_jalan <= tanggal_sampai)
        return stmt

    total = (await db.execute(apply(select(func.count(WarehouseSuratJalan.id))))).scalar_one()

    jumlah_item = (
        select(func.count(WarehouseSuratJalanItem.id))
        .where(WarehouseSuratJalanItem.surat_jalan_id == WarehouseSuratJalan.id)
        .correlate(WarehouseSuratJalan).scalar_subquery()
    )
    total_qty = (
        select(func.coalesce(func.sum(WarehouseSuratJalanItem.qty), 0))
        .where(WarehouseSuratJalanItem.surat_jalan_id == WarehouseSuratJalan.id)
        .correlate(WarehouseSuratJalan).scalar_subquery()
    )

    rows = (await db.execute(
        apply(select(
            WarehouseSuratJalan, FkpComplaint.nomor_fkp, FkpComplaint.status,
            Distributor.nama_perusahaan, Outlet.nama_toko, jumlah_item, total_qty,
        ))
        .options(selectinload(WarehouseSuratJalan.items))
        .order_by(WarehouseSuratJalan.created_at.desc(), WarehouseSuratJalan.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).all()

    items = [
        SuratJalanInboxItem(
            **SuratJalanResponse.model_validate(sj).model_dump(),
            nomor_fkp=nomor_fkp,
            fkp_status=fkp_status,
            distributor_nama=dist_nama,
            outlet_nama=outlet_nama,
            jumlah_item=int(n_item or 0),
            total_qty=int(n_qty or 0),
        )
        for sj, nomor_fkp, fkp_status, dist_nama, outlet_nama, n_item, n_qty in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "total_pages": _total_pages(total, page_size)}


async def get_surat_jalan_summary(user: User, kode_role: str, db: AsyncSession) -> dict:
    await require_permission(kode_role, PERMISSION, db)

    rows = (await db.execute(
        select(WarehouseSuratJalan.status, func.count(WarehouseSuratJalan.id))
        .group_by(WarehouseSuratJalan.status)
    )).all()
    counts = {s: 0 for s in SuratJalanStatus.ALL}
    for st, n in rows:
        counts[st] = counts.get(st, 0) + n

    return {
        "counts": counts,
        "total": sum(counts.values()),
        "perlu_dibuat": await _count_pending_fkp(db),
    }
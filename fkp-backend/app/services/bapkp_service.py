"""
app/services/bapkp_service.py

Business logic untuk BAPKP (Berita Acara Pemeriksaan Keluhan Pelanggan,
SPP/QC/FORM/25).

CATATAN PENAMAAN (baca dulu): project ini SUDAH punya
app/services/berita_acara_pdf_service.py dengan fungsi
`build_berita_acara_context()` -- untuk dokumen BEDA (Berita Acara
Pemusnahan, SPP/QC/FORM 26). Modul ini sengaja pakai nama `bapkp_service`
dan `build_bapkp_context()` (BUKAN `berita_acara_service` /
`build_berita_acara_context()`) supaya tidak bentrok nama fungsi/file
dengan yang sudah ada.

Prinsip utama (sesuai permintaan): QC TIDAK perlu input ulang data yang
sudah ada di FKP.

  1. get_bapkp_draft()   -> auto-fill preview dari data FKP yang sudah ada.
  2. create_bapkp()      -> simpan HANYA field BAPKP-only.
  3. build_bapkp_context() -> dipakai bersama oleh get_bapkp_detail()
     (response API) dan bapkp_pdf_service.py (generate PDF).

── PERMISSION (2 lapis, mengikuti pola fkp_service.py) ─────────────────────
Lapis 1 (Action, DB-driven):
    fkp.bapkp.create / fkp.bapkp.update / fkp.bapkp.view
    (BUKAN fkp.berita_acara.* -- kode itu sudah dipakai fitur Pemusnahan)

Lapis 2 (Data scope, hardcode) -- BAPKP adalah dokumen hasil pemeriksaan
QC internal, setara "hasil_pemeriksaan_qc" yang di fkp_service.py sudah
disembunyikan dari outlet/distributor/sc_spv (ROLE_HASIL_QC_HIDDEN).
Dibatasi ke fkp_service._ROLE_GLOBAL_ACCESS, `apsm` ikut diblokir karena
BAPKP bukan bagian alur approval APSM.

── DESAIN PENTING: kondisi_sample ───────────────────────────────────────
FkpItem.kondisi_sample SUDAH ADA di model tapi tidak pernah diisi lewat
schema mana pun saat ini. BAPKP jadi titik pengisian resminya --
create_bapkp()/update_bapkp() MENULIS LANGSUNG ke FkpItem.kondisi_sample,
BUKAN menyimpan salinan di tabel fkp_bapkp_items (lihat app/models/bapkp.py).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.models.bapkp import FkpBapkp, FkpBapkpItem
from app.models.fkp import FkpAttachment, FkpItem, FkpStatus
from app.models.distributor import Distributor
from app.models.outlet import Outlet
from app.models.user import User

from app.schemas.bapkp import (
    BapkpCreate,
    BapkpUpdate,
    BapkpDraftItem,
    BapkpDraftResponse,
)

from app.services.permission_service import require_permission
from app.services.pdf_utils import get_user_nama, load_file_base64
# Reuse helper & konstanta yang SUDAH ADA di fkp_service.py -- jangan
# duplikasi _get_or_404 / _ROLE_GLOBAL_ACCESS supaya kalau nanti berubah
# (mis. ada role baru), BAPKP otomatis ikut sinkron.
from app.services.fkp_service import _ROLE_GLOBAL_ACCESS, _get_or_404
from app.utils.bapkp_number import generate_nomor_ba


# ─── Mapping tipe attachment -> slot foto BAPKP (sama seperti fkp_pdf_service) ─
_FOTO_TIPE_MAP: Dict[str, str] = {
    "foto_expired": "expired",
    "foto_keluhan": "keluhan",
    "foto_sample": "keluhan",
    "foto_kode_produksi": "kode_produksi",
}

# BAPKP baru masuk akal dibuat setelah QC mulai/menyelesaikan investigasi.
_STATUS_BOLEH_BUAT_BAPKP = {FkpStatus.IN_INVESTIGATION, FkpStatus.INVESTIGATED}


# ─── Data-scope guard (Lapis 2, hardcode) ──────────────────────────────────

def _assert_role_boleh_akses_bapkp(kode_role: str) -> None:
    """
    Role di luar _ROLE_GLOBAL_ACCESS (outlet/distributor/sc_spv/apsm)
    TIDAK BOLEH create/view/update/download BAPKP sama sekali.
    """
    if kode_role not in _ROLE_GLOBAL_ACCESS:
        raise HTTPException(
            status_code=403,
            detail="Role Anda tidak memiliki akses ke Berita Acara Pemeriksaan (BAPKP).",
        )


def _hitung_tenggat_terpenuhi(
    tanggal_pengajuan: Optional[date], tanggal_diterima_qc: Optional[date]
) -> Optional[bool]:
    """< 1 minggu dari tanggal keluhan sampai tanggal_diterima_qc -> terpenuhi.
    Dihitung on-the-fly, bukan disimpan, supaya tidak ada 2 sumber kebenaran."""
    if not tanggal_pengajuan or not tanggal_diterima_qc:
        return None
    return (tanggal_diterima_qc - tanggal_pengajuan).days < 7


# ═════════════════════════════════════════════════════════════════════════
# DRAFT -- auto-fill sebelum create
# ═════════════════════════════════════════════════════════════════════════

async def get_bapkp_draft(
    fkp_id: uuid.UUID, user: User, kode_role: str, db: AsyncSession
) -> BapkpDraftResponse:
    await require_permission(kode_role, "fkp.bapkp.view", db)
    _assert_role_boleh_akses_bapkp(kode_role)

    fkp = await _get_or_404(fkp_id, db)

    outlet = None
    if fkp.outlet_id:
        r = await db.execute(select(Outlet).where(Outlet.id == fkp.outlet_id))
        outlet = r.scalar_one_or_none()

    distributor = None
    if fkp.distributor_id:
        r = await db.execute(select(Distributor).where(Distributor.id == fkp.distributor_id))
        distributor = r.scalar_one_or_none()

    r = await db.execute(
        select(FkpItem)
        .where(FkpItem.fkp_id == fkp_id)
        .options(selectinload(FkpItem.product))
        .order_by(FkpItem.created_at)
    )
    items = r.scalars().all()

    r_bapkp = await db.execute(select(FkpBapkp).where(FkpBapkp.fkp_id == fkp_id))
    bapkp_existing = r_bapkp.scalar_one_or_none()

    draft_items = [
        BapkpDraftItem(
            fkp_item_id=item.id,
            nama_produk=(
                item.nama_produk_custom
                or (item.product.nama_produk if item.product else None)
                or "\u2014"
            ),
            jenis_kemasan=item.jenis_kemasan or (item.product.jenis_kemasan if item.product else None),
            batch_number=item.batch_number,
            qty=item.qty,
            expired_date=item.expired_date,
            deskripsi_keluhan=item.deskripsi_keluhan,
            ada_sample_keluhan=item.ada_sample_keluhan,
            kondisi_sample=item.kondisi_sample,
        )
        for item in items
    ]

    return BapkpDraftResponse(
        fkp_id=fkp.id,
        nomor_fkp=fkp.nomor_fkp,
        tanggal_pengajuan=fkp.tanggal_pengajuan.date() if fkp.tanggal_pengajuan else None,
        prioritas=fkp.prioritas,
        outlet_nama=outlet.nama_toko if outlet else None,
        outlet_alamat=outlet.alamat_lengkap if outlet else None,
        outlet_no_hp=outlet.no_hp if outlet else None,
        outlet_email=outlet.email if outlet else None,
        distributor_nama=distributor.nama_perusahaan if distributor else None,
        items=draft_items,
        nomor_ba_disarankan=await generate_nomor_ba(db),
        sudah_ada_bapkp=bapkp_existing is not None,
    )


# ═════════════════════════════════════════════════════════════════════════
# CREATE
# ═════════════════════════════════════════════════════════════════════════

async def create_bapkp(
    fkp_id: uuid.UUID, data: BapkpCreate, user: User, kode_role: str, db: AsyncSession
) -> FkpBapkp:
    await require_permission(kode_role, "fkp.bapkp.create", db)
    _assert_role_boleh_akses_bapkp(kode_role)

    fkp = await _get_or_404(fkp_id, db)

    if fkp.status not in _STATUS_BOLEH_BUAT_BAPKP:
        raise HTTPException(
            status_code=400,
            detail=(
                f"BAPKP hanya bisa dibuat saat FKP berstatus salah satu dari "
                f"{sorted(_STATUS_BOLEH_BUAT_BAPKP)}. Status saat ini: '{fkp.status}'."
            ),
        )

    r_existing = await db.execute(select(FkpBapkp).where(FkpBapkp.fkp_id == fkp_id))
    if r_existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="FKP ini sudah memiliki BAPKP. Gunakan endpoint update (PATCH) untuk mengubahnya.",
        )

    # ── Validasi: fkp_item_id yang dikirim harus milik FKP ini, dan SEMUA
    #    item milik FKP wajib tercakup (tidak boleh sebagian) ─────────────
    r_items = await db.execute(select(FkpItem).where(FkpItem.fkp_id == fkp_id))
    fkp_items_by_id: Dict[uuid.UUID, FkpItem] = {i.id: i for i in r_items.scalars().all()}
    valid_item_ids = set(fkp_items_by_id.keys())

    input_item_ids = {i.fkp_item_id for i in data.items}
    asing = input_item_ids - valid_item_ids
    if asing:
        raise HTTPException(
            status_code=400,
            detail=f"fkp_item_id berikut bukan bagian dari FKP ini: {sorted(str(x) for x in asing)}",
        )

    kurang = valid_item_ids - input_item_ids
    if kurang:
        raise HTTPException(
            status_code=400,
            detail=(
                "Semua item pada FKP wajib diisi datanya di BAPKP. "
                f"Item yang belum diisi: {sorted(str(x) for x in kurang)}"
            ),
        )

    nomor_ba = data.nomor_ba or await generate_nomor_ba(db)

    bapkp = FkpBapkp(
        fkp_id=fkp_id,
        nomor_ba=nomor_ba,
        hari_pemeriksaan=data.hari_pemeriksaan,
        tanggal_pemeriksaan=data.tanggal_pemeriksaan,
        tanggal_diterima_qc=data.tanggal_diterima_qc,
        catatan_pemeriksaan=data.catatan_pemeriksaan,
        dibuat_oleh=user.id,
    )
    db.add(bapkp)
    await db.flush()  # supaya bapkp.id tersedia utk FK item di bawah

    for item_input in data.items:
        db.add(FkpBapkpItem(
            bapkp_id=bapkp.id,
            fkp_item_id=item_input.fkp_item_id,
            tanggal_kadaluarsa=item_input.tanggal_kadaluarsa,
            umur_produk=item_input.umur_produk,
            tanggal_dikirim=item_input.tanggal_dikirim,
            lama_di_gudang_spp=item_input.lama_di_gudang_spp,
        ))

        # kondisi_sample ditulis LANGSUNG ke FkpItem yang sudah ada
        # (lihat docstring modul) -- bukan disimpan di FkpBapkpItem.
        if item_input.kondisi_sample is not None:
            fkp_item = fkp_items_by_id[item_input.fkp_item_id]
            fkp_item.kondisi_sample = item_input.kondisi_sample
            fkp_item.updated_at = datetime.now(timezone.utc)
            db.add(fkp_item)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Nomor BA bentrok dengan data lain (kemungkinan race condition), silakan coba lagi.",
        )

    return await _load_bapkp_or_404(fkp_id, db)


# ═════════════════════════════════════════════════════════════════════════
# UPDATE
# ═════════════════════════════════════════════════════════════════════════

async def update_bapkp(
    fkp_id: uuid.UUID, data: BapkpUpdate, user: User, kode_role: str, db: AsyncSession
) -> FkpBapkp:
    await require_permission(kode_role, "fkp.bapkp.update", db)
    _assert_role_boleh_akses_bapkp(kode_role)

    bapkp = await _load_bapkp_or_404(fkp_id, db)

    # Ownership sederhana: hanya pembuat BAPKP atau superadmin yang boleh
    # edit -- pola sama seperti hapus_dokumen() di fkp_service.py.
    from app.services.authz_helpers import is_superadmin
    if not await is_superadmin(user, db) and bapkp.dibuat_oleh != user.id:
        raise HTTPException(
            status_code=403,
            detail="Hanya pembuat BAPKP atau superadmin yang bisa mengubahnya.",
        )

    for field in ("hari_pemeriksaan", "tanggal_pemeriksaan", "tanggal_diterima_qc", "catatan_pemeriksaan"):
        value = getattr(data, field)
        if value is not None:
            setattr(bapkp, field, value)
    bapkp.updated_at = datetime.now(timezone.utc)
    db.add(bapkp)

    if data.items is not None:
        r_items = await db.execute(select(FkpItem).where(FkpItem.fkp_id == fkp_id))
        fkp_items_by_id: Dict[uuid.UUID, FkpItem] = {i.id: i for i in r_items.scalars().all()}
        valid_item_ids = set(fkp_items_by_id.keys())
        input_item_ids = {i.fkp_item_id for i in data.items}

        asing = input_item_ids - valid_item_ids
        if asing:
            raise HTTPException(
                status_code=400,
                detail=f"fkp_item_id berikut bukan bagian dari FKP ini: {sorted(str(x) for x in asing)}",
            )

        # Full replace utk item-item BAPKP (jumlahnya kecil, cost rendah).
        r_old = await db.execute(
            select(FkpBapkpItem).where(FkpBapkpItem.bapkp_id == bapkp.id)
        )
        for old_item in r_old.scalars().all():
            await db.delete(old_item)

        for item_input in data.items:
            db.add(FkpBapkpItem(
                bapkp_id=bapkp.id,
                fkp_item_id=item_input.fkp_item_id,
                tanggal_kadaluarsa=item_input.tanggal_kadaluarsa,
                umur_produk=item_input.umur_produk,
                tanggal_dikirim=item_input.tanggal_dikirim,
                lama_di_gudang_spp=item_input.lama_di_gudang_spp,
            ))
            if item_input.kondisi_sample is not None:
                fkp_item = fkp_items_by_id[item_input.fkp_item_id]
                fkp_item.kondisi_sample = item_input.kondisi_sample
                fkp_item.updated_at = datetime.now(timezone.utc)
                db.add(fkp_item)

    await db.commit()
    return await _load_bapkp_or_404(fkp_id, db)


# ═════════════════════════════════════════════════════════════════════════
# LOAD HELPERS
# ═════════════════════════════════════════════════════════════════════════

async def _load_bapkp_or_404(fkp_id: uuid.UUID, db: AsyncSession) -> FkpBapkp:
    r = await db.execute(
        select(FkpBapkp)
        .where(FkpBapkp.fkp_id == fkp_id)
        .options(selectinload(FkpBapkp.items))
    )
    bapkp = r.scalar_one_or_none()
    if not bapkp:
        raise HTTPException(status_code=404, detail="BAPKP untuk FKP ini belum dibuat.")
    return bapkp


# ═════════════════════════════════════════════════════════════════════════
# CONTEXT GABUNGAN (dipakai API detail & PDF service)
# ═════════════════════════════════════════════════════════════════════════

async def build_bapkp_context(fkp_id: uuid.UUID, db: AsyncSession, upload_dir: str = "uploads") -> Dict:
    """
    Gabungkan data FKP (outlet, distributor, item asli -- termasuk
    FkpItem.kondisi_sample) + data BAPKP (hasil pemeriksaan QC) jadi 1
    dict context, siap dipakai untuk:
      - serialisasi response API (get_bapkp_detail)
      - render template Jinja2 BAPKP (bapkp_pdf_service.py)

    `upload_dir` diterima sbg parameter (bukan hardcode "uploads") supaya
    caller (router) bisa meneruskan settings.UPLOAD_DIR, sama seperti
    pola generate_fkp_pdf(fkp_id, db, upload_dir=settings.UPLOAD_DIR)
    yang sudah dipakai di fkp.py.
    """
    fkp = await _get_or_404(fkp_id, db)
    bapkp = await _load_bapkp_or_404(fkp_id, db)

    outlet = None
    if fkp.outlet_id:
        r = await db.execute(select(Outlet).where(Outlet.id == fkp.outlet_id))
        outlet = r.scalar_one_or_none()

    distributor = None
    if fkp.distributor_id:
        r = await db.execute(select(Distributor).where(Distributor.id == fkp.distributor_id))
        distributor = r.scalar_one_or_none()

    r = await db.execute(
        select(FkpItem)
        .where(FkpItem.fkp_id == fkp_id)
        .options(selectinload(FkpItem.product))
        .order_by(FkpItem.created_at)
    )
    fkp_items_by_id: Dict[uuid.UUID, FkpItem] = {item.id: item for item in r.scalars().all()}

    r_att = await db.execute(select(FkpAttachment).where(FkpAttachment.fkp_id == fkp_id))
    attachments = r_att.scalars().all()
    att_by_item: Dict[uuid.UUID, List[FkpAttachment]] = {}
    for att in attachments:
        if att.fkp_item_id:
            att_by_item.setdefault(att.fkp_item_id, []).append(att)

    merged_items: List[Dict] = []
    for bapkp_item in bapkp.items:
        src = fkp_items_by_id.get(bapkp_item.fkp_item_id)
        if src is None:
            continue  # item asli sudah tidak ada -- seharusnya tidak terjadi

        nama_produk = (
            src.nama_produk_custom
            or (src.product.nama_produk if src.product else None)
            or "\u2014"
        )
        item_attachments = att_by_item.get(src.id, [])
        foto_types = {
            _FOTO_TIPE_MAP[a.tipe_dokumen]
            for a in item_attachments
            if a.tipe_dokumen in _FOTO_TIPE_MAP
        }

        merged_items.append({
            "id": str(src.id),
            "nama_produk": nama_produk,
            "jenis_kemasan": src.jenis_kemasan or (src.product.jenis_kemasan if src.product else None),
            "qty": src.qty,
            "batch_number": src.batch_number,
            "deskripsi_keluhan": src.deskripsi_keluhan,
            "ada_sample_keluhan": src.ada_sample_keluhan,
            # kondisi_sample dibaca dari FkpItem langsung (lihat catatan
            # di docstring modul & app/models/bapkp.py ASUMSI #3).
            "kondisi_sample": src.kondisi_sample,
            "tanggal_kadaluarsa": bapkp_item.tanggal_kadaluarsa or src.expired_date,
            "expired_date": src.expired_date,
            "umur_produk": bapkp_item.umur_produk,
            "tanggal_dikirim": bapkp_item.tanggal_dikirim,
            "lama_di_gudang_spp": bapkp_item.lama_di_gudang_spp,
            "foto_types": list(foto_types),
            "attachments": [
                {
                    "tipe_dokumen": a.tipe_dokumen,
                    "keterangan": a.keterangan,
                    "base64": load_file_base64(upload_dir, a.url),
                }
                for a in item_attachments
            ],
        })

    submitted_by_name = await get_user_nama(db, fkp.submitted_by)
    tanggal_pengajuan_date = fkp.tanggal_pengajuan.date() if fkp.tanggal_pengajuan else None

    return {
        "fkp": {
            "id": str(fkp.id),
            "nomor_fkp": fkp.nomor_fkp,
            "status": fkp.status,
            "prioritas": fkp.prioritas,
            "lokasi_pembelian": fkp.lokasi_pembelian,
            "catatan_distributor": fkp.catatan_distributor,
            "tanggal_pengajuan": fkp.tanggal_pengajuan,
        },
        "ba": {
            "id": bapkp.id,
            "nomor_ba": bapkp.nomor_ba,
            "hari_pemeriksaan": bapkp.hari_pemeriksaan,
            "tanggal_pemeriksaan": bapkp.tanggal_pemeriksaan,
            "tanggal_diterima_qc": bapkp.tanggal_diterima_qc,
            "tenggat_terpenuhi": _hitung_tenggat_terpenuhi(tanggal_pengajuan_date, bapkp.tanggal_diterima_qc),
            "catatan_pemeriksaan": bapkp.catatan_pemeriksaan,
            "dibuat_oleh": bapkp.dibuat_oleh,
            "created_at": bapkp.created_at,
            "updated_at": bapkp.updated_at,
        },
        "outlet": {
            "nama_toko": outlet.nama_toko if outlet else None,
            "alamat_lengkap": outlet.alamat_lengkap if outlet else None,
            "no_hp": outlet.no_hp if outlet else None,
            "email": outlet.email if outlet else None,
            "distributor_name": distributor.nama_perusahaan if distributor else None,
        } if outlet else None,
        "items": merged_items,
        "submitted_by_name": submitted_by_name,
        "generated_at": datetime.now(timezone.utc),
    }


async def get_bapkp_detail(fkp_id: uuid.UUID, user: User, kode_role: str, db: AsyncSession) -> Dict:
    await require_permission(kode_role, "fkp.bapkp.view", db)
    _assert_role_boleh_akses_bapkp(kode_role)
    return await build_bapkp_context(fkp_id, db)
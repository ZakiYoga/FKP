"""
Warehouse Service — CRUD & state machine WarehouseSuratJalan (barang
pengganti outbound untuk resolusi tukar_barang).

[KEPUTUSAN — Kontradiksi A, dikonfirmasi user] SJ bisa dibuat SELAGI FKP
masih berstatus ACCEPTED, dan pembuatan SJ PERTAMA langsung men-trigger
transisi accepted → in_process (bukan menunggu status → issued). Bisa lebih
dari 1 SJ per FKP (pengiriman bertahap) — SJ kedua dan seterusnya dibuat
selagi FKP sudah in_process, dan tidak mencoba trigger transisi lagi.

[KEPUTUSAN — Kontradiksi B] metode_penanganan_fisik == DIMUSNAHKAN adalah
HARD GATE di sini: wajib sudah ada attachment
TipeDokumen.BERITA_ACARA_PEMUSNAHAN_TUKAR_BARANG sebelum SJ bisa dibuat.
Gate berita_acara_penukaran (dari QC) SENGAJA TIDAK dijadikan hard gate —
informal/SOP saja, supaya kasus top_urgent (barang berkutu/menjamur, harus
diganti cepat) tidak terblokir sistem.
"""
import uuid
from datetime import datetime, date, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlmodel import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fkp import FkpComplaint, FkpResolution, FkpAttachment, FkpStatus, TipeResolusi, MetodePenangananFisik, TipeDokumen
from app.models.warehouse import WarehouseSuratJalan, WarehouseSuratJalanItem
from app.models.user import User
from app.services.permission_service import require_permission
from app.services.fkp_service import _get_or_404, _log, kirim_notifikasi_transisi
from app.services.notification_service import notify_roles, notify_user, TipeNotifikasi


async def _get_resolution_or_404(fkp_id: uuid.UUID, db: AsyncSession) -> FkpResolution:
    r = await db.execute(select(FkpResolution).where(FkpResolution.fkp_id == fkp_id))
    resolusi = r.scalar_one_or_none()
    if not resolusi:
        raise HTTPException(status_code=400, detail="Resolusi belum dibuat untuk FKP ini.")
    return resolusi


async def _get_sj_or_404(sj_id: uuid.UUID, fkp_id: uuid.UUID, db: AsyncSession) -> WarehouseSuratJalan:
    r = await db.execute(
        select(WarehouseSuratJalan)
        .options(selectinload(WarehouseSuratJalan.items))
        .where(WarehouseSuratJalan.id == sj_id, WarehouseSuratJalan.fkp_id == fkp_id)
    )
    sj = r.scalar_one_or_none()
    if not sj:
        raise HTTPException(status_code=404, detail="Surat jalan tidak ditemukan.")
    return sj


# ─── CREATE ─────────────────────────────────────────────────────────────────

async def create_surat_jalan(
    fkp_id: uuid.UUID, data, user: User, kode_role: str, db: AsyncSession
) -> WarehouseSuratJalan:
    await require_permission(kode_role, "warehouse.surat_jalan.create", db)

    fkp = await _get_or_404(fkp_id, db)

    # [FIX Kontradiksi A] ACCEPTED (SJ pertama) atau IN_PROCESS (SJ susulan
    # — pengiriman bertahap karena stok kurang, sesuai keputusan user #7).
    if fkp.status not in (FkpStatus.ACCEPTED, FkpStatus.IN_PROCESS):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Surat jalan hanya bisa dibuat saat FKP berstatus 'accepted' "
                f"atau 'in_process'. Status saat ini: '{fkp.status}'."
            ),
        )

    resolusi = await _get_resolution_or_404(fkp_id, db)
    if resolusi.tipe_resolusi != TipeResolusi.TUKAR_BARANG:
        raise HTTPException(
            status_code=400,
            detail="Surat jalan hanya relevan untuk resolusi bertipe 'tukar_barang'.",
        )

    # [FIX Kontradiksi B] Hard gate — metode=dimusnahkan wajib ada BA dulu.
    if resolusi.metode_penanganan_fisik == MetodePenangananFisik.DIMUSNAHKAN:
        r_bukti = await db.execute(
            select(FkpAttachment).where(
                FkpAttachment.fkp_id == fkp_id,
                FkpAttachment.tipe_dokumen == TipeDokumen.BERITA_ACARA_PEMUSNAHAN_TUKAR_BARANG,
            )
        )
        if not r_bukti.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=(
                    "Upload dokumen 'Berita Acara Pemusnahan dan Tukar Barang' "
                    "terlebih dahulu sebelum menerbitkan surat jalan."
                ),
            )
    # CATATAN: gate berita_acara_penukaran (dari QC) SENGAJA tidak dicek di
    # sini — informal/SOP, lihat docstring modul di atas.

    r_dup = await db.execute(
        select(WarehouseSuratJalan).where(WarehouseSuratJalan.nomor_surat_jalan == data.nomor_surat_jalan)
    )
    if r_dup.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Nomor surat jalan '{data.nomor_surat_jalan}' sudah digunakan.")

    sj = WarehouseSuratJalan(
        fkp_id=fkp_id,
        nomor_surat_jalan=data.nomor_surat_jalan,
        tanggal_surat_jalan=data.tanggal_surat_jalan,
        nama_penerima=data.nama_penerima,
        alamat_penerima=data.alamat_penerima,
        telepon_penerima=data.telepon_penerima,
        ekspedisi=data.ekspedisi,
        nomor_resi=data.nomor_resi,
        tanggal_kirim=data.tanggal_kirim,
        catatan=data.catatan,
        dibuat_oleh=user.id,
    )
    db.add(sj)
    await db.flush()

    for item_data in data.items:
        db.add(WarehouseSuratJalanItem(
            surat_jalan_id=sj.id,
            fkp_item_id=item_data.fkp_item_id,
            nama_produk=item_data.nama_produk,
            qty=item_data.qty,
            satuan=item_data.satuan,
            keterangan=item_data.keterangan,
        ))

    # Trigger transisi HANYA untuk SJ pertama (fkp masih ACCEPTED). Kalau SJ
    # susulan (fkp sudah IN_PROCESS), tidak ada transisi lagi yang perlu dicatat.
    if fkp.status == FkpStatus.ACCEPTED:
        lama = fkp.status
        fkp.status = FkpStatus.IN_PROCESS
        fkp.updated_at = datetime.now(timezone.utc)
        db.add(fkp)
        await _log(
            db, fkp.id, lama, FkpStatus.IN_PROCESS, user.id,
            f"Surat jalan {sj.nomor_surat_jalan} dibuat, proses pengiriman barang pengganti dimulai.",
        )
        await kirim_notifikasi_transisi(db, fkp, lama, FkpStatus.IN_PROCESS, user)
        # [Phase 8 — Notifikasi §12.1] Generic kirim_notifikasi_transisi() di
        # atas sudah notify submitter + admin_ho. Tambahan rsm/superadmin
        # sesuai baris "confirm-resolusi (accepted → in_process)" §12.1 —
        # berlaku untuk SEMUA jalur trigger in_process, termasuk lewat SJ ini.
        await notify_roles(
            db, fkp.id, ["rsm", "superadmin"],
            f"FKP Mulai Diproses: {fkp.nomor_fkp}",
            f"FKP {fkp.nomor_fkp} masuk tahap in_process — resolusi tukar_barang.",
            TipeNotifikasi.STATUS_CHANGE,
        )

    await db.commit()
    return await _get_sj_or_404(sj.id, fkp_id, db)


# ─── READ ───────────────────────────────────────────────────────────────────

async def list_surat_jalan(fkp_id: uuid.UUID, user: User, kode_role: str, db: AsyncSession) -> List[WarehouseSuratJalan]:
    from app.services.fkp_service import get_fkp_detail
    await get_fkp_detail(fkp_id, db, user, kode_role)

    r = await db.execute(
        select(WarehouseSuratJalan)
        .options(selectinload(WarehouseSuratJalan.items))
        .where(WarehouseSuratJalan.fkp_id == fkp_id)
        .order_by(WarehouseSuratJalan.created_at.desc())
    )
    return r.scalars().all()


async def get_surat_jalan_detail(
    fkp_id: uuid.UUID, sj_id: uuid.UUID, user: User, kode_role: str, db: AsyncSession
) -> WarehouseSuratJalan:
    from app.services.fkp_service import get_fkp_detail
    await get_fkp_detail(fkp_id, db, user, kode_role)
    return await _get_sj_or_404(sj_id, fkp_id, db)


# ─── UPDATE (hanya draft) ───────────────────────────────────────────────────

async def update_surat_jalan(
    fkp_id: uuid.UUID, sj_id: uuid.UUID, data, user: User, kode_role: str, db: AsyncSession
) -> WarehouseSuratJalan:
    await require_permission(kode_role, "warehouse.surat_jalan.create", db)
    sj = await _get_sj_or_404(sj_id, fkp_id, db)

    if sj.status != "draft":
        raise HTTPException(status_code=400, detail="Surat jalan hanya bisa diedit selagi berstatus 'draft'.")

    update_data = data.model_dump(exclude_none=True)
    if "nomor_surat_jalan" in update_data and update_data["nomor_surat_jalan"] != sj.nomor_surat_jalan:
        r_dup = await db.execute(
            select(WarehouseSuratJalan).where(
                WarehouseSuratJalan.nomor_surat_jalan == update_data["nomor_surat_jalan"],
                WarehouseSuratJalan.id != sj_id,
            )
        )
        if r_dup.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Nomor surat jalan sudah digunakan SJ lain.")

    for key, value in update_data.items():
        setattr(sj, key, value)
    sj.updated_at = datetime.now(timezone.utc)
    db.add(sj)
    await db.commit()
    return await _get_sj_or_404(sj_id, fkp_id, db)


# ─── TRANSISI ───────────────────────────────────────────────────────────────

async def issue_surat_jalan(
    fkp_id: uuid.UUID, sj_id: uuid.UUID, user: User, kode_role: str, db: AsyncSession
) -> WarehouseSuratJalan:
    await require_permission(kode_role, "warehouse.surat_jalan.issue", db)
    sj = await _get_sj_or_404(sj_id, fkp_id, db)

    if sj.status != "draft":
        raise HTTPException(status_code=400, detail=f"Surat jalan harus berstatus 'draft', bukan '{sj.status}'.")
    if not sj.items:
        raise HTTPException(status_code=400, detail="Surat jalan belum memiliki item — tidak bisa diterbitkan.")

    fkp = await _get_or_404(fkp_id, db)

    from app.services.surat_jalan_pdf_service import generate_and_save_surat_jalan_pdf
    url_pdf = await generate_and_save_surat_jalan_pdf(sj, fkp, user, db)

    sj.url_pdf = url_pdf
    sj.status = "issued"
    sj.updated_at = datetime.now(timezone.utc)
    db.add(sj)

    # [Phase 8 — Notifikasi §12.1] SJ issued: admin_ho, rsm, superadmin
    await notify_roles(
        db, fkp_id, ["admin_ho", "rsm", "superadmin"],
        "Surat jalan diterbitkan",
        f"SJ No. {sj.nomor_surat_jalan} untuk FKP {fkp.nomor_fkp} sudah diterbitkan warehouse.",
        TipeNotifikasi.WAREHOUSE_SJ,
    )

    await db.commit()
    return await _get_sj_or_404(sj_id, fkp_id, db)


async def ship_surat_jalan(
    fkp_id: uuid.UUID, sj_id: uuid.UUID, data, user: User, kode_role: str, db: AsyncSession
) -> WarehouseSuratJalan:
    await require_permission(kode_role, "warehouse.surat_jalan.ship", db)
    sj = await _get_sj_or_404(sj_id, fkp_id, db)

    if sj.status != "issued":
        raise HTTPException(status_code=400, detail=f"Surat jalan harus berstatus 'issued', bukan '{sj.status}'.")

    if data.ekspedisi:
        sj.ekspedisi = data.ekspedisi
    if data.nomor_resi:
        sj.nomor_resi = data.nomor_resi
    sj.tanggal_kirim = data.tanggal_kirim or date.today()
    sj.status = "shipped"
    sj.updated_at = datetime.now(timezone.utc)
    db.add(sj)
    await db.commit()
    return await _get_sj_or_404(sj_id, fkp_id, db)


async def confirm_delivery_sj(
    fkp_id: uuid.UUID, sj_id: uuid.UUID, user: User, kode_role: str, db: AsyncSession
) -> WarehouseSuratJalan:
    await require_permission(kode_role, "warehouse.surat_jalan.confirm_delivery", db)
    sj = await _get_sj_or_404(sj_id, fkp_id, db)

    if sj.status != "shipped":
        raise HTTPException(status_code=400, detail=f"Surat jalan harus berstatus 'shipped', bukan '{sj.status}'.")

    sj.status = "delivered"
    sj.tanggal_delivered = datetime.now(timezone.utc)
    sj.updated_at = datetime.now(timezone.utc)
    db.add(sj)

    # [Phase 8 — Notifikasi §12.1] SJ delivered: submitter (outlet/distributor)
    fkp = await _get_or_404(fkp_id, db)
    await notify_user(
        db, fkp.submitted_by, fkp_id,
        "Barang pengganti diterima",
        f"Barang pengganti FKP {fkp.nomor_fkp} sudah diterima. SJ: {sj.nomor_surat_jalan}",
        TipeNotifikasi.WAREHOUSE_SJ,
    )

    await db.commit()
    return await _get_sj_or_404(sj_id, fkp_id, db)
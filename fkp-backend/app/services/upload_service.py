"""
Upload Service — menangani upload file foto bukti FKP ke local storage.
Fase 1: simpan di folder uploads/. Fase selanjutnya: migrasi ke S3/MinIO.

[FIX #7] Sebelumnya upload_attachment() tidak melakukan pengecekan akses
sama sekali — siapa pun dengan token valid bisa upload ke fkp_id manapun
selama dia tahu UUID-nya. Sekarang ditambahkan scope check berbasis
FkpComplaint.distributor_id, konsisten dengan aturan scoping section 3
dokumen (distributor_id sebagai anchor utama).

[FIX #3 turunan] delete_attachment() sebelumnya bandingkan kode_role dengan
string "superadmin" — diganti memakai is_superadmin() berbasis flag.

FIX sebelumnya: Upload sekarang mendukung fkp_item_id opsional sehingga foto
bisa dikaitkan langsung ke item tertentu (bukan hanya level FKP).
"""
import os
import uuid
import aiofiles
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.fkp import FkpAttachment, FkpComplaint, FkpItem, FkpStatus
from app.models.user import User
from app.models.fkp import TipeDokumen
from app.services.authz_helpers import (
    is_superadmin,
    has_global_access,
    assert_distributor_in_scope,
)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime"}
MAX_SIZE_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_DOC_TYPES = {"application/pdf", "application/msword",
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES | ALLOWED_DOC_TYPES


async def upload_attachment(
    fkp_id: uuid.UUID,
    file: UploadFile,
    user: User,
    db: AsyncSession,
    kode_role: str,
    fkp_item_id: Optional[uuid.UUID] = None,
    tipe_dokumen: Optional[str] = None,
    keterangan: Optional[str] = None,
) -> FkpAttachment:

    # Validasi FKP ada
    result = await db.execute(select(FkpComplaint).where(FkpComplaint.id == fkp_id))
    fkp = result.scalar_one_or_none()
    if not fkp:
        raise HTTPException(status_code=404, detail="FKP tidak ditemukan.")

    # [FIX #7] Scope check — user harus berada dalam scope distributor_id FKP
    # ini sesuai aturan section 3 dokumen. Tanpa ini, siapa pun bisa upload
    # attachment ke FKP siapa saja asal tahu UUID-nya.
    if not await has_global_access(user, kode_role, db):
        try:
            await assert_distributor_in_scope(
                fkp.distributor_id,
                user,
                kode_role,
                db,
                forbidden_message="Anda tidak berhak mengunggah lampiran ke FKP ini.",
            )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))

    if fkp.status in [FkpStatus.CLOSED, FkpStatus.REJECTED]:
        raise HTTPException(
            status_code=400,
            detail="Tidak bisa upload file ke FKP yang sudah ditutup/ditolak.",
        )

    if tipe_dokumen is None:
        tipe_dokumen = TipeDokumen.FOTO_KELUHAN
    elif tipe_dokumen not in TipeDokumen.ALL:
        raise HTTPException(
            status_code=400,
            detail=(
                f"tipe_dokumen tidak valid: '{tipe_dokumen}'. "
                f"Pilihan: {', '.join(TipeDokumen.ALL)}"
            ),
        )

    # Upload bukti resolusi hanya bisa saat accepted ke atas
    BUKTI_RESOLUSI = (
        TipeDokumen.UNTUK_TUKAR_BARANG
        + TipeDokumen.UNTUK_POTONG_TAGIHAN
        + TipeDokumen.UNTUK_PEMUSNAHAN
    )
    STATUS_BOLEH_UPLOAD_BUKTI = [
        FkpStatus.ACCEPTED, FkpStatus.IN_PROCESS,
    ]
    if tipe_dokumen in BUKTI_RESOLUSI and fkp.status not in STATUS_BOLEH_UPLOAD_BUKTI:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Bukti resolusi hanya bisa diupload saat status "
                f"'accepted' atau 'in_process'. Status saat ini: '{fkp.status}'."
            ),
        )

    if fkp_item_id is not None:
        r_item = await db.execute(
            select(FkpItem).where(
                FkpItem.id == fkp_item_id,
                FkpItem.fkp_id == fkp_id,
            )
        )
        if not r_item.scalar_one_or_none():
            raise HTTPException(
                status_code=404,
                detail="Item tidak ditemukan atau tidak termasuk dalam FKP ini.",
            )

    # Validasi tipe file
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Tipe file tidak diizinkan: {file.content_type}. "
                f"Gunakan: JPEG, PNG, WebP, MP4, MOV, PDF, atau DOCX."
            ),
        )

    # Baca file dan validasi ukuran
    file_bytes = await file.read()
    if len(file_bytes) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Ukuran file melebihi batas {settings.MAX_FILE_SIZE_MB}MB.",
        )

    # Generate nama file unik
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    unique_name = f"{fkp_id}_{uuid.uuid4().hex[:8]}.{ext}"

    # Buat subfolder per FKP (dan per item jika ada)
    if fkp_item_id:
        fkp_dir = os.path.join(settings.UPLOAD_DIR, "fkp", str(fkp_id), "items", str(fkp_item_id))
        url = f"/uploads/fkp/{fkp_id}/items/{fkp_item_id}/{unique_name}"
    else:
        fkp_dir = os.path.join(settings.UPLOAD_DIR, "fkp", str(fkp_id))
        url = f"/uploads/fkp/{fkp_id}/{unique_name}"

    os.makedirs(fkp_dir, exist_ok=True)
    file_path = os.path.join(fkp_dir, unique_name)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_bytes)

    if file.content_type in ALLOWED_IMAGE_TYPES:
        tipe_file = "image"
    elif file.content_type in ALLOWED_VIDEO_TYPES:
        tipe_file = "video"
    else:
        tipe_file = "document"
        
    attachment = FkpAttachment(
        fkp_id=fkp_id,
        fkp_item_id=fkp_item_id, 
        tipe_dokumen=tipe_dokumen,
        nama_file=file.filename,
        url=url,
        ukuran_bytes=len(file_bytes),
        tipe_file=tipe_file,
        keterangan=keterangan,
        uploaded_by=user.id,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)
    return attachment


async def delete_attachment(
    attachment_id: uuid.UUID,
    user: User,
    kode_role: str,
    db: AsyncSession,
) -> dict:
    """Hapus attachment (hanya oleh uploader atau superadmin)."""
    result = await db.execute(
        select(FkpAttachment).where(FkpAttachment.id == attachment_id)
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="File tidak ditemukan.")

    # [FIX #3 turunan] is_superadmin() berbasis flag, bukan string "superadmin"
    superadmin = await is_superadmin(user, db)
    if attachment.uploaded_by != user.id and not superadmin:
        raise HTTPException(status_code=403, detail="Tidak bisa menghapus file milik orang lain.")

    prefix = "/uploads/"
    if attachment.url.startswith(prefix):
        relative_path = attachment.url[len(prefix):]

    file_path = os.path.join(settings.UPLOAD_DIR, relative_path)
    if os.path.exists(file_path):
        os.remove(file_path)
        

    await db.delete(attachment)
    await db.commit()
    return {"message": "File berhasil dihapus."}
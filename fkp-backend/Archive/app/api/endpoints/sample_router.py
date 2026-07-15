"""
Router — Sample Shipment.

Dipasang di main.py dengan prefix="/api/fkp", sehingga path lengkapnya
persis sesuai §10.1 dokumen rencana: /api/fkp/{fkp_id}/samples/...
"""
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_kode_role
from app.models.user import User
from app.models.fkp import TipeDokumen
from app.schemas.sample import (
    SampleCreate, SampleReceiveRequest, SampleExamineRequest, SampleCancelRequest,
    SampleResponse, SampleStatusLogResponse,
)
from app.services import sample_service, upload_service
from sqlmodel import select

router = APIRouter()


@router.post("/{fkp_id}/samples", response_model=SampleResponse)
async def create_sample(
    fkp_id: uuid.UUID,
    data: SampleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await sample_service.create_sample_shipment(fkp_id, data, user, kode_role, db)


@router.get("/{fkp_id}/samples", response_model=list[SampleResponse])
async def list_samples(
    fkp_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await sample_service.list_samples_by_fkp(fkp_id, user, kode_role, db)


@router.get("/{fkp_id}/samples/{sample_id}", response_model=SampleResponse)
async def get_sample(
    fkp_id: uuid.UUID,
    sample_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await sample_service.get_sample_detail(fkp_id, sample_id, user, kode_role, db)


@router.post("/{fkp_id}/samples/{sample_id}/confirm-delivery", response_model=SampleResponse)
async def confirm_delivery(
    fkp_id: uuid.UUID,
    sample_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await sample_service.confirm_delivery(fkp_id, sample_id, user, kode_role, db)


@router.post("/{fkp_id}/samples/{sample_id}/receive", response_model=SampleResponse)
async def receive_sample(
    fkp_id: uuid.UUID,
    sample_id: uuid.UUID,
    data: SampleReceiveRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await sample_service.receive_sample(fkp_id, sample_id, data, user, kode_role, db)


@router.post("/{fkp_id}/samples/{sample_id}/forward-to-qc", response_model=SampleResponse)
async def forward_to_qc(
    fkp_id: uuid.UUID,
    sample_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await sample_service.forward_to_qc(fkp_id, sample_id, user, kode_role, db)


@router.post("/{fkp_id}/samples/{sample_id}/start-review", response_model=SampleResponse)
async def start_review(
    fkp_id: uuid.UUID,
    sample_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await sample_service.start_review(fkp_id, sample_id, user, kode_role, db)


@router.post("/{fkp_id}/samples/{sample_id}/examine", response_model=SampleResponse)
async def examine_sample(
    fkp_id: uuid.UUID,
    sample_id: uuid.UUID,
    data: SampleExamineRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await sample_service.examine_sample(fkp_id, sample_id, data, user, kode_role, db)


@router.post("/{fkp_id}/samples/{sample_id}/cancel", response_model=SampleResponse)
async def cancel_sample(
    fkp_id: uuid.UUID,
    sample_id: uuid.UUID,
    data: SampleCancelRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    return await sample_service.cancel_sample(fkp_id, sample_id, data, user, kode_role, db)


# ─── Dokumen sample (pakai infrastruktur upload_service yang sudah ada) ──────

@router.post("/{fkp_id}/samples/{sample_id}/documents")
async def upload_sample_document(
    fkp_id: uuid.UUID,
    sample_id: uuid.UUID,
    file: UploadFile = File(...),
    tipe_dokumen: str = Form(...),
    keterangan: str = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    """
    Upload dokumen sample (tanda_terima_sample, foto_kondisi_masuk,
    hasil_pemeriksaan_qc). Permission: warehouse, qc, admin_ho, superadmin
    (sesuai §10.1 dokumen) — dicek lewat require_permission di bawah,
    BUKAN lewat scope FKP biasa, karena aktor di sini bukan
    outlet/distributor/sc_spv pemilik FKP.

    File tersimpan sebagai FkpAttachment biasa (sample_shipment_id terisi) —
    otomatis bisa diunduh lewat endpoint attachment terautentikasi yang sudah
    ada: GET /api/fkp/{fkp_id}/attachments/{attachment_id}/file (lihat fix
    keamanan #1 sesi sebelumnya) — tidak perlu endpoint download terpisah.
    """
    from app.services.permission_service import require_permission, has_permission
    # Salah satu dari 3 permission ini cukup — cek longgar: siapa pun yang
    # boleh receive/forward/examine sample ini boleh upload dokumennya.
    allowed = False
    for perm in ("sample.receive", "sample.forward_qc", "sample.examine"):
        if await has_permission(kode_role, perm, db):
            allowed = True
            break
    if not allowed:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Anda tidak berhak mengunggah dokumen sample ini.")

    # Pastikan sample ada & milik fkp_id ini (404 kalau tidak)
    sample = await sample_service._get_sample_or_404(sample_id, fkp_id, db)

    return await upload_service.upload_attachment(
        fkp_id=fkp_id,
        file=file,
        user=user,
        db=db,
        kode_role=kode_role,
        tipe_dokumen=tipe_dokumen,
        keterangan=keterangan,
        sample_shipment_id=sample.id,
    )


@router.delete("/{fkp_id}/samples/{sample_id}/documents/{attachment_id}")
async def delete_sample_document(
    fkp_id: uuid.UUID,
    sample_id: uuid.UUID,
    attachment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kode_role: str = Depends(get_kode_role),
):
    """
    Hapus dokumen sample. Sesuai §10.1: uploader, admin_ho, superadmin.
    upload_service.delete_attachment() sudah menegakkan "uploader atau
    superadmin"; di sini kita tambahkan admin_ho secara eksplisit sesuai
    spesifikasi dokumen (deviasi kecil dari perilaku delete_attachment()
    generik yang dipakai attachment FKP biasa).
    """
    from fastapi import HTTPException
    from app.models.fkp import FkpAttachment
    from app.services.authz_helpers import is_superadmin

    r = await db.execute(
        select(FkpAttachment).where(
            FkpAttachment.id == attachment_id,
            FkpAttachment.sample_shipment_id == sample_id,
        )
    )
    attachment = r.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan.")

    is_owner = attachment.uploaded_by == user.id
    is_admin_ho = kode_role == "admin_ho"
    if not (is_owner or is_admin_ho or await is_superadmin(user, db)):
        raise HTTPException(status_code=403, detail="Tidak bisa menghapus dokumen milik orang lain.")

    # [FIX] TIDAK delegasi ke upload_service.delete_attachment() — fungsi itu
    # hanya mengizinkan uploader ATAU superadmin (tidak tahu soal admin_ho).
    # Karena otorisasi di atas sudah benar (uploader/admin_ho/superadmin
    # sesuai §10.1 dokumen), penghapusan file dilakukan langsung di sini.
    import os
    from app.core.config import settings

    prefix = "/uploads/"
    if attachment.url.startswith(prefix):
        relative_path = attachment.url[len(prefix):]
        file_path = os.path.join(settings.UPLOAD_DIR, relative_path)
        if os.path.exists(file_path):
            os.remove(file_path)

    await db.delete(attachment)
    await db.commit()
    return {"detail": "Dokumen berhasil dihapus."}
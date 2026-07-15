# app/api/endpoints/debug.py
from fastapi import APIRouter, Depends
from app.models.user import User
from app.core.dependencies import get_current_user

router = APIRouter()

@router.get("/test-email")
async def test_email(
    to: str,
    nomor_fkp: str = "FKP/2025/TEST/001",
    event: str = "submitted",   # submitted | need_revision | rejected | closed
    current_user: User = Depends(get_current_user),
):
    from app.services import email_service

    if event == "submitted":
        await email_service.kirim_email_fkp_submitted(
            to_email=to, nama_penerima="Test User",
            nomor_fkp=nomor_fkp,
            fkp_id="00000000-0000-0000-0000-000000000000",
            prioritas="urgent",
        )
    elif event == "need_revision":
        await email_service.kirim_email_fkp_need_revision(
            to_email=to, nama_penerima="Test User",
            nomor_fkp=nomor_fkp,
            fkp_id="00000000-0000-0000-0000-000000000000",
            catatan_revisi="Mohon lengkapi foto kemasan dan batch number.",
            direview_oleh="Budi (APSM)",
        )
    elif event == "rejected":
        await email_service.kirim_email_fkp_rejected(
            to_email=to, nama_penerima="Test User",
            nomor_fkp=nomor_fkp,
            fkp_id="00000000-0000-0000-0000-000000000000",
            alasan_penolakan="Keluhan tidak terbukti setelah investigasi lapangan.",
            ditolak_oleh="Siti (RSM)",
        )
    elif event == "closed":
        await email_service.kirim_email_fkp_closed(
            to_email=to, nama_penerima="Test User",
            nomor_fkp=nomor_fkp,
            fkp_id="00000000-0000-0000-0000-000000000000",
            tipe_resolusi="tukar_barang",
        )
    else:
        return {"error": f"Event '{event}' tidak dikenal."}

    return {"message": f"Email event='{event}' dikirim ke {to}"}
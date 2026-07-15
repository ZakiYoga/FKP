"""
Notification Endpoints — FKP SaktiFood.

GET    /api/notifications/             → List notifikasi user login (pagination + filter)
GET    /api/notifications/unread-count → Hanya jumlah belum dibaca (badge)
PUT    /api/notifications/read-all     → Tandai semua sebagai dibaca
PUT    /api/notifications/read         → Tandai beberapa sebagai dibaca (by IDs)
DELETE /api/notifications/{id}         → Hapus satu notifikasi
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationSummary,
    MarkReadRequest,
)
from app.services import notification_service

router = APIRouter()


@router.get(
    "/",
    response_model=NotificationListResponse,
    summary="List notifikasi saya",
    description=(
        "Ambil daftar notifikasi untuk user yang sedang login. "
        "Mendukung filter `unread_only`, pagination `limit` & `offset`."
    ),
)
async def get_my_notifications(
    unread_only: bool = Query(default=False, description="Hanya tampilkan yang belum dibaca"),
    limit: int = Query(default=50, ge=1, le=100, description="Jumlah item per halaman"),
    offset: int = Query(default=0, ge=0, description="Offset pagination"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.get_notifications(
        db=db,
        user=current_user,
        hanya_belum_dibaca=unread_only,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/unread-count",
    response_model=NotificationSummary,
    summary="Jumlah notifikasi belum dibaca (badge)",
    description="Endpoint ringan untuk polling badge di frontend. Hanya return unread_count.",
)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.get_unread_count(db=db, user=current_user)


@router.put(
    "/read-all",
    summary="Tandai semua notifikasi sebagai dibaca",
    description="Menandai seluruh notifikasi milik user yang login sebagai sudah dibaca.",
)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await notification_service.mark_all_as_read(db=db, user=current_user)
    return {"message": f"{result['updated']} notifikasi telah ditandai sebagai dibaca."}


@router.put(
    "/read",
    summary="Tandai beberapa notifikasi sebagai dibaca",
    description="Menandai notifikasi berdasarkan daftar ID yang dikirim di body request.",
)
async def mark_read(
    body: MarkReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not body.notification_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="notification_ids tidak boleh kosong.",
        )
    result = await notification_service.mark_as_read(
        db=db,
        user=current_user,
        notification_ids=body.notification_ids,
    )
    return {"message": f"{result['updated']} notifikasi telah ditandai sebagai dibaca."}


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus satu notifikasi",
    description="Hapus notifikasi berdasarkan ID. Hanya bisa menghapus notifikasi milik sendiri.",
)
async def delete_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await notification_service.delete_notification(
        db=db,
        user=current_user,
        notification_id=notification_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notifikasi tidak ditemukan atau bukan milik Anda.",
        )

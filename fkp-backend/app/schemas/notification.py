"""
Schema Pydantic untuk Notification API.
"""
import uuid
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


# ─── Response Schema ──────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    """Schema response satu notifikasi."""
    id: uuid.UUID
    user_id: uuid.UUID
    fkp_id: Optional[uuid.UUID] = None
    judul: str
    pesan: str
    tipe: str           # "status_change" | "need_action" | "info"
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

    # Info FKP (jika ada) — diisi service
    nomor_fkp: Optional[str] = None
    fkp_status: Optional[str] = None

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """Response list notifikasi dengan metadata."""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int


class NotificationSummary(BaseModel):
    """Hanya angka badge — ringan untuk polling."""
    unread_count: int


# ─── Request Schema ───────────────────────────────────────────────────────────

class MarkReadRequest(BaseModel):
    """Request body untuk mark beberapa notifikasi sebagai dibaca."""
    notification_ids: List[uuid.UUID]

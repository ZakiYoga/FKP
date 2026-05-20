import uuid
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import DateTime, Column
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .user import User
    from .fkp import FkpComplaint


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    fkp_id: Optional[uuid.UUID] = Field(default=None, foreign_key="fkp_complaints.id")
    judul: str = Field(max_length=200)
    pesan: str = Field()
    tipe: str = Field(max_length=50)  # "status_change" | "need_action" | "info"
    is_read: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )
    read_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # Relasi
    user: Optional["User"] = Relationship(back_populates="notifications")
    fkp: Optional["FkpComplaint"] = Relationship(back_populates="notifications")

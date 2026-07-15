import uuid
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime, timezone
from sqlalchemy import DateTime, Column
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .role import Role
    from .area import Area
    from .distributor import DistributorUser
    from .outlet import Outlet
    from .fkp import FkpComplaint, FkpStatusLog, FkpResolution
    from .notification import Notification
    from .testimoni import FkpTestimoni
    
class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    role_id: uuid.UUID = Field(foreign_key="roles.id", index=True)
    nama: str = Field(max_length=150)
    email: str = Field(max_length=150, unique=True, index=True)
    password_hash: str = Field(max_length=255)
    no_telepon: Optional[str] = Field(default=None, max_length=20)
    is_active: bool = Field(default=True)
    last_login: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    # Relasi
    role: Optional["Role"] = Relationship(back_populates="users")
    areas_as_pic: List["Area"] = Relationship(back_populates="pic_user")
    distributor_users: List["DistributorUser"] = Relationship(back_populates="user")
    outlets_as_pic: List["Outlet"] = Relationship(back_populates="pic_user")

    # FKP relasi
    fkp_submitted: List["FkpComplaint"] = Relationship(
        back_populates="submitted_by_user",
        sa_relationship_kwargs={"foreign_keys": "[FkpComplaint.submitted_by]"},
    )
    fkp_handled: List["FkpComplaint"] = Relationship(
        back_populates="handled_by_user",
        sa_relationship_kwargs={"foreign_keys": "[FkpComplaint.handled_by]"},
    )
    
    fkp_approved_as_marketing: List["FkpComplaint"] = Relationship(
        back_populates="marketing_approver",
        sa_relationship_kwargs={"foreign_keys": "[FkpComplaint.approved_by_marketing]"},
    )
    fkp_approved_as_direktur: List["FkpComplaint"] = Relationship(
        back_populates="direktur_approver",
        sa_relationship_kwargs={"foreign_keys": "[FkpComplaint.approved_by_direktur]"},
    )
    fkp_status_logs: List["FkpStatusLog"] = Relationship(back_populates="changed_by_user")
    notifications: List["Notification"] = Relationship(back_populates="user")
    
    fkp_resolutions_as_finance: List["FkpResolution"] = Relationship(
        back_populates="finance_user",
        sa_relationship_kwargs={"foreign_keys": "[FkpResolution.finance_user_id]"},
    )
    fkp_resolutions_created: List["FkpResolution"] = Relationship(
        back_populates="dibuat_oleh_user",
        sa_relationship_kwargs={"foreign_keys": "[FkpResolution.dibuat_oleh]"},
    )
    fkp_testimoni: List["FkpTestimoni"] = Relationship(back_populates="user")

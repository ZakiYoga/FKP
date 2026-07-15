import uuid
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime, date, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import DateTime, Column

from app.models.fkp import SampleStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.fkp import FkpComplaint, FkpItem, FkpAttachment


# ─── SAMPLE SHIPMENT (tracking sample fisik ke QC) ────────────────────────────
#
# Statusnya independen dari FkpStatus — hanya dipakai sebagai GATE agar
# qc_investigasi() tidak bisa dijalankan selama masih ada sample yang belum
# selesai diperiksa (status di luar SampleStatus.TERMINAL).
#
# 1 FkpItem bisa punya lebih dari 1 SampleShipment (mis. dikirim ulang kalau
# sample pertama rusak/hilang di jalan, atau dibatalkan lalu dikirim ulang).

class SampleShipment(SQLModel, table=True):
    __tablename__ = "sample_shipments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # ── Relasi ke FKP ──────────────────────────────────────────────────────
    fkp_id: uuid.UUID = Field(
        foreign_key="fkp_complaints.id", index=True,
        description="Denormalized dari fkp_item.fkp_id — efisiensi query"
    )
    fkp_item_id: uuid.UUID = Field(
        foreign_key="fkp_items.id", index=True,
        description="Relasi utama — item spesifik yang sample-nya dikirim"
    )

    # ── Status ─────────────────────────────────────────────────────────────
    status: str = Field(
        default=SampleStatus.SHIPPED, max_length=30, index=True
    )

    # ── Info Pengirim ───────────────────────────────────────────────────────
    sender_id: uuid.UUID = Field(
        foreign_key="users.id",
        description="User yang mendaftarkan pengiriman"
    )
    ekspedisi: Optional[str] = Field(default=None, max_length=100)
    nomor_resi: Optional[str] = Field(default=None, max_length=100)
    tanggal_kirim: Optional[date] = Field(default=None)
    catatan_pengirim: Optional[str] = Field(default=None)
    qty_sample: int = Field(default=1)

    # ── Delivered ──────────────────────────────────────────────────────────
    tanggal_delivered: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    dikonfirmasi_delivered_oleh: Optional[uuid.UUID] = Field(
        default=None, foreign_key="users.id"
    )

    # ── Warehouse Inbound ───────────────────────────────────────────────────
    diterima_oleh: Optional[uuid.UUID] = Field(
        default=None, foreign_key="users.id"
    )
    nomor_tanda_terima: Optional[str] = Field(default=None, max_length=50)
    tanggal_diterima: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    catatan_warehouse: Optional[str] = Field(default=None)

    # ── QC — hasil_pemeriksaan bersifat INTERNAL ONLY, jangan pernah
    # diekspos di response schema yang bisa dibaca role outlet/distributor.
    diperiksa_oleh: Optional[uuid.UUID] = Field(
        default=None, foreign_key="users.id"
    )
    tanggal_mulai_periksa: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    tanggal_selesai_periksa: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    hasil_pemeriksaan: Optional[str] = Field(default=None)

    # ── Cancellation ───────────────────────────────────────────────────────
    alasan_batal: Optional[str] = Field(default=None)
    dibatalkan_oleh: Optional[uuid.UUID] = Field(
        default=None, foreign_key="users.id"
    )
    tanggal_batal: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # ── Timestamps ─────────────────────────────────────────────────────────
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    # ── Relationships ──────────────────────────────────────────────────────
    fkp: Optional["FkpComplaint"] = Relationship(back_populates="sample_shipments")
    fkp_item: Optional["FkpItem"] = Relationship(back_populates="sample_shipments")
    sender: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[SampleShipment.sender_id]"}
    )
    warehouse_receiver: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[SampleShipment.diterima_oleh]"}
    )
    confirmed_delivery_by: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[SampleShipment.dikonfirmasi_delivered_oleh]"}
    )
    qc_examiner: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[SampleShipment.diperiksa_oleh]"}
    )
    cancelled_by_user: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[SampleShipment.dibatalkan_oleh]"}
    )
    status_logs: List["SampleStatusLog"] = Relationship(back_populates="sample")
    documents: List["FkpAttachment"] = Relationship(back_populates="sample_shipment")


# ─── SAMPLE STATUS LOGS (audit trail terpisah dari fkp_status_logs) ──────────
#
# Sengaja dipisah dari FkpStatusLog — sample shipment adalah sub-proses dengan
# siklus hidupnya sendiri; mencampurnya ke timeline status FKP utama akan
# mengacaukan tracking publik (public_tracking.py) yang membaca FkpStatusLog
# secara langsung untuk timeline yang ditampilkan ke publik.

class SampleStatusLog(SQLModel, table=True):
    __tablename__ = "sample_status_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sample_id: uuid.UUID = Field(
        foreign_key="sample_shipments.id", index=True
    )
    fkp_id: uuid.UUID = Field(
        foreign_key="fkp_complaints.id", index=True,
        description="Denormalized dari sample.fkp_id — untuk dashboard query"
    )
    status_lama: Optional[str] = Field(default=None, max_length=30)
    status_baru: str = Field(max_length=30)
    catatan: Optional[str] = Field(default=None)
    changed_by: uuid.UUID = Field(foreign_key="users.id")
    changed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    sample: Optional["SampleShipment"] = Relationship(back_populates="status_logs")
    changed_by_user: Optional["User"] = Relationship()
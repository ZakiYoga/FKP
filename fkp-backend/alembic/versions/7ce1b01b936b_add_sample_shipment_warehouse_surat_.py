"""add sample shipment & warehouse surat jalan

Revision ID: 7ce1b01b936b
Revises: 984c1c2d7b64
Create Date: 2026-07-06 10:34:33.463958

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '7ce1b01b936b'
down_revision: Union[str, None] = '984c1c2d7b64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── sample_shipments ────────────────────────────────────────────────────
    op.create_table(
        'sample_shipments',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('fkp_id', sa.Uuid(), nullable=False),
        sa.Column('fkp_item_id', sa.Uuid(), nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False),
        sa.Column('sender_id', sa.Uuid(), nullable=False),
        sa.Column('ekspedisi', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column('nomor_resi', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column('tanggal_kirim', sa.Date(), nullable=True),
        sa.Column('catatan_pengirim', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('qty_sample', sa.Integer(), nullable=False),
        sa.Column('tanggal_delivered', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dikonfirmasi_delivered_oleh', sa.Uuid(), nullable=True),
        sa.Column('diterima_oleh', sa.Uuid(), nullable=True),
        sa.Column('nomor_tanda_terima', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column('tanggal_diterima', sa.DateTime(timezone=True), nullable=True),
        sa.Column('catatan_warehouse', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('diperiksa_oleh', sa.Uuid(), nullable=True),
        sa.Column('tanggal_mulai_periksa', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tanggal_selesai_periksa', sa.DateTime(timezone=True), nullable=True),
        sa.Column('hasil_pemeriksaan', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('alasan_batal', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('dibatalkan_oleh', sa.Uuid(), nullable=True),
        sa.Column('tanggal_batal', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['fkp_id'], ['fkp_complaints.id']),
        sa.ForeignKeyConstraint(['fkp_item_id'], ['fkp_items.id']),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id']),
        sa.ForeignKeyConstraint(['dikonfirmasi_delivered_oleh'], ['users.id']),
        sa.ForeignKeyConstraint(['diterima_oleh'], ['users.id']),
        sa.ForeignKeyConstraint(['diperiksa_oleh'], ['users.id']),
        sa.ForeignKeyConstraint(['dibatalkan_oleh'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sample_shipments_fkp_id'), 'sample_shipments', ['fkp_id'], unique=False)
    op.create_index(op.f('ix_sample_shipments_fkp_item_id'), 'sample_shipments', ['fkp_item_id'], unique=False)
    op.create_index(op.f('ix_sample_shipments_status'), 'sample_shipments', ['status'], unique=False)
 
    # ── sample_status_logs ──────────────────────────────────────────────────
    op.create_table(
        'sample_status_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('sample_id', sa.Uuid(), nullable=False),
        sa.Column('fkp_id', sa.Uuid(), nullable=False),
        sa.Column('status_lama', sqlmodel.sql.sqltypes.AutoString(length=30), nullable=True),
        sa.Column('status_baru', sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False),
        sa.Column('catatan', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('changed_by', sa.Uuid(), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['sample_id'], ['sample_shipments.id']),
        sa.ForeignKeyConstraint(['fkp_id'], ['fkp_complaints.id']),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sample_status_logs_sample_id'), 'sample_status_logs', ['sample_id'], unique=False)
    op.create_index(op.f('ix_sample_status_logs_fkp_id'), 'sample_status_logs', ['fkp_id'], unique=False)
 
    # ── warehouse_surat_jalan ────────────────────────────────────────────────
    op.create_table(
        'warehouse_surat_jalan',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('fkp_id', sa.Uuid(), nullable=False),
        sa.Column('nomor_surat_jalan', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('tanggal_surat_jalan', sa.Date(), nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column('nama_penerima', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column('alamat_penerima', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
        sa.Column('telepon_penerima', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
        sa.Column('ekspedisi', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column('nomor_resi', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column('tanggal_kirim', sa.Date(), nullable=True),
        sa.Column('tanggal_delivered', sa.DateTime(timezone=True), nullable=True),
        sa.Column('url_pdf', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column('catatan', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('dibuat_oleh', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['fkp_id'], ['fkp_complaints.id']),
        sa.ForeignKeyConstraint(['dibuat_oleh'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_warehouse_surat_jalan_fkp_id'), 'warehouse_surat_jalan', ['fkp_id'], unique=False)
    op.create_index(op.f('ix_warehouse_surat_jalan_status'), 'warehouse_surat_jalan', ['status'], unique=False)
    op.create_index(
        op.f('ix_warehouse_surat_jalan_nomor_surat_jalan'),
        'warehouse_surat_jalan', ['nomor_surat_jalan'], unique=True,
    )
    # Index komposit — query paling umum: "SJ aktif untuk FKP X"
    op.create_index(
        'ix_wsj_fkp_status', 'warehouse_surat_jalan', ['fkp_id', 'status'], unique=False,
    )
 
    # ── warehouse_surat_jalan_items ─────────────────────────────────────────
    op.create_table(
        'warehouse_surat_jalan_items',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('surat_jalan_id', sa.Uuid(), nullable=False),
        sa.Column('fkp_item_id', sa.Uuid(), nullable=True),
        sa.Column('nama_produk', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column('qty', sa.Integer(), nullable=False),
        sa.Column('satuan', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column('keterangan', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.ForeignKeyConstraint(['surat_jalan_id'], ['warehouse_surat_jalan.id']),
        sa.ForeignKeyConstraint(['fkp_item_id'], ['fkp_items.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_warehouse_surat_jalan_items_surat_jalan_id'),
        'warehouse_surat_jalan_items', ['surat_jalan_id'], unique=False,
    )
 
    # ── ALTER fkp_attachments — tambah sample_shipment_id ───────────────────
    op.add_column(
        'fkp_attachments',
        sa.Column('sample_shipment_id', sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        'fk_fkp_attachments_sample_shipment_id',
        'fkp_attachments', 'sample_shipments',
        ['sample_shipment_id'], ['id'],
    )
    op.create_index(
        op.f('ix_fkp_attachments_sample_shipment_id'),
        'fkp_attachments', ['sample_shipment_id'], unique=False,
    )
 
 
def downgrade() -> None:
    op.drop_index(op.f('ix_fkp_attachments_sample_shipment_id'), table_name='fkp_attachments')
    op.drop_constraint('fk_fkp_attachments_sample_shipment_id', 'fkp_attachments', type_='foreignkey')
    op.drop_column('fkp_attachments', 'sample_shipment_id')
 
    op.drop_index(op.f('ix_warehouse_surat_jalan_items_surat_jalan_id'), table_name='warehouse_surat_jalan_items')
    op.drop_table('warehouse_surat_jalan_items')
 
    op.drop_index('ix_wsj_fkp_status', table_name='warehouse_surat_jalan')
    op.drop_index(op.f('ix_warehouse_surat_jalan_nomor_surat_jalan'), table_name='warehouse_surat_jalan')
    op.drop_index(op.f('ix_warehouse_surat_jalan_status'), table_name='warehouse_surat_jalan')
    op.drop_index(op.f('ix_warehouse_surat_jalan_fkp_id'), table_name='warehouse_surat_jalan')
    op.drop_table('warehouse_surat_jalan')
 
    op.drop_index(op.f('ix_sample_status_logs_fkp_id'), table_name='sample_status_logs')
    op.drop_index(op.f('ix_sample_status_logs_sample_id'), table_name='sample_status_logs')
    op.drop_table('sample_status_logs')
 
    op.drop_index(op.f('ix_sample_shipments_status'), table_name='sample_shipments')
    op.drop_index(op.f('ix_sample_shipments_fkp_item_id'), table_name='sample_shipments')
    op.drop_index(op.f('ix_sample_shipments_fkp_id'), table_name='sample_shipments')
    op.drop_table('sample_shipments')
"""fkp jalur pcs

Revision ID: bcd9772dbfcc
Revises: 71d6816e388c
Create Date: 2026-10-13 09:13:38.671964

Bagian 1 (kolom + index) dibuat otomatis oleh Alembic.
Bagian 2 dan 3 (data migration) ditambahkan manual karena autogenerate tidak pernah
menulis perubahan data.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'bcd9772dbfcc'
down_revision: Union[str, None] = '71d6816e388c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1) Skema (hasil autogenerate) ────────────────────────────────────────
    op.add_column('fkp_complaints', sa.Column('jalur', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True))
    op.add_column('fkp_complaints', sa.Column('pcs_tahap', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True))
    op.add_column('fkp_complaints', sa.Column('pcs_pengajuan_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('fkp_complaints', sa.Column('pcs_proses_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('fkp_complaints', sa.Column('pcs_selesai_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_fkp_complaints_jalur'), 'fkp_complaints', ['jalur'], unique=False)

    # ── 2) Backfill jalur untuk FKP yang SUDAH melewati admin_ho_review ──────
    # Berdasarkan status dan penanda approval (bukan hitung ulang qty), supaya setia
    # pada jalur yang benar-benar dijalani. Baris yang tidak cocok tetap NULL
    # (CASE tanpa ELSE), termasuk draft/submitted/apsm_reviewed dan FKP lama
    # yang tidak punya penanda approval.
    op.execute("""
        UPDATE fkp_complaints SET jalur = CASE
            WHEN status = 'rsm_approval_final'
              OR approved_by_rsm_final IS NOT NULL
                THEN 'approval_rsm'
            WHEN status IN ('rsm_approval_investigasi', 'in_investigation',
                            'investigated', 'rsm_approval_resolusi',
                            'direktur_approval')
              OR approved_by_direktur IS NOT NULL
                THEN 'approval_direktur'
        END
        WHERE jalur IS NULL
    """)

    # ── 3) Renceng -> pcs ────────────────────────────────────────────────────
    # product_kemasan unik (product_id, jenis_kemasan): bila produk sudah punya
    # baris pcs, baris renceng dihapus; sisanya diubah menjadi pcs.
    op.execute("""
        DELETE FROM product_kemasan pk
        WHERE pk.jenis_kemasan = 'renceng'
          AND EXISTS (SELECT 1 FROM product_kemasan x
                      WHERE x.product_id = pk.product_id AND x.jenis_kemasan = 'pcs')
    """)
    op.execute("UPDATE product_kemasan SET jenis_kemasan = 'pcs' WHERE jenis_kemasan = 'renceng'")
    op.execute("UPDATE product_catalog SET jenis_kemasan = 'pcs' WHERE jenis_kemasan = 'renceng'")
    op.execute("UPDATE fkp_items       SET jenis_kemasan = 'pcs' WHERE jenis_kemasan = 'renceng'")


def downgrade() -> None:
    op.drop_index(op.f('ix_fkp_complaints_jalur'), table_name='fkp_complaints')
    op.drop_column('fkp_complaints', 'pcs_selesai_at')
    op.drop_column('fkp_complaints', 'pcs_proses_at')
    op.drop_column('fkp_complaints', 'pcs_pengajuan_at')
    op.drop_column('fkp_complaints', 'pcs_tahap')
    op.drop_column('fkp_complaints', 'jalur')
    # Backfill jalur ikut hilang bersama kolomnya. Perubahan renceng -> pcs TIDAK
    # dikembalikan (data lama tidak bisa dibedakan lagi dari pcs asli).
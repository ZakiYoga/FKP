"""add class to product_catalog

Revision ID: f18a6f2f290c
Revises: 7f836e3ca4fb
Create Date: 2026-11-02 09:49:10.137344

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'f18a6f2f290c'
down_revision: Union[str, None] = '7f836e3ca4fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Tambah kolom sebagai nullable supaya baris lama tidak membuat ALTER gagal.
    op.add_column(
        "product_catalog",
        sa.Column("class", sa.String(length=20), nullable=True),
    )

    # 2) Backfill semua data lama ke 'general'.
    op.execute('UPDATE product_catalog SET "class" = \'general\' WHERE "class" IS NULL')

    # 3) Setelah semua baris terisi, jadikan required.
    op.alter_column(
        "product_catalog",
        "class",
        existing_type=sa.String(length=20),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("product_catalog", "class")

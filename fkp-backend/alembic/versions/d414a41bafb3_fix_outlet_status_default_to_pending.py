"""fix_outlet_status_default_to_pending

Revision ID: d414a41bafb3
Revises: 41719a28ab0c
Create Date: 2026-06-07 22:21:37.600175

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'd414a41bafb3'
down_revision: Union[str, None] = '41719a28ab0c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'outlets', 'status',
        existing_type=sa.String(length=20),
        server_default='pending',
        existing_nullable=False,
    )

def downgrade() -> None:
    op.alter_column(
        'outlets', 'status',
        existing_type=sa.String(length=20),
        server_default='aktif',
        existing_nullable=False,
    )

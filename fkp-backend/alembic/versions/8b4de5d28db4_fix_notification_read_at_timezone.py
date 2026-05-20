"""fix_notification_read_at_timezone

Revision ID: 8b4de5d28db4
Revises: 0c5822ed869f
Create Date: 2026-05-15 09:14:10.002755

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8b4de5d28db4'
down_revision: Union[str, None] = '0c5822ed869f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'notifications', 'read_at',
        existing_type=postgresql.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="read_at AT TIME ZONE 'UTC'",  # ← tambahkan ini
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    op.alter_column(
        'notifications', 'read_at',
        existing_type=sa.DateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
        postgresql_using="read_at AT TIME ZONE 'UTC'",  # ← tambahkan ini juga
    )
    # ### end Alembic commands ###

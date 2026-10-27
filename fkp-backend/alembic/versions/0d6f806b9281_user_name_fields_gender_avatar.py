"""user name fields, gender, avatar

Revision ID: 0d6f806b9281
Revises: c41f7a9e2b60
Create Date: 2026-10-21 11:50:33.868811

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '0d6f806b9281'
down_revision: Union[str, None] = 'c41f7a9e2b60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename (data nama lama otomatis terbawa ke first_name)
    op.alter_column(
        'users',
        'nama',
        new_column_name='first_name',
        existing_type=sa.String(length=150),
        existing_nullable=False,
    )

    op.add_column('users', sa.Column('last_name', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True))
    op.add_column('users', sa.Column('gender', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True))
    op.add_column('users', sa.Column('avatar_path', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True))


def downgrade() -> None:
    # Gabungkan last_name ke kolom nama agar tidak ada data yang hilang
    op.execute(
        "UPDATE users SET first_name = LEFT(TRIM(CONCAT_WS(' ', first_name, last_name)), 150)"
    )

    op.drop_column('users', 'avatar_path')
    op.drop_column('users', 'gender')
    op.drop_column('users', 'last_name')

    op.alter_column(
        'users',
        'first_name',
        new_column_name='nama',
        existing_type=sa.String(length=150),
        existing_nullable=False,
    )
"""apsm_sc_spv_area_id

Revision ID: 7f836e3ca4fb
Revises: ad0bc40f8a14
Create Date: 2026-10-29 11:24:42.466194

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f836e3ca4fb'
down_revision: Union[str, None] = 'ad0bc40f8a14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable dulu untuk backfill; dijadikan NOT NULL di revisi terpisah
    op.add_column('apsm_sc_spv', sa.Column('area_id', sa.Uuid(), nullable=True))
    op.create_index(op.f('ix_apsm_sc_spv_area_id'), 'apsm_sc_spv', ['area_id'], unique=False)
    op.create_foreign_key('fk_apsm_sc_spv_area_id', 'apsm_sc_spv', 'areas', ['area_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_apsm_sc_spv_area_id', 'apsm_sc_spv', type_='foreignkey')
    op.drop_index(op.f('ix_apsm_sc_spv_area_id'), table_name='apsm_sc_spv')
    op.drop_column('apsm_sc_spv', 'area_id')
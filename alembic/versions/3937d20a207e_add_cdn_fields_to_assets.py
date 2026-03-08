"""add cdn fields to assets

Revision ID: 3937d20a207e
Revises: c79ca26f1848
Create Date: 2026-03-08 15:43:22.400177

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3937d20a207e'
down_revision: Union[str, None] = 'c79ca26f1848'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add CDN-related columns to assets table
    op.add_column('assets', sa.Column('is_cdn', sa.Boolean(), nullable=True))
    op.add_column('assets', sa.Column('cdn_provider', sa.String(length=50), nullable=True))
    op.add_column('assets', sa.Column('original_domain', sa.String(length=255), nullable=True))

    # Create indexes for the new columns
    op.create_index(op.f('ix_assets_is_cdn'), 'assets', ['is_cdn'], unique=False)
    op.create_index(op.f('ix_assets_cdn_provider'), 'assets', ['cdn_provider'], unique=False)
    op.create_index(op.f('ix_assets_original_domain'), 'assets', ['original_domain'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_assets_original_domain'), table_name='assets')
    op.drop_index(op.f('ix_assets_cdn_provider'), table_name='assets')
    op.drop_index(op.f('ix_assets_is_cdn'), table_name='assets')

    # Drop columns
    op.drop_column('assets', 'original_domain')
    op.drop_column('assets', 'cdn_provider')
    op.drop_column('assets', 'is_cdn')

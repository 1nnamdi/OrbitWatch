"""schema v4: launch pad coordinates

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-07

"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("launches", sa.Column("pad_lat", sa.Float(), nullable=True))
    op.add_column("launches", sa.Column("pad_lon", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("launches", "pad_lon")
    op.drop_column("launches", "pad_lat")

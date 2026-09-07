"""schema v3: launches

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-07

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "launches",
        sa.Column("id", sa.String(36), primary_key=True),  # LL2 UUID
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("provider", sa.String(120), nullable=False),
        sa.Column("mission", sa.String(200), nullable=True),
        sa.Column("mission_type", sa.String(64), nullable=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("status_name", sa.String(64), nullable=False),
        sa.Column("net", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pad", sa.String(120), nullable=True),
        sa.Column("location", sa.String(120), nullable=True),
        sa.Column("image_url", sa.String(300), nullable=True),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_launches_net", "launches", ["net"])


def downgrade() -> None:
    op.drop_table("launches")

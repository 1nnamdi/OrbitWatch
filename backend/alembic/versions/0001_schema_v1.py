"""schema v1: satellites + tle_history

Revision ID: 0001
Revises:
Create Date: 2026-09-07

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "satellites",
        sa.Column("norad_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("group_name", sa.String(64), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_satellites_name", "satellites", ["name"])
    op.create_index("ix_satellites_group_name", "satellites", ["group_name"])

    op.create_table(
        "tle_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("norad_id", sa.Integer(), sa.ForeignKey("satellites.norad_id", ondelete="CASCADE"), nullable=False),
        sa.Column("line1", sa.String(70), nullable=False),
        sa.Column("line2", sa.String(70), nullable=False),
        sa.Column("epoch", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("norad_id", "epoch", name="uq_tle_norad_epoch"),
    )
    op.create_index("ix_tle_norad_epoch_desc", "tle_history", ["norad_id", "epoch"])


def downgrade() -> None:
    op.drop_table("tle_history")
    op.drop_table("satellites")

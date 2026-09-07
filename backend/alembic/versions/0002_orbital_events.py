"""schema v2: orbital_events + analysis_state

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-07

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orbital_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("norad_id", sa.Integer(), sa.ForeignKey("satellites.norad_id", ondelete="CASCADE"), nullable=False),
        sa.Column("epoch_before", sa.DateTime(timezone=True), nullable=False),
        sa.Column("epoch_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gap_hours", sa.Float(), nullable=False),
        sa.Column("delta_sma_km", sa.Float(), nullable=False),
        sa.Column("delta_inclination_deg", sa.Float(), nullable=False),
        sa.Column("delta_eccentricity", sa.Float(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("norad_id", "epoch_after", name="uq_event_norad_epoch_after"),
    )
    op.create_index("ix_orbital_events_norad_id", "orbital_events", ["norad_id"])
    op.create_index("ix_orbital_events_epoch_after", "orbital_events", ["epoch_after"])

    # single-row watermark: highest tle_history.id already analyzed
    op.create_table(
        "analysis_state",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("last_tle_id", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("analysis_state")
    op.drop_table("orbital_events")

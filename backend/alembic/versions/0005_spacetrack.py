"""schema v5: space-track satcat + decay predictions

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-07

"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "satcat",
        sa.Column("norad_id", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("object_name", sa.String(64), nullable=False),
        sa.Column("object_id", sa.String(16), nullable=True),  # intl designator
        sa.Column("object_type", sa.String(16), nullable=True),
        sa.Column("country", sa.String(16), nullable=True),
        sa.Column("launch_date", sa.Date, nullable=True),
        sa.Column("decay_date", sa.Date, nullable=True),
        sa.Column("launch_site", sa.String(16), nullable=True),
        sa.Column("rcs_size", sa.String(8), nullable=True),
        sa.Column("period_min", sa.Float, nullable=True),
        sa.Column("inclination_deg", sa.Float, nullable=True),
        sa.Column("apogee_km", sa.Float, nullable=True),
        sa.Column("perigee_km", sa.Float, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_satcat_object_name", "satcat", ["object_name"])
    op.create_index("ix_satcat_object_type", "satcat", ["object_type"])
    op.create_index("ix_satcat_launch_date", "satcat", ["launch_date"])
    op.create_index("ix_satcat_decay_date", "satcat", ["decay_date"])

    op.create_table(
        "decay_predictions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("norad_id", sa.Integer, nullable=False),
        sa.Column("object_name", sa.String(64), nullable=False),
        sa.Column("intl_des", sa.String(16), nullable=True),
        sa.Column("rcs_size", sa.String(8), nullable=True),
        sa.Column("country", sa.String(16), nullable=True),
        sa.Column("msg_epoch", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decay_epoch", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(16), nullable=True),
        sa.Column("msg_type", sa.String(16), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("norad_id", "msg_epoch", "msg_type", name="uq_decay_norad_msg"),
    )
    op.create_index("ix_decay_norad", "decay_predictions", ["norad_id"])
    op.create_index("ix_decay_epoch", "decay_predictions", ["decay_epoch"])


def downgrade() -> None:
    op.drop_table("decay_predictions")
    op.drop_table("satcat")

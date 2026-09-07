from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


from .db import Base


class Satellite(Base):
    __tablename__ = "satellites"

    norad_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(64), index=True)
    group_name: Mapped[str] = mapped_column(String(64), index=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tles: Mapped[list["TLE"]] = relationship(back_populates="satellite", cascade="all, delete-orphan")


class TLE(Base):
    __tablename__ = "tle_history"
    __table_args__ = (
        UniqueConstraint("norad_id", "epoch", name="uq_tle_norad_epoch"),
        Index("ix_tle_norad_epoch_desc", "norad_id", "epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    norad_id: Mapped[int] = mapped_column(ForeignKey("satellites.norad_id", ondelete="CASCADE"))
    line1: Mapped[str] = mapped_column(String(70))
    line2: Mapped[str] = mapped_column(String(70))
    epoch: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    satellite: Mapped[Satellite] = relationship(back_populates="tles")


class OrbitalEvent(Base):
    __tablename__ = "orbital_events"
    __table_args__ = (
        UniqueConstraint("norad_id", "epoch_after", name="uq_event_norad_epoch_after"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    norad_id: Mapped[int] = mapped_column(
        ForeignKey("satellites.norad_id", ondelete="CASCADE"), index=True
    )
    epoch_before: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    epoch_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    gap_hours: Mapped[float]
    delta_sma_km: Mapped[float]
    delta_inclination_deg: Mapped[float]
    delta_eccentricity: Mapped[float]
    score: Mapped[float]
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    satellite: Mapped[Satellite] = relationship()


class AnalysisState(Base):
    """Single-row watermark: highest tle_history.id already analyzed."""

    __tablename__ = "analysis_state"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    last_tle_id: Mapped[int] = mapped_column(server_default="0")


class Launch(Base):
    __tablename__ = "launches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # LL2 UUID
    name: Mapped[str] = mapped_column(String(200))
    provider: Mapped[str] = mapped_column(String(120))
    mission: Mapped[str | None] = mapped_column(String(200))
    mission_type: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24))
    status_name: Mapped[str] = mapped_column(String(64))
    net: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pad: Mapped[str | None] = mapped_column(String(120))
    location: Mapped[str | None] = mapped_column(String(120))
    pad_lat: Mapped[float | None]
    pad_lon: Mapped[float | None]
    image_url: Mapped[str | None] = mapped_column(String(300))
    last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

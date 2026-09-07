from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint, func
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


class SatCatEntry(Base):
    """Space-Track satellite catalog metadata (full catalog incl. decayed objects)."""

    __tablename__ = "satcat"

    norad_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    object_name: Mapped[str] = mapped_column(String(64), index=True)
    object_id: Mapped[str | None] = mapped_column(String(16))  # intl designator
    object_type: Mapped[str | None] = mapped_column(String(16), index=True)
    country: Mapped[str | None] = mapped_column(String(16))
    launch_date: Mapped[date | None] = mapped_column(Date, index=True)
    decay_date: Mapped[date | None] = mapped_column(Date, index=True)
    launch_site: Mapped[str | None] = mapped_column(String(16))
    rcs_size: Mapped[str | None] = mapped_column(String(8))
    period_min: Mapped[float | None]
    inclination_deg: Mapped[float | None]
    apogee_km: Mapped[float | None]
    perigee_km: Mapped[float | None]
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DecayPrediction(Base):
    """Space-Track TIP / decay messages (predicted and historical re-entries)."""

    __tablename__ = "decay_predictions"
    __table_args__ = (
        UniqueConstraint("norad_id", "msg_epoch", "msg_type", name="uq_decay_norad_msg"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    norad_id: Mapped[int] = mapped_column(index=True)  # no FK: object may be untracked by us
    object_name: Mapped[str] = mapped_column(String(64))
    intl_des: Mapped[str | None] = mapped_column(String(16))
    rcs_size: Mapped[str | None] = mapped_column(String(8))
    country: Mapped[str | None] = mapped_column(String(16))
    msg_epoch: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decay_epoch: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str | None] = mapped_column(String(16))
    msg_type: Mapped[str] = mapped_column(String(16))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

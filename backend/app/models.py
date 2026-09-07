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

"""Maneuver detection: diff orbital elements between consecutive TLEs per satellite."""

import logging
import math

from sgp4.api import Satrec
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import TLE, AnalysisState, OrbitalEvent

logger = logging.getLogger(__name__)

MU = 398600.4418  # km^3/s^2
RAD = 180.0 / math.pi

# detection thresholds (v1, tune after more history accumulates)
SMA_KM = 0.5
INC_DEG = 0.01
ECC = 1e-4
MAX_GAP_HOURS = 30 * 24


def _elements(line1: str, line2: str) -> tuple[float, float, float]:
    """(semi-major axis km, inclination deg, eccentricity) from a TLE."""
    rec = Satrec.twoline2rv(line1, line2)
    period_s = (2 * math.pi / rec.no_kozai) * 60  # no_kozai is rad/min
    sma = (MU * (period_s / (2 * math.pi)) ** 2) ** (1 / 3)
    return sma, rec.inclo * RAD, rec.ecco


def _score(d_sma: float, d_inc: float, d_ecc: float) -> float:
    # drag only lowers SMA, so an increase is weighted as a stronger maneuver signal
    sma_w = 2.0 if d_sma > 0 else 1.0
    return round(sma_w * abs(d_sma) / SMA_KM + abs(d_inc) / INC_DEG + abs(d_ecc) / ECC, 2)


def analyze_new_tles(db: Session) -> tuple[int, int]:
    """Diff each TLE past the watermark against its predecessor; returns (pairs_checked, events_created)."""
    state = db.get(AnalysisState, 1)
    if state is None:
        state = AnalysisState(id=1, last_tle_id=0)
        db.add(state)
        db.flush()

    new_rows = db.scalars(
        select(TLE).where(TLE.id > state.last_tle_id).order_by(TLE.id)
    ).all()

    pairs_checked = 0
    events_created = 0
    max_id = state.last_tle_id

    for tle in new_rows:
        max_id = max(max_id, tle.id)
        prev = db.scalars(
            select(TLE)
            .where(TLE.norad_id == tle.norad_id, TLE.epoch < tle.epoch)
            .order_by(TLE.epoch.desc())
            .limit(1)
        ).first()
        if prev is None:
            continue
        gap_hours = (tle.epoch - prev.epoch).total_seconds() / 3600
        if gap_hours <= 0 or gap_hours > MAX_GAP_HOURS:
            continue

        try:
            sma_b, inc_b, ecc_b = _elements(prev.line1, prev.line2)
            sma_a, inc_a, ecc_a = _elements(tle.line1, tle.line2)
        except Exception:
            logger.warning("Unparseable TLE pair for norad_id=%s", tle.norad_id)
            continue

        pairs_checked += 1
        d_sma = sma_a - sma_b
        d_inc = inc_a - inc_b
        d_ecc = ecc_a - ecc_b
        if abs(d_sma) <= SMA_KM and abs(d_inc) <= INC_DEG and abs(d_ecc) <= ECC:
            continue

        exists = db.scalar(
            select(OrbitalEvent.id).where(
                OrbitalEvent.norad_id == tle.norad_id,
                OrbitalEvent.epoch_after == tle.epoch,
            )
        )
        if exists is not None:
            continue

        db.add(
            OrbitalEvent(
                norad_id=tle.norad_id,
                epoch_before=prev.epoch,
                epoch_after=tle.epoch,
                gap_hours=round(gap_hours, 2),
                delta_sma_km=round(d_sma, 4),
                delta_inclination_deg=round(d_inc, 5),
                delta_eccentricity=round(d_ecc, 7),
                score=_score(d_sma, d_inc, d_ecc),
            )
        )
        events_created += 1

    state.last_tle_id = max_id
    db.commit()
    logger.info("Maneuver analysis: %d pairs checked, %d events", pairs_checked, events_created)
    return pairs_checked, events_created

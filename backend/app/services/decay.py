"""Re-entry watch: decay-rate trends fitted from stored TLE history (no external data needed)."""

import logging
import math
import time
from datetime import datetime, timedelta, timezone

from sgp4.api import Satrec
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import TLE, Satellite

logger = logging.getLogger(__name__)

MU = 398600.4418  # km^3/s^2
R_EARTH = 6378.137  # km
REENTRY_ALT_KM = 120.0  # nominal re-entry interface altitude

_cache: dict[tuple, tuple[float, list[dict]]] = {}
CACHE_TTL_S = 600


def _elements(line1: str, line2: str) -> tuple[float, float, float]:
    """(semi-major axis km, eccentricity, bstar) from a TLE."""
    rec = Satrec.twoline2rv(line1, line2)
    period_s = (2 * math.pi / rec.no_kozai) * 60
    sma = (MU * (period_s / (2 * math.pi)) ** 2) ** (1 / 3)
    return sma, rec.ecco, rec.bstar


def _fit_slope(points: list[tuple[float, float]]) -> float:
    """Least-squares slope for (t_days, sma_km) points."""
    n = len(points)
    mean_t = sum(t for t, _ in points) / n
    mean_y = sum(y for _, y in points) / n
    denom = sum((t - mean_t) ** 2 for t, _ in points)
    if denom == 0:
        return 0.0
    return sum((t - mean_t) * (y - mean_y) for t, y in points) / denom


def decay_trends(
    db: Session,
    max_perigee_km: float = 300.0,
    days: int = 14,
    min_points: int = 3,
    limit: int = 100,
) -> list[dict]:
    """Low-perigee satellites ranked by fitted SMA decay rate (km/day)."""
    key = (max_perigee_km, days, min_points, limit)
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_TTL_S:
        return cached[1]

    now = datetime.now(timezone.utc)
    fresh_cutoff = now - timedelta(days=5)

    latest = db.execute(
        select(TLE.norad_id, TLE.line1, TLE.line2, TLE.epoch, Satellite.name, Satellite.group_name)
        .join(Satellite, Satellite.norad_id == TLE.norad_id)
        .where(TLE.epoch > fresh_cutoff)
        .order_by(TLE.norad_id, TLE.epoch.desc())
        .distinct(TLE.norad_id)
    ).all()

    candidates: dict[int, dict] = {}
    for norad, line1, line2, epoch, name, group_name in latest:
        try:
            sma, ecc, bstar = _elements(line1, line2)
        except Exception:
            continue
        perigee = sma * (1 - ecc) - R_EARTH
        if perigee >= max_perigee_km or perigee <= 0:
            continue
        candidates[norad] = dict(
            norad_id=norad,
            name=name,
            group_name=group_name,
            epoch=epoch,
            sma_km=round(sma, 2),
            perigee_km=round(perigee, 1),
            apogee_km=round(sma * (1 + ecc) - R_EARTH, 1),
            bstar=bstar,
        )

    if not candidates:
        _cache[key] = (time.monotonic(), [])
        return []

    hist_cutoff = now - timedelta(days=days)
    history = db.execute(
        select(TLE.norad_id, TLE.line1, TLE.line2, TLE.epoch)
        .where(TLE.norad_id.in_(candidates), TLE.epoch > hist_cutoff)
        .order_by(TLE.norad_id, TLE.epoch)
    ).all()

    series: dict[int, list[tuple[float, float]]] = {}
    for norad, line1, line2, epoch in history:
        try:
            sma, _, _ = _elements(line1, line2)
        except Exception:
            continue
        series.setdefault(norad, []).append(((epoch - now).total_seconds() / 86400.0, sma))

    results = []
    for norad, cand in candidates.items():
        pts = series.get(norad, [])
        if len(pts) < min_points:
            continue
        rate = -_fit_slope(pts)  # positive = decaying
        margin = cand["perigee_km"] - REENTRY_ALT_KM
        est_days = margin / rate if rate > 0.05 and margin > 0 else None
        results.append(
            dict(
                **cand,
                points=len(pts),
                decay_rate_km_day=round(rate, 3),
                est_days_left=round(est_days, 1) if est_days is not None else None,
                est_reentry=now + timedelta(days=est_days) if est_days is not None else None,
            )
        )

    results.sort(key=lambda r: (r["est_days_left"] is None, r["est_days_left"] or 0, -r["decay_rate_km_day"]))
    results = results[:limit]
    _cache[key] = (time.monotonic(), results)
    logger.info("Decay trends: %d candidates, %d with enough history", len(candidates), len(results))
    return results

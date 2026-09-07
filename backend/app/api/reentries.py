"""Re-entry dashboard: Space-Track TIP predictions + decay trends computed from TLE history."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from ..db import get_db
from ..models import DecayPrediction
from ..schemas import DecayTrendOut, ReentryPredictionOut
from ..services import decay

router = APIRouter(prefix="/api/reentries", tags=["reentries"])


@router.get("", response_model=list[ReentryPredictionOut])
def reentry_predictions(days_past: int = Query(7, ge=0, le=90), db: Session = Depends(get_db)):
    """Latest decay/TIP message per object with decay epoch after now - days_past."""
    latest = (
        select(DecayPrediction)
        .distinct(DecayPrediction.norad_id)
        .order_by(DecayPrediction.norad_id, DecayPrediction.msg_epoch.desc())
        .subquery()
    )
    dp = aliased(DecayPrediction, latest)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_past)
    return db.scalars(
        select(dp).where(dp.decay_epoch >= cutoff).order_by(dp.decay_epoch)
    ).all()


@router.get("/trends", response_model=list[DecayTrendOut])
def reentry_trends(
    max_perigee_km: float = Query(300.0, gt=0, le=1000),
    days: int = Query(14, ge=2, le=60),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Low-perigee satellites ranked by SMA decay rate fitted from our TLE history."""
    return decay.decay_trends(db, max_perigee_km=max_perigee_km, days=days, limit=limit)

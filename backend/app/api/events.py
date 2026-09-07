from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import OrbitalEvent, Satellite
from ..schemas import AnalyzeResult, EventOut
from ..services import maneuvers

router = APIRouter(prefix="/api", tags=["events"])


@router.get("/events", response_model=list[EventOut])
def list_events(
    norad_id: int | None = None,
    min_score: float | None = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = (
        select(OrbitalEvent, Satellite.name, Satellite.group_name)
        .join(Satellite, Satellite.norad_id == OrbitalEvent.norad_id)
        .order_by(OrbitalEvent.epoch_after.desc())
        .limit(limit)
        .offset(offset)
    )
    if norad_id is not None:
        q = q.where(OrbitalEvent.norad_id == norad_id)
    if min_score is not None:
        q = q.where(OrbitalEvent.score >= min_score)
    return [
        EventOut(
            id=ev.id,
            norad_id=ev.norad_id,
            name=name,
            group_name=group_name,
            epoch_before=ev.epoch_before,
            epoch_after=ev.epoch_after,
            gap_hours=ev.gap_hours,
            delta_sma_km=ev.delta_sma_km,
            delta_inclination_deg=ev.delta_inclination_deg,
            delta_eccentricity=ev.delta_eccentricity,
            score=ev.score,
            detected_at=ev.detected_at,
        )
        for ev, name, group_name in db.execute(q)
    ]


@router.post("/analyze/maneuvers", response_model=AnalyzeResult)
def analyze_maneuvers(db: Session = Depends(get_db)):
    pairs, events = maneuvers.analyze_new_tles(db)
    return AnalyzeResult(pairs_checked=pairs, events_created=events)

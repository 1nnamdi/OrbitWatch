from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Satellite
from ..schemas import (
    BackfillRequest,
    BackfillResult,
    IngestResult,
    LaunchIngestResult,
    SpaceTrackIngestResult,
)
from ..services import maneuvers
from ..sources import celestrak, launchlibrary, spacetrack

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post("/celestrak", response_model=IngestResult)
def ingest_celestrak(group: str = "stations", db: Session = Depends(get_db)):
    sats, new_tles = celestrak.ingest_group(db, group)
    return IngestResult(group=group, satellites=sats, new_tles=new_tles)


@router.post("/launches", response_model=LaunchIngestResult)
def ingest_launches(db: Session = Depends(get_db)):
    fetched, created, updated = launchlibrary.ingest_upcoming(db)
    return LaunchIngestResult(fetched=fetched, created=created, updated=updated)


@router.post("/spacetrack", response_model=SpaceTrackIngestResult)
def ingest_spacetrack(db: Session = Depends(get_db)):
    """Fetch satcat + decay/TIP messages from Space-Track (requires credentials in .env)."""
    if not spacetrack.enabled():
        raise HTTPException(503, "Space-Track credentials not configured")
    try:
        with spacetrack.SpaceTrackClient() as st:
            decay_rows = spacetrack.ingest_decay(db, st)
            satcat_rows = spacetrack.ingest_satcat(db, st)
    except spacetrack.SpaceTrackError as e:
        raise HTTPException(502, str(e))
    return SpaceTrackIngestResult(satcat_rows=satcat_rows, decay_rows=decay_rows)


@router.post("/spacetrack/backfill", response_model=BackfillResult)
def backfill_spacetrack(req: BackfillRequest, db: Session = Depends(get_db)):
    """Backfill historical TLEs (gp_history) for a group or explicit NORAD ids,
    then run maneuver analysis over the new rows. Rate-limited; large groups take a while."""
    if not spacetrack.enabled():
        raise HTTPException(503, "Space-Track credentials not configured")
    if req.norad_ids:
        ids = req.norad_ids
    elif req.group:
        ids = list(
            db.scalars(select(Satellite.norad_id).where(Satellite.group_name == req.group))
        )
    else:
        raise HTTPException(422, "Provide either group or norad_ids")
    if not ids:
        raise HTTPException(404, "No matching satellites")
    ids = ids[: req.max_satellites]

    try:
        with spacetrack.SpaceTrackClient() as st:
            requests_made, new_tles = spacetrack.backfill_tles(db, st, ids, days=req.days)
    except spacetrack.SpaceTrackError as e:
        raise HTTPException(502, str(e))
    _, events_created = maneuvers.analyze_new_tles(db)
    return BackfillResult(
        satellites=len(ids), requests=requests_made, new_tles=new_tles, events_created=events_created
    )

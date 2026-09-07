from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import IngestResult, LaunchIngestResult
from ..sources import celestrak, launchlibrary

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post("/celestrak", response_model=IngestResult)
def ingest_celestrak(group: str = "stations", db: Session = Depends(get_db)):
    sats, new_tles = celestrak.ingest_group(db, group)
    return IngestResult(group=group, satellites=sats, new_tles=new_tles)


@router.post("/launches", response_model=LaunchIngestResult)
def ingest_launches(db: Session = Depends(get_db)):
    fetched, created, updated = launchlibrary.ingest_upcoming(db)
    return LaunchIngestResult(fetched=fetched, created=created, updated=updated)

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import TLE, Satellite
from ..schemas import (
    GroundTrackOut,
    PassesOut,
    PositionOut,
    SatelliteDetail,
    SatelliteOut,
    TLEOut,
)
from ..services import propagation

router = APIRouter(prefix="/api", tags=["satellites"])


def latest_tle_query():
    """Latest TLE row per norad_id (Postgres DISTINCT ON)."""
    return (
        select(TLE)
        .order_by(TLE.norad_id, TLE.epoch.desc())
        .distinct(TLE.norad_id)
    )


def get_latest_tle(db: Session, norad_id: int) -> tuple[Satellite, TLE]:
    sat = db.get(Satellite, norad_id)
    if sat is None:
        raise HTTPException(404, f"Satellite {norad_id} not found")
    tle = db.scalars(
        select(TLE).where(TLE.norad_id == norad_id).order_by(TLE.epoch.desc()).limit(1)
    ).first()
    if tle is None:
        raise HTTPException(404, f"No TLE stored for satellite {norad_id}")
    return sat, tle


@router.get("/satellites", response_model=list[SatelliteOut])
def list_satellites(
    search: str | None = None,
    group: str | None = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = select(Satellite).order_by(Satellite.norad_id).limit(limit).offset(offset)
    if search:
        q = q.where(Satellite.name.ilike(f"%{search}%"))
    if group:
        q = q.where(Satellite.group_name == group)
    return db.scalars(q).all()


@router.get("/satellites/{norad_id}", response_model=SatelliteDetail)
def satellite_detail(norad_id: int, db: Session = Depends(get_db)):
    sat, tle = get_latest_tle(db, norad_id)
    return SatelliteDetail(
        norad_id=sat.norad_id,
        name=sat.name,
        group_name=sat.group_name,
        line1=tle.line1,
        line2=tle.line2,
        epoch=tle.epoch,
    )


@router.get("/satellites/{norad_id}/position", response_model=PositionOut)
def satellite_position(norad_id: int, db: Session = Depends(get_db)):
    sat, tle = get_latest_tle(db, norad_id)
    pos = propagation.current_position(sat.name, tle.line1, tle.line2)
    return PositionOut(norad_id=sat.norad_id, name=sat.name, **pos)


@router.get("/satellites/{norad_id}/groundtrack", response_model=GroundTrackOut)
def satellite_groundtrack(
    norad_id: int,
    minutes: int = Query(90, ge=10, le=360),
    step_seconds: int = Query(30, ge=5, le=300),
    db: Session = Depends(get_db),
):
    sat, tle = get_latest_tle(db, norad_id)
    points = propagation.ground_track(sat.name, tle.line1, tle.line2, minutes, step_seconds)
    return GroundTrackOut(norad_id=sat.norad_id, name=sat.name, points=points)


@router.get("/satellites/{norad_id}/passes", response_model=PassesOut)
def satellite_passes(
    norad_id: int,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    hours: int = Query(48, ge=1, le=168),
    min_altitude: float = Query(10.0, ge=0, le=90),
    db: Session = Depends(get_db),
):
    sat, tle = get_latest_tle(db, norad_id)
    passes = propagation.predict_passes(
        sat.name, tle.line1, tle.line2, lat, lon, hours, min_altitude
    )
    return PassesOut(
        norad_id=sat.norad_id,
        name=sat.name,
        observer_lat=lat,
        observer_lon=lon,
        passes=passes,
    )


@router.get("/tles", response_model=list[TLEOut])
def bulk_tles(
    group: str | None = None,
    limit: int = Query(20000, le=50000),
    db: Session = Depends(get_db),
):
    """Latest TLE per satellite, for client-side propagation."""
    latest = latest_tle_query().subquery()
    q = (
        select(
            Satellite.norad_id,
            Satellite.name,
            Satellite.group_name,
            latest.c.line1,
            latest.c.line2,
            latest.c.epoch,
        )
        .join(latest, latest.c.norad_id == Satellite.norad_id)
        .order_by(Satellite.norad_id)
        .limit(limit)
    )
    if group:
        q = q.where(Satellite.group_name == group)
    return [
        TLEOut(
            norad_id=row.norad_id,
            name=row.name,
            group_name=row.group_name,
            line1=row.line1,
            line2=row.line2,
            epoch=row.epoch,
        )
        for row in db.execute(q)
    ]


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    return {
        "satellites": db.scalar(select(func.count(Satellite.norad_id))),
        "tles": db.scalar(select(func.count(TLE.id))),
        "groups": [g for (g,) in db.execute(select(Satellite.group_name).distinct())],
    }

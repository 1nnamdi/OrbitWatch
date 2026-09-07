"""Constellation growth: on-orbit object counts over time, derived from the Space-Track satcat."""
from collections import Counter
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import SatCatEntry
from ..schemas import ConstellationGrowthOut, ConstellationSummary, GrowthPoint

router = APIRouter(prefix="/api/constellations", tags=["constellations"])

# object_name prefix -> display label
CONSTELLATIONS: dict[str, str] = {
    "STARLINK": "Starlink",
    "ONEWEB": "OneWeb",
    "IRIDIUM": "Iridium",
    "GLOBALSTAR": "Globalstar",
    "FLOCK": "Planet Flock",
    "LEMUR": "Spire Lemur",
    "KUIPER": "Kuiper",
    "QIANFAN": "Qianfan (G60)",
    "ORBCOMM": "Orbcomm",
    "GONETS": "Gonets",
}


def _members(prefix: str):
    return (
        SatCatEntry.object_name.like(f"{prefix}%"),
        SatCatEntry.object_type == "PAYLOAD",
        SatCatEntry.launch_date.isnot(None),
    )


@router.get("", response_model=list[ConstellationSummary])
def list_constellations(db: Session = Depends(get_db)):
    out = []
    for prefix, label in CONSTELLATIONS.items():
        total, decayed = db.execute(
            select(
                func.count(),
                func.count(SatCatEntry.decay_date),
            ).where(*_members(prefix))
        ).one()
        if total:
            out.append(
                ConstellationSummary(
                    prefix=prefix, label=label, total=total, on_orbit=total - decayed, decayed=decayed
                )
            )
    out.sort(key=lambda c: -c.on_orbit)
    return out


@router.get("/{prefix}/growth", response_model=ConstellationGrowthOut)
def constellation_growth(prefix: str, db: Session = Depends(get_db)):
    prefix = prefix.upper()
    if prefix not in CONSTELLATIONS:
        raise HTTPException(404, f"Unknown constellation: {prefix}")

    rows = db.execute(
        select(SatCatEntry.launch_date, SatCatEntry.decay_date).where(*_members(prefix))
    ).all()
    if not rows:
        return ConstellationGrowthOut(prefix=prefix, label=CONSTELLATIONS[prefix], points=[])

    launched = Counter((d.year, d.month) for d, _ in rows)
    decayed = Counter((d.year, d.month) for _, d in rows if d is not None)

    first = min(d for d, _ in rows)
    today = date.today()
    y, m = first.year, first.month
    cum_l = cum_d = 0
    points = []
    while (y, m) <= (today.year, today.month):
        cum_l += launched.get((y, m), 0)
        cum_d += decayed.get((y, m), 0)
        points.append(
            GrowthPoint(month=f"{y:04d}-{m:02d}", launched=cum_l, decayed=cum_d, on_orbit=cum_l - cum_d)
        )
        m += 1
        if m > 12:
            m, y = 1, y + 1

    return ConstellationGrowthOut(prefix=prefix, label=CONSTELLATIONS[prefix], points=points)

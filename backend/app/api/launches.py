from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Launch
from ..schemas import LaunchOut

router = APIRouter(prefix="/api", tags=["launches"])


@router.get("/launches", response_model=list[LaunchOut])
def list_launches(
    hours_back: int = Query(24, ge=0, le=720),
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Launches ordered by NET, including recently flown ones within hours_back."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    q = (
        select(Launch)
        .where(Launch.net >= cutoff)
        .order_by(Launch.net)
        .limit(limit)
        .offset(offset)
    )
    return db.scalars(q).all()

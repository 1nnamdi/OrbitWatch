"""CelesTrak GP data ingestion (TLE format)."""
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import TLE, Satellite

logger = logging.getLogger(__name__)

GP_URL = "https://celestrak.org/NORAD/elements/gp.php"


def tle_epoch(line1: str) -> datetime:
    yy = int(line1[18:20])
    year = 2000 + yy if yy < 57 else 1900 + yy
    day_of_year = float(line1[20:32])
    return datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_of_year - 1)


def parse_tle_text(text: str) -> list[tuple[str, str, str]]:
    """Return (name, line1, line2) triples from a 3LE response."""
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    triples = []
    for i in range(0, len(lines) - 2, 3):
        name, l1, l2 = lines[i], lines[i + 1], lines[i + 2]
        if l1.startswith("1 ") and l2.startswith("2 "):
            triples.append((name.strip(), l1, l2))
    return triples


def fetch_group(group: str, timeout: float = 60.0) -> list[tuple[str, str, str]]:
    resp = httpx.get(GP_URL, params={"GROUP": group, "FORMAT": "tle"}, timeout=timeout, follow_redirects=True)
    resp.raise_for_status()
    return parse_tle_text(resp.text)


def ingest_group(db: Session, group: str) -> tuple[int, int]:
    """Upsert satellites and insert TLEs with unseen epochs. Returns (sats, new_tles)."""
    triples = fetch_group(group)
    now = datetime.now(timezone.utc)
    norad_ids = []
    parsed = []
    for name, l1, l2 in triples:
        try:
            norad = int(l1[2:7])
            epoch = tle_epoch(l1)
        except ValueError:
            logger.warning("Skipping malformed TLE: %s", l1)
            continue
        norad_ids.append(norad)
        parsed.append((norad, name, l1, l2, epoch))

    existing_sats = {
        s.norad_id: s
        for s in db.scalars(select(Satellite).where(Satellite.norad_id.in_(norad_ids)))
    }
    latest_epochs = dict(
        db.execute(
            select(TLE.norad_id, TLE.epoch)
            .where(TLE.norad_id.in_(norad_ids))
            .order_by(TLE.norad_id, TLE.epoch.desc())
            .distinct(TLE.norad_id)
        ).all()
    )

    new_tles = 0
    for norad, name, l1, l2, epoch in parsed:
        sat = existing_sats.get(norad)
        if sat is None:
            sat = Satellite(norad_id=norad, name=name, group_name=group, first_seen=now, last_seen=now)
            db.add(sat)
            existing_sats[norad] = sat
        else:
            sat.name = name
            sat.last_seen = now

        known = latest_epochs.get(norad)
        if known is None or epoch > known:
            db.add(TLE(norad_id=norad, line1=l1, line2=l2, epoch=epoch, fetched_at=now))
            new_tles += 1

    db.commit()
    logger.info("Ingested group=%s sats=%d new_tles=%d", group, len(parsed), new_tles)
    return len(parsed), new_tles

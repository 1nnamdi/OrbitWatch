"""Space-Track.org integration: satcat metadata, decay/TIP messages, historical TLE backfill.

Free account required — set SPACETRACK_USER / SPACETRACK_PASSWORD in .env.
Rate limits: <=30 requests/min, <=300/hour; satcat should be queried at most daily.
"""
import logging
import time
from datetime import date, datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ..config import settings
from ..models import TLE, DecayPrediction, SatCatEntry, Satellite
from .celestrak import tle_epoch

logger = logging.getLogger(__name__)

BASE = "https://www.space-track.org"
REQUEST_PAUSE_S = 2.5  # stay well under 30 req/min
SATCAT_PREDICATES = (
    "NORAD_CAT_ID,OBJECT_NAME,OBJECT_ID,OBJECT_TYPE,COUNTRY,LAUNCH,DECAY,"
    "SITE,RCS_SIZE,PERIOD,INCLINATION,APOGEE,PERIGEE"
)


class SpaceTrackError(RuntimeError):
    pass


def enabled() -> bool:
    return bool(settings.spacetrack_user and settings.spacetrack_password)


class SpaceTrackClient:
    """Session-cookie authenticated client. Honors HTTPS_PROXY from the environment."""

    def __init__(self):
        if not enabled():
            raise SpaceTrackError(
                "Space-Track credentials not configured (SPACETRACK_USER / SPACETRACK_PASSWORD)"
            )
        self._client = httpx.Client(base_url=BASE, timeout=180.0, follow_redirects=True)
        self._logged_in = False

    def _login(self) -> None:
        resp = self._client.post(
            "/ajaxauth/login",
            data={"identity": settings.spacetrack_user, "password": settings.spacetrack_password},
        )
        if resp.status_code != 200 or "Failed" in resp.text[:200]:
            raise SpaceTrackError(f"Space-Track login failed (HTTP {resp.status_code})")
        self._logged_in = True

    def query(self, path: str) -> list[dict]:
        """GET a basicspacedata query path (already URL-encoded), re-logging in on 401."""
        if not self._logged_in:
            self._login()
        resp = self._client.get(path)
        if resp.status_code in (401, 403):
            self._login()
            resp = self._client.get(path)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):  # error payloads come back as a dict
            raise SpaceTrackError(f"Space-Track query error: {data}")
        return data

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SpaceTrackClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def _date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "")).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ingest_satcat(db: Session, client: SpaceTrackClient) -> int:
    """Upsert the full Space-Track catalog (incl. decayed objects). Returns rows upserted."""
    rows = client.query(
        f"/basicspacedata/query/class/satcat/predicates/{SATCAT_PREDICATES}"
        "/orderby/NORAD_CAT_ID%20asc/format/json"
    )
    now = datetime.now(timezone.utc)
    payload = []
    for r in rows:
        norad = int(r["NORAD_CAT_ID"])
        payload.append(
            dict(
                norad_id=norad,
                object_name=(r.get("OBJECT_NAME") or "UNKNOWN")[:64],
                object_id=(r.get("OBJECT_ID") or None) and r["OBJECT_ID"][:16],
                object_type=(r.get("OBJECT_TYPE") or None) and r["OBJECT_TYPE"][:16],
                country=(r.get("COUNTRY") or None) and r["COUNTRY"][:16],
                launch_date=_date(r.get("LAUNCH")),
                decay_date=_date(r.get("DECAY")),
                launch_site=(r.get("SITE") or None) and r["SITE"][:16],
                rcs_size=(r.get("RCS_SIZE") or None) and r["RCS_SIZE"][:8],
                period_min=_float(r.get("PERIOD")),
                inclination_deg=_float(r.get("INCLINATION")),
                apogee_km=_float(r.get("APOGEE")),
                perigee_km=_float(r.get("PERIGEE")),
                updated_at=now,
            )
        )

    chunk_size = 2000  # keep bind-param count under the Postgres limit
    for i in range(0, len(payload), chunk_size):
        chunk = payload[i : i + chunk_size]
        stmt = pg_insert(SatCatEntry).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=[SatCatEntry.norad_id],
            set_={c: stmt.excluded[c] for c in chunk[0] if c != "norad_id"},
        )
        db.execute(stmt)
    db.commit()
    logger.info("Space-Track satcat ingest: %d rows upserted", len(payload))
    return len(payload)


def ingest_decay(db: Session, client: SpaceTrackClient, days: int = 30) -> int:
    """Upsert decay/TIP messages published in the last `days`. Returns rows upserted."""
    rows = client.query(
        f"/basicspacedata/query/class/decay/MSG_EPOCH/%3Enow-{days}"
        "/orderby/DECAY_EPOCH%20asc/format/json"
    )
    now = datetime.now(timezone.utc)
    payload = []
    seen = set()
    for r in rows:
        msg_epoch = _dt(r.get("MSG_EPOCH"))
        decay_epoch = _dt(r.get("DECAY_EPOCH"))
        if msg_epoch is None or decay_epoch is None:
            continue
        norad = int(r["NORAD_CAT_ID"])
        msg_type = (r.get("MSG_TYPE") or "Prediction")[:16]
        key = (norad, msg_epoch, msg_type)
        if key in seen:
            continue
        seen.add(key)
        payload.append(
            dict(
                norad_id=norad,
                object_name=(r.get("OBJECT_NAME") or "UNKNOWN")[:64],
                intl_des=(r.get("INTLDES") or None) and r["INTLDES"][:16],
                rcs_size=(r.get("RCS_SIZE") or None) and r["RCS_SIZE"][:8],
                country=(r.get("COUNTRY") or None) and r["COUNTRY"][:16],
                msg_epoch=msg_epoch,
                decay_epoch=decay_epoch,
                source=(r.get("SOURCE") or None) and r["SOURCE"][:16],
                msg_type=msg_type,
                fetched_at=now,
            )
        )

    if payload:
        stmt = pg_insert(DecayPrediction).values(payload)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_decay_norad_msg",
            set_={"decay_epoch": stmt.excluded.decay_epoch, "fetched_at": stmt.excluded.fetched_at},
        )
        db.execute(stmt)
    db.commit()
    logger.info("Space-Track decay ingest: %d messages upserted", len(payload))
    return len(payload)


def backfill_tles(
    db: Session, client: SpaceTrackClient, norad_ids: list[int], days: int = 14
) -> tuple[int, int]:
    """Fetch historical TLEs (gp_history) for the given sats. Returns (requests, new_tles).

    Only ids already present in the satellites table are queried (FK constraint).
    """
    known_ids = set(
        db.scalars(select(Satellite.norad_id).where(Satellite.norad_id.in_(norad_ids)))
    )
    ids = sorted(known_ids)
    chunk_size = 50
    requests_made = 0
    new_tles = 0

    for i in range(0, len(ids), chunk_size):
        chunk = ids[i : i + chunk_size]
        if requests_made:
            time.sleep(REQUEST_PAUSE_S)
        rows = client.query(
            "/basicspacedata/query/class/gp_history"
            f"/NORAD_CAT_ID/{','.join(map(str, chunk))}"
            f"/EPOCH/%3Enow-{days}/orderby/EPOCH%20asc/format/json"
        )
        requests_made += 1

        existing = set(
            db.execute(
                select(TLE.norad_id, TLE.epoch).where(TLE.norad_id.in_(chunk))
            ).all()
        )
        now = datetime.now(timezone.utc)
        for r in rows:
            line1, line2 = r.get("TLE_LINE1"), r.get("TLE_LINE2")
            if not line1 or not line2:
                continue
            norad = int(r["NORAD_CAT_ID"])
            try:
                epoch = tle_epoch(line1)  # same derivation as celestrak ingest → dedupe works
            except ValueError:
                continue
            if (norad, epoch) in existing:
                continue
            existing.add((norad, epoch))
            db.add(TLE(norad_id=norad, line1=line1, line2=line2, epoch=epoch, fetched_at=now))
            new_tles += 1
        db.commit()
        logger.info(
            "Space-Track backfill: chunk %d/%d, %d TLEs so far",
            i // chunk_size + 1,
            (len(ids) + chunk_size - 1) // chunk_size,
            new_tles,
        )

    logger.info("Space-Track backfill done: sats=%d requests=%d new_tles=%d", len(ids), requests_made, new_tles)
    return requests_made, new_tles

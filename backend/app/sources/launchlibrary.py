"""Launch Library 2 (thespacedevs) upcoming-launch ingestion."""
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Launch

logger = logging.getLogger(__name__)

LL2_URL = "https://ll.thespacedevs.com/2.2.0/launch/upcoming/"


def _dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def fetch_upcoming(limit: int = 50, timeout: float = 60.0) -> list[dict]:
    # mode=list keeps the payload flat and small; free tier allows 15 req/hour
    resp = httpx.get(
        LL2_URL,
        params={"limit": limit, "mode": "list"},
        timeout=timeout,
        follow_redirects=True,
    )
    resp.raise_for_status()
    return resp.json()["results"]


def ingest_upcoming(db: Session, limit: int = 50) -> tuple[int, int, int]:
    """Upsert upcoming launches by LL2 id. Returns (fetched, created, updated)."""
    results = fetch_upcoming(limit)
    ids = [r["id"] for r in results]
    existing = {
        l.id: l for l in db.scalars(select(Launch).where(Launch.id.in_(ids)))
    }

    created = updated = 0
    now = datetime.now(timezone.utc)
    for r in results:
        fields = dict(
            name=r["name"][:200],
            provider=(r.get("lsp_name") or "Unknown")[:120],
            mission=(r.get("mission") or None) and r["mission"][:200],
            mission_type=(r.get("mission_type") or None) and r["mission_type"][:64],
            status=r["status"]["abbrev"][:24],
            status_name=r["status"]["name"][:64],
            net=_dt(r["net"]),
            window_start=_dt(r.get("window_start")),
            window_end=_dt(r.get("window_end")),
            pad=(r.get("pad") or None) and r["pad"][:120],
            location=(r.get("location") or None) and r["location"][:120],
            image_url=(r.get("image") or None) and r["image"][:300],
            last_updated=_dt(r.get("last_updated")),
        )
        launch = existing.get(r["id"])
        if launch is None:
            db.add(Launch(id=r["id"], fetched_at=now, **fields))
            created += 1
        else:
            changed = False
            for k, v in fields.items():
                if getattr(launch, k) != v:
                    setattr(launch, k, v)
                    changed = True
            if changed:
                launch.fetched_at = now
                updated += 1

    db.commit()
    logger.info("LL2 ingest: fetched=%d created=%d updated=%d", len(results), created, updated)
    return len(results), created, updated

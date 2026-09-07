import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import ingest, satellites
from .config import settings
from .db import SessionLocal
from .sources import celestrak

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def scheduled_ingest():
    for group in settings.groups:
        db = SessionLocal()
        try:
            celestrak.ingest_group(db, group)
        except Exception:
            logger.exception("Scheduled ingest failed for group=%s", group)
        finally:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        scheduled_ingest,
        "interval",
        hours=settings.ingest_interval_hours,
        jitter=300,
        id="celestrak_ingest",
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="OrbitWatch API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(satellites.router)
app.include_router(ingest.router)


@app.get("/")
def root():
    return {"app": "OrbitWatch", "docs": "/docs"}

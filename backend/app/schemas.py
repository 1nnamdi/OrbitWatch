from datetime import datetime

from pydantic import BaseModel


class SatelliteOut(BaseModel):
    norad_id: int
    name: str
    group_name: str

    model_config = {"from_attributes": True}


class TLEOut(BaseModel):
    norad_id: int
    name: str
    group_name: str
    line1: str
    line2: str
    epoch: datetime


class SatelliteDetail(SatelliteOut):
    line1: str | None = None
    line2: str | None = None
    epoch: datetime | None = None


class PositionOut(BaseModel):
    norad_id: int
    name: str
    time: datetime
    lat: float
    lon: float
    alt_km: float


class TrackPoint(BaseModel):
    time: datetime
    lat: float
    lon: float
    alt_km: float


class GroundTrackOut(BaseModel):
    norad_id: int
    name: str
    points: list[TrackPoint]


class PassEvent(BaseModel):
    rise: datetime
    culminate: datetime
    set: datetime
    max_altitude_deg: float


class PassesOut(BaseModel):
    norad_id: int
    name: str
    observer_lat: float
    observer_lon: float
    passes: list[PassEvent]


class IngestResult(BaseModel):
    group: str
    satellites: int
    new_tles: int


class EventOut(BaseModel):
    id: int
    norad_id: int
    name: str
    group_name: str
    epoch_before: datetime
    epoch_after: datetime
    gap_hours: float
    delta_sma_km: float
    delta_inclination_deg: float
    delta_eccentricity: float
    score: float
    detected_at: datetime


class AnalyzeResult(BaseModel):
    pairs_checked: int
    events_created: int


class LaunchOut(BaseModel):
    id: str
    name: str
    provider: str
    mission: str | None
    mission_type: str | None
    status: str
    status_name: str
    net: datetime
    window_start: datetime | None
    window_end: datetime | None
    pad: str | None
    location: str | None
    pad_lat: float | None
    pad_lon: float | None

    model_config = {"from_attributes": True}


class LaunchIngestResult(BaseModel):
    fetched: int
    created: int
    updated: int

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


class ReentryPredictionOut(BaseModel):
    norad_id: int
    object_name: str
    intl_des: str | None
    rcs_size: str | None
    country: str | None
    msg_epoch: datetime
    decay_epoch: datetime
    source: str | None
    msg_type: str

    model_config = {"from_attributes": True}


class DecayTrendOut(BaseModel):
    norad_id: int
    name: str
    group_name: str
    epoch: datetime
    sma_km: float
    perigee_km: float
    apogee_km: float
    bstar: float
    points: int
    decay_rate_km_day: float
    est_days_left: float | None
    est_reentry: datetime | None


class ConstellationSummary(BaseModel):
    prefix: str
    label: str
    total: int
    on_orbit: int
    decayed: int


class GrowthPoint(BaseModel):
    month: str  # YYYY-MM
    launched: int
    decayed: int
    on_orbit: int


class ConstellationGrowthOut(BaseModel):
    prefix: str
    label: str
    points: list[GrowthPoint]


class SpaceTrackIngestResult(BaseModel):
    satcat_rows: int
    decay_rows: int


class BackfillRequest(BaseModel):
    group: str | None = None
    norad_ids: list[int] | None = None
    days: int = 14
    max_satellites: int = 500


class BackfillResult(BaseModel):
    satellites: int
    requests: int
    new_tles: int
    events_created: int

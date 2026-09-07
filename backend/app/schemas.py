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

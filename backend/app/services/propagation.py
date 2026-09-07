"""Orbit propagation and pass prediction built on skyfield/SGP4."""
from datetime import datetime, timedelta, timezone

from skyfield.api import EarthSatellite, load, wgs84

ts = load.timescale()


def _sat(name: str, line1: str, line2: str) -> EarthSatellite:
    return EarthSatellite(line1, line2, name, ts)


def current_position(name: str, line1: str, line2: str, when: datetime | None = None) -> dict:
    when = when or datetime.now(timezone.utc)
    t = ts.from_datetime(when)
    geo = wgs84.geographic_position_of(_sat(name, line1, line2).at(t))
    return {
        "time": when,
        "lat": geo.latitude.degrees,
        "lon": geo.longitude.degrees,
        "alt_km": geo.elevation.km,
    }


def ground_track(
    name: str,
    line1: str,
    line2: str,
    minutes: int = 90,
    step_seconds: int = 30,
) -> list[dict]:
    """Track from -minutes/2 to +minutes/2 around now."""
    sat = _sat(name, line1, line2)
    start = datetime.now(timezone.utc) - timedelta(minutes=minutes / 2)
    times = [start + timedelta(seconds=i) for i in range(0, minutes * 60 + 1, step_seconds)]
    t = ts.from_datetimes(times)
    geo = wgs84.geographic_position_of(sat.at(t))
    return [
        {"time": when, "lat": float(lat), "lon": float(lon), "alt_km": float(alt)}
        for when, lat, lon, alt in zip(
            times, geo.latitude.degrees, geo.longitude.degrees, geo.elevation.km
        )
    ]


def predict_passes(
    name: str,
    line1: str,
    line2: str,
    lat: float,
    lon: float,
    hours: int = 48,
    min_altitude_deg: float = 10.0,
) -> list[dict]:
    sat = _sat(name, line1, line2)
    observer = wgs84.latlon(lat, lon)
    t0 = ts.from_datetime(datetime.now(timezone.utc))
    t1 = ts.from_datetime(datetime.now(timezone.utc) + timedelta(hours=hours))
    times, events = sat.find_events(observer, t0, t1, altitude_degrees=min_altitude_deg)

    passes: list[dict] = []
    current: dict = {}
    for t, event in zip(times, events):
        when = t.utc_datetime()
        if event == 0:
            current = {"rise": when}
        elif event == 1 and "rise" in current:
            alt, _, _ = (sat - observer).at(t).altaz()
            current["culminate"] = when
            current["max_altitude_deg"] = round(float(alt.degrees), 1)
        elif event == 2 and "culminate" in current:
            current["set"] = when
            passes.append(current)
            current = {}
    return passes

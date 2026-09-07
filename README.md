# 🛰 OrbitWatch

**OrbitWatch** is an open-source OSINT platform that gathers public data, stores it, analyses it, and visualises it in a fun way — starting with **space** (live satellite tracking), and expanding into aviation, maritime, earth events, and beyond.

> Track 16,000+ active satellites live on a 3D globe, follow ground tracks on a 2D map, predict when the ISS flies over your house, and inspect the full orbital profile of any object with a single click.

---

## Features

### 🌍 Live 3D globe
- All ~16k active catalog objects (or just the space stations) animated in real time
- Client-side SGP4 propagation with [satellite.js](https://github.com/shashwatak/satellite-js) — smooth updates without hammering the API
- **Click any dot** to open a full detail panel (screen-space picking with occlusion — satellites behind the Earth are not selectable)

### 🗺 2D ground track
- Leaflet dark map with the ±90 min ground track of any satellite
- Live position marker refreshed every 5 seconds, antimeridian-aware track splitting

### 🔎 Satellite detail panel (globe + map)
Everything derivable from the latest TLE, computed client-side:
- **Live telemetry** — latitude, longitude, altitude, speed (km/s & km/h), updated every second
- **Identity** — NORAD ID, international designator, launch year & number, classification, catalog group
- **Orbit** — type (LEO/MEO/GEO/HEO), period & rev/day, inclination, apogee/perigee, semi-major axis, eccentricity, RAAN, argument of perigee, mean anomaly, B* drag term, revolution number
- **TLE epoch** and its age

### 📡 Pass predictions
- "When is X overhead?" — rise/culminate/set times and max elevation for any satellite over any observer location, up to 7 days ahead

### ⚙️ Data pipeline
- Scheduled ingestion from [CelesTrak](https://celestrak.org) (APScheduler, every 2 h by default)
- Full TLE history stored in PostgreSQL (dedup on `norad_id` + `epoch`) — the foundation for future maneuver detection and decay analysis
- Server-side propagation with [Skyfield](https://rhodesmill.org/skyfield/)/SGP4 for position, ground track, and pass endpoints

---

## Architecture

```
CelesTrak ──(APScheduler, 2h)──▶ FastAPI backend ──▶ PostgreSQL 16
                                      │                (satellites + tle_history)
                                      ▼
                            REST API  /api/…
                                      │
                                      ▼
                    React + Vite frontend (:5173)
             ┌───────────────┼────────────────┐
         3D globe        2D ground track    passes
      (react-globe.gl)   (react-leaflet)    table
      satellite.js client-side propagation
```

Every domain follows the same pipeline: **ingest → store (raw + structured) → analyse → visualise**. Build it once for satellites, reuse it for each new domain — see [ROADMAP.md](ROADMAP.md).

### Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.13, FastAPI, SQLAlchemy 2, Alembic, APScheduler, Skyfield/SGP4, httpx |
| Database | PostgreSQL 16 (Docker) |
| Frontend | React 18, TypeScript, Vite, react-globe.gl (three.js), react-leaflet, satellite.js, TanStack Query |

---

## Getting started

### Prerequisites
- Docker (for PostgreSQL and, optionally, the frontend dev server)
- Python 3.12+
- Node 20+ (only if running the frontend outside Docker)

### 1. Start the database (and frontend) containers

```sh
docker compose up -d db frontend
```

This starts:
- **db** — PostgreSQL 16 on `:5432` (user/pass/db: `orbitwatch`)
- **frontend** — Vite dev server on [http://localhost:5173](http://localhost:5173), proxying `/api` to the host backend
- **pgadmin** (optional) — [http://localhost:8080](http://localhost:8080)

### 2. Run the backend

```sh
cd backend
pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --port 8800 --reload
```

API docs are served at [http://localhost:8800/docs](http://localhost:8800/docs).

> **Note:** the frontend proxies API calls to port **8800** (port 8000 falls into the default Windows excluded-port range on some machines). Override with the `API_PROXY_TARGET` environment variable of the frontend container.

### 3. Ingest satellite data

```sh
# space stations only (fast)
curl -X POST "http://localhost:8800/api/ingest/celestrak?group=stations"

# full active catalog (~16k objects)
curl -X POST "http://localhost:8800/api/ingest/celestrak?group=active"
```

Ingestion also runs automatically every 2 hours (configurable).

### 4. Open the app

Go to [http://localhost:5173](http://localhost:5173) — Globe, Ground Track, and Passes pages are in the top navigation.

### Configuration

Backend settings via environment variables or `backend/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+psycopg://orbitwatch:orbitwatch@localhost:5432/orbitwatch` | SQLAlchemy connection string |
| `CELESTRAK_GROUPS` | `stations,active` | Groups fetched by the scheduler |
| `INGEST_INTERVAL_HOURS` | `2.0` | Scheduled ingest interval |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins |

---

## API overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/satellites?search=&group=` | Search the catalog |
| `GET` | `/api/satellites/{norad_id}` | Satellite detail incl. latest TLE |
| `GET` | `/api/satellites/{norad_id}/position` | Current geodetic position |
| `GET` | `/api/satellites/{norad_id}/groundtrack?minutes=` | Ground track points |
| `GET` | `/api/satellites/{norad_id}/passes?lat=&lon=&hours=` | Pass predictions for an observer |
| `GET` | `/api/tles?group=` | Latest TLE per satellite (bulk, for client-side propagation) |
| `GET` | `/api/stats` | Catalog counts and groups |
| `POST` | `/api/ingest/celestrak?group=` | Trigger an ingest run |
| `GET` | `/api/tiles/{z}/{x}/{y}.png` | Map tile proxy (for restrictive networks) |

Interactive documentation: `http://localhost:8800/docs`

---

## Project structure

```
backend/
  alembic/            # database migrations
  app/
    api/              # routers: satellites, ingest, tiles
    services/         # SGP4/Skyfield propagation & pass prediction
    sources/          # data source clients (celestrak)
    config.py         # env-based settings
    models.py         # Satellite + TLE history tables
frontend/
  src/
    pages/            # GlobePage, MapPage, PassesPage
    components/       # SatelliteSearch, SatDetails
    api.ts            # typed API client
  public/textures/    # self-hosted globe textures
docker-compose.yml    # db + pgadmin + frontend dev server
```

---

## Roadmap

Space is just the first vertical slice. Planned domains (see [ROADMAP.md](ROADMAP.md) for full details):

- 🛰 **Space** — Space-Track integration, launch tracker, maneuver/anomaly detection, re-entry dashboard
- ✈️ **Aviation** — live ADS-B map, emergency squawk alerts, military aircraft watcher
- 🚢 **Maritime** — AIS ingestion, dark fleet detection, port congestion
- 🌍 **Earth & events** — earthquakes, wildfires, aurora/ISS spotting alerts
- 💻 **Cyber** — certificate transparency, BGP anomalies
- 🔮 **Fusion** — cross-domain correlation on one globe

## Data sources

| Source | Auth | Used for |
|--------|------|----------|
| [CelesTrak](https://celestrak.org) | none | TLEs / GP data (current) |
| [Space-Track.org](https://www.space-track.org) | free account | catalog history (planned) |
| [Launch Library 2](https://thespacedevs.com/llapi) | none | launches (planned) |

## License

See [LICENSE](LICENSE).

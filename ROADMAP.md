# OrbitWatch — Roadmap & Build Tracker

> OrbitWatch is an OSINT platform that gathers public data, stores it, analyses it, and visualises it in a fun way — starting with space, expanding into aviation, maritime, and beyond.

**Legend:** 🔲 planned · 🔨 in progress · ✅ done · 💤 parked

---

## Vision

One platform, many trackers. Every domain follows the same pipeline:

```
ingest (scheduled fetch) → store (raw + structured) → analyse (compute/alert) → visualise (map/globe/dashboard)
```

Build the pipeline once for satellites, then reuse it for each new domain.

---

## Phase 0 — Foundation 🔨 (today / this week)

| Status | Task | Notes |
|--------|------|-------|
| ✅ | Decide core stack | Python + FastAPI + PostgreSQL (Docker), React + Vite frontend |
| ✅ | Repo scaffolding | `backend/`, `frontend/`, docker-compose, `.env.example`, `.gitignore` |
| ✅ | Generic ingestion framework | CelesTrak source + APScheduler (2h interval); more sources plug in later |
| ✅ | Database schema v1 | `satellites` + `tle_history` via Alembic |
| 🔲 | Dev tooling | Linting, tests, run scripts |

## Phase 1 — Space 🛰️ (first vertical slice)

| Status | Task | Notes |
|--------|------|-------|
| ✅ | Fetch ISS TLE from CelesTrak | Done via `stations` group ingest |
| ✅ | Store TLE history | Every new epoch stored; dedup on (norad_id, epoch) |
| ✅ | Propagate position with SGP4 (`skyfield`) | `/position`, `/groundtrack` endpoints |
| ✅ | 2D ground-track map | Leaflet + Esri dark tiles via backend tile proxy |
| ✅ | Expand to full CelesTrak catalog (~30k objects) | ~16k active objects ingested |
| ✅ | Pass predictions ("when is X overhead?") | `/passes` endpoint + UI page |
| ✅ | 3D globe (CesiumJS or Globe.gl) | react-globe.gl, client-side satellite.js propagation, 16k live objects |
| ✅ | Click-to-inspect satellite details | Click any globe dot → full panel: live telemetry, identity, orbital elements, TLE epoch (also on map page) |
| 🔲 | Space-Track.org integration | Free account; richer history, decay/re-entry data |
| 🔲 | Launch tracker (Launch Library 2 API) | Upcoming launches feed |
| 🔲 | Maneuver/anomaly detection | Diff TLE history — spot spy sat maneuvers |
| 🔲 | Re-entry prediction dashboard | Decay trends |
| 🔲 | Constellation growth visualizer | Starlink et al. over time |

## Phase 2 — Aviation ✈️

| Status | Task | Notes |
|--------|------|-------|
| 🔲 | OpenSky Network ingestion | Live ADS-B state vectors |
| 🔲 | Live flight map | Reuse map/globe components from Phase 1 |
| 🔲 | Emergency squawk alerter (7700/7600/7500) | Real-time alerts |
| 🔲 | Military/interesting aircraft watcher | Circling patterns, watchlists (ADS-B Exchange) |
| 🔲 | Historical flight analytics | Delays, congestion, patterns |

## Phase 3 — Maritime 🚢

| Status | Task | Notes |
|--------|------|-------|
| 🔲 | AIS ingestion (AISStream.io websocket) | Free tier available |
| 🔲 | Live ship map | Reuse map components |
| 🔲 | Dark fleet detector | AIS gap analysis (ships going silent) |
| 🔲 | Port congestion monitor | Cluster positions near ports |
| 🔲 | Undersea cable loitering watcher | AIS + cable route overlays |

## Phase 4 — Earth & Events 🌍

| Status | Task | Notes |
|--------|------|-------|
| 🔲 | Earthquake feed (USGS) | Easy win, great for alert framework |
| 🔲 | Wildfire tracker (NASA FIRMS) | |
| 🔲 | Aurora/ISS spotting alerter | NOAA SWPC + pass predictions from Phase 1 |
| 🔲 | Satellite imagery change detection (Sentinel-2) | Stretch goal |

## Phase 5 — Cyber & Beyond 💻 (ideas backlog)

| Status | Task | Notes |
|--------|------|-------|
| 💤 | Certificate transparency monitor (crt.sh) | |
| 💤 | Data breach monitor (HaveIBeenPwned) | |
| 💤 | BGP anomaly detector (RIPE RIS) | |
| 💤 | Congress/insider trading tracker (SEC EDGAR) | |
| 💤 | Government contract monitor (USASpending.gov) | |
| 💤 | GDELT event/news mapper | |

## Phase 6 — Cross-domain fusion 🔮 (the endgame)

| Status | Task | Notes |
|--------|------|-------|
| 💤 | Multi-modal correlation engine | Aircraft + ships + satellites over same region = event detection |
| 💤 | "Something's happening" anomaly alerts | Unusual activity detection across all feeds |
| 💤 | Unified OSINT dashboard | Everything on one globe |

---

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-09-07 | Start with space domain | Fits the name; free no-auth data (CelesTrak); teaches the full pipeline |
| 2026-09-07 | FastAPI + PostgreSQL (Docker) + React/Vite + Globe.gl | Chosen over SQLite/plain-JS starters |
| 2026-09-07 | Client-side propagation (satellite.js) for globe animation | Smooth updates without hammering the API; backend stays source of truth |
| 2026-09-07 | Python deps via `pip install --user`, frontend runs in Docker (MCR node image) | Group policy blocks venv/npx executables in project dirs; Docker Hub blocked by proxy → use mcr.microsoft.com |
| 2026-09-07 | Backend on port 8800 | Port 8000 reserved by Windows port exclusions |

## Working Notes

- 2026-09-07: Phase 0 + most of Phase 1 built and verified end-to-end. Backend on :8800 (docs at /docs), 16k sats ingested, ISS position/passes verified. Frontend on :5173 (globe / ground track / passes all working). Corporate-network workarounds: backend tile proxy (`/api/tiles`) because content filter blocks direct tile <img> loads; globe textures self-hosted in `frontend/public/textures/`.

### How to run

1. `docker compose up -d db frontend`
2. `python -m uvicorn app.main:app --port 8800 --app-dir backend --reload` (deps installed via `pip install --user`)
3. Open http://localhost:5173 — ingest via `POST /api/ingest/celestrak?group=active` (also auto-runs every 2h)

## Data Sources Reference

| Domain | Source | Auth | Notes |
|--------|--------|------|-------|
| Space | [CelesTrak](https://celestrak.org) | None | TLEs, GP data |
| Space | [Space-Track.org](https://www.space-track.org) | Free account | Official catalog, history |
| Space | [Launch Library 2](https://thespacedevs.com/llapi) | None (rate-limited) | Launches |
| Aviation | [OpenSky Network](https://opensky-network.org) | Free account helps | ADS-B |
| Aviation | ADS-B Exchange | Paid/feeder | Unfiltered military |
| Maritime | [AISStream.io](https://aisstream.io) | Free API key | AIS websocket |
| Earth | [USGS Earthquakes](https://earthquake.usgs.gov) | None | GeoJSON feeds |
| Earth | [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov) | Free key | Fires |

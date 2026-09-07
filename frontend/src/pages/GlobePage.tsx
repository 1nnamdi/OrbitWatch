import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Globe, { type GlobeMethods } from "react-globe.gl";
import { gstime, propagate, twoline2satrec, eciToGeodetic, degreesLat, degreesLong } from "satellite.js";
import { useQuery } from "@tanstack/react-query";
import { api, type Launch, type SatelliteSummary } from "../api";
import SatelliteSearch from "../components/SatelliteSearch";
import SatDetails from "../components/SatDetails";
import { STATUS_COLORS, countdown } from "./LaunchesPage";

const EARTH_RADIUS_KM = 6371;
const GLOBE_RADIUS = 100; // three-globe internal globe radius
const PICK_RADIUS_PX = 15;

interface SatPoint {
  norad_id: number;
  name: string;
  lat: number;
  lng: number;
  alt: number;
  alt_km: number;
}

export default function GlobePage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const pointsRef = useRef<SatPoint[]>([]);
  const downPos = useRef<{ x: number; y: number } | null>(null);
  const [size, setSize] = useState({ w: window.innerWidth, h: window.innerHeight - 50 });
  const [group, setGroup] = useState("stations");
  const [selected, setSelected] = useState<SatelliteSummary | null>(null);
  const [selectedLaunch, setSelectedLaunch] = useState<Launch | null>(null);
  const [now, setNow] = useState(Date.now());
  const [points, setPoints] = useState<SatPoint[]>([]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver(() =>
      setSize({ w: el.clientWidth, h: el.clientHeight })
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const { data: tles } = useQuery({
    queryKey: ["tles", group],
    queryFn: () => api.tles(group === "all" ? undefined : group),
    staleTime: 30 * 60_000,
  });

  const { data: launches } = useQuery({
    queryKey: ["launches"],
    queryFn: api.launches,
    staleTime: 5 * 60_000,
  });

  // upcoming (or <24h old) launches with known pad coordinates, soonest first
  const launchMarkers = useMemo(
    () =>
      (launches ?? [])
        .filter((l) => l.pad_lat != null && l.pad_lon != null)
        .sort((a, b) => a.net.localeCompare(b.net)),
    [launches]
  );

  // one label per distinct pad to avoid overdraw
  const padLabels = useMemo(() => {
    const seen = new Map<string, Launch>();
    for (const l of launchMarkers) {
      const key = `${l.pad_lat},${l.pad_lon}`;
      if (!seen.has(key)) seen.set(key, l);
    }
    return [...seen.values()];
  }, [launchMarkers]);

  useEffect(() => {
    if (!selectedLaunch) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [selectedLaunch]);

  const pickLaunch = useCallback(
    (id: string) => {
      const launch = launchMarkers.find((l) => l.id === id) ?? null;
      setSelectedLaunch(launch);
      if (launch) {
        setSelected(null);
        globeRef.current?.pointOfView(
          { lat: launch.pad_lat!, lng: launch.pad_lon!, altitude: 1.2 },
          1200
        );
      }
    },
    [launchMarkers]
  );

  const satrecs = useMemo(
    () =>
      (tles ?? []).map((t) => ({
        norad_id: t.norad_id,
        name: t.name,
        rec: twoline2satrec(t.line1, t.line2),
      })),
    [tles]
  );

  useEffect(() => {
    if (satrecs.length === 0) return;
    // heavier catalogs update less often to keep the main thread responsive
    const intervalMs = satrecs.length > 2000 ? 3000 : 1000;

    const tick = () => {
      const now = new Date();
      const gmst = gstime(now);
      const next: SatPoint[] = [];
      for (const { norad_id, name, rec } of satrecs) {
        const pv = propagate(rec, now);
        if (!pv || typeof pv.position !== "object") continue;
        const geo = eciToGeodetic(pv.position, gmst);
        next.push({
          norad_id,
          name,
          lat: degreesLat(geo.latitude),
          lng: degreesLong(geo.longitude),
          alt: geo.height / EARTH_RADIUS_KM,
          alt_km: geo.height,
        });
      }
      setPoints(next);
      pointsRef.current = next;
    };

    tick();
    const id = setInterval(tick, intervalMs);
    return () => clearInterval(id);
  }, [satrecs]);

  // Screen-space picking: nearest visible satellite within PICK_RADIUS_PX of the click.
  // The particles layer's own raycast threshold is too strict for 2.5px dots.
  const pickSatellite = useCallback((clickX: number, clickY: number): SatPoint | null => {
    const globe = globeRef.current;
    if (!globe) return null;
    const cam = globe.camera().position;
    const camLen2 = cam.x * cam.x + cam.y * cam.y + cam.z * cam.z;
    let best: SatPoint | null = null;
    let bestDist = PICK_RADIUS_PX;
    for (const p of pointsRef.current) {
      const s = globe.getScreenCoords(p.lat, p.lng, p.alt);
      const dx = s.x - clickX;
      const dy = s.y - clickY;
      if (Math.abs(dx) > bestDist || Math.abs(dy) > bestDist) continue;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist >= bestDist) continue;
      // occlusion: skip satellites hidden behind the globe sphere
      const w = globe.getCoords(p.lat, p.lng, p.alt);
      const dxw = w.x - cam.x;
      const dyw = w.y - cam.y;
      const dzw = w.z - cam.z;
      const a = dxw * dxw + dyw * dyw + dzw * dzw;
      const b = 2 * (cam.x * dxw + cam.y * dyw + cam.z * dzw);
      const c = camLen2 - GLOBE_RADIUS * GLOBE_RADIUS;
      const disc = b * b - 4 * a * c;
      if (disc > 0) {
        const t = (-b - Math.sqrt(disc)) / (2 * a);
        if (t > 0 && t < 0.999) continue; // globe surface sits between camera and satellite
      }
      best = p;
      bestDist = dist;
    }
    return best;
  }, []);

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!(e.target instanceof HTMLCanvasElement)) return;
      // ignore drag-rotate releases
      if (downPos.current && Math.hypot(e.clientX - downPos.current.x, e.clientY - downPos.current.y) > 5) return;
      const rect = e.currentTarget.getBoundingClientRect();
      const hit = pickSatellite(e.clientX - rect.left, e.clientY - rect.top);
      if (hit) {
        setSelectedLaunch(null);
        setSelected({
          norad_id: hit.norad_id,
          name: hit.name,
          group_name: "",
        });
      }
    },
    [pickSatellite]
  );

  const selectedPoint = useMemo(
    () => points.find((p) => p.norad_id === selected?.norad_id),
    [points, selected]
  );

  // TLE for the selected sat: from the loaded set, else fetched on demand
  const localTle = useMemo(
    () => tles?.find((t) => t.norad_id === selected?.norad_id),
    [tles, selected]
  );
  const { data: fetchedTle } = useQuery({
    queryKey: ["detail", selected?.norad_id],
    queryFn: () => api.detail(selected!.norad_id),
    enabled: !!selected && !localTle,
    staleTime: 30 * 60_000,
  });
  const selectedTle = localTle ?? (fetchedTle?.norad_id === selected?.norad_id ? fetchedTle : undefined);

  return (
    <div
      ref={containerRef}
      style={{ height: "100%", overflow: "hidden" }}
      onMouseDown={(e) => (downPos.current = { x: e.clientX, y: e.clientY })}
      onClick={handleClick}
    >
      <Globe
        ref={globeRef}
        width={size.w}
        height={size.h}
        globeImageUrl="/textures/earth-night.jpg"
        backgroundImageUrl="/textures/night-sky.png"
        particlesData={[{ list: points }]}
        particlesList="list"
        particleLat="lat"
        particleLng="lng"
        particleAltitude="alt"
        particleLabel="name"
        particlesColor={() => "#7fffd4"}
        particlesSize={2.5}
        pointsData={selectedPoint ? [selectedPoint] : []}
        pointLat="lat"
        pointLng="lng"
        pointAltitude="alt"
        pointColor={() => "#ff5252"}
        pointRadius={0.6}
        ringsData={padLabels}
        ringLat="pad_lat"
        ringLng="pad_lon"
        ringColor={(l: object) =>
          (l as Launch).id === selectedLaunch?.id
            ? (t: number) => `rgba(255,82,82,${1 - t})`
            : (t: number) => `rgba(255,183,77,${(1 - t) * 0.7})`
        }
        ringMaxRadius={3.5}
        ringPropagationSpeed={1.5}
        ringRepeatPeriod={1400}
        labelsData={padLabels}
        labelLat="pad_lat"
        labelLng="pad_lon"
        labelText="pad"
        labelSize={0.55}
        labelDotRadius={0.25}
        labelColor={() => "#ffb74d"}
        labelResolution={2}
      />
      <div className="panel">
        <h3>Live catalog</h3>
        <select value={group} onChange={(e) => setGroup(e.target.value)}>
          <option value="stations">Stations (ISS, CSS…)</option>
          <option value="all">Full catalog</option>
        </select>
        <span className="muted" style={{ fontSize: "0.8rem" }}>
          {points.length.toLocaleString()} objects on globe — click one for details
        </span>
        <h3 style={{ marginTop: "0.8rem" }}>🚀 Launches</h3>
        <select
          value={selectedLaunch?.id ?? ""}
          onChange={(e) => pickLaunch(e.target.value)}
        >
          <option value="">Select a launch…</option>
          {launchMarkers.map((l) => (
            <option key={l.id} value={l.id}>
              {new Date(l.net).toLocaleString(undefined, {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}{" "}
              — {l.name}
            </option>
          ))}
        </select>
        {selectedLaunch && (
          <div className="details">
            <div className="dhead">
              <b>{selectedLaunch.name}</b>
              <button className="dclose" onClick={() => setSelectedLaunch(null)} title="Close">
                ×
              </button>
            </div>
            <div className="drow">
              <span>Countdown</span>
              <span style={{ color: "var(--accent)", fontVariantNumeric: "tabular-nums" }}>
                {countdown(selectedLaunch.net, now)}
              </span>
            </div>
            <div className="drow">
              <span>Status</span>
              <span
                style={{ color: STATUS_COLORS[selectedLaunch.status] ?? "#9e9e9e", fontWeight: 600 }}
                title={selectedLaunch.status_name}
              >
                {selectedLaunch.status_name}
              </span>
            </div>
            <div className="drow">
              <span>NET</span>
              <span>{new Date(selectedLaunch.net).toLocaleString()}</span>
            </div>
            <div className="drow">
              <span>Provider</span>
              <span>{selectedLaunch.provider}</span>
            </div>
            {selectedLaunch.mission && (
              <div className="drow">
                <span>Mission</span>
                <span>
                  {selectedLaunch.mission}
                  {selectedLaunch.mission_type ? ` · ${selectedLaunch.mission_type}` : ""}
                </span>
              </div>
            )}
            {selectedLaunch.pad && (
              <div className="drow">
                <span>Pad</span>
                <span>{selectedLaunch.pad}</span>
              </div>
            )}
            {selectedLaunch.location && (
              <div className="drow">
                <span>Site</span>
                <span>{selectedLaunch.location}</span>
              </div>
            )}
          </div>
        )}
        <h3 style={{ marginTop: "0.8rem" }}>Track a satellite</h3>
        <SatelliteSearch selected={selected} onSelect={(s) => { setSelectedLaunch(null); setSelected(s); }} />
        {selected &&
          (selectedTle ? (
            <SatDetails
              norad_id={selectedTle.norad_id}
              name={selectedTle.name}
              group_name={selectedTle.group_name || undefined}
              line1={selectedTle.line1}
              line2={selectedTle.line2}
              onClose={() => setSelected(null)}
            />
          ) : (
            <div className="telemetry">
              <b>{selected.name}</b> #{selected.norad_id}
              <br />
              <span className="muted">loading orbital data…</span>
            </div>
          ))}
      </div>
    </div>
  );
}

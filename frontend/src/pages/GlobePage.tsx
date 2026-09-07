import { useEffect, useMemo, useRef, useState } from "react";
import Globe from "react-globe.gl";
import { gstime, propagate, twoline2satrec, eciToGeodetic, degreesLat, degreesLong } from "satellite.js";
import { useQuery } from "@tanstack/react-query";
import { api, type SatelliteSummary } from "../api";
import SatelliteSearch from "../components/SatelliteSearch";

const EARTH_RADIUS_KM = 6371;

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
  const [size, setSize] = useState({ w: window.innerWidth, h: window.innerHeight - 50 });
  const [group, setGroup] = useState("stations");
  const [selected, setSelected] = useState<SatelliteSummary | null>(null);
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
    };

    tick();
    const id = setInterval(tick, intervalMs);
    return () => clearInterval(id);
  }, [satrecs]);

  const selectedPoint = useMemo(
    () => points.find((p) => p.norad_id === selected?.norad_id),
    [points, selected]
  );

  return (
    <div ref={containerRef} style={{ height: "100%", overflow: "hidden" }}>
      <Globe
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
      />
      <div className="panel">
        <h3>Live catalog</h3>
        <select value={group} onChange={(e) => setGroup(e.target.value)}>
          <option value="stations">Stations (ISS, CSS…)</option>
          <option value="all">Full catalog</option>
        </select>
        <span className="muted" style={{ fontSize: "0.8rem" }}>
          {points.length.toLocaleString()} objects on globe
        </span>
        <h3 style={{ marginTop: "0.8rem" }}>Track a satellite</h3>
        <SatelliteSearch selected={selected} onSelect={setSelected} />
        {selected && (
          <div className="telemetry">
            <b>{selected.name}</b> #{selected.norad_id}
            {selectedPoint ? (
              <>
                <br />lat {selectedPoint.lat.toFixed(2)}° · lon {selectedPoint.lng.toFixed(2)}°
                <br />alt {selectedPoint.alt_km.toFixed(0)} km
              </>
            ) : (
              <>
                <br />
                <span className="muted">not in current globe set — switch to full catalog</span>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

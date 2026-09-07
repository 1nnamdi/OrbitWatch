import { useMemo, useState } from "react";
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer } from "react-leaflet";
import { useQuery } from "@tanstack/react-query";
import { api, type SatelliteSummary } from "../api";
import SatelliteSearch from "../components/SatelliteSearch";

const ISS: SatelliteSummary = { norad_id: 25544, name: "ISS (ZARYA)", group_name: "stations" };

function splitAtAntimeridian(points: { lat: number; lon: number }[]): [number, number][][] {
  const segments: [number, number][][] = [];
  let current: [number, number][] = [];
  let prevLon: number | null = null;
  for (const p of points) {
    if (prevLon !== null && Math.abs(p.lon - prevLon) > 180) {
      segments.push(current);
      current = [];
    }
    current.push([p.lat, p.lon]);
    prevLon = p.lon;
  }
  if (current.length) segments.push(current);
  return segments;
}

export default function MapPage() {
  const [sat, setSat] = useState<SatelliteSummary>(ISS);

  const { data: track } = useQuery({
    queryKey: ["groundtrack", sat.norad_id],
    queryFn: () => api.groundtrack(sat.norad_id),
    refetchInterval: 60_000,
  });

  const { data: pos } = useQuery({
    queryKey: ["position", sat.norad_id],
    queryFn: () => api.position(sat.norad_id),
    refetchInterval: 5_000,
  });

  const segments = useMemo(
    () => (track ? splitAtAntimeridian(track.points) : []),
    [track]
  );

  return (
    <div style={{ height: "100%" }}>
      <MapContainer center={[20, 0]} zoom={2} minZoom={1} worldCopyJump>
        <TileLayer
          attribution='Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ'
          url="/api/tiles/{z}/{x}/{y}.png?v=2"
          maxZoom={16}
        />
        {segments.map((seg, i) => (
          <Polyline key={i} positions={seg} pathOptions={{ color: "#4fc3f7", weight: 2 }} />
        ))}
        {pos && (
          <CircleMarker
            center={[pos.lat, pos.lon]}
            radius={8}
            pathOptions={{ color: "#ff5252", fillColor: "#ff5252", fillOpacity: 0.9 }}
          >
            <Popup>
              <b>{pos.name}</b>
              <br />
              lat {pos.lat.toFixed(2)}° · lon {pos.lon.toFixed(2)}°
              <br />
              alt {pos.alt_km.toFixed(0)} km
            </Popup>
          </CircleMarker>
        )}
      </MapContainer>
      <div className="panel">
        <h3>Ground track (±90 min)</h3>
        <SatelliteSearch selected={sat} onSelect={setSat} />
        <div className="telemetry">
          <b>{sat.name}</b> #{sat.norad_id}
          {pos && (
            <>
              <br />lat {pos.lat.toFixed(2)}° · lon {pos.lon.toFixed(2)}°
              <br />alt {pos.alt_km.toFixed(0)} km
            </>
          )}
        </div>
      </div>
    </div>
  );
}

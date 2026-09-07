import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type SatelliteSummary } from "../api";
import SatelliteSearch from "../components/SatelliteSearch";

const ISS: SatelliteSummary = { norad_id: 25544, name: "ISS (ZARYA)", group_name: "stations" };

function fmt(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function duration(rise: string, set: string) {
  const s = (new Date(set).getTime() - new Date(rise).getTime()) / 1000;
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
}

export default function PassesPage() {
  const [sat, setSat] = useState<SatelliteSummary>(ISS);
  const [lat, setLat] = useState("51.5");
  const [lon, setLon] = useState("-0.13");
  const [query, setQuery] = useState<{ lat: number; lon: number } | null>(null);

  const { data, isFetching, error } = useQuery({
    queryKey: ["passes", sat.norad_id, query],
    queryFn: () => api.passes(sat.norad_id, query!.lat, query!.lon),
    enabled: query !== null,
  });

  const useMyLocation = () => {
    navigator.geolocation?.getCurrentPosition((p) => {
      setLat(p.coords.latitude.toFixed(4));
      setLon(p.coords.longitude.toFixed(4));
    });
  };

  return (
    <div className="passes-layout">
      <div className="passes-side">
        <h3 style={{ marginBottom: "0.7rem" }}>Observer</h3>
        <label>Latitude</label>
        <input value={lat} onChange={(e) => setLat(e.target.value)} />
        <label>Longitude</label>
        <input value={lon} onChange={(e) => setLon(e.target.value)} />
        <button onClick={useMyLocation}>Use my location</button>
        <h3 style={{ margin: "0.7rem 0" }}>Satellite</h3>
        <SatelliteSearch selected={sat} onSelect={setSat} />
        <div className="telemetry" style={{ marginBottom: "0.7rem" }}>
          <b>{sat.name}</b> #{sat.norad_id}
        </div>
        <button onClick={() => setQuery({ lat: parseFloat(lat), lon: parseFloat(lon) })}>
          Predict passes (48 h)
        </button>
      </div>
      <div className="passes-main">
        <h2 style={{ marginBottom: "1rem" }}>
          Upcoming passes {data && `— ${data.name}`}
        </h2>
        {isFetching && <p className="muted">Computing…</p>}
        {error && <p style={{ color: "#ff5252" }}>{String(error)}</p>}
        {data && data.passes.length === 0 && (
          <p className="muted">No passes above 10° in the next 48 hours.</p>
        )}
        {data && data.passes.length > 0 && (
          <table className="passes">
            <thead>
              <tr>
                <th>Rise</th>
                <th>Culmination</th>
                <th>Set</th>
                <th>Duration</th>
                <th>Max altitude</th>
              </tr>
            </thead>
            <tbody>
              {data.passes.map((p, i) => (
                <tr key={i}>
                  <td>{fmt(p.rise)}</td>
                  <td>{fmt(p.culminate)}</td>
                  <td>{fmt(p.set)}</td>
                  <td>{duration(p.rise, p.set)}</td>
                  <td>{p.max_altitude_deg}°</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {!query && (
          <p className="muted">
            Set your observer location and hit “Predict passes” to see when {sat.name} flies
            overhead.
          </p>
        )}
      </div>
    </div>
  );
}

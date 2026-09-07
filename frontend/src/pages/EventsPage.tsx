import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type OrbitalEvent, type SatelliteDetail } from "../api";
import SatDetails from "../components/SatDetails";

function fmt(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function severity(score: number): { label: string; color: string } {
  if (score >= 10) return { label: "HIGH", color: "#ff5252" };
  if (score >= 3) return { label: "MED", color: "#ffb74d" };
  return { label: "LOW", color: "#4fc3f7" };
}

function signed(v: number, digits: number, unit: string) {
  return `${v > 0 ? "+" : ""}${v.toFixed(digits)}${unit}`;
}

export default function EventsPage() {
  const [minScore, setMinScore] = useState(0);
  const [selected, setSelected] = useState<SatelliteDetail | null>(null);

  const { data, isFetching, error } = useQuery({
    queryKey: ["events", minScore],
    queryFn: () => api.events(minScore > 0 ? minScore : undefined),
    refetchInterval: 60_000,
  });

  const openDetails = async (ev: OrbitalEvent) => {
    try {
      setSelected(await api.detail(ev.norad_id));
    } catch {
      setSelected(null);
    }
  };

  return (
    <div className="passes-layout">
      <div className="passes-main">
        <h2 style={{ marginBottom: "0.3rem" }}>Orbital events</h2>
        <p className="muted" style={{ marginBottom: "1rem" }}>
          Suspected maneuvers detected by diffing consecutive TLEs (ΔSMA &gt; 0.5 km, Δinc &gt;
          0.01°, Δecc &gt; 1e-4). SMA increases are weighted higher — drag only lowers orbits.
        </p>
        <label className="muted" style={{ fontSize: "0.85rem" }}>
          Min severity score:{" "}
          <select
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            style={{ marginBottom: "1rem" }}
          >
            <option value={0}>All</option>
            <option value={3}>≥ 3 (medium)</option>
            <option value={10}>≥ 10 (high)</option>
          </select>
        </label>
        {isFetching && !data && <p className="muted">Loading…</p>}
        {error && <p style={{ color: "#ff5252" }}>{String(error)}</p>}
        {data && data.length === 0 && (
          <p className="muted">
            No events detected yet. Analysis runs after each ingest cycle — maneuvers will show
            up as TLE history accumulates.
          </p>
        )}
        {data && data.length > 0 && (
          <table className="passes">
            <thead>
              <tr>
                <th>Epoch</th>
                <th>Satellite</th>
                <th>ΔSMA</th>
                <th>ΔInclination</th>
                <th>ΔEccentricity</th>
                <th>Gap</th>
                <th>Severity</th>
              </tr>
            </thead>
            <tbody>
              {data.map((ev) => {
                const sev = severity(ev.score);
                return (
                  <tr key={ev.id} onClick={() => openDetails(ev)} style={{ cursor: "pointer" }}>
                    <td>{fmt(ev.epoch_after)}</td>
                    <td>
                      <b style={{ color: "var(--accent)" }}>{ev.name}</b>{" "}
                      <span className="muted">#{ev.norad_id}</span>
                    </td>
                    <td>{signed(ev.delta_sma_km, 3, " km")}</td>
                    <td>{signed(ev.delta_inclination_deg, 4, "°")}</td>
                    <td>{signed(ev.delta_eccentricity, 6, "")}</td>
                    <td>{ev.gap_hours.toFixed(1)} h</td>
                    <td>
                      <span style={{ color: sev.color, fontWeight: 600 }}>
                        {sev.label} ({ev.score})
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
      {selected && selected.line1 && selected.line2 && (
        <div className="panel" style={{ left: "auto", right: 12 }}>
          <SatDetails
            norad_id={selected.norad_id}
            name={selected.name}
            group_name={selected.group_name}
            line1={selected.line1}
            line2={selected.line2}
            onClose={() => setSelected(null)}
          />
        </div>
      )}
    </div>
  );
}

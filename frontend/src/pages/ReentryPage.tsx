import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, type DecayTrend, type SatelliteDetail } from "../api";
import SatDetails from "../components/SatDetails";

function fmt(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function timeUntil(iso: string): { label: string; color: string } {
  const ms = new Date(iso).getTime() - Date.now();
  const abs = Math.abs(ms);
  const days = Math.floor(abs / 86_400_000);
  const hours = Math.floor((abs % 86_400_000) / 3_600_000);
  const label = days > 0 ? `${days}d ${hours}h` : `${hours}h ${Math.floor((abs % 3_600_000) / 60_000)}m`;
  if (ms < 0) return { label: `${label} ago`, color: "#9e9e9e" };
  if (ms < 86_400_000) return { label: `in ${label}`, color: "#ff5252" };
  if (ms < 3 * 86_400_000) return { label: `in ${label}`, color: "#ffb74d" };
  return { label: `in ${label}`, color: "#4fc3f7" };
}

export default function ReentryPage() {
  const [selected, setSelected] = useState<SatelliteDetail | null>(null);

  const { data: predictions, error: predError } = useQuery({
    queryKey: ["reentries"],
    queryFn: api.reentries,
    refetchInterval: 300_000,
  });
  const { data: trends, isFetching: trendsLoading } = useQuery({
    queryKey: ["reentry-trends"],
    queryFn: () => api.reentryTrends(),
    refetchInterval: 600_000,
  });

  const openDetails = async (t: DecayTrend) => {
    try {
      setSelected(await api.detail(t.norad_id));
    } catch {
      setSelected(null);
    }
  };

  return (
    <div className="passes-layout">
      <div className="passes-main">
        <h2 style={{ marginBottom: "0.3rem" }}>Re-entry watch</h2>
        <p className="muted" style={{ marginBottom: "1.2rem" }}>
          Official TIP decay predictions from Space-Track, plus low-perigee satellites ranked by
          the orbital decay rate fitted from our own TLE history.
        </p>

        <h3 style={{ marginBottom: "0.4rem" }}>Space-Track TIP predictions</h3>
        {predError && <p style={{ color: "#ff5252" }}>{String(predError)}</p>}
        {predictions && predictions.length === 0 && (
          <p className="muted" style={{ marginBottom: "1rem" }}>
            No decay messages yet. Set SPACETRACK_USER / SPACETRACK_PASSWORD in .env and run{" "}
            <code>POST /api/ingest/spacetrack</code> (also runs automatically every 12 h).
          </p>
        )}
        {predictions && predictions.length > 0 && (
          <table className="passes" style={{ marginBottom: "1.5rem" }}>
            <thead>
              <tr>
                <th>Decay epoch</th>
                <th>Countdown</th>
                <th>Object</th>
                <th>Intl des</th>
                <th>RCS</th>
                <th>Country</th>
                <th>Type</th>
                <th>Msg age</th>
              </tr>
            </thead>
            <tbody>
              {predictions.map((p) => {
                const t = timeUntil(p.decay_epoch);
                return (
                  <tr key={`${p.norad_id}-${p.msg_epoch}`}>
                    <td>{fmt(p.decay_epoch)}</td>
                    <td style={{ color: t.color, fontWeight: 600 }}>{t.label}</td>
                    <td>
                      <b style={{ color: "var(--accent)" }}>{p.object_name}</b>{" "}
                      <span className="muted">#{p.norad_id}</span>
                    </td>
                    <td>{p.intl_des ?? "—"}</td>
                    <td>{p.rcs_size ?? "—"}</td>
                    <td>{p.country ?? "—"}</td>
                    <td>{p.msg_type}</td>
                    <td className="muted">{fmt(p.msg_epoch)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}

        <h3 style={{ marginBottom: "0.4rem" }}>Decay watch (computed from TLE history)</h3>
        <p className="muted" style={{ marginBottom: "0.6rem", fontSize: "0.85rem" }}>
          Perigee &lt; 300 km; SMA decay rate is a least-squares fit over the last 14 days. ETA is
          a naive extrapolation to 120 km — real re-entry is highly variable. Click a row for
          details.
        </p>
        {trendsLoading && !trends && <p className="muted">Computing…</p>}
        {trends && trends.length === 0 && (
          <p className="muted">
            No candidates with enough TLE history yet — accumulates with ingest cycles, or backfill
            via <code>POST /api/ingest/spacetrack/backfill</code>.
          </p>
        )}
        {trends && trends.length > 0 && (
          <table className="passes">
            <thead>
              <tr>
                <th>Satellite</th>
                <th>Perigee</th>
                <th>Apogee</th>
                <th>Decay rate</th>
                <th>B*</th>
                <th>TLEs</th>
                <th>Est. re-entry</th>
              </tr>
            </thead>
            <tbody>
              {trends.map((t) => (
                <tr key={t.norad_id} onClick={() => openDetails(t)} style={{ cursor: "pointer" }}>
                  <td>
                    <b style={{ color: "var(--accent)" }}>{t.name}</b>{" "}
                    <span className="muted">#{t.norad_id}</span>
                  </td>
                  <td>{t.perigee_km.toFixed(0)} km</td>
                  <td>{t.apogee_km.toFixed(0)} km</td>
                  <td style={{ color: t.decay_rate_km_day > 1 ? "#ff5252" : undefined }}>
                    {t.decay_rate_km_day.toFixed(3)} km/d
                  </td>
                  <td>{t.bstar.toExponential(2)}</td>
                  <td className="muted">{t.points}</td>
                  <td>
                    {t.est_reentry ? (
                      <span style={{ color: timeUntil(t.est_reentry).color, fontWeight: 600 }}>
                        {fmt(t.est_reentry)} ({t.est_days_left?.toFixed(0)}d)
                      </span>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                </tr>
              ))}
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

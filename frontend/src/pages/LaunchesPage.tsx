import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type Launch } from "../api";

const STATUS_COLORS: Record<string, string> = {
  Go: "#66bb6a",
  Success: "#4fc3f7",
  Failure: "#ff5252",
  "Partial Failure": "#ff8a65",
  TBC: "#ffb74d",
  TBD: "#9e9e9e",
  "In Flight": "#ba68c8",
  Hold: "#ffb74d",
};

function fmt(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function countdown(net: string, now: number) {
  const diff = new Date(net).getTime() - now;
  if (diff <= 0) return "launched";
  const d = Math.floor(diff / 86_400_000);
  const h = Math.floor((diff % 86_400_000) / 3_600_000);
  const m = Math.floor((diff % 3_600_000) / 60_000);
  const s = Math.floor((diff % 60_000) / 1000);
  if (d > 0) return `T−${d}d ${h}h ${m}m`;
  if (h > 0) return `T−${h}h ${m}m ${s}s`;
  return `T−${m}m ${s}s`;
}

function StatusBadge({ launch }: { launch: Launch }) {
  const color = STATUS_COLORS[launch.status] ?? "#9e9e9e";
  return (
    <span style={{ color, fontWeight: 600 }} title={launch.status_name}>
      {launch.status}
    </span>
  );
}

export default function LaunchesPage() {
  const [now, setNow] = useState(Date.now());
  const { data, isFetching, error } = useQuery({
    queryKey: ["launches"],
    queryFn: api.launches,
    refetchInterval: 5 * 60_000,
  });

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="passes-layout">
      <div className="passes-main">
        <h2 style={{ marginBottom: "0.3rem" }}>Launches</h2>
        <p className="muted" style={{ marginBottom: "1rem" }}>
          Upcoming and recent launches from Launch Library 2 — refreshed hourly.
        </p>
        {isFetching && !data && <p className="muted">Loading…</p>}
        {error && <p style={{ color: "#ff5252" }}>{String(error)}</p>}
        {data && data.length === 0 && (
          <p className="muted">No launches stored yet — ingest runs hourly.</p>
        )}
        {data && data.length > 0 && (
          <table className="passes">
            <thead>
              <tr>
                <th>Countdown</th>
                <th>NET</th>
                <th>Launch</th>
                <th>Provider</th>
                <th>Mission</th>
                <th>Site</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.map((l) => (
                <tr key={l.id}>
                  <td style={{ fontVariantNumeric: "tabular-nums", color: "var(--accent)" }}>
                    {countdown(l.net, now)}
                  </td>
                  <td>{fmt(l.net)}</td>
                  <td>
                    <b>{l.name}</b>
                  </td>
                  <td>{l.provider}</td>
                  <td>
                    {l.mission ?? "—"}
                    {l.mission_type && <span className="muted"> · {l.mission_type}</span>}
                  </td>
                  <td>
                    {l.pad ?? "—"}
                    {l.location && <div className="muted">{l.location}</div>}
                  </td>
                  <td>
                    <StatusBadge launch={l} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";

export default function ConstellationsPage() {
  const [prefix, setPrefix] = useState<string | null>(null);

  const { data: list, error } = useQuery({
    queryKey: ["constellations"],
    queryFn: api.constellations,
  });
  const active = prefix ?? list?.[0]?.prefix ?? null;
  const { data: growth, isFetching } = useQuery({
    queryKey: ["constellation-growth", active],
    queryFn: () => api.constellationGrowth(active!),
    enabled: !!active,
  });

  return (
    <div className="passes-layout">
      <div className="passes-main">
        <h2 style={{ marginBottom: "0.3rem" }}>Constellation growth</h2>
        <p className="muted" style={{ marginBottom: "1rem" }}>
          On-orbit payload counts over time, reconstructed from Space-Track catalog launch and
          decay dates.
        </p>
        {error && <p style={{ color: "#ff5252" }}>{String(error)}</p>}
        {list && list.length === 0 && (
          <p className="muted">
            No catalog data yet. Set SPACETRACK_USER / SPACETRACK_PASSWORD in .env and run{" "}
            <code>POST /api/ingest/spacetrack</code> (also runs automatically every 12 h).
          </p>
        )}
        {list && list.length > 0 && (
          <>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "1rem" }}>
              {list.map((c) => (
                <button
                  key={c.prefix}
                  onClick={() => setPrefix(c.prefix)}
                  style={{
                    padding: "0.4rem 0.8rem",
                    borderRadius: 6,
                    border: `1px solid ${c.prefix === active ? "var(--accent)" : "#444"}`,
                    background: c.prefix === active ? "rgba(79,195,247,0.15)" : "transparent",
                    color: c.prefix === active ? "var(--accent)" : "inherit",
                    cursor: "pointer",
                  }}
                >
                  <b>{c.label}</b>{" "}
                  <span className="muted">
                    {c.on_orbit.toLocaleString()} on orbit · {c.decayed.toLocaleString()} decayed
                  </span>
                </button>
              ))}
            </div>
            {isFetching && !growth && <p className="muted">Loading…</p>}
            {growth && growth.points.length > 0 && (
              <div style={{ height: 420, marginTop: "0.5rem" }}>
                <ResponsiveContainer>
                  <ComposedChart data={growth.points} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
                    <CartesianGrid stroke="#333" strokeDasharray="3 3" />
                    <XAxis dataKey="month" stroke="#888" tick={{ fontSize: 11 }} minTickGap={40} />
                    <YAxis stroke="#888" tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{ background: "#111825", border: "1px solid #333" }}
                      labelStyle={{ color: "#aaa" }}
                    />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="on_orbit"
                      name="On orbit"
                      stroke="#4fc3f7"
                      fill="rgba(79,195,247,0.25)"
                      strokeWidth={2}
                    />
                    <Line
                      type="monotone"
                      dataKey="launched"
                      name="Launched (cum.)"
                      stroke="#81c784"
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="decayed"
                      name="Decayed (cum.)"
                      stroke="#ff8a65"
                      dot={false}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type SatelliteSummary } from "../api";

interface Props {
  selected: SatelliteSummary | null;
  onSelect: (sat: SatelliteSummary) => void;
}

export default function SatelliteSearch({ selected, onSelect }: Props) {
  const [search, setSearch] = useState("");
  const { data: results } = useQuery({
    queryKey: ["search", search],
    queryFn: () => api.satellites(search),
    enabled: search.length >= 2,
  });

  return (
    <>
      <input
        placeholder="Search satellites (e.g. ISS, STARLINK)…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      {results && (
        <ul className="results">
          {results.map((s) => (
            <li
              key={s.norad_id}
              className={selected?.norad_id === s.norad_id ? "selected" : ""}
              onClick={() => {
                onSelect(s);
                setSearch("");
              }}
            >
              {s.name} <span className="muted">#{s.norad_id}</span>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

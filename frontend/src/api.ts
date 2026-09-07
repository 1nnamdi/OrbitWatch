export interface SatelliteSummary {
  norad_id: number;
  name: string;
  group_name: string;
}

export interface TleRecord extends SatelliteSummary {
  line1: string;
  line2: string;
  epoch: string;
}

export interface TrackPoint {
  time: string;
  lat: number;
  lon: number;
  alt_km: number;
}

export interface GroundTrack {
  norad_id: number;
  name: string;
  points: TrackPoint[];
}

export interface Position {
  norad_id: number;
  name: string;
  time: string;
  lat: number;
  lon: number;
  alt_km: number;
}

export interface PassEvent {
  rise: string;
  culminate: string;
  set: string;
  max_altitude_deg: number;
}

export interface Passes {
  norad_id: number;
  name: string;
  observer_lat: number;
  observer_lon: number;
  passes: PassEvent[];
}

export interface Stats {
  satellites: number;
  tles: number;
  groups: string[];
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  satellites: (search: string, limit = 20) =>
    get<SatelliteSummary[]>(`/satellites?search=${encodeURIComponent(search)}&limit=${limit}`),
  tles: (group?: string) => get<TleRecord[]>(`/tles${group ? `?group=${group}` : ""}`),
  position: (noradId: number) => get<Position>(`/satellites/${noradId}/position`),
  groundtrack: (noradId: number, minutes = 180) =>
    get<GroundTrack>(`/satellites/${noradId}/groundtrack?minutes=${minutes}`),
  passes: (noradId: number, lat: number, lon: number, hours = 48) =>
    get<Passes>(`/satellites/${noradId}/passes?lat=${lat}&lon=${lon}&hours=${hours}`),
  stats: () => get<Stats>("/stats"),
};

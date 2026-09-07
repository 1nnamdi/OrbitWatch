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

export type SatelliteDetail = TleRecord;

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

export interface OrbitalEvent {
  id: number;
  norad_id: number;
  name: string;
  group_name: string;
  epoch_before: string;
  epoch_after: string;
  gap_hours: number;
  delta_sma_km: number;
  delta_inclination_deg: number;
  delta_eccentricity: number;
  score: number;
  detected_at: string;
}

export interface Launch {
  id: string;
  name: string;
  provider: string;
  mission: string | null;
  mission_type: string | null;
  status: string;
  status_name: string;
  net: string;
  window_start: string | null;
  window_end: string | null;
  pad: string | null;
  location: string | null;
  pad_lat: number | null;
  pad_lon: number | null;
}

export interface ReentryPrediction {
  norad_id: number;
  object_name: string;
  intl_des: string | null;
  rcs_size: string | null;
  country: string | null;
  msg_epoch: string;
  decay_epoch: string;
  source: string | null;
  msg_type: string;
}

export interface DecayTrend {
  norad_id: number;
  name: string;
  group_name: string;
  epoch: string;
  sma_km: number;
  perigee_km: number;
  apogee_km: number;
  bstar: number;
  points: number;
  decay_rate_km_day: number;
  est_days_left: number | null;
  est_reentry: string | null;
}

export interface ConstellationSummary {
  prefix: string;
  label: string;
  total: number;
  on_orbit: number;
  decayed: number;
}

export interface GrowthPoint {
  month: string;
  launched: number;
  decayed: number;
  on_orbit: number;
}

export interface ConstellationGrowth {
  prefix: string;
  label: string;
  points: GrowthPoint[];
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  satellites: (search: string, limit = 20) =>
    get<SatelliteSummary[]>(`/satellites?search=${encodeURIComponent(search)}&limit=${limit}`),
  detail: (noradId: number) => get<SatelliteDetail>(`/satellites/${noradId}`),
  tles: (group?: string) => get<TleRecord[]>(`/tles${group ? `?group=${group}` : ""}`),
  position: (noradId: number) => get<Position>(`/satellites/${noradId}/position`),
  groundtrack: (noradId: number, minutes = 180) =>
    get<GroundTrack>(`/satellites/${noradId}/groundtrack?minutes=${minutes}`),
  passes: (noradId: number, lat: number, lon: number, hours = 48) =>
    get<Passes>(`/satellites/${noradId}/passes?lat=${lat}&lon=${lon}&hours=${hours}`),
  events: (minScore?: number, limit = 200) =>
    get<OrbitalEvent[]>(`/events?limit=${limit}${minScore ? `&min_score=${minScore}` : ""}`),
  launches: () => get<Launch[]>("/launches"),
  reentries: () => get<ReentryPrediction[]>("/reentries"),
  reentryTrends: (maxPerigeeKm = 300) =>
    get<DecayTrend[]>(`/reentries/trends?max_perigee_km=${maxPerigeeKm}`),
  constellations: () => get<ConstellationSummary[]>("/constellations"),
  constellationGrowth: (prefix: string) =>
    get<ConstellationGrowth>(`/constellations/${prefix}/growth`),
  stats: () => get<Stats>("/stats"),
};

import { useEffect, useMemo, useState } from "react";
import {
  degreesLat,
  degreesLong,
  eciToGeodetic,
  gstime,
  propagate,
  twoline2satrec,
} from "satellite.js";

const MU = 398600.4418; // km^3/s^2
const R_EARTH = 6378.137; // equatorial radius km
const RAD = 180 / Math.PI;

export interface OrbitInfo {
  intlDesignator: string;
  launchYear: number | null;
  launchNumber: number | null;
  classification: string;
  epoch: Date;
  epochAgeDays: number;
  inclinationDeg: number;
  raanDeg: number;
  eccentricity: number;
  argPerigeeDeg: number;
  meanAnomalyDeg: number;
  meanMotionRevDay: number;
  periodMin: number;
  semiMajorAxisKm: number;
  apogeeKm: number;
  perigeeKm: number;
  bstar: number;
  revAtEpoch: number | null;
  orbitClass: string;
}

function classifyOrbit(periodMin: number, ecc: number, apogeeKm: number): string {
  if (ecc > 0.25) return "HEO — highly elliptical";
  if (Math.abs(periodMin - 1436.1) < 60 && ecc < 0.05) return "GEO — geosynchronous";
  if (apogeeKm < 2000) return "LEO — low Earth orbit";
  if (apogeeKm < 35_000) return "MEO — medium Earth orbit";
  return "High orbit";
}

export function deriveOrbit(line1: string, line2: string): OrbitInfo {
  const rec = twoline2satrec(line1, line2);
  const periodMin = (2 * Math.PI) / rec.no;
  const a = Math.cbrt(MU * ((periodMin * 60) / (2 * Math.PI)) ** 2);
  const epoch = new Date((rec.jdsatepoch - 2440587.5) * 86_400_000);

  const desg = line1.slice(9, 17).trim();
  const yy = parseInt(desg.slice(0, 2), 10);
  const launchYear = Number.isNaN(yy) ? null : yy + (yy < 57 ? 2000 : 1900);
  const launchNumber = parseInt(desg.slice(2, 5), 10);
  const rev = parseInt(line2.slice(63, 68), 10);
  const apogeeKm = a * (1 + rec.ecco) - R_EARTH;
  const perigeeKm = a * (1 - rec.ecco) - R_EARTH;

  return {
    intlDesignator: desg || "—",
    launchYear,
    launchNumber: Number.isNaN(launchNumber) ? null : launchNumber,
    classification: line1[7] === "C" ? "Classified" : line1[7] === "S" ? "Secret" : "Unclassified",
    epoch,
    epochAgeDays: (Date.now() - epoch.getTime()) / 86_400_000,
    inclinationDeg: rec.inclo * RAD,
    raanDeg: rec.nodeo * RAD,
    eccentricity: rec.ecco,
    argPerigeeDeg: rec.argpo * RAD,
    meanAnomalyDeg: rec.mo * RAD,
    meanMotionRevDay: 1440 / periodMin,
    periodMin,
    semiMajorAxisKm: a,
    apogeeKm,
    perigeeKm,
    bstar: rec.bstar,
    revAtEpoch: Number.isNaN(rev) ? null : rev,
    orbitClass: classifyOrbit(periodMin, rec.ecco, apogeeKm),
  };
}

interface Live {
  lat: number;
  lon: number;
  altKm: number;
  speedKms: number;
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="drow">
      <span>{k}</span>
      <span>{v}</span>
    </div>
  );
}

interface Props {
  norad_id: number;
  name: string;
  group_name?: string;
  line1: string;
  line2: string;
  onClose?: () => void;
}

export default function SatDetails({ norad_id, name, group_name, line1, line2, onClose }: Props) {
  const rec = useMemo(() => twoline2satrec(line1, line2), [line1, line2]);
  const orbit = useMemo(() => deriveOrbit(line1, line2), [line1, line2]);
  const [live, setLive] = useState<Live | null>(null);

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      const pv = propagate(rec, now);
      if (!pv || typeof pv.position !== "object" || typeof pv.velocity !== "object") {
        setLive(null);
        return;
      }
      const geo = eciToGeodetic(pv.position, gstime(now));
      const v = pv.velocity;
      setLive({
        lat: degreesLat(geo.latitude),
        lon: degreesLong(geo.longitude),
        altKm: geo.height,
        speedKms: Math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z),
      });
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [rec]);

  return (
    <div className="details">
      <div className="dhead">
        <b>{name}</b>
        {onClose && (
          <button className="dclose" onClick={onClose} title="Close">
            ×
          </button>
        )}
      </div>

      <h4>Live telemetry</h4>
      {live ? (
        <>
          <Row k="Latitude" v={`${live.lat.toFixed(4)}°`} />
          <Row k="Longitude" v={`${live.lon.toFixed(4)}°`} />
          <Row k="Altitude" v={`${live.altKm.toFixed(1)} km`} />
          <Row k="Speed" v={`${live.speedKms.toFixed(2)} km/s (${(live.speedKms * 3600).toFixed(0)} km/h)`} />
        </>
      ) : (
        <div className="muted">propagation unavailable for this TLE</div>
      )}

      <h4>Identity</h4>
      <Row k="NORAD ID" v={norad_id} />
      <Row k="Int'l designator" v={orbit.intlDesignator} />
      {orbit.launchYear && (
        <Row
          k="Launch"
          v={`${orbit.launchYear}${orbit.launchNumber ? `, launch #${orbit.launchNumber}` : ""}`}
        />
      )}
      <Row k="Classification" v={orbit.classification} />
      {group_name && <Row k="Catalog group" v={group_name} />}

      <h4>Orbit</h4>
      <Row k="Type" v={orbit.orbitClass} />
      <Row k="Period" v={`${orbit.periodMin.toFixed(1)} min (${orbit.meanMotionRevDay.toFixed(2)} rev/day)`} />
      <Row k="Inclination" v={`${orbit.inclinationDeg.toFixed(2)}°`} />
      <Row k="Apogee" v={`${orbit.apogeeKm.toFixed(0)} km`} />
      <Row k="Perigee" v={`${orbit.perigeeKm.toFixed(0)} km`} />
      <Row k="Semi-major axis" v={`${orbit.semiMajorAxisKm.toFixed(0)} km`} />
      <Row k="Eccentricity" v={orbit.eccentricity.toFixed(6)} />
      <Row k="RAAN" v={`${orbit.raanDeg.toFixed(2)}°`} />
      <Row k="Arg. of perigee" v={`${orbit.argPerigeeDeg.toFixed(2)}°`} />
      <Row k="Mean anomaly" v={`${orbit.meanAnomalyDeg.toFixed(2)}°`} />
      <Row k="B* drag term" v={orbit.bstar.toExponential(3)} />
      {orbit.revAtEpoch !== null && <Row k="Rev # at epoch" v={orbit.revAtEpoch.toLocaleString()} />}

      <h4>TLE epoch</h4>
      <Row k="Epoch" v={orbit.epoch.toISOString().replace("T", " ").slice(0, 19) + " UTC"} />
      <Row k="Age" v={`${orbit.epochAgeDays.toFixed(1)} days`} />
    </div>
  );
}

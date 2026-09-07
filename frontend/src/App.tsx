import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import GlobePage from "./pages/GlobePage";
import MapPage from "./pages/MapPage";
import PassesPage from "./pages/PassesPage";
import EventsPage from "./pages/EventsPage";
import LaunchesPage from "./pages/LaunchesPage";

export default function App() {
  const { data: stats } = useQuery({ queryKey: ["stats"], queryFn: api.stats });

  return (
    <>
      <nav className="topbar">
        <span className="brand">🛰 ORBITWATCH</span>
        <NavLink to="/globe">Globe</NavLink>
        <NavLink to="/map">Ground Track</NavLink>
        <NavLink to="/passes">Passes</NavLink>
        <NavLink to="/events">Events</NavLink>
        <NavLink to="/launches">Launches</NavLink>
        {stats && (
          <span className="stats">
            {stats.satellites.toLocaleString()} satellites · {stats.tles.toLocaleString()} TLEs
          </span>
        )}
      </nav>
      <div className="page">
        <Routes>
          <Route path="/" element={<Navigate to="/globe" replace />} />
          <Route path="/globe" element={<GlobePage />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/passes" element={<PassesPage />} />
          <Route path="/events" element={<EventsPage />} />
          <Route path="/launches" element={<LaunchesPage />} />
        </Routes>
      </div>
    </>
  );
}

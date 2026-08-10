import { useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { loadPayload } from "./data";
import type { Payload } from "./types";
import { Nav } from "./components/Nav";
import { Freshness } from "./components/Freshness";
import { NowView } from "./views/NowView";
import { WeekView } from "./views/WeekView";
import { CinemasView } from "./views/CinemasView";
import { CinemaDetail } from "./views/CinemaDetail";
import { ChainsView } from "./views/ChainsView";
import { FilmDetail } from "./views/FilmDetail";

export default function App() {
  const [payload, setPayload] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    loadPayload().then(setPayload).catch((e) => setError(String(e)));
  }, []);

  // Countdowns must stay honest without re-rendering constantly.
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(id);
  }, []);

  if (error) return <div className="wrap"><p className="empty">{error}</p></div>;
  if (!payload) return <div className="wrap"><p className="empty">Loading…</p></div>;

  return (
    <div className="wrap">
      <header className="head">
        <h1 className="head-title">Paris Cinema</h1>
        <Freshness generatedAt={payload.generated_at} now={now} />
      </header>
      <Nav />
      <main>
        <Routes>
          <Route path="/" element={<NowView payload={payload} now={now} />} />
          <Route path="/week" element={<WeekView payload={payload} now={now} />} />
          <Route path="/cinemas" element={<CinemasView payload={payload} now={now} />} />
          <Route path="/cinema/:id" element={<CinemaDetail payload={payload} now={now} />} />
          <Route path="/chains" element={<ChainsView payload={payload} now={now} />} />
          <Route path="/film/:key" element={<FilmDetail payload={payload} now={now} />} />
        </Routes>
      </main>
    </div>
  );
}

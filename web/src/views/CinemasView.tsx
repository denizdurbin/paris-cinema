import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { Payload } from "../types";
import { formatParisTime, parisDayKey } from "../time";

export function CinemasView({ payload, now }: { payload: Payload; now: Date }) {
  const [query, setQuery] = useState("");

  const stats = useMemo(() => {
    const today = parisDayKey(now);
    const map = new Map<string, { today: number; next: string | null }>();
    for (const v of payload.venues) map.set(v.id, { today: 0, next: null });
    for (const s of [...payload.screenings].sort((a, b) =>
      a.start_utc.localeCompare(b.start_utc)
    )) {
      const e = map.get(s.venue_id);
      if (!e) continue;
      if (parisDayKey(s.start_utc) === today) e.today += 1;
      if (!e.next && new Date(s.start_utc) > now) e.next = s.start_utc;
    }
    return map;
  }, [payload, now]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const independents = payload.venues.filter((v) => v.kind === "independent");
    const matched = q
      ? independents.filter((v) => v.name.toLowerCase().includes(q))
      : independents;
    return matched.sort(
      (a, b) => a.arrondissement - b.arrondissement || a.name.localeCompare(b.name)
    );
  }, [payload, query]);

  const groups = useMemo(() => {
    const m = new Map<number, typeof filtered>();
    for (const v of filtered) {
      const list = m.get(v.arrondissement);
      if (list) list.push(v);
      else m.set(v.arrondissement, [v]);
    }
    return [...m.entries()].sort(([a], [b]) => a - b);
  }, [filtered]);

  return (
    <>
      <input
        className="search"
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search cinemas"
        aria-label="Search cinemas"
      />

      {filtered.length === 0 && <p className="empty">No cinema matches “{query}”.</p>}

      {groups.map(([arr, venues]) => (
        <section className="section" key={arr}>
          <h2 className="section-title">{arr}<sup>e</sup></h2>
          {venues.map((v) => {
            const st = stats.get(v.id)!;
            return (
              <Link className="venue" to={`/cinema/${v.id}`} key={v.id}>
                <span className="venue-name">{v.name}</span>
                <span className="venue-meta faint tnum">
                  {v.coverage === "none"
                    ? "no data source"
                    : st.next
                      ? `next ${formatParisTime(st.next)}`
                      : "nothing scheduled"}
                </span>
              </Link>
            );
          })}
        </section>
      ))}
    </>
  );
}

import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { Payload } from "../types";
import { displayTitle } from "../data";
import { formatParisTime, parisDayKey } from "../time";

/** Lowercase, fold ligatures and strip diacritics: "ete" matches "Été", "oeil" matches "Œil". */
function fold(s: string): string {
  return s
    .replace(/œ/gi, "oe")
    .replace(/æ/gi, "ae")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

export function CinemasView({ payload, now }: { payload: Payload; now: Date }) {
  const [query, setQuery] = useState("");
  const q = fold(query.trim());

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
    const independents = payload.venues.filter((v) => v.kind === "independent");
    const matched = q
      ? independents.filter((v) => fold(v.name).includes(q))
      : independents;
    return matched.sort(
      (a, b) => a.arrondissement - b.arrondissement || a.name.localeCompare(b.name)
    );
  }, [payload, q]);

  const groups = useMemo(() => {
    const m = new Map<number, typeof filtered>();
    for (const v of filtered) {
      const list = m.get(v.arrondissement);
      if (list) list.push(v);
      else m.set(v.arrondissement, [v]);
    }
    return [...m.entries()].sort(([a], [b]) => a - b);
  }, [filtered]);

  const films = useMemo(() => {
    if (!q) return [];
    const today = parisDayKey(now);
    const byKey = new Map<string, { title: string; marquee: string; count: number }>();
    for (const s of payload.screenings) {
      if (!s.film_key) continue;
      if (parisDayKey(s.start_utc) < today) continue;
      const existing = byKey.get(s.film_key);
      if (existing) {
        existing.count += 1;
      } else {
        byKey.set(s.film_key, {
          title: displayTitle(payload, s),
          marquee: s.title_marquee,
          count: 1,
        });
      }
    }
    return [...byKey.entries()]
      .filter(([, f]) =>
        fold(f.title).includes(q) || fold(f.marquee).includes(q)
      )
      .sort((a, b) => a[1].title.localeCompare(b[1].title));
  }, [payload, q, now]);

  return (
    <>
      <input
        className="search"
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search cinemas or films"
        aria-label="Search cinemas or films"
      />

      {q && films.length === 0 && filtered.length === 0 && (
        <p className="empty">No cinema or film matches “{query}”.</p>
      )}

      {films.length > 0 && (
        <section className="section">
          <h2 className="section-title">Films</h2>
          {films.map(([key, f]) => (
            <Link
              className="venue"
              to={`/film/${encodeURIComponent(key)}`}
              key={key}
            >
              <span className="venue-name">{f.title}</span>
              <span className="venue-meta faint tnum">
                {f.count} screening{f.count !== 1 ? "s" : ""}
              </span>
            </Link>
          ))}
        </section>
      )}

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

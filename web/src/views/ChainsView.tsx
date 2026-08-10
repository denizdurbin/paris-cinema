import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { Payload, Screening, Venue } from "../types";
import { displayTitle } from "../data";
import { formatParisTime, parisDayKey } from "../time";

export function ChainsView({ payload, now }: { payload: Payload; now: Date }) {
  const chains = useMemo(() => {
    const names = new Set(
      payload.venues.filter((v) => v.kind === "chain" && v.chain).map((v) => v.chain!)
    );
    return [...names].sort();
  }, [payload]);

  const [active, setActive] = useState<string | null>(null);
  const chain = active ?? chains[0] ?? null;

  // One group per venue of the active chain, ordered by arrondissement.
  // Venues with nothing left today are dropped rather than shown empty.
  const groups = useMemo(() => {
    if (!chain) return [] as { venue: Venue; screenings: Screening[] }[];
    const today = parisDayKey(now);
    const venues = payload.venues
      .filter((v) => v.chain === chain)
      .sort((a, b) => a.arrondissement - b.arrondissement || a.name.localeCompare(b.name));

    const byVenue = new Map<string, Screening[]>();
    for (const s of payload.screenings) {
      if (parisDayKey(s.start_utc) !== today) continue;
      if (new Date(s.start_utc) <= now) continue;
      const list = byVenue.get(s.venue_id);
      if (list) list.push(s);
      else byVenue.set(s.venue_id, [s]);
    }

    return venues
      .map((venue) => ({
        venue,
        screenings: (byVenue.get(venue.id) ?? []).sort((a, b) =>
          a.start_utc.localeCompare(b.start_utc)
        ),
      }))
      .filter((g) => g.screenings.length > 0);
  }, [payload, chain, now]);

  if (chains.length === 0) return <p className="empty">No chain venues in the data.</p>;

  const total = groups.reduce((n, g) => n + g.screenings.length, 0);

  return (
    <>
      <div className="daybar">
        {chains.map((c) => (
          <button
            key={c}
            onClick={() => setActive(c)}
            className={c === chain ? "day day-on" : "day"}
          >
            <span className="day-label">{c}</span>
          </button>
        ))}
      </div>

      {groups.length === 0 ? (
        <p className="empty">Nothing left today at {chain}.</p>
      ) : (
        <>
          <p className="chain-total faint tnum">
            {total} screenings left today across {groups.length} locations
          </p>
          {groups.map(({ venue, screenings }) => (
            <section className="chain-section" key={venue.id}>
              <h2 className="section-title">
                {venue.name}
                <span className="section-count faint">
                  {venue.arrondissement}
                  <sup>e</sup> · {screenings.length}
                </span>
              </h2>
              <div className="chain-strip">
                {screenings.map((s) => {
                  const body = (
                    <>
                      <span className="chain-card-time tnum">
                        {formatParisTime(s.start_utc)}
                      </span>
                      <span className="chain-card-title">
                        {displayTitle(payload, s)}
                      </span>
                      {s.version !== "UNKNOWN" && (
                        <span className="tag">{s.version}</span>
                      )}
                    </>
                  );
                  const key = `${s.start_utc}-${s.title_marquee}`;
                  return s.film_key ? (
                    <Link
                      key={key}
                      className="chain-card"
                      to={`/film/${encodeURIComponent(s.film_key)}`}
                    >
                      {body}
                    </Link>
                  ) : (
                    <div key={key} className="chain-card">{body}</div>
                  );
                })}
              </div>
            </section>
          ))}
        </>
      )}
    </>
  );
}

import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import type { Payload } from "../types";
import { posterUrl, venueMap } from "../data";
import { formatDayLabel, groupByDay, parisDayKey } from "../time";
import { ScreeningRow } from "../components/ScreeningRow";

export function FilmDetail({ payload, now }: { payload: Payload; now: Date }) {
  const { key } = useParams();
  const venues = useMemo(() => venueMap(payload), [payload]);
  const film = key ? (payload.films[key] ?? null) : null;

  const screenings = useMemo(() => {
    const today = parisDayKey(now);
    return payload.screenings.filter(
      (s) => s.film_key === key && parisDayKey(s.start_utc) >= today
    );
  }, [payload, key, now]);

  const marquee = screenings[0]?.title_marquee ?? key ?? "Unknown";
  const title = film?.title_en || marquee;
  const poster = posterUrl(film, "w500");
  const days = useMemo(() => [...groupByDay(screenings).entries()], [screenings]);

  return (
    <>
      <div className="section">
        <Link to="/" className="back faint">← Back</Link>
        <div className="film-head">
          {poster && <img className="poster poster-w500" src={poster} alt={title} />}
          <div>
            <h2 className="detail-title">{title}</h2>
            {film?.title_en && film.title_en !== marquee && (
              <p className="faint">{marquee}</p>
            )}
            <p className="faint tnum">
              {[film?.year, film?.runtime && `${film.runtime} min`]
                .filter(Boolean)
                .join(" · ")}
            </p>
            {film?.overview && <p className="film-overview dim">{film.overview}</p>}
          </div>
        </div>
      </div>

      {days.length === 0 ? (
        <p className="empty">No upcoming screenings.</p>
      ) : (
        days.map(([day, list]) => (
          <section className="section" key={day}>
            <h2 className="section-title">{formatDayLabel(`${day}T12:00:00Z`)}</h2>
            {list.map((s) => (
              <ScreeningRow
                key={`${s.venue_id}-${s.start_utc}`}
                payload={payload}
                screening={s}
                venue={venues.get(s.venue_id)}
                now={now}
              />
            ))}
          </section>
        ))
      )}
    </>
  );
}

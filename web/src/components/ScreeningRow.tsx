import { Link } from "react-router-dom";
import type { Payload, Screening, Venue } from "../types";
import { displayTitle, filmFor, secondaryTitle } from "../data";
import { countdownLabel, formatParisTime } from "../time";
import { Poster } from "./Poster";

export function ScreeningRow({ payload, screening, venue, now, showCountdown = false }: {
  payload: Payload;
  screening: Screening;
  venue: Venue | undefined;
  now: Date;
  showCountdown?: boolean;
}) {
  const film = filmFor(payload, screening);
  const title = displayTitle(payload, screening);
  const secondary = secondaryTitle(payload, screening);

  return (
    <article className="row">
      <div className="row-time tnum">
        {formatParisTime(screening.start_utc)}
        {showCountdown && (
          <span className="row-countdown">{countdownLabel(screening.start_utc, now)}</span>
        )}
      </div>

      <Poster film={film} alt={title} />

      <div className="row-body">
        {screening.film_key ? (
          <Link className="row-title" to={`/film/${encodeURIComponent(screening.film_key)}`}>
            {title}
          </Link>
        ) : (
          <span className="row-title">{title}</span>
        )}
        {secondary && <div className="row-secondary faint">{secondary}</div>}
        <div className="row-meta dim">
          {venue && (
            <Link to={`/cinema/${venue.id}`} className="row-venue">{venue.name}</Link>
          )}
          {screening.version !== "UNKNOWN" && <span className="tag">{screening.version}</span>}
          {screening.is_event && <span className="tag tag-event">Event</span>}
        </div>
      </div>

      {screening.booking_url && (
        <a
          className="row-book"
          href={screening.booking_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          Reserve
        </a>
      )}
    </article>
  );
}

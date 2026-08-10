import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import type { Payload } from "../types";
import { formatDayLabel, groupByDay, parisDayKey } from "../time";
import { ScreeningRow } from "../components/ScreeningRow";

const ACCESSIBILITY_LABELS: Record<string, string> = {
  hall_accessible: "Step-free access",
  has_accessible_toilets: "Accessible toilets",
  audio_description_headsets_count: "Audio description headsets",
  hearing_receivers_count: "Hearing receivers",
  staff_accessibility_level: "Staff assistance",
};

export function CinemaDetail({ payload, now }: { payload: Payload; now: Date }) {
  const { id } = useParams();
  const venue = payload.venues.find((v) => v.id === id);

  const days = useMemo(() => {
    if (!venue) return [];
    const today = parisDayKey(now);
    return [
      ...groupByDay(
        payload.screenings.filter(
          (s) => s.venue_id === venue.id && parisDayKey(s.start_utc) >= today
        )
      ).entries(),
    ];
  }, [payload, venue, now]);

  if (!venue) return <p className="empty">Unknown cinema.</p>;

  return (
    <>
      <div className="section">
        <Link to="/cinemas" className="back faint">← Cinemas</Link>
        <h2 className="detail-title">{venue.name}</h2>
        <p className="faint">
          {venue.arrondissement}<sup>e</sup> arrondissement
          {venue.chain && ` · ${venue.chain}`}
        </p>

        {venue.accessibility && (
          <ul className="access">
            {Object.entries(venue.accessibility)
              .filter(([, val]) => val !== null && val !== false && val !== 0)
              .map(([k, val]) => (
                <li key={k} className="faint">
                  {ACCESSIBILITY_LABELS[k] ?? k}
                  {typeof val === "number" && val > 1 ? `: ${val}` : ""}
                </li>
              ))}
          </ul>
        )}
      </div>

      {venue.coverage === "none" ? (
        <p className="empty">
          We don’t have a data source for this cinema yet, so its programme isn’t listed
          here. Check the cinema’s own site.
        </p>
      ) : days.length === 0 ? (
        <p className="empty">Nothing scheduled in the current listings.</p>
      ) : (
        days.map(([day, list]) => (
          <section className="section" key={day}>
            <h2 className="section-title">{formatDayLabel(`${day}T12:00:00Z`)}</h2>
            {list.map((s) => (
              <ScreeningRow
                key={`${s.start_utc}-${s.title_marquee}`}
                payload={payload}
                screening={s}
                venue={venue}
                now={now}
              />
            ))}
          </section>
        ))
      )}
    </>
  );
}

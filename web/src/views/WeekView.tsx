import { useMemo, useState } from "react";
import type { Payload } from "../types";
import { venueMap } from "../data";
import { formatDayLabel, groupByDay, parisDayKey } from "../time";
import { ScreeningRow } from "../components/ScreeningRow";

export function WeekView({ payload, now }: { payload: Payload; now: Date }) {
  const venues = useMemo(() => venueMap(payload), [payload]);

  const days = useMemo(() => {
    const independents = new Set(
      payload.venues.filter((v) => v.kind === "independent").map((v) => v.id)
    );
    const today = parisDayKey(now);
    const upcoming = payload.screenings.filter(
      (s) => independents.has(s.venue_id) && parisDayKey(s.start_utc) >= today
    );
    return [...groupByDay(upcoming).entries()].slice(0, 7);
  }, [payload, now]);

  const [selected, setSelected] = useState<string | null>(null);
  const active = selected ?? days[0]?.[0] ?? null;
  const screenings = days.find(([d]) => d === active)?.[1] ?? [];

  if (days.length === 0) {
    return <p className="empty">No upcoming screenings.</p>;
  }

  return (
    <>
      <div className="daybar">
        {days.map(([day, list]) => (
          <button
            key={day}
            onClick={() => setSelected(day)}
            className={day === active ? "day day-on" : "day"}
          >
            <span className="day-label">{formatDayLabel(`${day}T12:00:00Z`)}</span>
            <span className="day-count tnum">{list.length}</span>
          </button>
        ))}
      </div>

      <div className="section">
        {screenings.map((s) => (
          <ScreeningRow
            key={`${s.venue_id}-${s.start_utc}-${s.title_marquee}`}
            payload={payload}
            screening={s}
            venue={venues.get(s.venue_id)}
            now={now}
          />
        ))}
      </div>
    </>
  );
}

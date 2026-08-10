import { useMemo, useState } from "react";
import type { Payload } from "../types";
import { venueMap } from "../data";
import { parisDayKey } from "../time";
import { ScreeningRow } from "../components/ScreeningRow";

export function ChainsView({ payload, now }: { payload: Payload; now: Date }) {
  const venues = useMemo(() => venueMap(payload), [payload]);

  const chains = useMemo(() => {
    const names = new Set(
      payload.venues.filter((v) => v.kind === "chain" && v.chain).map((v) => v.chain!)
    );
    return [...names].sort();
  }, [payload]);

  const [active, setActive] = useState<string | null>(null);
  const chain = active ?? chains[0] ?? null;

  const screenings = useMemo(() => {
    if (!chain) return [];
    const ids = new Set(
      payload.venues.filter((v) => v.chain === chain).map((v) => v.id)
    );
    const today = parisDayKey(now);
    return payload.screenings
      .filter(
        (s) =>
          ids.has(s.venue_id) &&
          parisDayKey(s.start_utc) === today &&
          new Date(s.start_utc) > now
      )
      .sort((a, b) => a.start_utc.localeCompare(b.start_utc));
  }, [payload, chain, now]);

  if (chains.length === 0) return <p className="empty">No chain venues in the data.</p>;

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

      <div className="section">
        {screenings.length === 0 ? (
          <p className="empty">Nothing left today at {chain}.</p>
        ) : (
          screenings.map((s) => (
            <ScreeningRow
              key={`${s.venue_id}-${s.start_utc}-${s.title_marquee}`}
              payload={payload}
              screening={s}
              venue={venues.get(s.venue_id)}
              now={now}
            />
          ))
        )}
      </div>
    </>
  );
}

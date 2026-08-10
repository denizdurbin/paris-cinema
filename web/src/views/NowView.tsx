import { useMemo } from "react";
import type { Payload } from "../types";
import { venueMap } from "../data";
import { bucketScreenings, formatParisTime, parisDayKey } from "../time";
import { ScreeningRow } from "../components/ScreeningRow";
import { Section } from "../components/Section";
import { useVenueFilter } from "../useVenueFilter";
import { VenueFilter } from "../components/VenueFilter";

export function NowView({ payload, now }: { payload: Payload; now: Date }) {
  const venues = useMemo(() => venueMap(payload), [payload]);
  const filter = useVenueFilter(payload.venues);

  // bucketScreenings derives its allow-list from the venues array it is given,
  // so narrowing that array is all the filtering required. time.ts is untouched.
  const visibleVenues = useMemo(
    () => payload.venues.filter((v) => filter.isVisible(v.id)),
    [payload.venues, filter]
  );
  const buckets = useMemo(
    () => bucketScreenings(payload.screenings, visibleVenues, now),
    [payload.screenings, visibleVenues, now]
  );

  const nothingSoon =
    buckets.justStarted.length + buckets.next30.length + buckets.withinHour.length === 0;

  // For the empty state: the next independent screening at any point in the future.
  const nextUp = useMemo(() => {
    const independents = new Set(
      payload.venues.filter((v) => v.kind === "independent").map((v) => v.id)
    );
    return payload.screenings
      .filter((s) => independents.has(s.venue_id) && new Date(s.start_utc) > now)
      .sort((a, b) => a.start_utc.localeCompare(b.start_utc))[0];
  }, [payload, now]);

  const render = (list: typeof payload.screenings, countdown: boolean) =>
    list.map((s) => (
      <ScreeningRow
        key={`${s.venue_id}-${s.start_utc}-${s.title_marquee}`}
        payload={payload}
        screening={s}
        venue={venues.get(s.venue_id)}
        now={now}
        showCountdown={countdown}
      />
    ));

  return (
    <>
      <VenueFilter venues={payload.venues} {...filter} />
      {nothingSoon && (
        <Section title="Starting soon">
          <p className="empty">
            {filter.visibleCount === 0 ? (
              "No cinemas selected — open the filter above and pick some."
            ) : nextUp ? (
              <>
                Nothing starting soon. Next up:{" "}
                {formatParisTime(nextUp.start_utc)} at{" "}
                {venues.get(nextUp.venue_id)?.name ?? nextUp.venue_id}
                {parisDayKey(nextUp.start_utc) !== parisDayKey(now) && " tomorrow"}.
              </>
            ) : (
              "No upcoming screenings in the data."
            )}
          </p>
        </Section>
      )}

      {buckets.justStarted.length > 0 && (
        <Section title="Just started, you can still make it!" count={buckets.justStarted.length}>
          {render(buckets.justStarted, true)}
        </Section>
      )}

      {buckets.next30.length > 0 && (
        <Section title="Next 30 minutes" count={buckets.next30.length}>
          {render(buckets.next30, true)}
        </Section>
      )}

      {buckets.withinHour.length > 0 && (
        <Section title="Within the hour" count={buckets.withinHour.length}>
          {render(buckets.withinHour, true)}
        </Section>
      )}

      <Section title="Later today" count={buckets.laterToday.length}>
        {buckets.laterToday.length > 0 ? (
          render(buckets.laterToday, false)
        ) : (
          <p className="empty">Nothing else today.</p>
        )}
      </Section>
    </>
  );
}

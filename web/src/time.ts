import type { Screening, Venue } from "./types";

export const PARIS = "Europe/Paris";
export const GRACE_MINUTES = 15;

const hhmm = new Intl.DateTimeFormat("en-GB", {
  timeZone: PARIS, hour: "2-digit", minute: "2-digit", hour12: false,
});

const ymd = new Intl.DateTimeFormat("en-CA", {
  timeZone: PARIS, year: "numeric", month: "2-digit", day: "2-digit",
});

const dayLabelFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: PARIS, weekday: "short", day: "numeric", month: "short",
});

export function formatParisTime(iso: string): string {
  return hhmm.format(new Date(iso));
}

/** "2026-08-10" in Paris local terms. en-CA gives ISO-ordered output. */
export function parisDayKey(iso: string | Date): string {
  return ymd.format(typeof iso === "string" ? new Date(iso) : iso);
}

export function formatDayLabel(iso: string | Date): string {
  return dayLabelFmt.format(typeof iso === "string" ? new Date(iso) : iso);
}

export function minutesUntil(iso: string, now: Date): number {
  return Math.round((new Date(iso).getTime() - now.getTime()) / 60000);
}

/** "in 12 min" / "just started" / "20:15" */
export function countdownLabel(iso: string, now: Date): string {
  const m = minutesUntil(iso, now);
  if (m < 0) return "just started";
  if (m === 0) return "starting now";
  if (m < 60) return `in ${m} min`;
  return formatParisTime(iso);
}

export interface Buckets {
  justStarted: Screening[];
  next30: Screening[];
  withinHour: Screening[];
  laterToday: Screening[];
}

export function bucketScreenings(
  screenings: Screening[], venues: Venue[], now: Date
): Buckets {
  const independents = new Set(
    venues.filter((v) => v.kind === "independent").map((v) => v.id)
  );
  const today = parisDayKey(now);

  const out: Buckets = { justStarted: [], next30: [], withinHour: [], laterToday: [] };

  for (const s of screenings) {
    if (!independents.has(s.venue_id)) continue;
    const m = minutesUntil(s.start_utc, now);

    if (m < -GRACE_MINUTES) continue;
    if (m < 0) out.justStarted.push(s);
    else if (m <= 30) out.next30.push(s);
    else if (m <= 60) out.withinHour.push(s);
    else if (parisDayKey(s.start_utc) === today) out.laterToday.push(s);
  }

  const byStart = (a: Screening, b: Screening) => a.start_utc.localeCompare(b.start_utc);
  out.justStarted.sort(byStart);
  out.next30.sort(byStart);
  out.withinHour.sort(byStart);
  out.laterToday.sort(byStart);
  return out;
}

/** Groups screenings by Paris day key, ascending. */
export function groupByDay(screenings: Screening[]): Map<string, Screening[]> {
  const map = new Map<string, Screening[]>();
  for (const s of [...screenings].sort((a, b) => a.start_utc.localeCompare(b.start_utc))) {
    const k = parisDayKey(s.start_utc);
    const list = map.get(k);
    if (list) list.push(s);
    else map.set(k, [s]);
  }
  return new Map([...map.entries()].sort(([a], [b]) => a.localeCompare(b)));
}

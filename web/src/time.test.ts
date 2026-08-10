import { describe, expect, it } from "vitest";
import { bucketScreenings, parisDayKey, formatParisTime, minutesUntil } from "./time";
import type { Screening, Venue } from "./types";

const NOW = new Date("2026-08-09T18:00:00Z"); // 20:00 in Paris (CEST)

function screening(startUtc: string, venue_id = "le-champo"): Screening {
  return {
    venue_id,
    start_utc: startUtc,
    title_marquee: "Playtime",
    film_key: "playtime",
    version: "VO",
    booking_url: null,
    source: "allocine",
    is_event: false,
    fetched_at: "2026-08-09T15:00:00+00:00",
  };
}

const venues: Venue[] = [
  { id: "le-champo", name: "Le Champo", arrondissement: 5, kind: "independent",
    chain: null, coverage: "allocine", accessibility: null },
  { id: "ugc-danton", name: "UGC Danton", arrondissement: 6, kind: "chain",
    chain: "UGC", coverage: "allocine", accessibility: null },
];

describe("formatParisTime", () => {
  it("renders UTC in Paris local time", () => {
    expect(formatParisTime("2026-08-09T18:15:00Z")).toBe("20:15");
  });

  it("handles the winter offset", () => {
    expect(formatParisTime("2026-12-09T19:15:00Z")).toBe("20:15");
  });
});

describe("minutesUntil", () => {
  it("is positive for the future", () => {
    expect(minutesUntil("2026-08-09T18:30:00Z", NOW)).toBe(30);
  });
  it("is negative for the past", () => {
    expect(minutesUntil("2026-08-09T17:50:00Z", NOW)).toBe(-10);
  });
});

describe("parisDayKey", () => {
  it("groups by Paris calendar day, not UTC day", () => {
    // 23:30 UTC on the 9th is 01:30 Paris on the 10th.
    expect(parisDayKey("2026-08-09T23:30:00Z")).toBe("2026-08-10");
  });
});

describe("bucketScreenings", () => {
  it("puts a screening 10 minutes ago in justStarted", () => {
    const b = bucketScreenings([screening("2026-08-09T17:50:00Z")], venues, NOW);
    expect(b.justStarted).toHaveLength(1);
  });

  it("drops a screening 20 minutes ago entirely", () => {
    const b = bucketScreenings([screening("2026-08-09T17:40:00Z")], venues, NOW);
    expect(b.justStarted).toHaveLength(0);
    expect(b.next30).toHaveLength(0);
    expect(b.laterToday).toHaveLength(0);
  });

  it("includes a screening exactly 15 minutes ago (inclusive boundary)", () => {
    const b = bucketScreenings([screening("2026-08-09T17:45:00Z")], venues, NOW);
    expect(b.justStarted).toHaveLength(1);
  });

  it("puts a screening in 20 minutes in next30", () => {
    const b = bucketScreenings([screening("2026-08-09T18:20:00Z")], venues, NOW);
    expect(b.next30).toHaveLength(1);
  });

  it("puts a screening in 45 minutes in withinHour", () => {
    const b = bucketScreenings([screening("2026-08-09T18:45:00Z")], venues, NOW);
    expect(b.withinHour).toHaveLength(1);
  });

  it("puts a screening in 3 hours in laterToday", () => {
    const b = bucketScreenings([screening("2026-08-09T21:00:00Z")], venues, NOW);
    expect(b.laterToday).toHaveLength(1);
  });

  it("excludes tomorrow from laterToday", () => {
    const b = bucketScreenings([screening("2026-08-10T18:00:00Z")], venues, NOW);
    expect(b.laterToday).toHaveLength(0);
  });

  it("excludes chain venues from every bucket", () => {
    const b = bucketScreenings(
      [screening("2026-08-09T18:20:00Z", "ugc-danton")], venues, NOW
    );
    expect(b.next30).toHaveLength(0);
    expect(b.laterToday).toHaveLength(0);
  });

  it("sorts each bucket by start time", () => {
    const b = bucketScreenings(
      [screening("2026-08-09T18:25:00Z"), screening("2026-08-09T18:05:00Z")],
      venues, NOW
    );
    expect(b.next30.map((s) => s.start_utc)).toEqual([
      "2026-08-09T18:05:00Z", "2026-08-09T18:25:00Z",
    ]);
  });
});

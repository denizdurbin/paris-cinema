# Plan 3 — Cinema filter, chains by location, copy fix

**Executor:** Cline with Kimi K3. Self-contained: assumes no prior conversation.

Plans 1 and 2 are complete. The pipeline runs hourly and the site is deployed at
<https://denizdurbin.github.io/paris-cinema/>. This plan adds three things:

1. A **cinema filter on the Now view** — pick which cinemas you want to see.
2. **UGC and MK2 grouped by location** rather than one flat list per chain.
3. A **copy fix** on the "just started" heading.

Work top to bottom. Every task ends with a command and an expected result.

---

## Current state you are building on

```
web/src/
  App.tsx                    routes; owns `payload` and a `now` that ticks every 30s
  data.ts                    loadPayload, filmFor, displayTitle, posterUrl, venueMap
  time.ts                    bucketScreenings, groupByDay, formatParisTime, parisDayKey
  time.test.ts               14 vitest tests
  types.ts                   Payload, Venue, Screening, Film
  components/                Nav, Freshness, SourceBanner, Section, ScreeningRow, Poster
  views/                     NowView, WeekView, CinemasView, CinemaDetail, ChainsView, FilmDetail
  styles/tokens.css          design tokens
  styles/base.css            reset + layout
  styles/components.css      component styles
```

Key facts you need:

- `Venue` has `kind: "independent" | "chain"`, `chain: string | null`,
  `arrondissement: number`, `coverage: "allocine" | "operator" | "none"`.
- `bucketScreenings(screenings, venues, now)` in `time.ts` derives its allow-list from the
  `venues` argument: it only buckets screenings whose venue appears in that array **and**
  has `kind === "independent"`. **Do not modify `time.ts`.** To filter, pass it a narrower
  `venues` array. This is why no test changes are needed.
- The dev server runs at `http://localhost:5173/paris-cinema/` — note the subpath. The bare
  root redirects.

## Global rules

- TypeScript `strict`. No `any`.
- Plain CSS with the existing custom properties. No Tailwind, no component library.
- Use the existing spacing tokens (`--s1`..`--s8`). Never improvise a pixel value.
- Never format a timestamp without `timeZone: "Europe/Paris"`.
- `npm run build` must pass before you commit any task.
- Commit after each task with the message given.

---

## Task 1: Fix the "just started" copy

**File:** `web/src/views/NowView.tsx`

- [ ] **Step 1:** Find this line (around line 60):

```tsx
        <Section title="Just started — you'd still make it" count={buckets.justStarted.length}>
```

Change it to:

```tsx
        <Section title="Just started, you can still make it!" count={buckets.justStarted.length}>
```

- [ ] **Step 2:** Verify.

```bash
cd web && npm run build
```

- [ ] **Step 3:** Commit.

```bash
git add web/src/views/NowView.tsx
git commit -m "feat: reword the just-started heading"
```

---

## Task 2: Venue filter state, with tests

A hook owning which cinemas are visible, persisted across visits.

**Files:** create `web/src/useVenueFilter.ts` and `web/src/useVenueFilter.test.ts`

**Design decision you must follow:** persist the set of **hidden** venue ids, not the
visible ones. Cinemas get added to the catalogue over time; if we stored the visible set, a
newly added cinema would be invisible to anyone who had ever touched the filter, and they
would never know it existed. Storing exclusions means anything new is visible by default.

**Interface produced:**

```ts
useVenueFilter(allVenues: Venue[]): {
  hidden: Set<string>;          // venue ids explicitly hidden
  isVisible: (id: string) => boolean;
  toggle: (id: string) => void;
  showAll: () => void;
  hideAll: (ids: string[]) => void;
  visibleCount: number;         // among independents
  totalCount: number;           // independents in the catalogue
  isFiltered: boolean;          // true when anything is hidden
}
```

- [ ] **Step 1:** Write `web/src/useVenueFilter.test.ts`.

```ts
import { beforeEach, describe, expect, it } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useVenueFilter, STORAGE_KEY } from "./useVenueFilter";
import type { Venue } from "./types";

function venue(id: string, kind: Venue["kind"] = "independent"): Venue {
  return { id, name: id, arrondissement: 5, kind, chain: null,
           coverage: "allocine", accessibility: null };
}

const VENUES = [venue("a"), venue("b"), venue("c"), venue("ugc-1", "chain")];

beforeEach(() => localStorage.clear());

describe("useVenueFilter", () => {
  it("shows everything by default", () => {
    const { result } = renderHook(() => useVenueFilter(VENUES));
    expect(result.current.isFiltered).toBe(false);
    expect(result.current.visibleCount).toBe(3);
    expect(result.current.totalCount).toBe(3);
  });

  it("counts only independents", () => {
    const { result } = renderHook(() => useVenueFilter(VENUES));
    expect(result.current.totalCount).toBe(3); // ugc-1 excluded
  });

  it("toggling hides then shows again", () => {
    const { result } = renderHook(() => useVenueFilter(VENUES));
    act(() => result.current.toggle("a"));
    expect(result.current.isVisible("a")).toBe(false);
    expect(result.current.visibleCount).toBe(2);
    expect(result.current.isFiltered).toBe(true);
    act(() => result.current.toggle("a"));
    expect(result.current.isVisible("a")).toBe(true);
    expect(result.current.isFiltered).toBe(false);
  });

  it("persists hidden ids to localStorage", () => {
    const { result } = renderHook(() => useVenueFilter(VENUES));
    act(() => result.current.toggle("b"));
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY)!)).toEqual(["b"]);
  });

  it("restores hidden ids from localStorage", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(["c"]));
    const { result } = renderHook(() => useVenueFilter(VENUES));
    expect(result.current.isVisible("c")).toBe(false);
    expect(result.current.visibleCount).toBe(2);
  });

  it("a venue added after the filter was set stays visible", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(["a"]));
    const { result } = renderHook(() =>
      useVenueFilter([...VENUES, venue("brand-new")])
    );
    expect(result.current.isVisible("brand-new")).toBe(true);
  });

  it("showAll clears everything", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(["a", "b"]));
    const { result } = renderHook(() => useVenueFilter(VENUES));
    act(() => result.current.showAll());
    expect(result.current.isFiltered).toBe(false);
    expect(result.current.visibleCount).toBe(3);
  });

  it("hideAll hides the ids given", () => {
    const { result } = renderHook(() => useVenueFilter(VENUES));
    act(() => result.current.hideAll(["a", "b", "c"]));
    expect(result.current.visibleCount).toBe(0);
  });

  it("survives corrupt localStorage", () => {
    localStorage.setItem(STORAGE_KEY, "not json");
    const { result } = renderHook(() => useVenueFilter(VENUES));
    expect(result.current.isFiltered).toBe(false);
    expect(result.current.visibleCount).toBe(3);
  });
});
```

- [ ] **Step 2:** Install the test dependencies and configure a DOM environment.

```bash
cd web && npm install -D @testing-library/react jsdom
```

Then add the `test` block to `web/vite.config.ts`, keeping the existing `base`:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/paris-cinema/",
  test: {
    environment: "jsdom",
  },
});
```

If TypeScript complains that `test` is not a valid property, change the first import line to:

```ts
/// <reference types="vitest/config" />
import { defineConfig } from "vite";
```

- [ ] **Step 3:** Run the tests and confirm they fail.

```bash
cd web && npm test
```

Expected: FAIL — cannot resolve `./useVenueFilter`.

- [ ] **Step 4:** Write `web/src/useVenueFilter.ts`.

```ts
import { useCallback, useEffect, useMemo, useState } from "react";
import type { Venue } from "./types";

export const STORAGE_KEY = "paris-cinema:hidden-venues";

/** Reads the persisted hidden set, tolerating absent or corrupt storage. */
function readHidden(): Set<string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return new Set();
    return new Set(parsed.filter((x): x is string => typeof x === "string"));
  } catch {
    return new Set();
  }
}

export function useVenueFilter(allVenues: Venue[]) {
  const [hidden, setHidden] = useState<Set<string>>(readHidden);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...hidden]));
    } catch {
      // Private browsing or a full quota. Filtering still works for this
      // session; only persistence is lost, which is not worth crashing over.
    }
  }, [hidden]);

  const independents = useMemo(
    () => allVenues.filter((v) => v.kind === "independent"),
    [allVenues]
  );

  const isVisible = useCallback((id: string) => !hidden.has(id), [hidden]);

  const toggle = useCallback((id: string) => {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const showAll = useCallback(() => setHidden(new Set()), []);

  const hideAll = useCallback((ids: string[]) => setHidden(new Set(ids)), []);

  const visibleCount = independents.filter((v) => !hidden.has(v.id)).length;

  return {
    hidden,
    isVisible,
    toggle,
    showAll,
    hideAll,
    visibleCount,
    totalCount: independents.length,
    isFiltered: visibleCount < independents.length,
  };
}
```

- [ ] **Step 5:** Run the tests.

```bash
cd web && npm test
```

Expected: PASS — 14 existing `time.test.ts` tests plus 9 new ones, 23 total.

- [ ] **Step 6:** Commit.

```bash
git add web/src/useVenueFilter.ts web/src/useVenueFilter.test.ts web/vite.config.ts web/package.json web/package-lock.json
git commit -m "feat: add persisted venue filter state"
```

---

## Task 3: Venue filter UI, wired into the Now view

**Files:** create `web/src/components/VenueFilter.tsx`; modify
`web/src/views/NowView.tsx` and `web/src/styles/components.css`

The design is deliberately restrained: a single summary line that expands. It must never
push the screening list below the fold when collapsed — the Now band is the point of the
app, and a filter that buries it defeats the purpose.

- [ ] **Step 1:** Create `web/src/components/VenueFilter.tsx`.

```tsx
import { useMemo, useState } from "react";
import type { Venue } from "../types";

interface Props {
  venues: Venue[];
  isVisible: (id: string) => boolean;
  toggle: (id: string) => void;
  showAll: () => void;
  hideAll: (ids: string[]) => void;
  visibleCount: number;
  totalCount: number;
  isFiltered: boolean;
}

export function VenueFilter({
  venues, isVisible, toggle, showAll, hideAll, visibleCount, totalCount, isFiltered,
}: Props) {
  const [open, setOpen] = useState(false);

  const independents = useMemo(
    () =>
      venues
        .filter((v) => v.kind === "independent")
        .sort((a, b) => a.arrondissement - b.arrondissement || a.name.localeCompare(b.name)),
    [venues]
  );

  return (
    <div className="filter">
      <button
        className="filter-toggle"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className={isFiltered ? "filter-summary-on" : "filter-summary"}>
          {isFiltered ? `${visibleCount} of ${totalCount} cinemas` : "All cinemas"}
        </span>
        <span className="filter-chevron faint">{open ? "Hide" : "Filter"}</span>
      </button>

      {open && (
        <div className="filter-panel">
          <div className="filter-actions">
            <button className="filter-action" onClick={showAll}>
              Select all
            </button>
            <button
              className="filter-action"
              onClick={() => hideAll(independents.map((v) => v.id))}
            >
              Clear all
            </button>
          </div>

          <div className="filter-chips">
            {independents.map((v) => (
              <button
                key={v.id}
                onClick={() => toggle(v.id)}
                aria-pressed={isVisible(v.id)}
                className={isVisible(v.id) ? "chip chip-on" : "chip"}
              >
                {v.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2:** Wire it into `web/src/views/NowView.tsx`.

Add these imports at the top:

```tsx
import { useVenueFilter } from "../useVenueFilter";
import { VenueFilter } from "../components/VenueFilter";
```

Immediately after `const venues = useMemo(() => venueMap(payload), [payload]);`, add:

```tsx
  const filter = useVenueFilter(payload.venues);

  // bucketScreenings derives its allow-list from the venues array it is given,
  // so narrowing that array is all the filtering required. time.ts is untouched.
  const visibleVenues = useMemo(
    () => payload.venues.filter((v) => filter.isVisible(v.id)),
    [payload.venues, filter]
  );
```

Then change the `buckets` memo from:

```tsx
  const buckets = useMemo(
    () => bucketScreenings(payload.screenings, payload.venues, now),
    [payload, now]
  );
```

to:

```tsx
  const buckets = useMemo(
    () => bucketScreenings(payload.screenings, visibleVenues, now),
    [payload.screenings, visibleVenues, now]
  );
```

Finally, render the filter as the **first** element inside the returned fragment, before
the `{nothingSoon && ...}` block:

```tsx
      <VenueFilter venues={payload.venues} {...filter} />
```

- [ ] **Step 3:** Handle the everything-hidden case. Still in `NowView.tsx`, replace the
      existing `nothingSoon` empty-state paragraph so it distinguishes "nothing is on" from
      "you hid everything" — otherwise the app looks broken when it is merely filtered.

Find:

```tsx
          <p className="empty">
            {nextUp ? (
```

and change the opening to:

```tsx
          <p className="empty">
            {filter.visibleCount === 0 ? (
              "No cinemas selected — open the filter above and pick some."
            ) : nextUp ? (
```

The existing `nextUp` and fallback branches stay exactly as they are.

- [ ] **Step 4:** Append to `web/src/styles/components.css`.

```css
.filter { margin-top: var(--s5); }

.filter-toggle {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  width: 100%;
  padding: var(--s2) 0;
  font-size: var(--fs-sm);
}

.filter-summary { color: var(--text-dim); }
.filter-summary-on { color: var(--accent); }
.filter-chevron { font-size: var(--fs-xs); }

.filter-panel { padding: var(--s2) 0 var(--s4); }

.filter-actions { display: flex; gap: var(--s4); margin-bottom: var(--s3); }

.filter-action {
  font-size: var(--fs-xs);
  color: var(--text-faint);
  padding: 0;
}
.filter-action:hover { color: var(--accent); }

.filter-chips { display: flex; flex-wrap: wrap; gap: var(--s2); }

.chip {
  font-size: var(--fs-xs);
  padding: var(--s1) var(--s2);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text-faint);
}
.chip-on { color: var(--bg); background: var(--accent); }
```

- [ ] **Step 5:** Verify by hand. Run `cd web && npm run dev`, open
      <http://localhost:5173/paris-cinema/> and check:
  - the summary reads "All cinemas" on first load
  - clicking "Filter" reveals chips, all highlighted
  - deselecting a cinema immediately removes its screenings from every band
  - the summary switches to "N of 34 cinemas" in the accent colour
  - reloading the page keeps your selection
  - "Clear all" produces the "No cinemas selected" message, not a blank page

- [ ] **Step 6:** Build and commit.

```bash
cd web && npm run build
git add web/src web/src/styles/components.css
git commit -m "feat: add cinema filter to the Now view"
```

---

## Task 4: Group chain screenings by location

Currently `ChainsView` lists every screening for the selected chain in one flat, time-sorted
list. UGC Les Halles alone runs ~268 screenings a day, so this is unusable. Group by venue
instead.

**File:** `web/src/views/ChainsView.tsx` — replace the whole file.

- [ ] **Step 1:** Replace `web/src/views/ChainsView.tsx` with:

```tsx
import { useMemo, useState } from "react";
import type { Payload, Screening, Venue } from "../types";
import { parisDayKey } from "../time";
import { ScreeningRow } from "../components/ScreeningRow";

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
            <section className="section" key={venue.id}>
              <h2 className="section-title">
                {venue.name}
                <span className="section-count faint">
                  {venue.arrondissement}
                  <sup>e</sup> · {screenings.length}
                </span>
              </h2>
              {screenings.map((s) => (
                <ScreeningRow
                  key={`${s.start_utc}-${s.title_marquee}`}
                  payload={payload}
                  screening={s}
                  venue={venue}
                  now={now}
                />
              ))}
            </section>
          ))}
        </>
      )}
    </>
  );
}
```

- [ ] **Step 2:** Append to `web/src/styles/components.css`.

```css
.chain-total { font-size: var(--fs-xs); margin: var(--s4) 0 0; }
```

- [ ] **Step 3:** Verify by hand. With the dev server running, open the **UGC & MK2** tab:
  - screenings are grouped under venue headings, not one flat list
  - each heading shows the arrondissement and a count
  - switching between UGC and MK2 regroups correctly
  - venues with nothing left today do not appear at all
  - the venue name in each row still links to that cinema's page

- [ ] **Step 4:** Build and commit.

```bash
cd web && npm run build
git add web/src/views/ChainsView.tsx web/src/styles/components.css
git commit -m "feat: group chain screenings by location"
```

---

## Task 5: Ship it

- [ ] **Step 1:** Run everything.

```bash
cd web && npm test && npm run build
```

Expected: 23 tests pass, build succeeds.

- [ ] **Step 2:** Check the mobile layout at 375px in DevTools:
  - no horizontal scrolling on any tab
  - filter chips wrap rather than overflow
  - chain venue headings do not truncate awkwardly

- [ ] **Step 3:** Push. The `push` trigger on `master` runs the refresh workflow, which
      rebuilds and redeploys to GitHub Pages.

```bash
git push
```

- [ ] **Step 4:** Watch the run, then check the live site.

```bash
gh run watch --exit-status
```

Then open <https://denizdurbin.github.io/paris-cinema/> and confirm the filter persists
across a reload and the chains tab is grouped by location.

---

## Notes on decisions made here

**The filter applies to the Now view only.** That is what was asked for. It is the view
where noise hurts most, since "what can I walk into" is a question about a handful of
nearby cinemas rather than all thirty-four. The hook is view-agnostic, so extending it to
Week later means importing it there and narrowing the same array.

**Hidden ids are persisted, not visible ones.** A cinema added to the catalogue later stays
visible to existing users. The reverse would silently hide new venues from anyone who had
ever opened the filter.

**`time.ts` is deliberately untouched.** `bucketScreenings` already takes the venue list as
an argument, so filtering is a matter of passing fewer venues. That keeps all 14 existing
timezone and bucketing tests valid and unchanged.

**Chain groups omit empty venues.** A UGC list padded with ten "nothing on" headings would
bury the locations that do have screenings.

# Paris Independent Cinema Showtimes — Design

**Date:** 2026-08-08
**Status:** Approved design, pending implementation plan

## Purpose

A showtimes site covering twelve independent / art-et-essai cinemas in Paris, built
as a gift. The leading question it answers is **"what can we walk into right now?"** —
the target venues cluster in the Quartier Latin within a few minutes' walk of each
other, which makes "starting soon" a genuinely actionable question there.

Two users. No accounts, no personalisation, no user data collected or stored.

## Background: why this exists

The SCARE open dataset (`programmation-cinemas`, Data Fair) was the obvious starting
point but is not sufficient:

- It lists twelve Paris venues, but only five have real programming. Screenings in the
  seven days from 2026-08-08: Saint-André des Arts 70, L'Entrepot 52, Le Champo 40,
  Le Grand Action 37, Studio des Ursulines 28, Épée de bois 3, Le Louxor 1, and zero
  for Balzac, Elysées Lincoln, Cinq Caumartin, Sept Parnassiens and Chaplin Saint Lambert.
- It contains none of the venues that motivated the project: Écoles Cinéma Club,
  Reflet Médicis, La Filmothèque du Quartier Latin, L'Arlequin, Majestic Bastille.

Those five map to three operators, two of which publish usable JSON:

| Operator | Venues | Source | Access |
| --- | --- | --- | --- |
| Dulac Cinémas | Arlequin, Reflet Médicis, Majestic Bastille, Escurial, Majestic Passy | `dulaccinemas.com/api/home-bootstrap?days=14` | Open JSON, `schema_version` 4 |
| Paris Cinéma Club | Écoles Cinéma Club, Le Champo | `pariscinemaclub.com/wp-json/` | Open WP REST, `film` post type |
| Ciné Sorbonne | La Filmothèque du Quartier Latin | `lafilmotheque.fr` | HTML only (`wp-json` returns 403) |

Le Champo belongs to Paris Cinéma Club, so it appears in two sources and must be
deduplicated.

## Scope

**In scope (v1):** twelve venues, four adapters, "starting soon" / today / week /
cinema-by-cinema browsing, film detail pages, TMDB artwork and synopses, venue search.

**Out of scope (v1):** watchlists, alerts and push notifications, accounts, retrospective
and season tracking, venues beyond the twelve, native mobile app, offline support.

Alerts were ranked lowest of the four candidate features and are deliberately excluded.

## Platform decisions

| Concern | Decision |
| --- | --- |
| Delivery | Static website, no runtime backend |
| Hosting | Vercel (static output) |
| Build/refresh | GitHub Actions cron, hourly during opening hours |
| Pipeline language | Python 3.13 |
| Frontend | Vite + React |
| UI language | English |
| Film titles | English headline (TMDB `en-US`), French marquee title beneath |
| Metadata | TMDB, enriched at build time |

### Why static rather than a live backend

An earlier draft used FastAPI. It was dropped for reasons that make the app better,
not merely cheaper:

- **"Starting in the next 30 minutes" needs no server.** It is arithmetic over
  timestamps, computed in the browser against `now` and re-evaluated on every render.
  A snapshot hours old still produces a correct live countdown.
- **Free-tier backends sleep.** Render's free tier spins down and takes ~30s to wake.
  The core use case is opening the site on the street; a cold start ruins it.
- **The TMDB key stays out of the browser.** Build-time enrichment keeps the key in CI.
- **Scrapes fail visibly.** A broken source is a red CI run, not a broken page during
  an evening out.

Consequence accepted: data is frozen between runs, so a newly published screening can
take up to an hour to appear. For repertory cinemas publishing days ahead, this is
immaterial. The live countdown is unaffected.

### Refresh schedule

GitHub Actions `schedule`, hourly across the Paris opening window, plus
`workflow_dispatch` for manual refresh. Constraints that shaped this:

- 5 minutes is GitHub's hard floor; scheduled runs are best-effort and can be delayed,
  so avoid the top of the hour.
- Billing rounds every job to a full minute. Hourly across ~15 hours is ~450 minutes/month
  against the 2,000 free minutes for private repos. Public repos are unmetered.
- `ubuntu-latest` only. Windows bills 2x and macOS 10x.

Nothing is gained from a tighter cadence: the odds a screening is published and starts
within the same hour are negligible.

**Known hazard:** GitHub disables scheduled workflows after 60 days of repository
inactivity, and deploys from the job do not reset that clock. Mitigated by stamping
`generated_at` into the JSON and surfacing it in the UI (see Freshness).

## Architecture

```
adapters/            one module per source, all satisfying the same protocol
  base.py              Adapter: .slug, .venues, .fetch(window) -> list[RawScreening]
  dulac.py             JSON API      -> Arlequin, Reflet, Majestic Bastille, Escurial, Passy
  paris_cinema_club.py WP REST       -> Écoles Cinéma Club, Le Champo
  filmotheque.py       HTML scrape   -> La Filmothèque
  scare.py             Data Fair API -> Saint-André, L'Entrepot, Grand Action, Ursulines
core/
  models.py            Screening / Film / Venue (pydantic)
  normalise.py         timezone, title casing, version parsing
  dedupe.py            identity rules and source priority
  venues.py            canonical venue catalogue
  pipeline.py          concurrent fetch, per-adapter isolation, stale carry-forward
metadata/
  tmdb.py              title+year -> English title, poster, overview; cached
cinepipeline/__main__.py  entry point; writes public/data/*.json
web/                      Vite + React
```

**The adapter is the unit of everything.** Adding a cinema is one file plus a catalogue
entry; a failing source degrades in isolation. Every other decision follows from this.

### Data flow

```
GitHub Actions (cron)
  └─ python -m cinepipeline
       fetch live screenings.json (baseline)
       4 adapters, concurrent, isolated
       normalise -> dedupe -> TMDB enrich
       write public/data/screenings.json + venues.json
  └─ vite build -> vercel deploy --prod

Browser: fetch screenings.json -> filter by now() -> render
```

### Venue catalogue

Hand-written, not derived. Twelve entries, each with canonical id, display name, address
and coordinates. Sources disagree on naming (`Reflet Medicis` vs *Reflet Médicis*), and
each adapter maps its own source ids to canonical ids explicitly.

## Normalisation rules

Driven by hazards confirmed in the live data.

**Timezones.** All timestamps are parsed to timezone-aware UTC on ingest and rendered in
`Europe/Paris` on output. Dulac emits *naive UTC*: a 10:30 Paris screening arrives as
`2026-08-08T08:30:00` with no offset. SCARE mixes `+02:00` and `Z`. A missed conversion
puts evening screenings at breakfast, which on a "starting soon" screen is total failure,
not a cosmetic bug.

**Titles.** Two fields retained: `title_marquee` (source-derived, cleaned from shouting
caps — SCARE emits `LES VACANCES DE MR HULOT`) and `title_en` (TMDB). English displays
as the headline, French beneath, so the app still matches what is printed on the door.

**Deduplication.** Key is `(venue_id, start_utc, title_key)`. Le Champo appears in both
SCARE and Paris Cinéma Club, so this is load-bearing. On collision the operator's own
feed wins over SCARE; the operator is authoritative for its own listings.

**Versions.** `VO` / `VOST` / `VF` normalised to a single enum across sources.

## TMDB matching

Repertory programming is the hard case for title matching, and doing this naively is the
most likely way for the app to look shabby.

1. **Search French, display English.** Sources carry French release titles, so search with
   `language=fr-FR`, then read `en-US` for the English title and overview. Searching TMDB
   in English for "Les Vacances de M. Hulot" returns nothing useful.
2. **Score candidates rather than taking the first hit.** Title similarity + runtime match
   + year proximity. SCARE supplies `filmduration` in seconds (5280 = 88 min), which
   separates restorations and same-title remakes more reliably than anything else available.
3. **Skip non-films.** Dulac flags ciné-club and special events via `type` and
   `event_label`. Sending those to TMDB returns confident nonsense.
4. **Curate the tail.** `tmdb_overrides.json`, hand-editable, maps `title_key -> tmdb_id`,
   with `null` meaning "deliberately unmatched". The catalogue across twelve venues is a
   few hundred titles a year, so this closes the gap to near-perfect. The build emits
   `unmatched.txt` so misses are fixed in batches.
5. **Fallback chain, never a broken image:** TMDB art -> source art (SCARE `filmposter`,
   Dulac imagery) -> typographic placeholder card.

TMDB being unavailable must never fail the build; it degrades to source art. Match results
cache via `actions/cache`; `tmdb_overrides.json` lives in git.

Poster sizes: `w185` in lists, `w500` on detail pages, lazy-loaded.

## Screens

Mobile-first. Four zones plus a detail view.

**1. Now band** — the hero, first thing on screen.
- *Just started* — began within the last 15 minutes, labelled "you'd still make it".
  French cinemas run ads and trailers, so a 20:00 screening is realistically catchable
  at 20:10; dropping it the instant the clock passes discards the app's best moments.
- *Next 30 minutes*
- *Within the hour*

Each row: poster thumb, English title, French marquee beneath, venue, start time, live
countdown ticking every 30s, version tag, booking link.

**2. Rest of today** — later screenings grouped by venue.

**3. Week ahead** — day selector, today + 6.

**4. Cinemas** — twelve venue cards (name, address, next screening, today's count) with a
**client-side search box filtering by name**. Tapping through gives that cinema's full
programme grouped by day, plus a maps link. Dulac's five expose accessibility fields
(`hall_accessible`, `audio_description_headsets_count`, `hearing_receivers_count`,
`has_accessible_toilets`, `staff_accessibility_level`) which render when present and are
hidden otherwise.

**Film detail** — poster, backdrop, English synopsis, runtime, director, and every
upcoming screening of that film across all twelve venues. This covers the "where else is
this playing?" job without a film search box.

**Filters:** venue and version. A distance or "walkable now" filter is explicitly *out of
scope*: it would require browser geolocation, which is not otherwise needed, and the twelve
venues are not uniformly walkable from one another (Majestic Passy is in the 16th, Majestic
Bastille in the 11th). Venue coordinates are stored in the catalogue so this remains
possible later.

**Empty states are load-bearing.** At 23:40 the Now band is empty and must say
"nothing starting soon — first tomorrow, 11:50 at Le Champo", never render a void.

**Visual direction:** dark, poster-led, generous typography, TMDB backdrops as ambient
headers. Performance is part of looking good; correct image sizes and lazy loading are
requirements, not polish.

## Failure handling

**The deployed site is the snapshot store.** The build first fetches the currently live
`screenings.json` as a baseline, then overlays fresh adapter output. An adapter that fails
keeps its previous entries, tagged with their original `fetched_at`. No cache plumbing, no
data branch, no data commits.

- Per-adapter isolation, always. One source cannot take down the build.
- Deploy if *any* adapter succeeded. Abort without deploying if *all* fail, so a network
  blip cannot replace a good site with an empty one.
- Per-source status ships inside the JSON.

**Freshness.** `generated_at` is stamped into the output. The UI shows a discreet
"updated 3h ago", escalating to a visible warning past 12h. This doubles as the early
warning if Actions is ever disabled for inactivity.

## Testing

Fixtures captured from real responses (Dulac JSON, PCC WP JSON, Filmothèque HTML, SCARE
JSON) so parser tests run offline and deterministically.

Regression tests target the confirmed hazards rather than chasing coverage:

- Dulac naive UTC: `2026-08-08T08:30:00` renders as 10:30 Paris
- DST changeover night in late October
- Le Champo deduplicated across two sources, operator winning
- `LES VACANCES DE MR HULOT` normalises to title case
- Grace-window boundary at exactly 15 minutes
- Non-film event entries excluded from TMDB matching

**A separate daily contract-check job** hits live sources and asserts their shape. It is
deliberately not part of the refresh job: a source redesign should produce a loud, distinct
failure rather than a refresh that quietly returns fewer venues.

Frontend tests cover the one piece of real logic, the pure function
`(screenings, now) -> buckets`. Everything else is rendering.

## Deployment

Vercel, static output, deployed from GitHub Actions.

Secrets: `TMDB_API_KEY`, `VERCEL_TOKEN`.

```yaml
name: refresh
on:
  schedule:
    - cron: '5 7-21 * * *'
  workflow_dispatch:
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python -m cinepipeline
        env:
          TMDB_API_KEY: ${{ secrets.TMDB_API_KEY }}
      - run: npm ci && npm run build
      - run: npx vercel deploy --prod --token=${{ secrets.VERCEL_TOKEN }}
```

## Open risks

| Risk | Mitigation |
| --- | --- |
| Filmothèque HTML redesign breaks the scraper | Daily contract check; stale carry-forward keeps the site usable |
| Dulac or PCC change their undocumented JSON shape | Same; `schema_version` is present in Dulac's payload and can be asserted |
| Actions disabled after 60 days inactivity | Freshness indicator makes it visible within hours |
| TMDB mismatches on heritage titles | Runtime-based scoring plus hand-curated overrides |

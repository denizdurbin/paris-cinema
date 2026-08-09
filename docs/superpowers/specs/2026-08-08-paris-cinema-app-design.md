# Paris Cinema Showtimes — Design

**Date:** 2026-08-08
**Status:** Approved design, pending implementation plan
**Revision:** 2 — data layer rewritten after venue scope grew from 12 to 34 + chains

## Purpose

A showtimes site covering the independent / art-et-essai cinemas of Paris, plus the UGC
and MK2 chains in separate sections. Built as a gift.

The leading question is **"what can we walk into right now?"** — many of these venues
cluster tightly in the 5th and 6th arrondissements, which makes "starting soon" a
genuinely actionable question there.

Two users. No accounts, no personalisation, no user data collected or stored.

## Venue scope

**Independents (34).** The 32-member Cinémas Indépendants Parisiens network, plus Le Champo
and La Filmothèque du Quartier Latin — neither is a CIP member, both were explicitly
requested.

| Arr. | Venues |
| --- | --- |
| 1er | Jeu de Paume |
| 4e | Luminor Hôtel de Ville |
| 5e | Cinéma du Panthéon, Épée de Bois, Écoles Cinéma Club, Grand Action, Reflet Médicis, Studio Galande, Studio des Ursulines, **Le Champo**, **La Filmothèque du Quartier Latin** |
| 6e | Les 3 Luxembourg, L'Arlequin, Christine Cinéma Club, Lucernaire, Nouvel Odéon, Saint-André des Arts, Le Saint-Germain des Prés |
| 8e | Le Balzac, Les Elysées Lincoln |
| 9e | 5 Caumartin, Max Linder Panorama |
| 10e | L'Archipel, Le Brady, Louxor |
| 11e | Majestic Bastille |
| 13e | L'Escurial |
| 14e | 7 Parnassiens, L'Entrepôt |
| 16e | Majestic Passy |
| 17e | Cinéma des Cinéastes, Club de l'Étoile |
| 18e | Le CiNey, Studio 28 |

**Chains.** UGC and MK2 Paris sites. Included, but confined to their own sections and
**excluded from the Now band** — see Screens.

Every venue carries `kind: independent | chain` in the catalogue. That single field drives
all chain/independent separation in the UI.

## Background: how the data layer was chosen

The first draft used four bespoke operator adapters for twelve venues. That does not scale
to 34 venues across roughly fifteen operators, so the data layer was redesigned. Findings
that drove it:

**The SCARE open dataset is not viable as a backbone.** It lists twelve Paris venues but
only five have real programming — in the week from 2026-08-08: Saint-André des Arts 70,
L'Entrepot 52, Le Champo 40, Le Grand Action 37, Studio des Ursulines 28, Épée de bois 3,
Le Louxor 1, and zero for five others. Now superseded entirely by AlloCiné; **dropped**.

**paris-cine.info** is an excellent independent aggregator with a small undocumented PHP
API (`get_movies.php`, `get_showtimes.php?mov_id=N`). Its catalogue carries 405 currently
programmed films, 385 of them with IMDb IDs plus English titles and multi-site ratings.
Rejected as a source on two grounds: the API is film-centric, so a full timetable costs
~405 requests per refresh against one person's hobby site with no CDN; and its showtimes
carry `"srcs":"AO"`, meaning it aggregates AlloCiné — building on it would be scraping a
scraper.

**AlloCiné is the upstream** and covers every French cinema including UGC, MK2 and Pathé.
Verified working: `allocine.fr/seance/salle_gen_csalle=C0071.html` (Écoles Cinéma Club)
returns 200, server-rendered, with `MovieTheater` JSON-LD and showtimes in
`data-showtime-time="2026-08-09T20:15:00+02:00"` — correctly offset-aware. One page per
venue, ~34 requests per refresh.

Its API is undocumented and use is technically contrary to their terms; this is a personal
two-user project, and it is the basis of essentially every French showtimes tool.

**Operator-direct sources are retained where they are richer.** Dulac's JSON
(`dulaccinemas.com/api/home-bootstrap?days=14`) is authoritative for its five venues and
uniquely carries per-venue accessibility data. Paris Cinéma Club's WP REST covers Écoles
and Le Champo.

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

- **"Starting in the next 30 minutes" needs no server.** It is arithmetic over timestamps,
  computed in the browser against `now` and re-evaluated on every render. A snapshot hours
  old still produces a correct live countdown.
- **Free-tier backends sleep.** Render's free tier takes ~30s to wake. The core use case is
  opening the site on the street; a cold start ruins it.
- **The TMDB key stays out of the browser.** Build-time enrichment keeps it in CI.
- **Scrapes fail visibly** — a red CI run, not a broken page during an evening out.

Consequence accepted: data is frozen between runs, so a newly published screening can take
up to an hour to appear. The live countdown is unaffected.

### Refresh schedule

GitHub Actions `schedule`, hourly across the Paris opening window, plus `workflow_dispatch`
for manual refresh.

- 5 minutes is GitHub's hard floor; runs are best-effort, so avoid the top of the hour.
- Billing rounds every job to a full minute. Hourly across ~15 hours is ~450 minutes/month
  against 2,000 free for private repos. Public repos are unmetered.
- `ubuntu-latest` only (Windows bills 2x, macOS 10x).

**Known hazard:** GitHub disables scheduled workflows after 60 days of repository
inactivity, and deploys from the job do not reset that clock. Mitigated by the freshness
indicator.

## Architecture

```
adapters/
  base.py              Adapter: .slug, .venues, .fetch(window) -> list[RawScreening]
  allocine.py          PRIMARY — all 34 independents + UGC/MK2, one page per venue
  dulac.py             Arlequin, Reflet, Majestic Bastille, Escurial, Passy (+accessibility)
  paris_cinema_club.py Écoles Cinéma Club, Le Champo
core/
  models.py            Screening / Film / Venue (pydantic)
  normalise.py         timezone, title casing, version parsing
  dedupe.py            identity rules and source priority
  venues.py            canonical catalogue: id, name, arrondissement, address,
                       coords, kind, allocine_code
  pipeline.py          concurrent fetch, per-adapter isolation, stale carry-forward
metadata/
  tmdb.py              title+year -> English title, poster, overview; cached
cinepipeline/__main__.py  entry point; writes public/data/*.json
web/                      Vite + React
```

Three adapters cover 40+ venues. AlloCiné provides breadth; the two operator adapters
provide depth where it matters. Adding a venue is normally a catalogue entry with an
`allocine_code` and no new code at all.

### Data flow

```
GitHub Actions (cron)
  └─ python -m cinepipeline
       fetch live screenings.json (baseline)
       3 adapters, concurrent, isolated, rate-limited
       normalise -> dedupe -> TMDB enrich
       write public/data/screenings.json + venues.json
  └─ vite build -> vercel deploy --prod

Browser: fetch screenings.json -> filter by now() -> render
```

### Politeness constraints

AlloCiné is fetched at ~34 requests per run, hourly. The adapter must use a descriptive
User-Agent, a small concurrency cap (4), a short delay between requests, and honour
`Cache-Control` where present. No source is ever fetched more than once per run.

### Venue catalogue

Hand-written, not derived. One entry per venue: canonical id, display name, arrondissement,
address, coordinates, `kind`, `allocine_code`, and optional operator source ids. Sources
disagree on naming (`Reflet Medicis` vs *Reflet Médicis*); the catalogue is the single
source of truth and each adapter maps its own ids onto it.

CIP's WordPress REST API (`cinemas-partenaires` post type) is a convenient one-off source
for seeding names and addresses. It carries no programming data and is not a runtime
dependency.

## Normalisation rules

**Timezones.** All timestamps parsed to timezone-aware UTC on ingest, rendered
`Europe/Paris` on output. AlloCiné supplies correct offsets. **Dulac emits naive UTC** — a
10:30 Paris screening arrives as `2026-08-08T08:30:00` with no offset. A missed conversion
puts evening screenings at breakfast, which on a "starting soon" screen is total failure.

**Titles.** Two fields: `title_marquee` (source-derived, cleaned from shouting caps) and
`title_en` (TMDB). English displays as headline, French beneath, so the app still matches
what is printed on the door.

**Deduplication — now load-bearing across the board.** AlloCiné covers every venue, so it
overlaps Dulac on five and Paris Cinéma Club on two. Key is
`(venue_id, start_utc, title_key)`. **Operator-direct always wins over AlloCiné**; the
operator is authoritative for its own listings, and Dulac additionally carries fields
AlloCiné lacks.

**Versions.** `VO` / `VOST` / `VF` normalised to one enum across sources.

## TMDB matching

Repertory programming is the hard case, and naive matching is the likeliest way for the app
to look shabby.

1. **Search French, display English.** Sources carry French release titles; search with
   `language=fr-FR`, then read `en-US` for English title and overview.
2. **Score candidates rather than taking the first hit** — title similarity, runtime match,
   year proximity. Runtime separates restorations and same-title remakes better than
   anything else available.
3. **Skip non-films.** Dulac flags ciné-club and special events via `type` / `event_label`;
   AlloCiné lists opera and concert broadcasts. These must not be sent to TMDB.
4. **Curate the tail.** `tmdb_overrides.json` maps `title_key -> tmdb_id`, `null` meaning
   deliberately unmatched. The build writes `unmatched.txt` so misses are fixed in batches.
   With ~400 films in circulation this closes the gap to near-perfect.
5. **Fallback chain, never a broken image:** TMDB art -> source art -> typographic
   placeholder card.

TMDB being unavailable must never fail the build. Match results cache via `actions/cache`;
`tmdb_overrides.json` lives in git. Poster sizes `w185` in lists, `w500` on detail.

## Screens

Mobile-first. Four zones plus a detail view.

**1. Now band** — the hero. **Independents only; chains excluded.**
- *Just started* — began within the last 15 minutes, labelled "you'd still make it".
  French cinemas run ads and trailers, so a 20:00 screening is realistically catchable at
  20:10; dropping it the instant the clock passes discards the app's best moments.
- *Next 30 minutes*
- *Within the hour*

Each row: poster thumb, English title, French marquee beneath, venue, start time, live
countdown ticking every 30s, version tag, booking link.

**2. Rest of today** — later screenings grouped by venue.

**3. Week ahead** — day selector, today + 6.

**4. Cinemas** — venue cards (name, arrondissement, address, next screening, today's count)
with a **client-side search box filtering by name**. Grouped by arrondissement. Tapping
through gives that venue's full programme by day, plus a maps link. Dulac's five expose
accessibility fields (`hall_accessible`, `audio_description_headsets_count`,
`hearing_receivers_count`, `has_accessible_toilets`, `staff_accessibility_level`) which
render when present and are hidden otherwise.

**5. Chains** — separate UGC and MK2 sections, same today/week structure, deliberately
outside the Now band.

**Film detail** — poster, backdrop, English synopsis, runtime, director, and every upcoming
screening of that film across all venues. Covers "where else is this playing?" without a
film search box.

**Filters:** venue, version, arrondissement.

A distance or "walkable now" filter is **out of scope**: it needs browser geolocation, which
nothing else requires, and the venues span the 1st to the 18th. Coordinates are stored so it
remains possible later.

**Empty states are load-bearing.** At 23:40 the Now band is empty and must say "nothing
starting soon — first tomorrow, 11:50 at Le Champo", never render a void.

**Visual direction:** dark, poster-led, generous typography, TMDB backdrops as ambient
headers. Performance is part of looking good; correct image sizes and lazy loading are
requirements, not polish.

## Failure handling

**The deployed site is the snapshot store.** The build first fetches the live
`screenings.json` as a baseline, then overlays fresh adapter output. A failed adapter keeps
its previous entries tagged with their original `fetched_at`. No cache plumbing, no data
branch, no data commits.

- Per-adapter isolation, always.
- AlloCiné failures are **per-venue**, not all-or-nothing: one venue page returning 404 or
  changed markup must not lose the other 33.
- Deploy if any adapter succeeded; abort without deploying if all fail, so a network blip
  cannot replace a good site with an empty one.
- Per-source and per-venue status ships inside the JSON.

**Freshness.** `generated_at` is stamped into the output; the UI shows "updated 3h ago",
escalating to a visible warning past 12h. Doubles as the early warning if Actions is
disabled for inactivity.

## Testing

Fixtures captured from real responses (AlloCiné venue HTML, Dulac JSON, PCC WP JSON) so
parser tests run offline and deterministically.

Regression tests target confirmed hazards, not coverage:

- Dulac naive UTC: `2026-08-08T08:30:00` renders 10:30 Paris
- AlloCiné offset timestamps survive round-tripping unchanged
- DST changeover night in late October
- Dulac and PCC venues deduplicated against AlloCiné, operator winning
- Shouting-caps titles normalise to title case
- Grace-window boundary at exactly 15 minutes
- Non-film events (opera, concert broadcasts) excluded from TMDB matching
- Chain venues never appear in Now-band output

**A separate daily contract-check job** hits live sources and asserts their shape, so an
AlloCiné markup change produces a loud, distinct failure rather than a refresh that quietly
returns fewer venues. This is the single most likely thing to break.

Frontend tests cover the one piece of real logic, `(screenings, now) -> buckets`.

## Deployment

Vercel, static output, deployed from GitHub Actions. Secrets: `TMDB_API_KEY`, `VERCEL_TOKEN`.

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
| AlloCiné markup change breaks the primary adapter | Daily contract check; per-venue isolation; stale carry-forward keeps the site usable |
| AlloCiné blocks scraping | Operator-direct adapters still cover 7 venues; would need per-operator expansion |
| Dulac or PCC change their undocumented JSON | Same; Dulac's payload carries `schema_version` which can be asserted |
| Actions disabled after 60 days inactivity | Freshness indicator makes it visible within hours |
| TMDB mismatches on heritage titles | Runtime-based scoring plus hand-curated overrides |
| 34 venue pages per run is impolite if cadence rises | Concurrency cap, delays, descriptive User-Agent, hourly ceiling |

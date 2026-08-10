# paris-cinema

Showtimes for the independent cinemas of Paris, with the question that actually matters
when you're already outside: **what can we walk into right now?**

Many of these venues sit within a few hundred metres of each other in the 5th and 6th
arrondissements, so "starting in the next 30 minutes" is a walkable question there in a way
it isn't in most cities. That band is the top of the page; everything else is secondary.

UGC and MK2 are included, but in their own section and deliberately excluded from
"starting soon" — one multiplex programmes more screenings in a day than six independents
combined, and mixing them buries exactly what this is for.

## Status

| Part | State |
| --- | --- |
| Data pipeline (Python) | Working — 53 tests passing |
| Frontend (Vite + React) | In progress — see [the plan](docs/plans/2026-08-09-frontend.md) |
| Deployment | Not yet live |

## How it works

There is no runtime backend. A scheduled GitHub Action runs the pipeline, writes a static
JSON snapshot, builds the site and deploys it.

```
GitHub Actions (hourly, 09:00–23:00 Paris)
  └─ python -m cinepipeline
       3 sources, fetched concurrently and isolated from each other
       normalise → deduplicate → enrich → write screenings.json
  └─ vite build → deploy

Browser: fetch screenings.json → filter against now() → render
```

The "starting soon" countdown is computed in the browser from timestamps in the snapshot,
so it stays accurate to the second even when the underlying data is an hour old. The
snapshot only controls how quickly *newly published* screenings appear.

Static hosting was chosen over a live backend on purpose: free-tier backends sleep, and a
30-second cold start is unacceptable for something you open on a pavement while deciding
whether you can make the 20:15.

## Data sources

| Source | Covers | Notes |
| --- | --- | --- |
| [AlloCiné](https://www.allocine.fr) | 49 venues | Primary. One page per venue, offset-aware timestamps |
| [Dulac Cinémas](https://www.dulaccinemas.com) | 5 venues | Public JSON API. Authoritative for its own venues; uniquely carries accessibility data |
| [TMDB](https://www.themoviedb.org) | Film metadata | Optional — posters, English titles, synopses |

Where sources overlap, the operator's own feed wins over AlloCiné, since the operator is
authoritative for its own listings.

AlloCiné is fetched at roughly 34 requests per run, hourly, with a concurrency cap of 4, a
delay between requests and a descriptive User-Agent. This is a personal-scale project.

Thanks to [Paris Ciné Info](https://paris-cine.info), which is a better-curated aggregator
than this one and was how several of these sources were found. It is not used as a data
source — it's one person's site without a CDN, and building on it would mean scraping a
scraper.

### Coverage gaps

Five catalogued cinemas have no data source and are shown as such rather than appearing
empty: Jeu de Paume, Épée de Bois, Louxor, Club de l'Étoile and Le CiNey. "We don't have
this cinema's data" and "this cinema has nothing on" are different statements and the UI
does not conflate them.

Venues also legitimately go dark in August, when a good number of Paris independents close
for *les vacances*.

## Running it

Requires Python 3.13 and Node 20.

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows;  source .venv/bin/activate elsewhere
pip install -e ".[dev]"
pytest                        # 53 tests, offline against committed fixtures
python -m cinepipeline        # writes web/public/data/screenings.json
```

`screenings.json` is generated and git-ignored, so run the pipeline before starting the
frontend or it will have nothing to display.

```bash
cd web && npm install && npm run dev
```

Posters, English titles and synopses need a TMDB key. Copy `.env.example` to `.env` and
fill it in — `.env` is git-ignored and loaded automatically when the `dev` extras are
installed. Alternatively export `TMDB_API_KEY` in your shell; the pipeline only ever reads
the environment, so both work.

Use the **API Key (v3 auth)**, the 32-character hex string — not the API Read Access Token,
which is a JWT and will be rejected.

Without a key the pipeline degrades cleanly to a text-only listing. That path is supported,
not broken: posters render as absent rather than as placeholders.

### Tests

```bash
pytest                # unit tests, offline
pytest -m contract    # hits live sources; asserts their shape hasn't changed
```

The contract tests run daily on their own schedule, separate from the refresh job, so a
source redesign fails loudly instead of quietly returning fewer venues. They are the first
thing to check when data looks wrong.

## Layout

```
cinepipeline/
  adapters/     one module per source, all behind a single protocol
  core/         models, canonical venue catalogue, normalisation, dedup
  metadata/     TMDB enrichment
web/            Vite + React frontend
docs/           design spec and implementation plans
tests/          unit tests plus committed fixtures from real responses
```

Adding a cinema is normally a single entry in `cinepipeline/core/venues.py` — no new code.

## Design notes

Two details that cause silent, hard-to-spot bugs and are pinned by tests:

**Dulac emits naive UTC.** A screening at 10:30 Paris arrives as `2026-08-08T08:30:00` with
no offset. Everything is parsed to timezone-aware UTC on ingest and rendered in
`Europe/Paris` on output; naive datetimes raise rather than being guessed at.

**AlloCiné obfuscates booking URLs** inside the element's `class` attribute — strip every
`ACr`, pad, then base64-decode.

The full reasoning behind the architecture is in
[the design spec](docs/superpowers/specs/2026-08-08-paris-cinema-app-design.md).

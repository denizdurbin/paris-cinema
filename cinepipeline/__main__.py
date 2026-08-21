"""Entry point. Fetches, merges, enriches and writes the static payload.

The deployed site is the snapshot store: we fetch the live screenings.json as a
baseline so a failing source degrades to its previous data rather than vanishing.
"""

import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

from cinepipeline import output
from cinepipeline.adapters.allocine import AllocineAdapter
from cinepipeline.adapters.dulac import DulacAdapter
from cinepipeline.core import dedupe
from cinepipeline.metadata.tmdb import TMDBClient

# Local convenience only: load .env if python-dotenv is installed (it is a dev
# extra). CI supplies real environment variables from GitHub secrets and never
# has this package, so the import failing is the normal path there.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

DEFAULT_OUT = Path("web/public/data")
BASELINE_URL = os.environ.get(
    "BASELINE_URL", "https://paris-cinema.vercel.app/data/screenings.json"
)


def carry_forward(
    fresh: list[dict], baseline: list[dict], failed: set[str], now: datetime
) -> list[dict]:
    fresh_venues = {e["venue_id"] for e in fresh}
    carried = [
        e
        for e in baseline
        if e["venue_id"] in failed
        and e["venue_id"] not in fresh_venues
        and datetime.fromisoformat(e["start_utc"]) > now
    ]
    return fresh + carried


def _load_baseline(url: str) -> dict:
    try:
        r = httpx.get(url, timeout=15.0, follow_redirects=True)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


async def run(out_dir: Path = DEFAULT_OUT, baseline_url: str = BASELINE_URL) -> int:
    generated_at = datetime.now(UTC)
    baseline = _load_baseline(baseline_url)

    allocine, dulac = AllocineAdapter(), DulacAdapter()
    results = await asyncio.gather(
        allocine.fetch(), dulac.fetch(), return_exceptions=False
    )

    if all(not r.ok for r in results):
        print("ERROR: every adapter failed; refusing to deploy", file=sys.stderr)
        return 1

    merged = dedupe.merge([r.screenings for r in results])

    # Events are excluded from automatic matching: titles like "Kaleidoscope -
    # seance speciale" are not films and TMDB returns confident nonsense for them.
    # An explicit override outranks that heuristic, though, because real films do
    # get programmed in cine-club slots and a manual decision should always win.
    tmdb = TMDBClient()
    # film_key -> display title plus matching hints. Several screenings share a
    # film_key; first non-null hint wins so runs are reproducible.
    titles: dict[str, dict] = {}
    for s in merged:
        if not s.film_key or (s.is_event and s.film_key not in tmdb.overrides):
            continue
        hints = titles.setdefault(
            s.film_key, {"title": s.title_marquee, "year": None, "director": None}
        )
        if hints["year"] is None:
            hints["year"] = s.film_year
        if hints["director"] is None:
            hints["director"] = s.film_director
    films = await tmdb.enrich(titles)

    payload = output.build_payload(
        merged, films, list(results), dulac.accessibility, generated_at
    )

    failed = {v for r in results for v in r.failed_venues}
    payload["screenings"] = carry_forward(
        payload["screenings"], baseline.get("screenings", []), failed, generated_at
    )

    output.write(payload, out_dir)
    print(
        f"wrote {len(payload['screenings'])} screenings, "
        f"{len(payload['films'])} films, {len(failed)} failed venues, "
        f"{len(tmdb.unmatched)} unmatched films"
    )
    for title in tmdb.unmatched:
        print(f"  unmatched: {title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))

"""The JSON contract consumed by the frontend."""

import json
from datetime import datetime
from pathlib import Path

from cinepipeline.adapters.base import AdapterResult
from cinepipeline.core import venues
from cinepipeline.core.models import Screening
from cinepipeline.metadata.tmdb import FilmMeta


def build_payload(
    screenings: list[Screening],
    films: dict[str, FilmMeta],
    results: list[AdapterResult],
    accessibility: dict[str, dict],
    generated_at: datetime,
) -> dict:
    return {
        "generated_at": generated_at.isoformat(),
        "sources": [
            {
                "slug": r.slug,
                "ok": r.ok,
                "ok_venues": len(r.ok_venues),
                "failed_venues": r.failed_venues,
            }
            for r in results
        ],
        "venues": [
            {
                "id": v.id,
                "name": v.name,
                "arrondissement": v.arrondissement,
                "kind": v.kind,
                "chain": v.chain,
                "coverage": v.coverage,
                "accessibility": accessibility.get(v.id),
            }
            for v in venues.VENUES
        ],
        "films": {k: m.model_dump() for k, m in films.items()},
        "screenings": [
            {
                "venue_id": s.venue_id,
                "start_utc": s.start_utc.isoformat(),
                "title_marquee": s.title_marquee,
                "film_key": s.film_key,
                "version": str(s.version),
                "booking_url": s.booking_url,
                "source": s.source,
                "is_event": s.is_event,
                "fetched_at": s.fetched_at.isoformat(),
            }
            for s in screenings
        ],
    }


def write(payload: dict, out_dir: Path) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "screenings.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

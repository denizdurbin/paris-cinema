"""Dulac Cinemas adapter - authoritative for its five venues.

WARNING: `date` in seances_week is NAIVE UTC. "2026-08-08T08:30:00" is 10:30 Paris.
"""

from datetime import UTC, datetime

from cinepipeline.adapters.base import AdapterResult
from cinepipeline.core import normalise
from cinepipeline.core.models import Screening, Version
from cinepipeline.http import client, get_json

URL = "https://www.dulaccinemas.com/api/home-bootstrap?days=14"

# Dulac cinema id -> canonical venue id
CINEMA_MAP = {
    "1": "arlequin",
    "165": "majestic-bastille",
    "422": "escurial",
    "518": "majestic-passy",
    "583": "reflet-medicis",
}

ACCESSIBILITY_FIELDS = (
    "hall_accessible",
    "audio_description_headsets_count",
    "hearing_receivers_count",
    "has_accessible_toilets",
    "staff_accessibility_level",
)

VERSION_MAP = {"VO": Version.VO, "VOST": Version.VOST, "VF": Version.VF}


def _venue_for(seance: dict, salles: dict) -> str | None:
    salle = salles.get(str(seance.get("salle_id")), {})
    return CINEMA_MAP.get(str(salle.get("cinema_id")))


def parse_bootstrap(payload: dict, fetched_at: datetime) -> list[Screening]:
    salles = payload.get("salles_by_id", {})
    films = payload.get("films_by_id", {})
    out: list[Screening] = []

    for seance in payload.get("seances_week", []):
        if seance.get("is_cancelled"):
            continue
        venue_id = _venue_for(seance, salles)
        if venue_id is None:
            continue

        film = films.get(str(seance.get("film_id")), {})
        raw_title = film.get("title") or (seance.get("title") or "").split(":")[1:2]
        if isinstance(raw_title, list):
            raw_title = raw_title[0] if raw_title else ""
        if not raw_title:
            continue

        out.append(
            Screening(
                venue_id=venue_id,
                start_utc=normalise.to_utc(seance["date"], assume="utc"),
                title_marquee=normalise.clean_title(raw_title),
                title_key=normalise.title_key(raw_title),
                version=VERSION_MAP.get(seance.get("version", ""), Version.UNKNOWN),
                source="dulac",
                fetched_at=fetched_at,
                booking_url=seance.get("booking_url") or None,
                film_key=normalise.title_key(raw_title),
                is_event=bool(seance.get("is_special") or seance.get("event_label")),
            )
        )
    return out


def extract_accessibility(payload: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for cid, cinema in payload.get("cinemas_by_id", {}).items():
        venue_id = CINEMA_MAP.get(str(cid))
        if venue_id is None:
            continue
        out[venue_id] = {f: cinema.get(f) for f in ACCESSIBILITY_FIELDS}
    return out


class DulacAdapter:
    slug = "dulac"

    def __init__(self) -> None:
        self.accessibility: dict[str, dict] = {}

    async def fetch(self) -> AdapterResult:
        fetched_at = datetime.now(UTC)
        result = AdapterResult(slug=self.slug, screenings=[])
        try:
            async with client() as c:
                payload = await get_json(c, URL)
            result.screenings = parse_bootstrap(payload, fetched_at)
            self.accessibility = extract_accessibility(payload)
            result.ok_venues = set(CINEMA_MAP.values())
        except Exception as exc:
            result.error = f"{type(exc).__name__}: {exc}"
        return result

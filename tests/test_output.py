import json
from datetime import UTC, datetime

from cinepipeline import output
from cinepipeline.adapters.base import AdapterResult
from cinepipeline.core.models import Screening, Version
from cinepipeline.metadata.tmdb import FilmMeta

NOW = datetime(2026, 8, 8, 13, 0, tzinfo=UTC)


def a_screening():
    return Screening(
        venue_id="le-champo",
        start_utc=datetime(2026, 8, 8, 18, 15, tzinfo=UTC),
        title_marquee="Playtime",
        title_key="playtime",
        version=Version.VO,
        source="allocine",
        fetched_at=NOW,
        film_key="playtime",
    )


def test_payload_has_contract_keys():
    p = output.build_payload([a_screening()], {}, [], {}, NOW)
    assert set(p) == {"generated_at", "sources", "venues", "films", "screenings"}


def test_generated_at_is_iso_utc():
    p = output.build_payload([], {}, [], {}, NOW)
    assert p["generated_at"] == "2026-08-08T13:00:00+00:00"


def test_every_catalogued_venue_is_listed():
    from cinepipeline.core import venues
    p = output.build_payload([], {}, [], {}, NOW)
    assert len(p["venues"]) == len(venues.VENUES)


def test_accessibility_attached_when_present():
    p = output.build_payload([], {}, [], {"arlequin": {"hall_accessible": True}}, NOW)
    arlequin = next(v for v in p["venues"] if v["id"] == "arlequin")
    assert arlequin["accessibility"] == {"hall_accessible": True}


def test_films_serialised():
    films = {"playtime": FilmMeta(tmdb_id=1, title_en="Playtime", runtime=124)}
    p = output.build_payload([], films, [], {}, NOW)
    assert p["films"]["playtime"]["title_en"] == "Playtime"


def test_source_status_summarised():
    r = AdapterResult(slug="allocine", screenings=[], ok_venues={"a", "b"},
                      failed_venues={"c": "boom"})
    p = output.build_payload([], {}, [r], {}, NOW)
    assert p["sources"][0] == {
        "slug": "allocine", "ok": True, "ok_venues": 2, "failed_venues": {"c": "boom"},
    }


def test_write_creates_file(tmp_path):
    p = output.build_payload([a_screening()], {}, [], {}, NOW)
    output.write(p, tmp_path)
    written = json.loads((tmp_path / "screenings.json").read_text(encoding="utf-8"))
    assert written["screenings"][0]["venue_id"] == "le-champo"

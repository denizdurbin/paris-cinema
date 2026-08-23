from datetime import UTC, datetime

from cinepipeline.__main__ import carry_forward, carry_forward_films
from cinepipeline.metadata.tmdb import FilmMeta

NOW = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)


def entry(venue, start="2026-08-08T18:15:00+00:00", fetched="2026-08-08T09:00:00+00:00"):
    return {"venue_id": venue, "start_utc": start, "title_marquee": "X",
            "film_key": "x", "version": "VO", "booking_url": None,
            "source": "allocine", "is_event": False, "fetched_at": fetched}


def test_failed_venue_entries_are_carried_forward():
    fresh = [entry("le-champo")]
    baseline = [entry("filmotheque", fetched="2026-08-08T03:00:00+00:00")]
    out = carry_forward(fresh, baseline, {"filmotheque"}, NOW)
    assert len(out) == 2
    carried = next(e for e in out if e["venue_id"] == "filmotheque")
    assert carried["fetched_at"] == "2026-08-08T03:00:00+00:00"


def test_successful_empty_venue_is_not_carried_forward():
    out = carry_forward([], [entry("le-champo")], set(), NOW)
    assert out == []


def test_fresh_data_wins_over_baseline_for_same_venue():
    fresh = [entry("le-champo", fetched="2026-08-08T12:00:00+00:00")]
    baseline = [entry("le-champo", fetched="2026-08-08T03:00:00+00:00")]
    out = carry_forward(fresh, baseline, {"le-champo"}, NOW)
    assert len(out) == 1
    assert out[0]["fetched_at"] == "2026-08-08T12:00:00+00:00"


def test_past_baseline_entries_are_not_carried_forward():
    """A failed venue must not resurrect screenings that have already started."""
    baseline = [
        entry("filmotheque", start="2026-08-08T10:00:00+00:00"),  # before NOW
        entry("filmotheque", start="2026-08-08T20:00:00+00:00"),  # after NOW
    ]
    out = carry_forward([], baseline, {"filmotheque"}, NOW)
    assert [e["start_utc"] for e in out] == ["2026-08-08T20:00:00+00:00"]


def film(tmdb_id=1234, poster="/p.jpg"):
    return {"tmdb_id": tmdb_id, "title_en": "A Film", "overview": None,
            "poster_path": poster, "backdrop_path": None, "runtime": 90,
            "year": 2020, "director": "Someone"}


def test_unmatched_film_keeps_baseline_metadata():
    out = carry_forward_films({}, {"x": film()}, ["x"], set())
    assert out["x"].tmdb_id == 1234
    assert out["x"].poster_path == "/p.jpg"


def test_fresh_match_wins_over_baseline_metadata():
    fresh = {"x": FilmMeta(tmdb_id=9999)}
    out = carry_forward_films(fresh, {"x": film()}, ["x"], set())
    assert out["x"].tmdb_id == 9999


def test_baseline_metadata_not_resurrected_when_no_longer_programmed():
    out = carry_forward_films({}, {"x": film()}, [], set())
    assert out == {}


def test_explicit_null_override_blocks_metadata_carry_forward():
    """A null override means "never match this" — the baseline must not
    smuggle the rejected film back in."""
    out = carry_forward_films({}, {"x": film()}, ["x"], {"x"})
    assert out == {}


def test_metadata_carry_forward_tolerates_malformed_baseline():
    out = carry_forward_films(
        {}, {"x": None, "y": {"poster_path": 42}}, ["x", "y"], set()
    )
    assert out == {}

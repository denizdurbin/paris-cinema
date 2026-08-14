from datetime import UTC, datetime

from cinepipeline.__main__ import carry_forward

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

from datetime import UTC, datetime

from cinepipeline.core import dedupe
from cinepipeline.core.models import Screening, Version

NOW = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)
START = datetime(2026, 8, 8, 18, 15, tzinfo=UTC)


def make(source, venue="arlequin", booking=None, title="Playtime"):
    return Screening(
        venue_id=venue,
        start_utc=START,
        title_marquee=title,
        title_key=title.lower(),
        version=Version.VO,
        source=source,
        fetched_at=NOW,
        booking_url=booking,
    )


def test_operator_wins_over_allocine():
    out = dedupe.merge([[make("allocine")], [make("dulac")]])
    assert len(out) == 1
    assert out[0].source == "dulac"


def test_different_venues_are_not_merged():
    out = dedupe.merge([[make("allocine", venue="arlequin")],
                        [make("allocine", venue="le-champo")]])
    assert len(out) == 2


def test_different_titles_at_same_slot_are_not_merged():
    out = dedupe.merge([[make("allocine", title="Playtime")],
                        [make("allocine", title="Parade")]])
    assert len(out) == 2


def test_booking_url_backfilled_from_loser():
    out = dedupe.merge([
        [make("allocine", booking="https://allocine.example/book")],
        [make("dulac", booking=None)],
    ])
    assert out[0].source == "dulac"
    assert out[0].booking_url == "https://allocine.example/book"


def test_output_sorted_by_start_then_venue():
    later = make("allocine", venue="zzz")
    later = later.model_copy(update={"start_utc": datetime(2026, 8, 8, 20, 0, tzinfo=UTC)})
    out = dedupe.merge([[later], [make("allocine", venue="aaa")]])
    assert [s.venue_id for s in out] == ["aaa", "zzz"]

import json
from datetime import UTC, datetime
from pathlib import Path

from cinepipeline.adapters import dulac

FIXTURE = Path(__file__).parent / "fixtures" / "dulac_home_bootstrap.json"
NOW = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)
PAYLOAD = json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_parses_all_seances():
    out = dulac.parse_bootstrap(PAYLOAD, NOW)
    assert len(out) == len(PAYLOAD["seances_week"])
    assert all(s.source == "dulac" for s in out)


def test_naive_utc_is_converted_not_assumed_local():
    """The Kwaidan screening is titled 10:30 and dated 08:30 with no offset."""
    out = dulac.parse_bootstrap(PAYLOAD, NOW)
    match = [s for s in out if s.start_utc == datetime(2026, 8, 8, 8, 30, tzinfo=UTC)]
    assert match, "expected the 08:30Z screening"
    assert match[0].start_paris.hour == 10
    assert match[0].start_paris.minute == 30


def test_venue_ids_are_canonical():
    out = dulac.parse_bootstrap(PAYLOAD, NOW)
    allowed = {
        "arlequin", "majestic-bastille", "escurial", "majestic-passy", "reflet-medicis",
    }
    assert {s.venue_id for s in out} <= allowed


def test_cancelled_screenings_are_dropped():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["seances_week"][0]["is_cancelled"] = True
    out = dulac.parse_bootstrap(payload, NOW)
    assert len(out) == len(payload["seances_week"]) - 1


def test_special_entries_flagged_as_events():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["seances_week"][0]["is_special"] = True
    payload["seances_week"][0]["event_label"] = "Ciné-club"
    out = dulac.parse_bootstrap(payload, NOW)
    assert any(s.is_event for s in out)


def test_accessibility_keyed_by_canonical_venue():
    acc = dulac.extract_accessibility(PAYLOAD)
    assert set(acc) == {
        "arlequin", "majestic-bastille", "escurial", "majestic-passy", "reflet-medicis",
    }
    assert "hall_accessible" in acc["arlequin"]

from datetime import UTC, datetime
from pathlib import Path

from cinepipeline.adapters import allocine
from cinepipeline.core.models import Version

FIXTURE = Path(__file__).parent / "fixtures" / "allocine_C0071.html"
NOW = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)


def test_decode_booking_url():
    token = "ACraHRACr0cHM6Ly9lY29sZXNjaW5lbWFjbHViLmNvdGVjaW5lLmZyL3IvMjM0Mjgy"
    assert allocine.decode_booking_url(token) == (
        "https://ecolescinemaclub.cotecine.fr/r/234282"
    )


def test_decode_rejects_internal_links():
    # Decodes to "/film/fichefilm-51536/critiques/spectateurs/" - not a booking URL.
    token = "ACrL2ZACrpbG0vZmljaGVmaWxtLTUxNTM2L2NyaXRpcXVlcy9zcGVjdGF0ZXVycy8="
    assert allocine.decode_booking_url(token) is None


def test_decode_returns_none_on_garbage():
    assert allocine.decode_booking_url("not-base64-at-all") is None


def test_parse_venue_page_extracts_screenings():
    html = FIXTURE.read_text(encoding="utf-8")
    out = allocine.parse_venue_page(html, "ecoles-cinema-club", NOW)
    assert len(out) > 0
    assert all(s.venue_id == "ecoles-cinema-club" for s in out)
    assert all(s.source == "allocine" for s in out)
    assert all(s.start_utc.tzinfo is not None for s in out)


def test_parse_venue_page_reads_known_showtime():
    html = FIXTURE.read_text(encoding="utf-8")
    out = allocine.parse_venue_page(html, "ecoles-cinema-club", NOW)
    at_1340 = [s for s in out if s.start_paris.strftime("%Y-%m-%d %H:%M") == "2026-08-09 13:40"]
    assert at_1340, "expected the 13:40 screening on 2026-08-09"
    s = at_1340[0]
    assert s.version is Version.VO
    assert s.booking_url == "https://ecolescinemaclub.cotecine.fr/r/234282"


def test_parse_venue_page_titles_are_populated():
    html = FIXTURE.read_text(encoding="utf-8")
    out = allocine.parse_venue_page(html, "ecoles-cinema-club", NOW)
    assert all(s.title_marquee for s in out)
    assert all(s.title_key for s in out)

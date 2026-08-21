"""Live-source shape assertions. Run daily, separately from the refresh job,
so a source redesign fails loudly instead of quietly returning fewer venues."""

import httpx
import pytest

from cinepipeline.adapters import allocine, dulac
from cinepipeline.http import USER_AGENT

pytestmark = pytest.mark.contract
HEADERS = {"User-Agent": USER_AGENT}


def test_allocine_venue_page_still_parses():
    url = allocine.BASE.format(code="C0073")  # Le Champo
    html = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=30).text
    assert 'data-showtime-time="' in html, "AlloCine showtime attribute is gone"
    assert "movie-card-theater" in html, "AlloCine film card class is gone"
    assert "meta-body-info" in html, "AlloCine release-date container is gone"
    assert "meta-body-direction" in html, "AlloCine director block is gone"


def test_allocine_booking_obfuscation_unchanged():
    url = allocine.BASE.format(code="C0071")
    html = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=30).text
    assert "ACr" in html, "AlloCine booking-URL obfuscation scheme changed"


def test_dulac_schema_version_unchanged():
    payload = httpx.get(dulac.URL, headers=HEADERS, timeout=30).json()
    assert payload["meta"]["schema_version"] == 4
    assert isinstance(payload["seances_week"], list)
    assert set(dulac.CINEMA_MAP) <= set(payload["cinemas_by_id"])


def test_dulac_dates_still_naive():
    """If Dulac starts sending offsets, our assume='utc' becomes wrong."""
    payload = httpx.get(dulac.URL, headers=HEADERS, timeout=30).json()
    sample = payload["seances_week"][0]["date"]
    assert "+" not in sample and not sample.endswith("Z"), (
        "Dulac now sends offsets - remove assume='utc' in the adapter"
    )

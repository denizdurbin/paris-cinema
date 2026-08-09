from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from cinepipeline.core import normalise
from cinepipeline.core.models import Screening, Version

PARIS = ZoneInfo("Europe/Paris")


def test_offset_aware_string_is_preserved():
    dt = normalise.to_utc("2026-08-09T20:15:00+02:00")
    assert dt == datetime(2026, 8, 9, 18, 15, tzinfo=UTC)


def test_naive_string_assumed_utc_renders_correct_paris_time():
    # Dulac emits naive UTC: this is 10:30 in Paris.
    dt = normalise.to_utc("2026-08-08T08:30:00", assume="utc")
    assert dt == datetime(2026, 8, 8, 8, 30, tzinfo=UTC)
    assert dt.astimezone(PARIS).hour == 10
    assert dt.astimezone(PARIS).minute == 30


def test_naive_string_assumed_paris():
    dt = normalise.to_utc("2026-08-08T10:30:00", assume="paris")
    assert dt == datetime(2026, 8, 8, 8, 30, tzinfo=UTC)


def test_dst_changeover_night():
    # 2026-10-25 is the European DST changeover; Paris goes +02:00 -> +01:00.
    before = normalise.to_utc("2026-10-25T01:30:00+02:00")
    after = normalise.to_utc("2026-10-25T02:30:00+01:00")
    assert before == datetime(2026, 10, 24, 23, 30, tzinfo=UTC)
    assert after == datetime(2026, 10, 25, 1, 30, tzinfo=UTC)


def test_unknown_assume_rejected():
    with pytest.raises(ValueError):
        normalise.to_utc("2026-08-08T08:30:00")


def test_clean_title_fixes_shouting():
    assert normalise.clean_title("LES VACANCES DE MR HULOT") == "Les Vacances De Mr Hulot"
    assert normalise.clean_title("Le Champo") == "Le Champo"
    assert normalise.clean_title("  Kwaïdan  ") == "Kwaïdan"


def test_title_key_is_accent_and_case_insensitive():
    assert normalise.title_key("Kwaïdan") == normalise.title_key("KWAIDAN")
    assert normalise.title_key("Les Vacances de M. Hulot") == "lesvacancesdemhulot"


def test_parse_version_from_experiences():
    assert normalise.parse_version(["Localization.Version.Original"]) is Version.VO
    assert normalise.parse_version(["Format.Projection.Digital"]) is Version.VF
    assert normalise.parse_version([]) is Version.VF


def test_screening_rejects_naive_datetime():
    with pytest.raises(ValueError):
        Screening(
            venue_id="le-champo",
            start_utc=datetime(2026, 8, 8, 20, 0),  # naive
            title_marquee="Playtime",
            title_key="playtime",
            version=Version.VO,
            source="allocine",
            fetched_at=datetime.now(UTC),
        )


def test_screening_start_paris_property():
    s = Screening(
        venue_id="le-champo",
        start_utc=datetime(2026, 8, 8, 18, 15, tzinfo=UTC),
        title_marquee="Playtime",
        title_key="playtime",
        version=Version.VO,
        source="allocine",
        fetched_at=datetime.now(UTC),
    )
    assert s.start_paris.hour == 20
    assert s.start_paris.minute == 15

import unicodedata
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Literal

from cinepipeline.core.models import PARIS, Version

Assume = Literal["utc", "paris"]


def to_utc(value: str | datetime, assume: Assume | None = None) -> datetime:
    """Parse to timezone-aware UTC.

    Offset-aware input is converted directly. Naive input REQUIRES an explicit
    `assume`, because guessing is how evening screenings end up at breakfast.
    """
    dt = datetime.fromisoformat(value) if isinstance(value, str) else value
    if dt.tzinfo is not None:
        return dt.astimezone(UTC)
    if assume == "utc":
        return dt.replace(tzinfo=UTC)
    if assume == "paris":
        return dt.replace(tzinfo=PARIS).astimezone(UTC)
    raise ValueError(f"naive datetime {dt!r} needs an explicit assume= of 'utc' or 'paris'")


def clean_title(raw: str) -> str:
    t = " ".join(raw.split())
    letters = [c for c in t if c.isalpha()]
    if letters and all(c.isupper() for c in letters):
        t = t.title()
    return t


def title_key(raw: str) -> str:
    t = unicodedata.normalize("NFKD", raw.casefold())
    return "".join(c for c in t if c.isalnum() and not unicodedata.combining(c))


def parse_version(experiences: Iterable[str]) -> Version:
    tags = set(experiences)
    if "Localization.Version.Original" in tags:
        return Version.VO
    return Version.VF

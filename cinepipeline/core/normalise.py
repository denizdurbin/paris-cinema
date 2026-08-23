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
    # NFKD has no decomposition for the Turkish dotless ı, so it survives as a
    # distinct letter: AlloCiné writes "Aydin" where TMDB writes "Aydın" and
    # the same person reads as a director mismatch. Fold it to plain i.
    t = unicodedata.normalize("NFKD", raw.casefold().replace("ı", "i"))
    return "".join(c for c in t if c.isalnum() and not unicodedata.combining(c))


def name_key(raw: str) -> str:
    """title_key plus precomposed-letter folds NFKD doesn't decompose.

    "Jānis" (ā = U+0101) NFKD-decomposes to "jaānis" — the ā stays — so the
    accent-stripping above never reaches it and "Cimmermanis" ≠ "Cimermanis".
    Fold the common precomposed vowels sources disagree about.
    """
    folded = raw.casefold().translate(
        str.maketrans({"ā": "a", "ē": "e", "ī": "i", "ō": "o", "ū": "u"})
    )
    return title_key(folded)


def parse_version(experiences: Iterable[str]) -> Version:
    tags = set(experiences)
    if "Localization.Version.Original" in tags:
        return Version.VO
    return Version.VF

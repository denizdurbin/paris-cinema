# Paris Cinema Showtimes — Data Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python pipeline that fetches showtimes for 40+ Paris cinemas from three sources, normalises and deduplicates them, enriches with TMDB metadata, and writes a static `screenings.json` consumed by the frontend.

**Architecture:** Three adapters behind one protocol — AlloCiné (primary, HTML, all venues), Dulac (JSON API, 5 venues, authoritative + accessibility), Paris Cinéma Club (WP REST, 2 venues). A hand-written venue catalogue is the single source of truth for identity. Everything normalises to timezone-aware UTC, deduplicates with operator-direct winning over AlloCiné, then enriches from TMDB at build time. Output is a single JSON file plus a venues file.

**Tech Stack:** Python 3.13, `httpx` (async), `selectolax` (HTML), `pydantic` v2, `pytest`, `pytest-asyncio`. Standard library `zoneinfo` for timezones.

This is **Plan 1 of 2**. Plan 2 covers the Vite + React frontend and Vercel deployment, written against the JSON contract defined in Task 10 here.

## Global Constraints

- Python **3.13**. Target `py313`.
- Timezone for all display/bucketing logic: **`Europe/Paris`**. All internal timestamps are **timezone-aware UTC**. Naive datetimes are a bug and must raise.
- **No secrets in code.** `TMDB_API_KEY` comes from the environment only.
- HTTP: descriptive User-Agent `paris-cinema-app/1.0 (personal project)`, concurrency cap **4**, minimum **0.3s** delay between requests to the same host, 20s timeout.
- Every adapter is **isolated**: one failing adapter, or one failing venue within AlloCiné, must never abort the run.
- Venue identity comes **only** from `core/venues.py`. Adapters map their own ids onto canonical ids; no adapter invents a venue.
- Commit after every task. Conventional commit prefixes (`feat:`, `test:`, `chore:`).

## Fixtures already in the repo

These were captured from live sources on 2026-08-08 and are committed at `tests/fixtures/`:

| File | Source | Notes |
| --- | --- | --- |
| `allocine_C0071.html` | `allocine.fr/seance/salle_gen_csalle=C0071.html` | Écoles Cinéma Club, 324 KB |
| `dulac_home_bootstrap.json` | `dulaccinemas.com/api/home-bootstrap?days=14` | 273 séances, `schema_version` 4 |
| `allocine_paris_codes.json` | `allocine.fr/salle/cinema/ville-115755/` pages 1–12 | 77 Paris theatre code→name pairs |

## Verified source facts

Established by direct inspection. Do not re-derive; do not assume anything beyond this.

**AlloCiné venue page:** `https://www.allocine.fr/seance/salle_gen_csalle={CODE}.html`

- Each screening is a `<span>` carrying `data-showtime-time`, e.g. `2026-08-09T13:40:00+02:00`
  — **offset-aware**, parse directly.
- Version lives in `data-experiences`, an HTML-escaped JSON array, e.g.
  `["Localization.Version.Original","Format.Projection.Digital"]`. `Localization.Version.Original`
  means VO. Absence means VF. Use this, **not** the French prose in `.showtimes-version .text`.
- The booking URL is obfuscated in the element's `class` attribute: take the long token,
  **remove every `ACr`**, right-pad with `=` to a multiple of 4, base64-decode.
  Verified: `ACraHRACr0cHM6Ly9lY29sZXNjaW5lbWFjbHViLmNvdGVjaW5lLmZyL3IvMjM0Mjgy`
  → `https://ecolescinemaclub.cotecine.fr/r/234282`.
  Decoded values beginning `/` are internal AlloCiné links, not booking URLs — discard them.
- Film cards are `div.movie-card-theater`; the title is in `.meta-title-link`.

**Dulac:** `https://www.dulaccinemas.com/api/home-bootstrap?days=14`

- Top-level keys: `meta`, `slides`, `seances_week`, `films_by_id`, `salles_by_id`, `cinemas_by_id`.
- `seances_week` is a flat list. Each entry: `id`, `title`, `date`, `booking_url`,
  `is_cancelled`, `is_special`, `version`, `format`, `type`, `event_label`, `film_id`, `salle_id`.
- **`date` is naive UTC.** `"date":"2026-08-08T08:30:00"` with `"title":"Reflet Medicis:Kwaïdan:08/08/2026 10:30:00"`
  is 10:30 Paris. Attach UTC, then convert. This is the single most dangerous field in the project.
- `cinemas_by_id` keys are the 5 Dulac venue ids: `1` Arlequin, `165` Majestic Bastille,
  `422` Escurial, `518` Majestic Passy, `583` Reflet Medicis. Venue name is under `title`.
- Accessibility fields live on `cinemas_by_id[*]`: `hall_accessible`,
  `audio_description_headsets_count`, `hearing_receivers_count`, `has_accessible_toilets`,
  `staff_accessibility_level`.

**Paris Cinéma Club:** `https://pariscinemaclub.com/wp-json/wp/v2/` — WordPress REST, open.
Custom post type `film` exists. Covers Écoles Cinéma Club and Le Champo.

**Venues AlloCiné does not carry** (confirmed absent from the 77-venue Paris listing and
from theatre search): Jeu de Paume, Épée de Bois, Louxor, Club de l'Étoile, Le CiNey.
These are catalogued with `allocine_code: None` and marked `coverage: "none"`. The UI must
show them as uncovered rather than pretend they have no screenings. Adding adapters for them
is explicitly out of scope for this plan.

---

## File Structure

```
pyproject.toml                     deps, pytest config, ruff
cinepipeline/
  __init__.py
  __main__.py                      CLI entry point; orchestrates and writes JSON
  http.py                          shared async client: UA, limits, retry
  core/
    __init__.py
    models.py                      Venue, Screening, Film — pydantic
    venues.py                      the canonical catalogue (data + lookup helpers)
    normalise.py                   to_utc, clean_title, parse_version
    dedupe.py                      merge screenings across sources
  adapters/
    __init__.py
    base.py                        Adapter protocol + AdapterResult
    allocine.py                    primary
    dulac.py
    paris_cinema_club.py
  metadata/
    __init__.py
    tmdb.py                        search, score, cache, overrides
  output.py                        JSON contract writer
tests/
  fixtures/                        (already committed)
  test_venues.py
  test_normalise.py
  test_allocine.py
  test_dulac.py
  test_dedupe.py
  test_tmdb.py
  test_output.py
.github/workflows/refresh.yml
.github/workflows/contract-check.yml
```

---

### Task 1: Scaffolding and the venue catalogue

**Files:**
- Create: `pyproject.toml`
- Create: `cinepipeline/__init__.py`, `cinepipeline/core/__init__.py`, `cinepipeline/adapters/__init__.py`, `cinepipeline/metadata/__init__.py`
- Create: `cinepipeline/core/venues.py`
- Test: `tests/test_venues.py`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: `Venue` dataclass with fields `id: str`, `name: str`, `arrondissement: int`,
  `kind: Literal["independent","chain"]`, `chain: str | None`, `allocine_code: str | None`,
  `coverage: Literal["allocine","operator","none"]`, `dulac_id: str | None`.
  Module-level `VENUES: tuple[Venue, ...]`, plus `by_id(vid) -> Venue`,
  `by_allocine_code(code) -> Venue | None`, `independents() -> tuple[Venue, ...]`,
  `chains() -> tuple[Venue, ...]`.

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "cinepipeline"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "httpx>=0.27",
    "selectolax>=0.3.21",
    "pydantic>=2.7",
]

[project.optional-dependencies]
dev = ["pytest>=8", "pytest-asyncio>=0.23", "ruff>=0.5"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py313"
line-length = 100
```

- [ ] **Step 2: Write the failing test**

`tests/test_venues.py`:

```python
from cinepipeline.core import venues


def test_catalogue_has_expected_counts():
    assert len(venues.independents()) == 34
    assert len(venues.chains()) >= 19


def test_ids_are_unique():
    ids = [v.id for v in venues.VENUES]
    assert len(ids) == len(set(ids))


def test_allocine_codes_are_unique_and_well_formed():
    codes = [v.allocine_code for v in venues.VENUES if v.allocine_code]
    assert len(codes) == len(set(codes))
    assert all(c.startswith("C") and c[1:].isdigit() for c in codes)


def test_five_independents_have_no_allocine_coverage():
    uncovered = {v.id for v in venues.independents() if v.coverage == "none"}
    assert uncovered == {
        "jeu-de-paume", "epee-de-bois", "louxor", "club-de-letoile", "le-ciney",
    }
    assert all(venues.by_id(v).allocine_code is None for v in uncovered)


def test_lookup_by_allocine_code():
    assert venues.by_allocine_code("C0071").id == "ecoles-cinema-club"
    assert venues.by_allocine_code("C9999") is None


def test_dulac_venues_carry_dulac_ids():
    dulac = {v.id: v.dulac_id for v in venues.VENUES if v.dulac_id}
    assert dulac == {
        "arlequin": "1",
        "majestic-bastille": "165",
        "escurial": "422",
        "majestic-passy": "518",
        "reflet-medicis": "583",
    }
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `pytest tests/test_venues.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cinepipeline'`

- [ ] **Step 4: Write `cinepipeline/core/venues.py`**

Create the empty `__init__.py` files first, then:

```python
"""Canonical venue catalogue. The single source of truth for venue identity.

Adapters map their own source ids onto these ids; no adapter invents a venue.
AlloCine codes were resolved from allocine.fr/salle/cinema/ville-115755/ on 2026-08-08.
"""

from dataclasses import dataclass
from typing import Literal

Kind = Literal["independent", "chain"]
Coverage = Literal["allocine", "operator", "none"]


@dataclass(frozen=True, slots=True)
class Venue:
    id: str
    name: str
    arrondissement: int
    kind: Kind = "independent"
    chain: str | None = None
    allocine_code: str | None = None
    coverage: Coverage = "allocine"
    dulac_id: str | None = None


def _ind(id, name, arr, code, **kw):
    return Venue(id=id, name=name, arrondissement=arr, allocine_code=code,
                 coverage="allocine" if code else "none", **kw)


def _chain(id, name, arr, chain, code):
    return Venue(id=id, name=name, arrondissement=arr, kind="chain",
                 chain=chain, allocine_code=code, coverage="allocine")


VENUES: tuple[Venue, ...] = (
    # --- independents -----------------------------------------------------
    _ind("jeu-de-paume", "Jeu de Paume", 1, None),
    _ind("luminor-hotel-de-ville", "Luminor Hôtel de Ville", 4, "C0013"),
    _ind("cinema-du-pantheon", "Cinéma du Panthéon", 5, "C0076"),
    _ind("epee-de-bois", "Épée de Bois", 5, None),
    _ind("ecoles-cinema-club", "Écoles Cinéma Club", 5, "C0071"),
    _ind("grand-action", "Le Grand Action", 5, "C0072"),
    _ind("reflet-medicis", "Reflet Médicis", 5, "C0074", dulac_id="583"),
    _ind("studio-galande", "Studio Galande", 5, "C0016"),
    _ind("studio-des-ursulines", "Studio des Ursulines", 5, "C0083"),
    _ind("le-champo", "Le Champo", 5, "C0073"),
    _ind("filmotheque", "La Filmothèque du Quartier Latin", 5, "C0020"),
    _ind("les-3-luxembourg", "Les 3 Luxembourg", 6, "C0095"),
    _ind("arlequin", "L'Arlequin", 6, "C0054", dulac_id="1"),
    _ind("christine-cinema-club", "Christine Cinéma Club", 6, "C0015"),
    _ind("lucernaire", "Lucernaire", 6, "C0093"),
    _ind("nouvel-odeon", "Nouvel Odéon", 6, "C0041"),
    _ind("saint-andre-des-arts", "Saint-André des Arts", 6, "C0100"),
    _ind("saint-germain-des-pres", "Le Saint-Germain des Prés", 6, "C0096"),
    _ind("le-balzac", "Le Balzac", 8, "C0009"),
    _ind("elysees-lincoln", "Les Elysées Lincoln", 8, "C0108"),
    _ind("cinq-caumartin", "5 Caumartin", 9, "C0012"),
    _ind("max-linder", "Max Linder Panorama", 9, "C0089"),
    _ind("archipel", "L'Archipel", 10, "C0134"),
    _ind("le-brady", "Le Brady", 10, "C0023"),
    _ind("louxor", "Louxor", 10, None),
    _ind("majestic-bastille", "Majestic Bastille", 11, "C0139", dulac_id="165"),
    _ind("escurial", "L'Escurial", 13, "C0147", dulac_id="422"),
    _ind("sept-parnassiens", "7 Parnassiens", 14, "C0025"),
    _ind("entrepot", "L'Entrepôt", 14, "C0005"),
    _ind("majestic-passy", "Majestic Passy", 16, "C0120", dulac_id="518"),
    _ind("cinema-des-cineastes", "Cinéma des Cinéastes", 17, "C0004"),
    _ind("club-de-letoile", "Club de l'Étoile", 17, None),
    _ind("le-ciney", "Le CiNey", 18, None),
    _ind("studio-28", "Studio 28", 18, "C0061"),
    # --- chains: UGC ------------------------------------------------------
    _chain("ugc-cine-cite-bercy", "UGC Ciné Cité Bercy", 12, "UGC", "C0026"),
    _chain("ugc-cine-cite-les-halles", "UGC Ciné Cité Les Halles", 1, "UGC", "C0159"),
    _chain("ugc-cine-cite-maillot", "UGC Ciné Cité Maillot", 17, "UGC", "C0175"),
    _chain("ugc-danton", "UGC Danton", 6, "UGC", "C0102"),
    _chain("ugc-gobelins", "UGC Gobelins", 13, "UGC", "C0150"),
    _chain("ugc-lyon-bastille", "UGC Lyon Bastille", 12, "UGC", "C0146"),
    _chain("ugc-montparnasse", "UGC Montparnasse", 6, "UGC", "C0103"),
    _chain("ugc-odeon", "UGC Odéon", 6, "UGC", "C0104"),
    _chain("ugc-opera", "UGC Opéra", 9, "UGC", "C0126"),
    _chain("ugc-rotonde", "UGC Rotonde", 6, "UGC", "C0105"),
    # --- chains: MK2 ------------------------------------------------------
    _chain("mk2-bastille-beaumarchais", "MK2 Bastille (Beaumarchais)", 11, "MK2", "C0140"),
    _chain("mk2-bastille-fg", "MK2 Bastille (Fg St Antoine)", 11, "MK2", "C0040"),
    _chain("mk2-beaubourg", "MK2 Beaubourg", 3, "MK2", "C0050"),
    _chain("mk2-bibliotheque", "MK2 Bibliothèque", 13, "MK2", "C2954"),
    _chain("mk2-gambetta", "MK2 Gambetta", 20, "MK2", "C0192"),
    _chain("mk2-nation", "MK2 Nation", 12, "MK2", "C0144"),
    _chain("mk2-odeon-st-germain", "MK2 Odéon (St Germain)", 6, "MK2", "C0097"),
    _chain("mk2-odeon-st-michel", "MK2 Odéon (St Michel)", 6, "MK2", "C0092"),
    _chain("mk2-quai-de-loire", "MK2 Quai de Loire", 19, "MK2", "C1621"),
    _chain("mk2-quai-de-seine", "MK2 Quai de Seine", 19, "MK2", "C0003"),
)

_BY_ID = {v.id: v for v in VENUES}
_BY_CODE = {v.allocine_code: v for v in VENUES if v.allocine_code}


def by_id(vid: str) -> Venue:
    return _BY_ID[vid]


def by_allocine_code(code: str) -> Venue | None:
    return _BY_CODE.get(code)


def independents() -> tuple[Venue, ...]:
    return tuple(v for v in VENUES if v.kind == "independent")


def chains() -> tuple[Venue, ...]:
    return tuple(v for v in VENUES if v.kind == "chain")
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `pytest tests/test_venues.py -v`
Expected: PASS, 6 tests

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml cinepipeline tests/test_venues.py
git commit -m "feat: add venue catalogue with resolved AlloCine codes"
```

---

### Task 2: Models and normalisation

**Files:**
- Create: `cinepipeline/core/models.py`
- Create: `cinepipeline/core/normalise.py`
- Test: `tests/test_normalise.py`

**Interfaces:**
- Consumes: `Venue` from Task 1.
- Produces:
  - `Screening` pydantic model: `venue_id: str`, `start_utc: datetime` (aware),
    `title_marquee: str`, `title_key: str`, `version: Version`, `source: str`,
    `booking_url: str | None`, `film_key: str | None`, `is_event: bool`,
    `fetched_at: datetime`. Property `start_paris -> datetime`.
  - `Version` enum: `VO`, `VOST`, `VF`, `UNKNOWN`.
  - `normalise.to_utc(value, assume) -> datetime`
  - `normalise.clean_title(raw) -> str`
  - `normalise.title_key(raw) -> str`
  - `normalise.parse_version(experiences) -> Version`

- [ ] **Step 1: Write the failing test**

`tests/test_normalise.py`:

```python
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from cinepipeline.core.models import Screening, Version
from cinepipeline.core import normalise

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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_normalise.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cinepipeline.core.models'`

- [ ] **Step 3: Write `cinepipeline/core/models.py`**

```python
from datetime import datetime
from enum import StrEnum
from zoneinfo import ZoneInfo

from pydantic import BaseModel, field_validator

PARIS = ZoneInfo("Europe/Paris")


class Version(StrEnum):
    VO = "VO"
    VOST = "VOST"
    VF = "VF"
    UNKNOWN = "UNKNOWN"


class Screening(BaseModel):
    venue_id: str
    start_utc: datetime
    title_marquee: str
    title_key: str
    version: Version
    source: str
    fetched_at: datetime
    booking_url: str | None = None
    film_key: str | None = None
    is_event: bool = False

    @field_validator("start_utc", "fetched_at")
    @classmethod
    def _must_be_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("datetime must be timezone-aware")
        return v

    @property
    def start_paris(self) -> datetime:
        return self.start_utc.astimezone(PARIS)

    @property
    def dedupe_key(self) -> tuple[str, datetime, str]:
        return (self.venue_id, self.start_utc, self.title_key)
```

- [ ] **Step 4: Write `cinepipeline/core/normalise.py`**

```python
import unicodedata
from datetime import UTC, datetime
from typing import Iterable, Literal

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
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_normalise.py -v`
Expected: PASS, 10 tests

- [ ] **Step 6: Commit**

```bash
git add cinepipeline/core/models.py cinepipeline/core/normalise.py tests/test_normalise.py
git commit -m "feat: add screening model and timezone-safe normalisation"
```

---

### Task 3: Adapter protocol and shared HTTP client

**Files:**
- Create: `cinepipeline/adapters/base.py`
- Create: `cinepipeline/http.py`
- Test: `tests/test_base.py`

**Interfaces:**
- Consumes: `Screening` from Task 2.
- Produces:
  - `AdapterResult` dataclass: `slug: str`, `screenings: list[Screening]`,
    `ok_venues: set[str]`, `failed_venues: dict[str, str]`, `error: str | None`.
    Property `ok: bool` — true when `error is None`.
  - `Adapter` protocol with `slug: str` and `async fetch() -> AdapterResult`.
  - `http.client()` async context manager yielding a configured `httpx.AsyncClient`.
  - `http.GATE` — `asyncio.Semaphore(4)`.

- [ ] **Step 1: Write the failing test**

`tests/test_base.py`:

```python
from cinepipeline.adapters.base import AdapterResult


def test_result_ok_when_no_error():
    r = AdapterResult(slug="allocine", screenings=[], ok_venues={"le-champo"})
    assert r.ok is True


def test_result_not_ok_when_error():
    r = AdapterResult(slug="dulac", screenings=[], error="boom")
    assert r.ok is False


def test_failed_venues_default_empty():
    r = AdapterResult(slug="allocine", screenings=[])
    assert r.failed_venues == {}
    assert r.ok_venues == set()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_base.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `cinepipeline/http.py`**

```python
import asyncio
from contextlib import asynccontextmanager

import httpx

USER_AGENT = "paris-cinema-app/1.0 (personal project)"
TIMEOUT = 20.0
MAX_CONCURRENCY = 4
MIN_DELAY = 0.3

GATE = asyncio.Semaphore(MAX_CONCURRENCY)


@asynccontextmanager
async def client():
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT, "Accept-Language": "fr-FR,fr;q=0.9"},
        timeout=TIMEOUT,
        follow_redirects=True,
    ) as c:
        yield c


async def get_text(c: httpx.AsyncClient, url: str) -> str:
    async with GATE:
        resp = await c.get(url)
        await asyncio.sleep(MIN_DELAY)
    resp.raise_for_status()
    return resp.text


async def get_json(c: httpx.AsyncClient, url: str):
    async with GATE:
        resp = await c.get(url)
        await asyncio.sleep(MIN_DELAY)
    resp.raise_for_status()
    return resp.json()
```

- [ ] **Step 4: Write `cinepipeline/adapters/base.py`**

```python
from dataclasses import dataclass, field
from typing import Protocol

from cinepipeline.core.models import Screening


@dataclass(slots=True)
class AdapterResult:
    slug: str
    screenings: list[Screening]
    ok_venues: set[str] = field(default_factory=set)
    failed_venues: dict[str, str] = field(default_factory=dict)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class Adapter(Protocol):
    slug: str

    async def fetch(self) -> AdapterResult: ...
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `pytest tests/test_base.py -v`
Expected: PASS, 3 tests

- [ ] **Step 6: Commit**

```bash
git add cinepipeline/http.py cinepipeline/adapters/base.py tests/test_base.py
git commit -m "feat: add adapter protocol and shared http client"
```

---

### Task 4: AlloCiné adapter

**Files:**
- Create: `cinepipeline/adapters/allocine.py`
- Test: `tests/test_allocine.py`

**Interfaces:**
- Consumes: `AdapterResult` (Task 3), `Screening`/`Version` (Task 2), `venues` (Task 1),
  `normalise.to_utc`/`clean_title`/`title_key`/`parse_version` (Task 2).
- Produces:
  - `decode_booking_url(class_attr: str) -> str | None`
  - `parse_venue_page(html: str, venue_id: str, fetched_at: datetime) -> list[Screening]`
  - `AllocineAdapter` class with `slug = "allocine"` and `async fetch()`.

- [ ] **Step 1: Write the failing test**

`tests/test_allocine.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_allocine.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cinepipeline.adapters.allocine'`

- [ ] **Step 3: Write `cinepipeline/adapters/allocine.py`**

```python
"""AlloCine adapter - primary source, covers every catalogued venue with a code.

Page: https://www.allocine.fr/seance/salle_gen_csalle={CODE}.html
Showtimes carry offset-aware `data-showtime-time`, so no timezone guessing.
Booking URLs are base64 hidden inside the class attribute with `ACr` noise.
"""

import base64
import binascii
import json
from datetime import datetime

from selectolax.parser import HTMLParser

from cinepipeline.adapters.base import AdapterResult
from cinepipeline.core import normalise, venues
from cinepipeline.core.models import Screening
from cinepipeline.http import client, get_text

BASE = "https://www.allocine.fr/seance/salle_gen_csalle={code}.html"


def decode_booking_url(class_attr: str) -> str | None:
    """Strip the `ACr` noise, base64-decode, keep only absolute http(s) URLs."""
    for token in class_attr.split():
        if "ACr" not in token:
            continue
        raw = token.replace("ACr", "")
        raw += "=" * (-len(raw) % 4)
        try:
            decoded = base64.b64decode(raw).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            continue
        if decoded.startswith(("http://", "https://")):
            return decoded
    return None


def parse_venue_page(html: str, venue_id: str, fetched_at: datetime) -> list[Screening]:
    tree = HTMLParser(html)
    out: list[Screening] = []

    for card in tree.css("div.movie-card-theater"):
        title_node = card.css_first(".meta-title-link")
        if title_node is None:
            continue
        raw_title = title_node.text(strip=True)
        if not raw_title:
            continue
        marquee = normalise.clean_title(raw_title)
        key = normalise.title_key(raw_title)

        for item in card.css("[data-showtime-time]"):
            stamp = item.attributes.get("data-showtime-time")
            if not stamp:
                continue
            try:
                start = normalise.to_utc(stamp)
            except ValueError:
                continue

            try:
                experiences = json.loads(item.attributes.get("data-experiences") or "[]")
            except json.JSONDecodeError:
                experiences = []

            out.append(
                Screening(
                    venue_id=venue_id,
                    start_utc=start,
                    title_marquee=marquee,
                    title_key=key,
                    version=normalise.parse_version(experiences),
                    source="allocine",
                    fetched_at=fetched_at,
                    booking_url=decode_booking_url(item.attributes.get("class") or ""),
                    film_key=key,
                )
            )
    return out


class AllocineAdapter:
    slug = "allocine"

    async def fetch(self) -> AdapterResult:
        fetched_at = datetime.now(tz=__import__("datetime").UTC)
        result = AdapterResult(slug=self.slug, screenings=[])
        targets = [v for v in venues.VENUES if v.allocine_code]

        try:
            async with client() as c:
                for venue in targets:
                    url = BASE.format(code=venue.allocine_code)
                    try:
                        html = await get_text(c, url)
                        result.screenings.extend(
                            parse_venue_page(html, venue.id, fetched_at)
                        )
                        result.ok_venues.add(venue.id)
                    except Exception as exc:  # per-venue isolation
                        result.failed_venues[venue.id] = f"{type(exc).__name__}: {exc}"
        except Exception as exc:
            result.error = f"{type(exc).__name__}: {exc}"

        return result
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_allocine.py -v`
Expected: PASS, 6 tests

- [ ] **Step 5: Sanity-check against the live site once**

Run:

```bash
python -c "import asyncio,datetime as d; from cinepipeline.adapters.allocine import *; import httpx; print(len(parse_venue_page(httpx.get(BASE.format(code='C0073'), headers={'User-Agent':'paris-cinema-app/1.0 (personal project)'}, follow_redirects=True).text, 'le-champo', d.datetime.now(d.UTC))), 'screenings at Le Champo')"
```

Expected: a non-zero count. If zero, the markup has changed — stop and inspect before continuing.

- [ ] **Step 6: Commit**

```bash
git add cinepipeline/adapters/allocine.py tests/test_allocine.py
git commit -m "feat: add AlloCine adapter with per-venue isolation"
```

---

### Task 5: Dulac adapter

**Files:**
- Create: `cinepipeline/adapters/dulac.py`
- Test: `tests/test_dulac.py`

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces:
  - `parse_bootstrap(payload: dict, fetched_at: datetime) -> list[Screening]`
  - `extract_accessibility(payload: dict) -> dict[str, dict]` keyed by canonical venue id.
  - `DulacAdapter` with `slug = "dulac"` and `async fetch()`.

- [ ] **Step 1: Write the failing test**

`tests/test_dulac.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_dulac.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `cinepipeline/adapters/dulac.py`**

```python
"""Dulac Cinemas adapter - authoritative for its five venues.

WARNING: `date` in seances_week is NAIVE UTC. "2026-08-08T08:30:00" is 10:30 Paris.
"""

from datetime import UTC, datetime

from cinepipeline.adapters.base import AdapterResult
from cinepipeline.core import normalise
from cinepipeline.core.models import Screening, Version
from cinepipeline.http import client, get_json

URL = "https://www.dulaccinemas.com/api/home-bootstrap?days=14"

# Dulac cinema id -> canonical venue id
CINEMA_MAP = {
    "1": "arlequin",
    "165": "majestic-bastille",
    "422": "escurial",
    "518": "majestic-passy",
    "583": "reflet-medicis",
}

ACCESSIBILITY_FIELDS = (
    "hall_accessible",
    "audio_description_headsets_count",
    "hearing_receivers_count",
    "has_accessible_toilets",
    "staff_accessibility_level",
)

VERSION_MAP = {"VO": Version.VO, "VOST": Version.VOST, "VF": Version.VF}


def _venue_for(seance: dict, salles: dict) -> str | None:
    salle = salles.get(str(seance.get("salle_id")), {})
    return CINEMA_MAP.get(str(salle.get("cinema_id")))


def parse_bootstrap(payload: dict, fetched_at: datetime) -> list[Screening]:
    salles = payload.get("salles_by_id", {})
    films = payload.get("films_by_id", {})
    out: list[Screening] = []

    for seance in payload.get("seances_week", []):
        if seance.get("is_cancelled"):
            continue
        venue_id = _venue_for(seance, salles)
        if venue_id is None:
            continue

        film = films.get(str(seance.get("film_id")), {})
        raw_title = film.get("title") or (seance.get("title") or "").split(":")[1:2]
        if isinstance(raw_title, list):
            raw_title = raw_title[0] if raw_title else ""
        if not raw_title:
            continue

        out.append(
            Screening(
                venue_id=venue_id,
                start_utc=normalise.to_utc(seance["date"], assume="utc"),
                title_marquee=normalise.clean_title(raw_title),
                title_key=normalise.title_key(raw_title),
                version=VERSION_MAP.get(seance.get("version", ""), Version.UNKNOWN),
                source="dulac",
                fetched_at=fetched_at,
                booking_url=seance.get("booking_url") or None,
                film_key=normalise.title_key(raw_title),
                is_event=bool(seance.get("is_special") or seance.get("event_label")),
            )
        )
    return out


def extract_accessibility(payload: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for cid, cinema in payload.get("cinemas_by_id", {}).items():
        venue_id = CINEMA_MAP.get(str(cid))
        if venue_id is None:
            continue
        out[venue_id] = {f: cinema.get(f) for f in ACCESSIBILITY_FIELDS}
    return out


class DulacAdapter:
    slug = "dulac"

    def __init__(self) -> None:
        self.accessibility: dict[str, dict] = {}

    async def fetch(self) -> AdapterResult:
        fetched_at = datetime.now(UTC)
        result = AdapterResult(slug=self.slug, screenings=[])
        try:
            async with client() as c:
                payload = await get_json(c, URL)
            result.screenings = parse_bootstrap(payload, fetched_at)
            self.accessibility = extract_accessibility(payload)
            result.ok_venues = set(CINEMA_MAP.values())
        except Exception as exc:
            result.error = f"{type(exc).__name__}: {exc}"
        return result
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_dulac.py -v`
Expected: PASS, 6 tests

- [ ] **Step 5: Commit**

```bash
git add cinepipeline/adapters/dulac.py tests/test_dulac.py
git commit -m "feat: add Dulac adapter handling naive-UTC timestamps"
```

---

### Task 6: Deduplication

**Files:**
- Create: `cinepipeline/core/dedupe.py`
- Test: `tests/test_dedupe.py`

**Interfaces:**
- Consumes: `Screening` (Task 2).
- Produces: `merge(groups: list[list[Screening]]) -> list[Screening]` and
  `SOURCE_PRIORITY: dict[str, int]` (lower wins).

- [ ] **Step 1: Write the failing test**

`tests/test_dedupe.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_dedupe.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `cinepipeline/core/dedupe.py`**

```python
"""Merge screenings across sources.

AlloCine covers every venue, so it overlaps the operator feeds. The operator is
authoritative for its own listings, so it wins - but we keep any booking URL the
loser had, since AlloCine sometimes has one where the operator does not.
"""

from cinepipeline.core.models import Screening

SOURCE_PRIORITY: dict[str, int] = {
    "dulac": 0,
    "paris_cinema_club": 0,
    "allocine": 10,
}


def _rank(s: Screening) -> int:
    return SOURCE_PRIORITY.get(s.source, 99)


def merge(groups: list[list[Screening]]) -> list[Screening]:
    best: dict[tuple, Screening] = {}
    for group in groups:
        for s in group:
            key = s.dedupe_key
            incumbent = best.get(key)
            if incumbent is None:
                best[key] = s
                continue
            winner, loser = (s, incumbent) if _rank(s) < _rank(incumbent) else (incumbent, s)
            if winner.booking_url is None and loser.booking_url is not None:
                winner = winner.model_copy(update={"booking_url": loser.booking_url})
            best[key] = winner

    return sorted(best.values(), key=lambda s: (s.start_utc, s.venue_id, s.title_key))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_dedupe.py -v`
Expected: PASS, 5 tests

- [ ] **Step 5: Commit**

```bash
git add cinepipeline/core/dedupe.py tests/test_dedupe.py
git commit -m "feat: add cross-source deduplication with operator priority"
```

---

### Task 7: TMDB enrichment

**Files:**
- Create: `cinepipeline/metadata/tmdb.py`
- Create: `tmdb_overrides.json` (repo root, hand-editable)
- Test: `tests/test_tmdb.py`

**Interfaces:**
- Consumes: `normalise.title_key` (Task 2).
- Produces:
  - `FilmMeta` pydantic model: `title_en: str | None`, `overview: str | None`,
    `poster_path: str | None`, `backdrop_path: str | None`, `tmdb_id: int | None`,
    `runtime: int | None`, `year: int | None`.
  - `score_candidate(candidate: dict, title: str, runtime_min: int | None) -> float`
  - `pick_best(candidates: list[dict], title: str, runtime_min: int | None) -> dict | None`
  - `load_overrides(path) -> dict[str, int | None]`
  - `TMDBClient` with `async enrich(title_keys) -> dict[str, FilmMeta]`

The score threshold is **0.55**; below that, no match.

- [ ] **Step 1: Write the failing test**

`tests/test_tmdb.py`:

```python
import json

from cinepipeline.metadata import tmdb


def cand(title, year=None, orig=None):
    return {"title": title, "original_title": orig or title,
            "release_date": f"{year}-01-01" if year else "", "id": 1}


def test_exact_title_scores_high():
    assert tmdb.score_candidate(cand("Playtime"), "Playtime", None) > 0.9


def test_unrelated_title_scores_low():
    assert tmdb.score_candidate(cand("Jaws"), "Playtime", None) < 0.4


def test_accent_and_case_insensitive():
    assert tmdb.score_candidate(cand("Kwaïdan"), "KWAIDAN", None) > 0.9


def test_pick_best_returns_none_below_threshold():
    assert tmdb.pick_best([cand("Jaws"), cand("Alien")], "Playtime", None) is None


def test_pick_best_prefers_closer_title():
    out = tmdb.pick_best([cand("Play Time 2"), cand("Playtime")], "Playtime", None)
    assert out["title"] == "Playtime"


def test_overrides_round_trip(tmp_path):
    p = tmp_path / "ov.json"
    p.write_text(json.dumps({"playtime": 1234, "someevent": None}), encoding="utf-8")
    ov = tmdb.load_overrides(p)
    assert ov["playtime"] == 1234
    assert ov["someevent"] is None


def test_missing_overrides_file_is_empty(tmp_path):
    assert tmdb.load_overrides(tmp_path / "nope.json") == {}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_tmdb.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create `tmdb_overrides.json` at the repo root**

```json
{}
```

- [ ] **Step 4: Write `cinepipeline/metadata/tmdb.py`**

```python
"""TMDB enrichment.

Search in fr-FR (sources carry French release titles), read en-US for display.
Score candidates on title similarity plus runtime and year agreement; heritage
programming is full of same-title remakes and restorations.
"""

import json
import os
from difflib import SequenceMatcher
from pathlib import Path

from pydantic import BaseModel

from cinepipeline.core.normalise import title_key
from cinepipeline.http import client, get_json

API = "https://api.themoviedb.org/3"
THRESHOLD = 0.55
OVERRIDES_PATH = Path("tmdb_overrides.json")


class FilmMeta(BaseModel):
    tmdb_id: int | None = None
    title_en: str | None = None
    overview: str | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    runtime: int | None = None
    year: int | None = None


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, title_key(a), title_key(b)).ratio()


def score_candidate(candidate: dict, title: str, runtime_min: int | None) -> float:
    best_title = max(
        _similarity(candidate.get("title") or "", title),
        _similarity(candidate.get("original_title") or "", title),
    )
    score = best_title
    if runtime_min and candidate.get("runtime"):
        delta = abs(candidate["runtime"] - runtime_min)
        score += 0.10 if delta <= 3 else (-0.15 if delta > 15 else 0.0)
    return max(0.0, min(1.0, score))


def pick_best(candidates: list[dict], title: str, runtime_min: int | None) -> dict | None:
    if not candidates:
        return None
    ranked = sorted(
        candidates, key=lambda c: score_candidate(c, title, runtime_min), reverse=True
    )
    top = ranked[0]
    return top if score_candidate(top, title, runtime_min) >= THRESHOLD else None


def load_overrides(path: Path = OVERRIDES_PATH) -> dict[str, int | None]:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


class TMDBClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("TMDB_API_KEY", "")
        self.overrides = load_overrides()
        self.unmatched: list[str] = []

    async def enrich(self, titles: dict[str, str]) -> dict[str, FilmMeta]:
        """titles maps title_key -> display title. Never raises; degrades to {}."""
        if not self.api_key:
            return {}
        out: dict[str, FilmMeta] = {}
        try:
            async with client() as c:
                for key, display in titles.items():
                    if key in self.overrides and self.overrides[key] is None:
                        continue
                    forced = self.overrides.get(key)
                    try:
                        if forced:
                            detail = await get_json(
                                c, f"{API}/movie/{forced}?api_key={self.api_key}&language=en-US"
                            )
                        else:
                            found = await get_json(
                                c,
                                f"{API}/search/movie?api_key={self.api_key}"
                                f"&language=fr-FR&query={display}",
                            )
                            best = pick_best(found.get("results", []), display, None)
                            if best is None:
                                self.unmatched.append(display)
                                continue
                            detail = await get_json(
                                c,
                                f"{API}/movie/{best['id']}?api_key={self.api_key}"
                                "&language=en-US",
                            )
                        out[key] = FilmMeta(
                            tmdb_id=detail.get("id"),
                            title_en=detail.get("title"),
                            overview=detail.get("overview"),
                            poster_path=detail.get("poster_path"),
                            backdrop_path=detail.get("backdrop_path"),
                            runtime=detail.get("runtime"),
                            year=int((detail.get("release_date") or "0")[:4] or 0) or None,
                        )
                    except Exception:
                        self.unmatched.append(display)
        except Exception:
            return out
        return out
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_tmdb.py -v`
Expected: PASS, 7 tests

- [ ] **Step 6: Commit**

```bash
git add cinepipeline/metadata/tmdb.py tmdb_overrides.json tests/test_tmdb.py
git commit -m "feat: add TMDB enrichment with scoring and manual overrides"
```

---

### Task 8: Output contract

**Files:**
- Create: `cinepipeline/output.py`
- Test: `tests/test_output.py`

**Interfaces:**
- Consumes: `Screening` (Task 2), `Venue`/`venues` (Task 1), `FilmMeta` (Task 7),
  `AdapterResult` (Task 3).
- Produces: `build_payload(screenings, films, results, accessibility, generated_at) -> dict`
  and `write(payload, out_dir: Path) -> None`.

**This dict is the contract Plan 2 consumes.** Shape:

```json
{
  "generated_at": "2026-08-08T13:00:00+00:00",
  "sources": [{"slug":"allocine","ok":true,"ok_venues":33,"failed_venues":{}}],
  "venues": [{"id":"le-champo","name":"Le Champo","arrondissement":5,
              "kind":"independent","chain":null,"coverage":"allocine",
              "accessibility":null}],
  "films": {"playtime": {"tmdb_id":1, "title_en":"Playtime", "overview":"...",
                          "poster_path":"/x.jpg","backdrop_path":null,
                          "runtime":124,"year":1967}},
  "screenings": [{"venue_id":"le-champo","start_utc":"2026-08-08T18:15:00+00:00",
                  "title_marquee":"Playtime","film_key":"playtime","version":"VO",
                  "booking_url":"https://...","source":"allocine",
                  "is_event":false,"fetched_at":"2026-08-08T13:00:00+00:00"}]
}
```

- [ ] **Step 1: Write the failing test**

`tests/test_output.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_output.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cinepipeline.output'`

- [ ] **Step 3: Write `cinepipeline/output.py`**

```python
"""The JSON contract consumed by the frontend."""

import json
from datetime import datetime
from pathlib import Path

from cinepipeline.adapters.base import AdapterResult
from cinepipeline.core import venues
from cinepipeline.core.models import Screening
from cinepipeline.metadata.tmdb import FilmMeta


def build_payload(
    screenings: list[Screening],
    films: dict[str, FilmMeta],
    results: list[AdapterResult],
    accessibility: dict[str, dict],
    generated_at: datetime,
) -> dict:
    return {
        "generated_at": generated_at.isoformat(),
        "sources": [
            {
                "slug": r.slug,
                "ok": r.ok,
                "ok_venues": len(r.ok_venues),
                "failed_venues": r.failed_venues,
            }
            for r in results
        ],
        "venues": [
            {
                "id": v.id,
                "name": v.name,
                "arrondissement": v.arrondissement,
                "kind": v.kind,
                "chain": v.chain,
                "coverage": v.coverage,
                "accessibility": accessibility.get(v.id),
            }
            for v in venues.VENUES
        ],
        "films": {k: m.model_dump() for k, m in films.items()},
        "screenings": [
            {
                "venue_id": s.venue_id,
                "start_utc": s.start_utc.isoformat(),
                "title_marquee": s.title_marquee,
                "film_key": s.film_key,
                "version": str(s.version),
                "booking_url": s.booking_url,
                "source": s.source,
                "is_event": s.is_event,
                "fetched_at": s.fetched_at.isoformat(),
            }
            for s in screenings
        ],
    }


def write(payload: dict, out_dir: Path) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "screenings.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_output.py -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Commit**

```bash
git add cinepipeline/output.py tests/test_output.py
git commit -m "feat: add JSON output contract"
```

---

### Task 9: Pipeline orchestration with stale carry-forward

**Files:**
- Create: `cinepipeline/__main__.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `carry_forward(fresh, baseline, failed_venue_ids) -> list[dict]` and
  `async run(out_dir, baseline_url) -> int` (process exit code).

Carry-forward rule: for any venue that produced no fresh screenings **and** is listed as
failed, reuse that venue's entries from the baseline payload unchanged (keeping their
original `fetched_at`). Never carry forward a venue that succeeded — an empty successful
result legitimately means "nothing on".

- [ ] **Step 1: Write the failing test**

`tests/test_pipeline.py`:

```python
from cinepipeline.__main__ import carry_forward


def entry(venue, start="2026-08-08T18:15:00+00:00", fetched="2026-08-08T09:00:00+00:00"):
    return {"venue_id": venue, "start_utc": start, "title_marquee": "X",
            "film_key": "x", "version": "VO", "booking_url": None,
            "source": "allocine", "is_event": False, "fetched_at": fetched}


def test_failed_venue_entries_are_carried_forward():
    fresh = [entry("le-champo")]
    baseline = [entry("filmotheque", fetched="2026-08-08T03:00:00+00:00")]
    out = carry_forward(fresh, baseline, {"filmotheque"})
    assert len(out) == 2
    carried = next(e for e in out if e["venue_id"] == "filmotheque")
    assert carried["fetched_at"] == "2026-08-08T03:00:00+00:00"


def test_successful_empty_venue_is_not_carried_forward():
    out = carry_forward([], [entry("le-champo")], set())
    assert out == []


def test_fresh_data_wins_over_baseline_for_same_venue():
    fresh = [entry("le-champo", fetched="2026-08-08T12:00:00+00:00")]
    baseline = [entry("le-champo", fetched="2026-08-08T03:00:00+00:00")]
    out = carry_forward(fresh, baseline, {"le-champo"})
    assert len(out) == 1
    assert out[0]["fetched_at"] == "2026-08-08T12:00:00+00:00"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL — `ImportError: cannot import name 'carry_forward'`

- [ ] **Step 3: Write `cinepipeline/__main__.py`**

```python
"""Entry point. Fetches, merges, enriches and writes the static payload.

The deployed site is the snapshot store: we fetch the live screenings.json as a
baseline so a failing source degrades to its previous data rather than vanishing.
"""

import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

from cinepipeline import output
from cinepipeline.adapters.allocine import AllocineAdapter
from cinepipeline.adapters.dulac import DulacAdapter
from cinepipeline.core import dedupe
from cinepipeline.metadata.tmdb import TMDBClient

DEFAULT_OUT = Path("web/public/data")
BASELINE_URL = os.environ.get(
    "BASELINE_URL", "https://paris-cinema.vercel.app/data/screenings.json"
)


def carry_forward(fresh: list[dict], baseline: list[dict], failed: set[str]) -> list[dict]:
    fresh_venues = {e["venue_id"] for e in fresh}
    carried = [
        e for e in baseline if e["venue_id"] in failed and e["venue_id"] not in fresh_venues
    ]
    return fresh + carried


def _load_baseline(url: str) -> dict:
    try:
        r = httpx.get(url, timeout=15.0, follow_redirects=True)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


async def run(out_dir: Path = DEFAULT_OUT, baseline_url: str = BASELINE_URL) -> int:
    generated_at = datetime.now(UTC)
    baseline = _load_baseline(baseline_url)

    allocine, dulac = AllocineAdapter(), DulacAdapter()
    results = await asyncio.gather(
        allocine.fetch(), dulac.fetch(), return_exceptions=False
    )

    if all(not r.ok for r in results):
        print("ERROR: every adapter failed; refusing to deploy", file=sys.stderr)
        return 1

    merged = dedupe.merge([r.screenings for r in results])
    titles = {s.film_key: s.title_marquee for s in merged if s.film_key and not s.is_event}
    films = await TMDBClient().enrich(titles)

    payload = output.build_payload(
        merged, films, list(results), dulac.accessibility, generated_at
    )

    failed = {v for r in results for v in r.failed_venues}
    payload["screenings"] = carry_forward(
        payload["screenings"], baseline.get("screenings", []), failed
    )

    output.write(payload, out_dir)
    print(
        f"wrote {len(payload['screenings'])} screenings, "
        f"{len(payload['films'])} films, {len(failed)} failed venues"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_pipeline.py -v`
Expected: PASS, 3 tests

- [ ] **Step 5: Run the whole suite**

Run: `pytest -v`
Expected: PASS, all tests across all files

- [ ] **Step 6: Run the pipeline for real**

Run: `python -m cinepipeline`
Expected: a line like `wrote NNNN screenings, NNN films, 0 failed venues`, and
`web/public/data/screenings.json` on disk. Without `TMDB_API_KEY` set, films will be 0 —
that is correct degradation, not a failure.

- [ ] **Step 7: Commit**

```bash
git add cinepipeline/__main__.py tests/test_pipeline.py
git commit -m "feat: add pipeline orchestration with stale carry-forward"
```

---

### Task 10: GitHub Actions workflows

**Files:**
- Create: `.github/workflows/refresh.yml`
- Create: `.github/workflows/contract-check.yml`
- Create: `tests/test_contract.py`

**Interfaces:**
- Consumes: `python -m cinepipeline` (Task 9), adapters (Tasks 4–5).
- Produces: no Python interfaces. `contract-check.yml` runs `pytest -m contract`.

- [ ] **Step 1: Add the contract marker to `pyproject.toml`**

Append under `[tool.pytest.ini_options]`:

```toml
markers = ["contract: hits live sources; excluded from the default run"]
addopts = "-m 'not contract'"
```

- [ ] **Step 2: Write `tests/test_contract.py`**

```python
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
```

- [ ] **Step 3: Run the contract tests once by hand**

Run: `pytest -m contract -v`
Expected: PASS, 4 tests. A failure here means a source changed and the adapter needs work.

- [ ] **Step 4: Write `.github/workflows/refresh.yml`**

```yaml
name: refresh
on:
  schedule:
    - cron: '5 7-21 * * *'
  workflow_dispatch:
  push:
    branches: [main]

concurrency:
  group: refresh
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: pip install -e .
      - run: python -m cinepipeline
        env:
          TMDB_API_KEY: ${{ secrets.TMDB_API_KEY }}
          BASELINE_URL: ${{ vars.BASELINE_URL }}
      - uses: actions/upload-artifact@v4
        with:
          name: screenings
          path: web/public/data/screenings.json
```

The Vercel deploy step is added in Plan 2, once `web/` exists.

- [ ] **Step 5: Write `.github/workflows/contract-check.yml`**

```yaml
name: contract-check
on:
  schedule:
    - cron: '20 6 * * *'
  workflow_dispatch:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: pip install -e ".[dev]"
      - run: pytest -m contract -v
```

- [ ] **Step 6: Commit**

```bash
git add .github pyproject.toml tests/test_contract.py
git commit -m "ci: add hourly refresh and daily source contract check"
```

---

## Deferred to Plan 2

- Vite + React frontend (Now band, today, week, cinemas + search, chains, film detail)
- Vercel deploy step appended to `refresh.yml`
- Paris Cinéma Club adapter — AlloCiné already covers Écoles and Le Champo, so it adds
  authority rather than coverage. Its `SOURCE_PRIORITY` entry already exists.
- Adapters for the five uncovered venues (Jeu de Paume, Épée de Bois, Louxor,
  Club de l'Étoile, Le CiNey)

## Self-Review Notes

**Spec coverage.** Every spec section maps to a task: catalogue and chain separation → 1;
timezone and title rules → 2; adapter isolation → 3, 4, 5; dedup with operator priority → 6;
TMDB with scoring, overrides and graceful degradation → 7; JSON contract and freshness
stamp → 8; stale carry-forward and all-fail abort → 9; cron cadence, politeness and the
contract check → 10. Screens are Plan 2 by design.

**Known deviation from the spec.** The spec lists three adapters; this plan ships two, with
Paris Cinéma Club deferred. AlloCiné already covers both of its venues, so it is pure
redundancy for v1 and its absence blocks nothing. `SOURCE_PRIORITY` already contains its
slug so adding it later needs no changes elsewhere.

**Interface consistency.** `title_key` is a function in `normalise` and a field on
`Screening`; `film_key` on `Screening` is deliberately the same value, kept separate so a
future TMDB id can replace it without touching dedup. `AdapterResult.ok_venues` is a
`set[str]` internally and serialised as a count in the payload.

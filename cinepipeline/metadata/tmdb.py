"""TMDB enrichment.

Search in fr-FR (sources carry French release titles), read en-US for display.
Score candidates on title similarity plus runtime and year agreement; heritage
programming is full of same-title remakes and restorations.
"""

import asyncio
import json
import os
import re
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote

import httpx
from pydantic import BaseModel

from cinepipeline.core.normalise import name_key, title_key
from cinepipeline.http import client, get_json

API = "https://api.themoviedb.org/3"
THRESHOLD = 0.55
OVERRIDES_PATH = Path("tmdb_overrides.json")
RETRY_ATTEMPTS = 3
RETRY_BACKOFF = 1.0


async def _get_json_retried(c, url: str) -> dict:
    """One transient TMDB error must not strip a film's poster for a whole run:
    retry with backoff. A 404 is a real answer (bad override id), not transient.
    """
    for attempt in range(RETRY_ATTEMPTS):
        try:
            return await get_json(c, url)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404 or attempt == RETRY_ATTEMPTS - 1:
                raise
        except httpx.HTTPError:
            if attempt == RETRY_ATTEMPTS - 1:
                raise
        await asyncio.sleep(RETRY_BACKOFF * (attempt + 1))
    raise AssertionError("unreachable")


class FilmMeta(BaseModel):
    tmdb_id: int | None = None
    title_en: str | None = None
    overview: str | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    runtime: int | None = None
    year: int | None = None
    director: str | None = None


def director_of(detail: dict) -> str | None:
    """Director name(s) from a detail payload fetched with append_to_response=credits."""
    crew = (detail.get("credits") or {}).get("crew") or []
    names = [m["name"] for m in crew if m.get("job") == "Director" and m.get("name")]
    return ", ".join(names) or None


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, title_key(a), title_key(b)).ratio()


def score_candidate(
    candidate: dict,
    title: str,
    runtime_min: int | None,
    *,
    year: int | None = None,
) -> float:
    best_title = max(
        _similarity(candidate.get("title") or "", title),
        _similarity(candidate.get("original_title") or "", title),
    )
    score = best_title
    if runtime_min and candidate.get("runtime"):
        delta = abs(candidate["runtime"] - runtime_min)
        score += 0.10 if delta <= 3 else (-0.15 if delta > 15 else 0.0)
    if year and candidate.get("release_date"):
        try:
            delta = abs(int(candidate["release_date"][:4]) - year)
        except (TypeError, ValueError):
            delta = None
        if delta is not None:
            # AlloCiné gives the French release date, TMDB the earliest one, so
            # a foreign film can legitimately sit a few years apart.
            score += 0.15 if delta <= 1 else (0.0 if delta <= 3 else -0.50)
    # No upper clamp: collapsing every strong match to exactly 1.000 makes ties
    # fall through to TMDB's popularity ordering.
    return max(0.0, score)


def pick_best(
    candidates: list[dict],
    title: str,
    runtime_min: int | None,
    *,
    year: int | None = None,
) -> dict | None:
    if not candidates:
        return None
    ranked = sorted(
        candidates,
        key=lambda c: score_candidate(c, title, runtime_min, year=year),
        reverse=True,
    )
    top = ranked[0]
    return top if score_candidate(top, title, runtime_min, year=year) >= THRESHOLD else None


def _name_set(names: str | None) -> set[str]:
    return {name_key(n) for n in (names or "").split(",") if name_key(n)}


def _segments(raw: str) -> list[str]:
    """Normalised segments of one name, e.g. "G.W. Pabst" -> ["g", "w", "pabst"]."""
    return [k for p in re.split(r"[\s.]+", raw) if p and (k := name_key(p))]


def _names_compatible(hint: str, actual: str) -> bool:
    """True when two single names could refer to the same person.

    Sources routinely disagree on *transliteration* (TMDB's "Jānis
    Cimmermanis" vs AlloCiné's "Janis Cimermanis") and on *initials*
    ("G.W. Pabst" vs "Georg Wilhelm Pabst"). Folded-character equality is
    therefore not enough: compare segments, letting one fold- or
    character-drop difference slide, and treat initials as standing for the
    full given name.
    """
    if name_key(hint) == name_key(actual):
        return True
    hs, as_ = _segments(hint), _segments(actual)
    if not hs or not as_:
        return False
    if hs[-1] != as_[-1] and not _close_enough(hs[-1], as_[-1]):
        # Surnames must at least be within one character of each other —
        # "Cimmermanis" vs "Cimermanis" is the same name; "Pabst" vs
        # "von Braun" is not.
        return False
    given_h, given_a = hs[:-1], as_[:-1]
    if len(given_h) != len(given_a):
        shorter, longer = (
            (given_h, given_a) if len(given_h) < len(given_a) else (given_a, given_h)
        )
        longer = longer[: len(shorter)]
        given_h, given_a = shorter, longer
    for h, a in zip(given_h, given_a):
        if len(h) == 1 or len(a) == 1:
            if h[0] != a[0]:
                return False
        elif h != a and not _close_enough(h, a):
            return False
    return True


def _close_enough(a: str, b: str) -> bool:
    """Within one character — catches doubled-letter transliteration drift
    ("cimmermanis" vs "cimermanis") without equating different names."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    return SequenceMatcher(None, a, b).ratio() >= 0.85


def director_mismatch(hint: str | None, actual: str | None) -> bool:
    """True only when both sides name directors and share none. Absence of
    evidence is not a mismatch. Initials and precomposed accents count as
    the same person: sources disagree about "G.W. Pabst" vs "Georg Wilhelm
    Pabst" and "Jānis" vs "Janis" all the time."""
    hinted = [n.strip() for n in (hint or "").split(",") if n.strip()]
    found = [n.strip() for n in (actual or "").split(",") if n.strip()]
    if not hinted or not found:
        return False
    return not any(_names_compatible(h, a) for h in hinted for a in found)


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

    async def _search_and_detail(
        self, c, display: str, hints: dict
    ) -> dict | None:
        """Search TMDB, pick the best candidate, fetch its detail.

        Tries the plain fr-FR search first, then a year-filtered one: generic
        one-word titles ("Girl", "Paradise") bury the actual film under
        hundreds of more popular same-word films, and the filter pulls it
        onto the first page.

        The year hint comes from AlloCiné, which sometimes shows the
        *re-release* year for restored heritage films (Demy's Lola hinted as
        2013, Kurosawa's Château de l'araignée as 1966). When no candidate
        survives with the year hint, a second pass scores without it, letting
        the director hint carry the disambiguation.
        """
        year = hints.get("year")
        director = hints.get("director")
        urls = [
            (
                f"{API}/search/movie?api_key={self.api_key}"
                f"&language=fr-FR&query={quote(display, safe='')}"
            ),
        ]
        if year:
            urls.append(f"{urls[0]}&year={year}")

        # Passes: first honour the year hint; if the director hint then never
        # matches anything, the year is probably AlloCiné's re-release year
        # (Demy's Lola hinted as 2013), so score again without it.
        passes = [(year, True), (None, True)] if year else [(None, True)]

        for pass_year, _ in passes:
            for url in urls:
                found = await _get_json_retried(c, url)
                candidates = found.get("results", [])
                if not candidates:
                    continue
                # Check the top candidates in score order, not just the single
                # best: same-title same-year films ("Paradise" x2 in 2026) tie
                # on title+year, and the director hint is the only way to tell
                # them apart.
                ranked = sorted(
                    candidates,
                    key=lambda c: score_candidate(c, display, None, year=pass_year),
                    reverse=True,
                )
                for candidate in ranked[:5]:
                    if (
                        score_candidate(candidate, display, None, year=pass_year)
                        < THRESHOLD
                    ):
                        break
                    detail = await _get_json_retried(
                        c,
                        f"{API}/movie/{candidate['id']}?api_key={self.api_key}"
                        "&language=en-US&append_to_response=credits",
                    )
                    if not director_mismatch(director, director_of(detail)):
                        return detail
        return None

    async def enrich(self, titles: dict[str, dict]) -> dict[str, FilmMeta]:
        """titles maps title_key -> {"title", "year", "director"} hints.

        Never raises; degrades to {}. A wrong poster is worse than no poster:
        when the source names a director and the matched film names different
        ones, the match is rejected and the key stays unmatched.
        """
        if not self.api_key:
            return {}
        out: dict[str, FilmMeta] = {}
        try:
            async with client() as c:
                for key, hints in titles.items():
                    display = hints["title"]
                    if key in self.overrides and self.overrides[key] is None:
                        continue
                    forced = self.overrides.get(key)
                    try:
                        if forced:
                            detail = await _get_json_retried(
                                c,
                                f"{API}/movie/{forced}?api_key={self.api_key}"
                                "&language=en-US&append_to_response=credits",
                            )
                        else:
                            detail = await self._search_and_detail(c, display, hints)
                            if detail is None:
                                self.unmatched.append(display)
                                continue
                        if director_mismatch(hints.get("director"), director_of(detail)):
                            self.unmatched.append(display)
                            continue
                        out[key] = FilmMeta(
                            tmdb_id=detail.get("id"),
                            title_en=detail.get("title"),
                            overview=detail.get("overview"),
                            poster_path=detail.get("poster_path"),
                            backdrop_path=detail.get("backdrop_path"),
                            runtime=detail.get("runtime"),
                            year=int((detail.get("release_date") or "0")[:4] or 0) or None,
                            director=director_of(detail),
                        )
                    except Exception:
                        self.unmatched.append(display)
        except Exception:
            return out
        return out

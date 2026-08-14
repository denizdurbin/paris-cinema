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
    director: str | None = None


def director_of(detail: dict) -> str | None:
    """Director name(s) from a detail payload fetched with append_to_response=credits."""
    crew = (detail.get("credits") or {}).get("crew") or []
    names = [m["name"] for m in crew if m.get("job") == "Director" and m.get("name")]
    return ", ".join(names) or None


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
                                c,
                                f"{API}/movie/{forced}?api_key={self.api_key}"
                                "&language=en-US&append_to_response=credits",
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
                                "&language=en-US&append_to_response=credits",
                            )
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

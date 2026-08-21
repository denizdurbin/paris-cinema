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


def test_director_of_picks_director_from_crew():
    detail = {"credits": {"crew": [
        {"job": "Producer", "name": "Someone"},
        {"job": "Director", "name": "Jacques Tati"},
    ]}}
    assert tmdb.director_of(detail) == "Jacques Tati"


def test_director_of_joins_multiple_directors():
    detail = {"credits": {"crew": [
        {"job": "Director", "name": "A"},
        {"job": "Director", "name": "B"},
    ]}}
    assert tmdb.director_of(detail) == "A, B"


def test_director_of_handles_missing_credits():
    assert tmdb.director_of({}) is None
    assert tmdb.director_of({"credits": None}) is None
    assert tmdb.director_of({"credits": {"crew": []}}) is None


def test_year_hint_disambiguates_same_title_films():
    """La Filmothèque screened Antonioni's La Notte (1961); AlloCiné's French
    title for it is "La Nuit", which also names an unrelated 2026 short."""
    recent = cand("La Nuit", year=2026)
    recent["id"] = 2026
    antonioni = cand("La Nuit", year=1961, orig="La Notte")
    antonioni["id"] = 1961
    out = tmdb.pick_best([recent, antonioni], "La Nuit", None, year=1961)
    assert out is not None
    assert out["id"] == 1961


def test_year_hint_disambiguates_on_original_title_only():
    """Same case, but TMDB's fr-FR title is not localised, so the 1961 film
    only matches via original_title."""
    recent = cand("La Nuit", year=2026)
    recent["id"] = 2026
    antonioni = cand("La Notte", year=1961)
    antonioni["id"] = 1961
    out = tmdb.pick_best([recent, antonioni], "La Nuit", None, year=1961)
    assert out is not None
    assert out["id"] == 1961


def test_year_hint_absent_keeps_title_only_behaviour():
    """Dulac films carry no hint: scoring must be identical to before."""
    recent = cand("La Nuit", year=2026)
    recent["id"] = 2026
    antonioni = cand("La Nuit", year=1961, orig="La Notte")
    antonioni["id"] = 1961
    assert tmdb.score_candidate(recent, "La Nuit", None) == 1.0
    assert tmdb.score_candidate(antonioni, "La Nuit", None) == 1.0


def test_year_hint_tolerates_small_deltas():
    """French release dates can sit 1-3 years from TMDB's earliest release."""
    c = cand("Playtime", year=1967)
    assert tmdb.score_candidate(c, "Playtime", None, year=1968) > 1.0
    assert tmdb.score_candidate(c, "Playtime", None, year=1970) == 1.0
    assert tmdb.score_candidate(c, "Playtime", None, year=1980) < 0.55


def test_director_mismatch_only_when_both_sides_known():
    assert tmdb.director_mismatch("Michelangelo Antonioni", "Someone Else")
    assert not tmdb.director_mismatch("Michelangelo Antonioni", "michelangelo antonioni")
    assert not tmdb.director_mismatch(None, "Someone Else")
    assert not tmdb.director_mismatch("Michelangelo Antonioni", None)
    assert not tmdb.director_mismatch(None, None)


def test_director_mismatch_handles_multiple_directors():
    assert not tmdb.director_mismatch("Sydney Pollack", "Frank Perry, Sydney Pollack")
    assert tmdb.director_mismatch("Dario Argento", "Frank Perry, Sydney Pollack")


def test_director_mismatch_is_accent_insensitive():
    assert not tmdb.director_mismatch("Denis Côté", "Denis Cote")

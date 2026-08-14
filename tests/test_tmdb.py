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

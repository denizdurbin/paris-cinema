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

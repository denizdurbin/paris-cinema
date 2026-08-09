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

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

"""AlloCine adapter - primary source, covers every catalogued venue with a code.

Page: https://www.allocine.fr/seance/salle_gen_csalle={CODE}.html
Showtimes carry offset-aware `data-showtime-time`, so no timezone guessing.
Booking URLs are base64 hidden inside the class attribute with `ACr` noise.
"""

import base64
import binascii
import json
import re
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


def parse_release_year(card) -> int | None:
    """Year of the original release date.

    Scoped to `.meta-body-info`: restorations carry a second `.date` span under
    a "Date de reprise" label in a sibling `.meta-body-item`, and that one is
    the re-release year, not the film's.
    """
    info = card.css_first(".meta-body-info")
    if info is None:
        return None
    date_node = info.css_first(".date")
    if date_node is None:
        return None
    m = re.search(r"\b(\d{4})\b", date_node.text(strip=True))
    return int(m.group(1)) if m else None


def parse_directors(card) -> str | None:
    """Director name(s), comma-joined when there are several."""
    names = [
        node.text(strip=True)
        for node in card.css(".meta-body-direction .dark-grey-link")
        if node.text(strip=True)
    ]
    return ", ".join(names) or None


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
        film_year = parse_release_year(card)
        film_director = parse_directors(card)

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
                    film_year=film_year,
                    film_director=film_director,
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

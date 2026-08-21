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
    # Matching hints for TMDB enrichment; only AlloCiné cards carry them.
    film_year: int | None = None
    film_director: str | None = None

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

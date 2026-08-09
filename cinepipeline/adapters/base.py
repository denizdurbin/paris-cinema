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

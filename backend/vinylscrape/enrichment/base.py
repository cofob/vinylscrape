from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class EnrichmentResult:
    musicbrainz_id: str | None = None
    release_group_id: str | None = None
    label: str | None = None
    year: int | None = None
    genres: list[str] = field(default_factory=list)
    youtube_url: str | None = None


class BaseEnricher(ABC):
    @abstractmethod
    async def enrich(self, artist: str, title: str) -> EnrichmentResult | None: ...

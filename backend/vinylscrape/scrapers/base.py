from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class ScrapedTrack:
    position: str
    title: str
    duration: str | None = None
    youtube_url: str | None = None


@dataclass
class ScrapedVinylListing:
    title: str
    artist: str
    price: Decimal
    currency: str = "GEL"
    image_url: str | None = None
    detail_url: str | None = None
    in_stock: bool = True


@dataclass
class ScrapedVinylDetail:
    title: str
    artist: str
    price: Decimal
    currency: str = "GEL"
    image_url: str | None = None
    detail_url: str | None = None
    in_stock: bool = True
    label: str | None = None
    catalog_number: str | None = None
    year: int | None = None
    condition: str | None = None
    genres: list[str] = field(default_factory=list)
    tracklist: list[ScrapedTrack] = field(default_factory=list)
    youtube_url: str | None = None


class BaseScraper(ABC):
    """Each scraper must implement these methods."""

    @abstractmethod
    async def scrape_listing(self, page: int) -> list[ScrapedVinylListing]:
        """Crawl a catalog page, return list of brief records."""
        ...

    @abstractmethod
    async def scrape_detail(self, url: str) -> ScrapedVinylDetail:
        """Parse a single product page -- full data."""
        ...

    @abstractmethod
    async def get_total_pages(self) -> int | None:
        """Total number of catalog pages (if known)."""
        ...

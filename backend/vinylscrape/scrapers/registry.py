from collections.abc import Callable
from typing import TypeVar

from vinylscrape.scrapers.base import BaseScraper

SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {}
ScraperT = TypeVar("ScraperT", bound=type[BaseScraper])


def register_scraper(key: str) -> Callable[[ScraperT], ScraperT]:
    """Decorator to register a scraper class by key."""

    def decorator(cls: ScraperT) -> ScraperT:
        SCRAPER_REGISTRY[key] = cls
        return cls

    return decorator


class ScraperRegistry:
    """Provides access to registered scrapers."""

    def get_scraper(self, key: str) -> BaseScraper:
        cls = SCRAPER_REGISTRY.get(key)
        if cls is None:
            raise KeyError(f"No scraper registered for key: {key}")
        return cls()

    def list_scrapers(self) -> list[str]:
        return list(SCRAPER_REGISTRY.keys())

    def has_scraper(self, key: str) -> bool:
        return key in SCRAPER_REGISTRY

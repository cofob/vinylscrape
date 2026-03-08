import logging
from typing import cast

import httpx

from vinylscrape.scrapers.http import request_with_retry

logger = logging.getLogger(__name__)


class YouTubeSearcher:
    """Finds YouTube preview URLs for vinyl records.

    Priority order:
    1. YouTube URLs from scraper data (morevi.ge has them in tracklist)
    2. MusicBrainz URL relations (handled in musicbrainz.py)
    3. SerpAPI YouTube search (if API key is configured)
    4. Exa search with youtube.com filter (fallback if SerpAPI is unavailable or fails)
    """

    SERPAPI_URL = "https://serpapi.com/search.json"
    EXA_SEARCH_URL = "https://api.exa.ai/search"

    def __init__(self, serpapi_key: str = "", exa_api_key: str = "") -> None:
        self._serpapi_key = serpapi_key
        self._exa_api_key = exa_api_key
        self._client = httpx.AsyncClient(timeout=20.0)

    @property
    def enabled(self) -> bool:
        return bool(self._serpapi_key) or bool(self._exa_api_key)

    async def find_preview(
        self,
        artist: str,
        title: str,
        existing_urls: list[str] | None = None,
    ) -> str | None:
        """Return the best YouTube URL for the given release."""
        # If we already have URLs from scraping, use the first one
        if existing_urls:
            return existing_urls[0]

        # Try SerpAPI first if configured
        if self._serpapi_key:
            result = await self._search_serpapi(artist, title)
            if result:
                return result
            # SerpAPI failed or returned no results, fall through to Exa

        # Fallback to Exa search with youtube.com filter
        if self._exa_api_key:
            return await self._search_exa(artist, title)

        logger.debug("No search API keys configured, skipping YouTube search")
        return None

    async def _search_serpapi(self, artist: str, title: str) -> str | None:
        """Search YouTube via SerpAPI and return the best video URL."""
        query = f"{artist} - {title} vinyl"

        try:
            resp = await request_with_retry(
                self._client,
                "GET",
                self.SERPAPI_URL,
                params={
                    "engine": "youtube",
                    "search_query": query,
                    "api_key": self._serpapi_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            logger.exception("SerpAPI YouTube search failed for %s - %s", artist, title)
            return None

        video_results = data.get("video_results", [])
        if not video_results:
            logger.debug("SerpAPI returned no YouTube results for %s - %s", artist, title)
            return None

        # Return the first video link
        best = video_results[0]
        link = best.get("link")

        if link:
            logger.info(
                "SerpAPI YouTube result for %s - %s: %s (%s)",
                artist,
                title,
                best.get("title", ""),
                link,
            )
            return cast(str, link)

        return None

    async def _search_exa(self, artist: str, title: str) -> str | None:
        """Search YouTube via Exa API with youtube.com domain filter."""
        query = f"{artist} - {title}"

        try:
            resp = await request_with_retry(
                self._client,
                "POST",
                self.EXA_SEARCH_URL,
                headers={
                    "content-type": "application/json",
                    "x-api-key": self._exa_api_key,
                },
                json={
                    "query": query,
                    "includeDomains": ["youtube.com"],
                    "numResults": 5,
                    "type": "auto",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            logger.exception("Exa YouTube search failed for %s - %s", artist, title)
            return None

        results = data.get("results", [])
        if not results:
            logger.debug("Exa returned no YouTube results for %s - %s", artist, title)
            return None

        best = results[0]
        url = best.get("url")

        if url:
            logger.info(
                "Exa YouTube result for %s - %s: %s (%s)",
                artist,
                title,
                best.get("title", ""),
                url,
            )
            return cast(str, url)

        return None

    async def close(self) -> None:
        await self._client.aclose()

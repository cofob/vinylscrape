import json
import logging

import httpx

from vinylscrape.enrichment.base import BaseEnricher, EnrichmentResult
from vinylscrape.scrapers.http import request_with_retry

logger = logging.getLogger(__name__)


class ExaSearchEnricher(BaseEnricher):
    """Web search enricher using the Exa API with structured summary extraction.

    Searches for vinyl release metadata (label, year, genres) when MusicBrainz
    doesn't return a match. Requires an Exa API key.
    """

    EXA_SEARCH_URL = "https://api.exa.ai/search"

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    async def enrich(self, artist: str, title: str) -> EnrichmentResult | None:
        if not self._api_key:
            logger.debug("No Exa API key configured, skipping web search enrichment")
            return None

        query = f'{artist} "{title}" vinyl record release'

        try:
            resp = await request_with_retry(
                self._client,
                "POST",
                self.EXA_SEARCH_URL,
                headers={
                    "x-api-key": self._api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "query": query,
                    "numResults": 5,
                    "type": "auto",
                    "contents": {
                        "summary": {
                            "query": (
                                f"Extract vinyl record metadata for "
                                f'"{artist} - {title}": '
                                f"the record label name, release year, "
                                f"and music genres/styles."
                            ),
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "label": {
                                        "type": "string",
                                        "description": (
                                            "Record label name, e.g. 'Warp Records'. "
                                            "Empty string if unknown."
                                        ),
                                    },
                                    "year": {
                                        "type": "integer",
                                        "description": (
                                            "Release year as a 4-digit number, e.g. 2019. "
                                            "0 if unknown."
                                        ),
                                    },
                                    "genres": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": (
                                            "List of music genres/styles, e.g. "
                                            "['Electronic', 'Techno']. ALWAYS in English. "
                                            "Empty array if unknown."
                                        ),
                                    },
                                },
                                "required": ["label", "year", "genres"],
                                "additionalProperties": False,
                            },
                        },
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            logger.exception("Exa search failed for %s - %s", artist, title)
            return None

        results = data.get("results", [])
        if not results:
            logger.debug("Exa returned no results for %s - %s", artist, title)
            return None

        # Aggregate structured data from all results, picking the first
        # non-empty value for each field
        label: str | None = None
        year: int | None = None
        genres: list[str] = []

        for r in results:
            summary_raw = r.get("summary", "")
            if not summary_raw:
                continue

            try:
                parsed = json.loads(summary_raw)
            except (json.JSONDecodeError, TypeError):
                continue

            if not label and parsed.get("label"):
                label = parsed["label"]
            if not year and parsed.get("year") and parsed["year"] > 0:
                year = parsed["year"]
            if not genres and parsed.get("genres"):
                genres = [g for g in parsed["genres"] if isinstance(g, str) and g]

        if not label and not year and not genres:
            logger.debug("Exa results had no extractable metadata for %s - %s", artist, title)
            return None

        logger.info(
            "Exa enrichment for %s - %s: label=%s, year=%s, genres=%s",
            artist,
            title,
            label,
            year,
            genres,
        )

        return EnrichmentResult(
            label=label,
            year=year,
            genres=genres,
        )

    async def close(self) -> None:
        await self._client.aclose()

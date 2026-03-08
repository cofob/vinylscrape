import logging

from vinylscrape.enrichment.base import EnrichmentResult
from vinylscrape.enrichment.musicbrainz import MusicBrainzClient
from vinylscrape.enrichment.web_search import ExaSearchEnricher
from vinylscrape.enrichment.youtube import YouTubeSearcher

logger = logging.getLogger(__name__)


class EnrichmentPipeline:
    """Orchestrates the enrichment chain:
    1. MusicBrainz lookup
    2. Exa web search fallback (if MusicBrainz misses label/year/genres)
    3. YouTube preview finder (SerpAPI, then Exa with youtube.com filter)
    """

    def __init__(
        self,
        musicbrainz: MusicBrainzClient,
        youtube: YouTubeSearcher,
        web_search: ExaSearchEnricher,
    ):
        self._mb = musicbrainz
        self._yt = youtube
        self._web = web_search

    async def enrich(
        self,
        artist: str,
        title: str,
        existing_youtube_urls: list[str] | None = None,
    ) -> EnrichmentResult:
        result = EnrichmentResult()

        # Step 1: MusicBrainz
        mb_result = await self._mb.enrich(artist, title)
        if mb_result:
            result.musicbrainz_id = mb_result.musicbrainz_id
            result.release_group_id = mb_result.release_group_id
            result.label = mb_result.label
            result.year = mb_result.year
            result.genres = mb_result.genres
            result.tracklist = mb_result.tracklist
            if mb_result.youtube_url:
                result.youtube_url = mb_result.youtube_url

        # Step 2: Exa web search fallback (fill gaps MusicBrainz didn't cover)
        if self._web.enabled and (not result.label or not result.year or not result.genres):
            web_result = await self._web.enrich(artist, title)
            if web_result:
                if not result.label and web_result.label:
                    result.label = web_result.label
                if not result.year and web_result.year:
                    result.year = web_result.year
                if not result.genres and web_result.genres:
                    result.genres = web_result.genres

        # Step 3: YouTube (SerpAPI YouTube search if not found via MusicBrainz)
        if not result.youtube_url:
            yt_url = await self._yt.find_preview(artist, title, existing_youtube_urls)
            if yt_url:
                result.youtube_url = yt_url

        return result

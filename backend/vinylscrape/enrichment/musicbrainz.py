import asyncio
import logging
from functools import partial
from typing import cast

import musicbrainzngs

from vinylscrape.enrichment.base import BaseEnricher, EnrichmentResult, EnrichmentTrack

logger = logging.getLogger(__name__)


class MusicBrainzClient(BaseEnricher):
    """MusicBrainz API client with rate limiting (1 req/sec)."""

    def __init__(self, app_name: str = "VinylScrape/1.0"):
        musicbrainzngs.set_useragent(app_name, "1.0", "https://github.com/cofob/vinylscrape")
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    async def _rate_limit(self) -> None:
        """Ensure at least 1 second between requests."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            wait = max(0, 1.0 - (now - self._last_request))
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request = asyncio.get_event_loop().time()

    @staticmethod
    def _is_vinyl(release: dict) -> bool:
        """Check whether any medium on a release is a vinyl format."""
        for medium in release.get("medium-list", []):
            fmt = (medium.get("format") or "").lower()
            if "vinyl" in fmt:
                return True
        return False

    @staticmethod
    def _pick_best(releases: list[dict], min_score: int = 80) -> dict | None:
        """Pick the best release, preferring vinyl over other formats.

        Among all releases with ``ext:score >= min_score``, return the
        first vinyl release.  If none of the qualifying releases are
        vinyl, fall back to the first qualifying release regardless of
        format.
        """
        best_any: dict | None = None
        for release in releases:
            score = int(release.get("ext:score", 0))
            if score < min_score:
                continue
            if best_any is None:
                best_any = release
            if MusicBrainzClient._is_vinyl(release):
                return release
        return best_any

    async def enrich(self, artist: str, title: str) -> EnrichmentResult | None:
        await self._rate_limit()

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                partial(
                    musicbrainzngs.search_releases,
                    artist=artist,
                    release=title,
                    limit=25,
                ),
            )
        except Exception:
            logger.exception("MusicBrainz search failed for %s - %s", artist, title)
            return None

        releases = result.get("release-list", [])
        if not releases:
            return None

        best = self._pick_best(releases)

        if not best:
            return None

        mb_id = best.get("id")
        release_group_id = best.get("release-group", {}).get("id")

        # Extract label
        label = None
        label_info = best.get("label-info-list", [])
        if label_info:
            label = label_info[0].get("label", {}).get("name")

        # Extract year
        year = None
        date = best.get("date", "")
        if date and len(date) >= 4:
            try:
                year = int(date[:4])
            except ValueError:
                pass

        # Extract genres from tags
        genres = []
        tags = best.get("tag-list", [])
        for tag in tags:
            genres.append(tag.get("name", ""))

        # Fetch YouTube URL and tracklist from the release in one API call
        youtube_url = None
        tracklist: list[EnrichmentTrack] = []
        if mb_id:
            youtube_url, tracklist = await self._get_release_details(mb_id)

        return EnrichmentResult(
            musicbrainz_id=mb_id,
            release_group_id=release_group_id,
            label=label,
            year=year,
            genres=genres,
            youtube_url=youtube_url,
            tracklist=tracklist,
        )

    async def _get_release_details(
        self, release_id: str
    ) -> tuple[str | None, list[EnrichmentTrack]]:
        """Fetch YouTube URL and tracklist for a release in a single API call."""
        await self._rate_limit()

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                partial(
                    musicbrainzngs.get_release_by_id,
                    release_id,
                    includes=["url-rels", "recordings"],
                ),
            )
        except Exception:
            logger.exception("Failed to get release details for %s", release_id)
            return None, []

        release = result.get("release", {})

        # Extract YouTube URL from relations
        youtube_url: str | None = None
        for rel in release.get("url-relation-list", []):
            url = rel.get("target", "")
            if "youtube.com" in url or "youtu.be" in url:
                youtube_url = cast(str, url)
                break

        # Extract tracklist from media
        tracks: list[EnrichmentTrack] = []
        for medium in release.get("medium-list", []):
            for track in medium.get("track-list", []):
                recording = track.get("recording", {})
                position = track.get("number", "")
                title = recording.get("title") or track.get("title", "")
                if not position or not title:
                    continue
                # Convert length in ms to "M:SS" string
                duration: str | None = None
                length = recording.get("length")
                if length:
                    try:
                        total_secs = int(length) // 1000
                        duration = f"{total_secs // 60}:{total_secs % 60:02d}"
                    except (ValueError, TypeError):
                        pass
                tracks.append(EnrichmentTrack(position=position, title=title, duration=duration))

        return youtube_url, tracks

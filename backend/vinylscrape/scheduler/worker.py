import argparse
import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import TypedDict

import httpx

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Ensure scrapers are registered by importing them
import vinylscrape.scrapers.morevi  # noqa: F401
import vinylscrape.scrapers.retromania  # noqa: F401
import vinylscrape.scrapers.vinylge  # noqa: F401
import vinylscrape.scrapers.vodkast  # noqa: F401
from vinylscrape.config import Config
from vinylscrape.db.models import Source, Track, Vinyl
from vinylscrape.db.repositories import (
    GenreRepository,
    SourceRepository,
    TrackRepository,
    VinylRepository,
    VinylSourceRepository,
)
from vinylscrape.db.session import create_engine, create_session_factory
from vinylscrape.enrichment.musicbrainz import MusicBrainzClient
from vinylscrape.enrichment.pipeline import EnrichmentPipeline
from vinylscrape.enrichment.web_search import ExaSearchEnricher
from vinylscrape.enrichment.youtube import YouTubeSearcher
from vinylscrape.og.generator import OgImageGenerator
from vinylscrape.scrapers.base import BaseScraper, ScrapedVinylDetail
from vinylscrape.scrapers.registry import ScraperRegistry
from vinylscrape.storage.s3 import ImageStorage

logger = logging.getLogger(__name__)


class EnrichmentItem(TypedDict):
    id: object
    artist: str
    title: str
    yt_urls: list[str]


def _slugify(text: str) -> str:
    import unicodedata

    slug = unicodedata.normalize("NFKD", text)
    slug = slug.encode("ascii", "ignore").decode("ascii")
    slug = slug.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug


async def import_vinyl_detail(
    detail: ScrapedVinylDetail,
    source: Source,
    session: AsyncSession,
) -> None:
    """Import a scraped vinyl detail into the database with deduplication."""
    vinyl_repo = VinylRepository(session)
    vinyl_source_repo = VinylSourceRepository(session)
    genre_repo = GenreRepository(session)
    track_repo = TrackRepository(session)

    # Deduplicate by artist + title
    vinyl = await vinyl_repo.find_by_artist_title(detail.artist, detail.title)
    is_new = vinyl is None

    if is_new:
        vinyl = Vinyl(
            title=detail.title,
            artist=detail.artist,
            label=detail.label,
            catalog_number=detail.catalog_number,
            year=detail.year,
            condition=detail.condition,
            image_url=detail.image_url,
            youtube_url=detail.youtube_url,
        )
        await vinyl_repo.create(vinyl)
        # Generate URL-friendly slug: {artist}-{title}-{short_id}
        vinyl.slug = f"{_slugify(detail.artist)}-{_slugify(detail.title)}-{str(vinyl.id)[:8]}"
        # Eagerly load relationships on the newly-created object so we can
        # access them without triggering a lazy load (which fails in async).
        await session.refresh(vinyl, ["genres", "sources", "tracklist"])
    else:
        assert vinyl is not None
        # Update fields if new data is available
        if detail.label and not vinyl.label:
            vinyl.label = detail.label
        if detail.catalog_number and not vinyl.catalog_number:
            vinyl.catalog_number = detail.catalog_number
        if detail.year and not vinyl.year:
            vinyl.year = detail.year
        if detail.condition and not vinyl.condition:
            vinyl.condition = detail.condition
        if detail.image_url and not vinyl.image_url:
            vinyl.image_url = detail.image_url
        if detail.youtube_url and not vinyl.youtube_url:
            vinyl.youtube_url = detail.youtube_url

    assert vinyl is not None

    # Upsert vinyl_source
    await vinyl_source_repo.upsert(
        vinyl_id=vinyl.id,
        source_id=source.id,
        external_url=detail.detail_url or "",
        price=detail.price,
        currency=detail.currency,
        in_stock=detail.in_stock,
    )

    # Genres
    existing_genre_ids = {g.id for g in vinyl.genres}
    for genre_name in detail.genres:
        slug = _slugify(genre_name)
        if slug:
            genre = await genre_repo.get_or_create(genre_name, slug)
            if genre.id not in existing_genre_ids:
                vinyl.genres.append(genre)
                existing_genre_ids.add(genre.id)

    # Tracklist
    if detail.tracklist:
        tracks = [
            Track(
                position=t.position,
                title=t.title,
                duration=t.duration,
                youtube_url=t.youtube_url,
            )
            for t in detail.tracklist
        ]
        await track_repo.replace_for_vinyl(vinyl.id, tracks)

    await session.flush()


async def _scrape_and_upload(
    scraper: BaseScraper,
    image_storage: ImageStorage,
    detail_url: str,
    semaphore: asyncio.Semaphore,
) -> ScrapedVinylDetail | None:
    """Scrape a detail page and re-upload its image to S3.

    Runs under a concurrency-limiting semaphore so that at most N detail
    pages are being fetched in parallel.
    """
    async with semaphore:
        try:
            detail = await scraper.scrape_detail(detail_url)
        except Exception:
            logger.exception("Failed to scrape detail: %s", detail_url)
            return None

        # Download image and re-upload to S3
        if detail.image_url:
            try:
                s3_url = await image_storage.upload_image(detail.image_url)
                if s3_url:
                    detail.image_url = s3_url
            except Exception:
                logger.exception("Failed to upload image for: %s", detail_url)

        return detail


async def run_scrape(
    source: Source,
    registry: ScraperRegistry,
    session_factory: async_sessionmaker[AsyncSession],
    image_storage: ImageStorage,
    max_pages: int | None = None,
    concurrency: int = 3,
    scrape_delay: float = 1.0,
) -> int:
    """Run a full or partial scrape for a source. Returns number of items imported."""
    scraper = registry.get_scraper(source.scraper_key)
    total_pages = await scraper.get_total_pages()

    if max_pages is not None and total_pages is not None:
        total_pages = min(total_pages, max_pages)

    if total_pages is None:
        total_pages = max_pages  # None means paginate until empty

    imported = 0
    page = 0
    semaphore = asyncio.Semaphore(concurrency)

    while True:
        page += 1
        if total_pages is not None and page > total_pages:
            break

        # Rate-limit listing page fetches
        if page > 1 and scrape_delay > 0:
            await asyncio.sleep(scrape_delay)

        try:
            listings = await scraper.scrape_listing(page)
        except Exception:
            logger.exception("Failed to scrape listing page %d for %s", page, source.name)
            break

        if not listings:
            break  # No more items — past the last page

        # Filter out listings without detail URLs and recently-scraped ones
        since = datetime.now(timezone.utc) - timedelta(weeks=1)
        urls_to_scrape: list[str] = []
        for listing in listings:
            if not listing.detail_url:
                continue
            try:
                async with session_factory() as session:
                    vs_repo = VinylSourceRepository(session)
                    if await vs_repo.was_recently_scraped(listing.detail_url, source.id, since):
                        logger.debug("Skipping recently scraped: %s", listing.detail_url)
                        continue
            except Exception:
                pass  # On error, proceed with scraping
            urls_to_scrape.append(listing.detail_url)

        if not urls_to_scrape:
            continue

        # Scrape detail pages + upload images in parallel (up to `concurrency`)
        tasks = [
            _scrape_and_upload(scraper, image_storage, url, semaphore) for url in urls_to_scrape
        ]
        results = await asyncio.gather(*tasks)

        # Import into DB sequentially to avoid concurrency issues
        for detail in results:
            if detail is None:
                continue
            try:
                async with session_factory() as session:
                    await import_vinyl_detail(detail, source, session)
                    await session.commit()
                    imported += 1
            except Exception:
                logger.exception("Failed to import vinyl: %s", detail.detail_url)

    # Update last_scraped_at
    async with session_factory() as session:
        source_repo = SourceRepository(session)
        await source_repo.update_last_scraped(source.id)
        await session.commit()

    return imported


async def _enrich_one(
    item: EnrichmentItem,
    session_factory: async_sessionmaker[AsyncSession],
    pipeline: EnrichmentPipeline,
) -> bool:
    """Enrich a single vinyl record. Returns True if the record was processed."""
    try:
        result = await pipeline.enrich(item["artist"], item["title"], item["yt_urls"])

        async with session_factory() as session:
            v = await session.get(Vinyl, item["id"])
            if v is None:
                return False

            now = datetime.now(timezone.utc)

            if result.musicbrainz_id:
                vinyl_repo = VinylRepository(session)
                existing = await vinyl_repo.find_by_musicbrainz_id(result.musicbrainz_id)
                if existing and existing.id != v.id:
                    logger.info(
                        "Merging duplicate vinyl %s into canonical %s (musicbrainz_id=%s)",
                        v.id,
                        existing.id,
                        result.musicbrainz_id,
                    )
                    await vinyl_repo.merge_into(duplicate=v, canonical=existing)
                    if result.release_group_id and not existing.release_group_id:
                        existing.release_group_id = result.release_group_id
                    if result.youtube_url and not existing.youtube_url:
                        existing.youtube_url = result.youtube_url
                    if result.label and not existing.label:
                        existing.label = result.label
                    if result.year and not existing.year:
                        existing.year = result.year
                    existing.enrichment_attempted_at = now
                    await session.commit()
                    return True
                v.musicbrainz_id = result.musicbrainz_id
                v.release_group_id = result.release_group_id

            # Always save whatever fallback data was found
            if result.youtube_url and not v.youtube_url:
                v.youtube_url = result.youtube_url
            if result.label and not v.label:
                v.label = result.label
            if result.year and not v.year:
                v.year = result.year

            # Mark as attempted regardless of outcome so it isn't retried every run
            v.enrichment_attempted_at = now
            await session.commit()
            return True

    except Exception:
        logger.exception("Failed to enrich vinyl: %s - %s", item["artist"], item["title"])
        # Still mark as attempted to avoid infinite retry loops
        try:
            async with session_factory() as session:
                v = await session.get(Vinyl, item["id"])
                if v:
                    v.enrichment_attempted_at = datetime.now(timezone.utc)
                    await session.commit()
        except Exception:
            logger.exception("Failed to stamp enrichment_attempted_at for %s", item["id"])
        return False


async def run_enrichment(
    session_factory: async_sessionmaker[AsyncSession],
    pipeline: EnrichmentPipeline,
    limit: int = 50,
) -> int:
    """Enrich vinyl records that are missing enrichment data, in parallel."""
    # Collect data we need while inside the session, then close it
    vinyl_data: list[EnrichmentItem] = []
    async with session_factory() as session:
        vinyl_repo = VinylRepository(session)
        unenriched = await vinyl_repo.get_unenriched(limit)
        for v in unenriched:
            vinyl_data.append(
                {
                    "id": v.id,
                    "artist": v.artist,
                    "title": v.title,
                    "yt_urls": [t.youtube_url for t in v.tracklist if t.youtube_url],
                }
            )

    results = await asyncio.gather(
        *[_enrich_one(item, session_factory, pipeline) for item in vinyl_data]
    )
    return sum(results)


async def backfill_slugs(
    session_factory: async_sessionmaker[AsyncSession],
    limit: int = 200,
) -> int:
    """Assign slugs to vinyl records that don't have one yet.

    Returns the number of records updated.
    """
    async with session_factory() as session:
        vinyl_repo = VinylRepository(session)
        records = await vinyl_repo.get_without_slug(limit)
        for v in records:
            v.slug = f"{_slugify(v.artist)}-{_slugify(v.title)}-{str(v.id)[:8]}"
        await session.commit()
        return len(records)


async def _generate_one_og_image(
    record: dict,
    session_factory: async_sessionmaker[AsyncSession],
    og_generator: OgImageGenerator,
    semaphore: asyncio.Semaphore,
) -> bool:
    """Generate and persist a single OG image. Returns True on success."""
    async with semaphore:
        try:
            url = await og_generator.generate(
                record["id"],  # type: ignore[arg-type]
                record["title"],  # type: ignore[arg-type]
                record["artist"],  # type: ignore[arg-type]
                record["image_url"],  # type: ignore[arg-type]
            )
        except Exception:
            logger.exception("Failed to generate OG image for vinyl %s", record["id"])
            return False

    if not url:
        return False

    try:
        async with session_factory() as session:
            v = await session.get(Vinyl, record["id"])
            if v:
                v.og_image_url = url
                await session.commit()
                return True
    except Exception:
        logger.exception("Failed to persist OG image URL for vinyl %s", record["id"])
    return False


async def generate_og_images(
    session_factory: async_sessionmaker[AsyncSession],
    og_generator: OgImageGenerator,
    limit: int = 50,
    concurrency: int = 10,
) -> int:
    """Generate OG preview images for records that are missing them.

    Up to *concurrency* images are generated in parallel.
    """
    # Collect data while inside a session, then close it before making HTTP calls
    async with session_factory() as session:
        vinyl_repo = VinylRepository(session)
        records = await vinyl_repo.get_without_og_image(limit)
        record_data = [
            {
                "id": v.id,
                "title": v.title,
                "artist": v.artist,
                "image_url": v.image_url,
            }
            for v in records
        ]

    semaphore = asyncio.Semaphore(concurrency)
    results = await asyncio.gather(
        *[_generate_one_og_image(r, session_factory, og_generator, semaphore) for r in record_data]
    )
    return sum(results)


async def _fetch_coverart_url(mb_id: str, http: httpx.AsyncClient) -> str | None:
    """Return the front-cover image URL from the MusicBrainz Cover Art Archive.

    Tries the release endpoint first, then falls back to the release-group endpoint
    when the release itself has no cover art.
    """
    for entity in ("release", "release-group"):
        url = f"https://coverartarchive.org/{entity}/{mb_id}"
        try:
            resp = await http.get(url, follow_redirects=True, timeout=20.0)
        except Exception:
            logger.debug("CAA request failed for %s/%s", entity, mb_id)
            continue

        if resp.status_code == 404:
            continue
        if not resp.is_success:
            logger.debug("CAA returned %d for %s/%s", resp.status_code, entity, mb_id)
            continue

        try:
            data = resp.json()
        except Exception:
            logger.debug("CAA returned non-JSON for %s/%s", entity, mb_id)
            continue

        for image in data.get("images", []):
            if image.get("front"):
                # Prefer the "500" thumbnail, fall back to the full image.
                thumbnails = image.get("thumbnails", {})
                return thumbnails.get("500") or thumbnails.get("large") or image.get("image")

    return None


async def enrich_images(
    session_factory: async_sessionmaker[AsyncSession],
    image_storage: ImageStorage,
    limit: int = 50,
) -> int:
    """Download cover art from MusicBrainz CAA for vinyls missing an image_url.

    Only processes records that have a musicbrainz_id but no image_url.
    Returns the number of records updated.
    """
    async with session_factory() as session:
        vinyl_repo = VinylRepository(session)
        records = await vinyl_repo.get_without_image(limit)
        record_data = [
            {"id": v.id, "musicbrainz_id": v.musicbrainz_id, "release_group_id": v.release_group_id}
            for v in records
        ]

    if not record_data:
        return 0

    count = 0
    async with httpx.AsyncClient(
        headers={"User-Agent": "VinylScrape/1.0 (https://vinylscrape.cfb.wtf)"},
    ) as http:
        for record in record_data:
            mb_id: str = record["musicbrainz_id"]  # type: ignore[assignment]
            rg_id: str | None = record["release_group_id"]  # type: ignore[assignment]

            # Try the release ID first; if no art, try the release-group ID.
            caa_url = await _fetch_coverart_url(mb_id, http)
            if not caa_url and rg_id:
                caa_url = await _fetch_coverart_url(rg_id, http)

            if not caa_url:
                logger.debug("No cover art found on CAA for mb_id=%s", mb_id)
                continue

            s3_url = await image_storage.upload_image(caa_url)
            if not s3_url:
                logger.warning("Failed to upload CAA image for mb_id=%s", mb_id)
                continue

            async with session_factory() as session:
                v = await session.get(Vinyl, record["id"])
                if v:
                    v.image_url = s3_url
                    await session.commit()
                    count += 1
                    logger.info("Updated image for vinyl %s (mb_id=%s)", record["id"], mb_id)

    return count


async def ensure_sources(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Ensure default sources exist in the database."""
    default_sources = [
        {
            "name": "morevi.ge",
            "base_url": "https://morevi.ge",
            "scraper_key": "morevi",
        },
        {
            "name": "vinyl.ge",
            "base_url": "https://vinyl.ge",
            "scraper_key": "vinylge",
        },
        {
            "name": "retromania.ge",
            "base_url": "https://retromania.ge",
            "scraper_key": "retromania",
        },
        {
            "name": "vodkast.ge",
            "base_url": "https://www.vodkast.ge",
            "scraper_key": "vodkast",
        },
    ]

    async with session_factory() as session:
        source_repo = SourceRepository(session)
        for src in default_sources:
            existing = await source_repo.get_by_name(src["name"])
            if not existing:
                await source_repo.create(
                    Source(
                        name=src["name"],
                        base_url=src["base_url"],
                        scraper_key=src["scraper_key"],
                    )
                )
        await session.commit()


async def main(
    skip_crawl: bool = False,
    skip_enrichment: bool = False,
    skip_image_enrichment: bool = False,
    skip_image_generation: bool = False,
) -> None:
    """Main entry point for the worker process."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = Config()
    engine = create_engine(config)
    session_factory = create_session_factory(engine)
    registry = ScraperRegistry()

    mb = MusicBrainzClient(config.musicbrainz_app_name)
    exa = ExaSearchEnricher(config.exa_api_key)
    yt = YouTubeSearcher(config.serpapi_api_key)
    pipeline = EnrichmentPipeline(mb, yt, exa)

    image_storage = ImageStorage(config)
    await image_storage.ensure_bucket()

    og_generator = OgImageGenerator(image_storage, config)

    await ensure_sources(session_factory)

    if not skip_crawl:
        async with session_factory() as session:
            source_repo = SourceRepository(session)
            sources = await source_repo.get_enabled()

        for source in sources:
            if registry.has_scraper(source.scraper_key):
                logger.info("Starting scrape for %s", source.name)
                count = await run_scrape(
                    source,
                    registry,
                    session_factory,
                    image_storage,
                    concurrency=config.scrape_concurrent,
                    scrape_delay=config.scrape_delay,
                )
                logger.info("Scraped %d items from %s", count, source.name)
    else:
        logger.info("Skipping crawl (--skip-crawl)")

    # Run enrichment in batches until all records are processed
    if not skip_enrichment:
        logger.info("Starting enrichment...")
        total_enriched = 0
        batch_size = 50
        while True:
            enriched = await run_enrichment(session_factory, pipeline, limit=batch_size)
            total_enriched += enriched
            if enriched < batch_size:
                break
            logger.info("Enriched %d records so far...", total_enriched)
        logger.info("Enriched %d records total", total_enriched)
    else:
        logger.info("Skipping enrichment (--skip-enrichment)")

    # Download cover art from MusicBrainz CAA for records missing an image
    if not skip_image_enrichment:
        logger.info("Enriching images from MusicBrainz Cover Art Archive...")
        total_img = 0
        batch_size = 50
        while True:
            enriched = await enrich_images(session_factory, image_storage, limit=batch_size)
            total_img += enriched
            if enriched < batch_size:
                break
            logger.info("Enriched %d images so far...", total_img)
        logger.info("Enriched %d images total", total_img)
    else:
        logger.info("Skipping image enrichment (--skip-image-enrichment)")

    # Backfill slugs for records that don't have one yet
    logger.info("Backfilling slugs...")
    total_slugged = 0
    while True:
        slugged = await backfill_slugs(session_factory, limit=200)
        total_slugged += slugged
        if slugged < 200:
            break
        logger.info("Slugified %d records so far...", total_slugged)
    logger.info("Slugified %d records total", total_slugged)

    # Generate OG preview images for records that don't have them yet
    if not skip_image_generation:
        logger.info("Generating OG preview images...")
        total_og = 0
        while True:
            generated = await generate_og_images(session_factory, og_generator, limit=50)
            total_og += generated
            if generated < 50:
                break
            logger.info("Generated %d OG images so far...", total_og)
        logger.info("Generated %d OG images total", total_og)
    else:
        logger.info("Skipping OG image generation (--skip-image-generation)")

    await yt.close()
    await exa.close()
    await og_generator.close()
    await image_storage.close()
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VinylScrape worker")
    parser.add_argument(
        "--skip-crawl",
        action="store_true",
        default=False,
        help="Skip the crawl phase and run enrichment only",
    )
    parser.add_argument(
        "--skip-enrichment",
        action="store_true",
        default=False,
        help="Skip the enrichment phase",
    )
    parser.add_argument(
        "--skip-image-enrichment",
        action="store_true",
        default=False,
        help="Skip the image enrichment phase (MusicBrainz Cover Art Archive)",
    )
    parser.add_argument(
        "--skip-image-generation",
        action="store_true",
        default=False,
        help="Skip the OG image generation phase",
    )
    args = parser.parse_args()
    asyncio.run(
        main(
            skip_crawl=args.skip_crawl,
            skip_enrichment=args.skip_enrichment,
            skip_image_enrichment=args.skip_image_enrichment,
            skip_image_generation=args.skip_image_generation,
        )
    )

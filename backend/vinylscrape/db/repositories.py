import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import Select, case, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vinylscrape.db.models import Genre, Source, Track, Vinyl, VinylSource, vinyl_genre

GRADE_RANK = {
    "m": 8,
    "nm": 7,
    "vg+": 6,
    "vg": 5,
    "g+": 4,
    "g": 3,
    "f": 2,
    "p": 1,
}


class StatsData(TypedDict):
    total_vinyls: int
    in_stock: int
    sources: int
    top_genres: dict[str, int]
    last_updated_at: datetime | None


class VinylRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, vinyl_id: uuid.UUID) -> Vinyl | None:
        stmt = (
            select(Vinyl)
            .where(Vinyl.id == vinyl_id)
            .options(
                selectinload(Vinyl.sources).joinedload(VinylSource.source),
                selectinload(Vinyl.genres),
                selectinload(Vinyl.tracklist),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_artist_title(self, artist: str, title: str) -> Vinyl | None:
        stmt = (
            select(Vinyl)
            .where(
                func.lower(Vinyl.artist) == artist.lower(),
                func.lower(Vinyl.title) == title.lower(),
            )
            .options(
                selectinload(Vinyl.sources).joinedload(VinylSource.source),
                selectinload(Vinyl.genres),
                selectinload(Vinyl.tracklist),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_musicbrainz_id(self, mb_id: str) -> Vinyl | None:
        stmt = select(Vinyl).where(Vinyl.musicbrainz_id == mb_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def _build_search_query(
        self,
        q: str | None = None,
        genre_slugs: list[str] | None = None,
        source_names: list[str] | None = None,
        in_stock: bool | None = None,
        price_min: float | None = None,
        price_max: float | None = None,
        condition: str | None = None,
        sort: str = "date",
    ) -> Select[tuple[Vinyl]]:
        stmt = select(Vinyl).options(
            selectinload(Vinyl.sources).joinedload(VinylSource.source),
            selectinload(Vinyl.genres),
        )

        if q:
            search_term = f"%{q}%"
            stmt = stmt.where((Vinyl.artist.ilike(search_term)) | (Vinyl.title.ilike(search_term)))

        if genre_slugs:
            # Vinyl must belong to ANY of the selected genres (union)
            stmt = stmt.where(
                Vinyl.id.in_(
                    select(vinyl_genre.c.vinyl_id)
                    .join(Genre, Genre.id == vinyl_genre.c.genre_id)
                    .where(Genre.slug.in_(genre_slugs))
                )
            )

        if source_names:
            stmt = (
                stmt.join(Vinyl.sources)
                .join(VinylSource.source)
                .where(Source.name.in_(source_names))
            )

        if in_stock is True:
            if source_names is None:
                stmt = stmt.join(Vinyl.sources, isouter=False)
            stmt = stmt.where(VinylSource.in_stock.is_(True))

        if price_min is not None or price_max is not None:
            if source_names is None and in_stock is not True:
                stmt = stmt.join(Vinyl.sources, isouter=False)
            if price_min is not None:
                stmt = stmt.where(VinylSource.price >= Decimal(str(price_min)))
            if price_max is not None:
                stmt = stmt.where(VinylSource.price <= Decimal(str(price_max)))

        if condition is not None:
            # Goldmine grades ordered best→worst; rank 0 = unknown/ungraded.
            # Filter keeps records whose rank is >= the requested minimum rank.
            min_rank = GRADE_RANK.get(condition.lower(), 0)
            rank_expr = case(
                {k: v for k, v in GRADE_RANK.items()},
                value=func.lower(Vinyl.condition),
                else_=0,
            )
            stmt = stmt.where(rank_expr >= min_rank)

        stmt = stmt.distinct()

        match sort:
            case "price_asc" | "price_desc":
                # PostgreSQL does not allow ORDER BY (subquery) with
                # SELECT DISTINCT unless the expression is in the select
                # list. Work around this by wrapping the distinct-filtered
                # query as a subquery of vinyl IDs, then selecting the
                # full ORM objects ordered by min price.
                id_subq = stmt.with_only_columns(Vinyl.id).subquery()
                min_price = (
                    select(func.min(VinylSource.price))
                    .where(VinylSource.vinyl_id == Vinyl.id)
                    .correlate(Vinyl)
                    .scalar_subquery()
                    .label("min_price")
                )
                stmt = (
                    select(Vinyl)
                    .where(Vinyl.id.in_(select(id_subq.c.id)))
                    .options(
                        selectinload(Vinyl.sources).joinedload(VinylSource.source),
                        selectinload(Vinyl.genres),
                    )
                )
                if sort == "price_asc":
                    stmt = stmt.order_by(min_price.asc())
                else:
                    stmt = stmt.order_by(min_price.desc())
            case "title":
                stmt = stmt.order_by(Vinyl.title.asc())
            case _:
                stmt = stmt.order_by(Vinyl.created_at.desc())

        return stmt

    async def search(
        self,
        q: str | None = None,
        genre_slugs: list[str] | None = None,
        source_names: list[str] | None = None,
        in_stock: bool | None = None,
        price_min: float | None = None,
        price_max: float | None = None,
        condition: str | None = None,
        sort: str = "date",
        page: int = 1,
        per_page: int = 24,
    ) -> tuple[list[Vinyl], int]:
        base_query = self._build_search_query(
            q=q,
            genre_slugs=genre_slugs,
            source_names=source_names,
            in_stock=in_stock,
            price_min=price_min,
            price_max=price_max,
            condition=condition,
            sort=sort,
        )

        # Count — strip ordering since it's irrelevant for counting and
        # causes "ORDER BY expressions must appear in select list" with DISTINCT
        count_stmt = select(func.count()).select_from(base_query.order_by(None).subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        # Paginate
        stmt = base_query.offset((page - 1) * per_page).limit(per_page)
        result = await self.session.execute(stmt)
        items = list(result.scalars().unique().all())

        return items, total

    async def create(self, vinyl: Vinyl) -> Vinyl:
        self.session.add(vinyl)
        await self.session.flush()
        return vinyl

    async def get_all_for_sitemap(self) -> list[tuple[uuid.UUID, str | None, datetime]]:
        stmt = select(Vinyl.id, Vinyl.slug, Vinyl.updated_at).order_by(Vinyl.updated_at.desc())
        result = await self.session.execute(stmt)
        return list(result.all())

    async def get_without_slug(self, limit: int = 200) -> list[Vinyl]:
        stmt = (
            select(Vinyl).where(Vinyl.slug.is_(None)).order_by(Vinyl.created_at.desc()).limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_without_image(self, limit: int = 50) -> list[Vinyl]:
        """Return vinyls that have no image_url but do have a musicbrainz_id."""
        stmt = (
            select(Vinyl)
            .where(Vinyl.image_url.is_(None))
            .where(Vinyl.musicbrainz_id.isnot(None))
            .order_by(Vinyl.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_without_og_image(self, limit: int = 50) -> list[Vinyl]:
        stmt = (
            select(Vinyl)
            .where(Vinyl.og_image_url.is_(None))
            .order_by(Vinyl.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_slug(self, slug: str) -> Vinyl | None:
        stmt = (
            select(Vinyl)
            .where(Vinyl.slug == slug)
            .options(
                selectinload(Vinyl.sources).joinedload(VinylSource.source),
                selectinload(Vinyl.genres),
                selectinload(Vinyl.tracklist),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_unenriched(self, limit: int = 50) -> list[Vinyl]:
        stmt = (
            select(Vinyl)
            .where(Vinyl.enrichment_attempted_at.is_(None))
            .options(selectinload(Vinyl.tracklist))
            .order_by(Vinyl.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def merge_into(self, duplicate: Vinyl, canonical: Vinyl) -> None:
        """Merge *duplicate* into *canonical* and delete *duplicate*.

        All VinylSource rows are re-pointed to *canonical* so that their
        ``external_url`` values remain in the database.  This prevents the
        crawler from treating those URLs as never-seen and re-scraping them
        on every run.
        Tracks are moved only when *canonical* currently has none.
        Genres are union-merged.
        Scalar fields (label, year, etc.) fill gaps in *canonical*.
        """
        # Load all relationships we need to inspect
        dup = await self.get_by_id(duplicate.id)
        can = await self.get_by_id(canonical.id)
        if dup is None or can is None:
            return

        # --- VinylSource rows ---
        # Collect external URLs the canonical already owns so we can skip
        # true duplicates (same source *and* same URL).
        existing_keys = {(vs.source_id, vs.external_url) for vs in can.sources}
        for vs in dup.sources:
            if (vs.source_id, vs.external_url) in existing_keys:
                # Exact same listing already on canonical — safe to discard.
                await self.session.execute(delete(VinylSource).where(VinylSource.id == vs.id))
            else:
                # Re-point to canonical (different URL or different source).
                await self.session.execute(
                    update(VinylSource).where(VinylSource.id == vs.id).values(vinyl_id=can.id)
                )

        # --- Tracks ---
        if not can.tracklist and dup.tracklist:
            await self.session.execute(
                update(Track).where(Track.vinyl_id == dup.id).values(vinyl_id=can.id)
            )
        else:
            await self.session.execute(delete(Track).where(Track.vinyl_id == dup.id))

        # --- Genres ---
        existing_genre_ids = {g.id for g in can.genres}
        for genre in dup.genres:
            if genre.id not in existing_genre_ids:
                can.genres.append(genre)

        # --- Scalar fields: fill gaps on canonical ---
        for attr in ("label", "catalog_number", "year", "condition", "image_url", "youtube_url"):
            if getattr(can, attr) is None and getattr(dup, attr) is not None:
                setattr(can, attr, getattr(dup, attr))

        await self.session.flush()

        # Delete the duplicate record
        await self.session.execute(delete(Vinyl).where(Vinyl.id == dup.id))
        await self.session.flush()


class SourceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> list[Source]:
        result = await self.session.execute(select(Source).order_by(Source.name))
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> Source | None:
        result = await self.session.execute(select(Source).where(Source.name == name))
        return result.scalar_one_or_none()

    async def get_by_scraper_key(self, key: str) -> Source | None:
        result = await self.session.execute(select(Source).where(Source.scraper_key == key))
        return result.scalar_one_or_none()

    async def get_enabled(self) -> list[Source]:
        result = await self.session.execute(
            select(Source).where(Source.enabled.is_(True)).order_by(Source.name)
        )
        return list(result.scalars().all())

    async def create(self, source: Source) -> Source:
        self.session.add(source)
        await self.session.flush()
        return source

    async def update_last_scraped(self, source_id: uuid.UUID) -> None:
        source = await self.session.get(Source, source_id)
        if source:
            source.last_scraped_at = datetime.now(timezone.utc)
            await self.session.flush()


class VinylSourceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find(
        self,
        vinyl_id: uuid.UUID,
        source_id: uuid.UUID,
        external_url: str | None = None,
    ) -> VinylSource | None:
        stmt = select(VinylSource).where(
            VinylSource.vinyl_id == vinyl_id,
            VinylSource.source_id == source_id,
        )
        if external_url is not None:
            stmt = stmt.where(VinylSource.external_url == external_url)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def was_recently_scraped(
        self, external_url: str, source_id: uuid.UUID, since: datetime
    ) -> bool:
        """Check if a URL was already scraped after the given datetime."""
        stmt = select(func.count()).where(
            VinylSource.external_url == external_url,
            VinylSource.source_id == source_id,
            VinylSource.scraped_at >= since,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def upsert(
        self,
        vinyl_id: uuid.UUID,
        source_id: uuid.UUID,
        external_url: str,
        price: Decimal,
        currency: str,
        in_stock: bool,
    ) -> VinylSource:
        existing = await self.find(vinyl_id, source_id, external_url)
        if existing:
            existing.price = price
            existing.currency = currency
            existing.in_stock = in_stock
            existing.external_url = external_url
            existing.scraped_at = datetime.now(timezone.utc)
            await self.session.flush()
            return existing

        vs = VinylSource(
            vinyl_id=vinyl_id,
            source_id=source_id,
            external_url=external_url,
            price=price,
            currency=currency,
            in_stock=in_stock,
        )
        self.session.add(vs)
        await self.session.flush()
        return vs

    async def get_urls_for_source(
        self, source_id: uuid.UUID, scraped_before: datetime | None = None
    ) -> list[tuple[uuid.UUID, str]]:
        """Return (vinyl_source.id, external_url) pairs for a given source.

        If *scraped_before* is provided, only rows whose ``scraped_at`` is
        older than that timestamp are returned (i.e. stale records that need
        a price/availability refresh).
        """
        stmt = select(VinylSource.id, VinylSource.external_url).where(
            VinylSource.source_id == source_id,
        )
        if scraped_before is not None:
            stmt = stmt.where(VinylSource.scraped_at < scraped_before)
        result = await self.session.execute(stmt)
        return list(result.all())

    async def update_price(
        self,
        vinyl_source_id: uuid.UUID,
        price: Decimal,
        currency: str,
        in_stock: bool,
    ) -> None:
        """Update only price, currency, in_stock, and scraped_at for a
        single VinylSource row.  This is used by the weekly price-refresh
        job and intentionally does NOT touch the parent Vinyl record so
        that enrichment pipelines are not re-triggered and already-merged
        data stays intact.
        """
        await self.session.execute(
            update(VinylSource)
            .where(VinylSource.id == vinyl_source_id)
            .values(
                price=price,
                currency=currency,
                in_stock=in_stock,
                scraped_at=datetime.now(timezone.utc),
            )
        )

    async def mark_out_of_stock(self, vinyl_source_id: uuid.UUID) -> None:
        """Mark a VinylSource as out-of-stock and bump scraped_at.

        Used when the product page returns 404 (removed from the shop).
        The last-known price is preserved for historical reference.
        """
        await self.session.execute(
            update(VinylSource)
            .where(VinylSource.id == vinyl_source_id)
            .values(
                in_stock=False,
                scraped_at=datetime.now(timezone.utc),
            )
        )


class GenreRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_with_counts(
        self,
        q: str | None = None,
        source_names: list[str] | None = None,
        in_stock: bool | None = None,
        genre_slugs: list[str] | None = None,
        condition: str | None = None,
    ) -> list[tuple[Genre, int]]:
        """Return genres with vinyl counts, optionally filtered.

        Counts reflect how many vinyls match the given filters AND belong
        to each genre, so the genre pills show relevant numbers.
        When genre_slugs is set, only vinyls that belong to ANY of those
        genres are counted (union semantics).
        """
        # Base: join genre -> vinyl_genre -> vinyl
        stmt = (
            select(Genre, func.count(func.distinct(vinyl_genre.c.vinyl_id)).label("vinyl_count"))
            .join(vinyl_genre, Genre.id == vinyl_genre.c.genre_id)
            .join(Vinyl, Vinyl.id == vinyl_genre.c.vinyl_id)
        )

        if q:
            search_term = f"%{q}%"
            stmt = stmt.where((Vinyl.artist.ilike(search_term)) | (Vinyl.title.ilike(search_term)))

        if source_names or in_stock is True:
            stmt = stmt.join(VinylSource, VinylSource.vinyl_id == Vinyl.id)
            if source_names:
                stmt = stmt.join(Source, Source.id == VinylSource.source_id).where(
                    Source.name.in_(source_names)
                )
            if in_stock is True:
                stmt = stmt.where(VinylSource.in_stock.is_(True))

        if condition is not None:
            min_rank = GRADE_RANK.get(condition.lower(), 0)
            rank_expr = case(
                {k: v for k, v in GRADE_RANK.items()},
                value=func.lower(Vinyl.condition),
                else_=0,
            )
            stmt = stmt.where(rank_expr >= min_rank)

        # Filter: vinyl must belong to ANY of the currently selected genres (union)
        if genre_slugs:
            stmt = stmt.where(
                Vinyl.id.in_(
                    select(vinyl_genre.c.vinyl_id)
                    .join(Genre, Genre.id == vinyl_genre.c.genre_id)
                    .where(Genre.slug.in_(genre_slugs))
                )
            )

        stmt = (
            stmt.group_by(Genre.id)
            .having(func.count(func.distinct(vinyl_genre.c.vinyl_id)) > 0)
            .order_by(Genre.name)
        )

        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_or_create(self, name: str, slug: str) -> Genre:
        result = await self.session.execute(select(Genre).where(Genre.slug == slug))
        genre = result.scalar_one_or_none()
        if genre:
            return genre

        genre = Genre(name=name, slug=slug)
        self.session.add(genre)
        await self.session.flush()
        return genre


class TrackRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def replace_for_vinyl(self, vinyl_id: uuid.UUID, tracks: list[Track]) -> None:
        # Delete existing tracks
        await self.session.execute(delete(Track).where(Track.vinyl_id == vinyl_id))
        for track in tracks:
            track.vinyl_id = vinyl_id
            self.session.add(track)
        await self.session.flush()


class StatsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_stats(self) -> StatsData:
        total = (await self.session.execute(select(func.count(Vinyl.id)))).scalar_one()
        in_stock_count = (
            await self.session.execute(
                select(func.count(func.distinct(VinylSource.vinyl_id))).where(
                    VinylSource.in_stock.is_(True)
                )
            )
        ).scalar_one()
        source_count = (await self.session.execute(select(func.count(Source.id)))).scalar_one()
        last_updated_at = (
            await self.session.execute(select(func.max(VinylSource.scraped_at)))
        ).scalar_one()

        genres_stmt = (
            select(Genre.name, func.count(vinyl_genre.c.vinyl_id))
            .outerjoin(vinyl_genre, Genre.id == vinyl_genre.c.genre_id)
            .group_by(Genre.name)
            .order_by(func.count(vinyl_genre.c.vinyl_id).desc())
            .limit(20)
        )
        genres_result = await self.session.execute(genres_stmt)
        top_genres = {row[0]: row[1] for row in genres_result.all()}

        return {
            "total_vinyls": total,
            "in_stock": in_stock_count,
            "sources": source_count,
            "top_genres": top_genres,
            "last_updated_at": last_updated_at,
        }

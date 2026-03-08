import math
import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, HTTPException, Query

from vinylscrape.api.dependencies import verify_admin_key
from vinylscrape.api.schemas import (
    GenreOut,
    PaginatedResponse,
    ScrapeRequest,
    ScrapeStatusOut,
    SourceOut,
    StatsOut,
    TrackOut,
    VinylDetail,
    VinylListItem,
    VinylSitemapItem,
    VinylSourceOut,
)
from vinylscrape.db.models import Vinyl
from vinylscrape.db.repositories import (
    GenreRepository,
    SourceRepository,
    StatsRepository,
    VinylRepository,
)

router = APIRouter(prefix="/api/v1", route_class=DishkaRoute)


def _vinyl_to_detail(vinyl: Vinyl) -> VinylDetail:
    return VinylDetail(
        id=vinyl.id,
        title=vinyl.title,
        artist=vinyl.artist,
        label=vinyl.label,
        catalog_number=vinyl.catalog_number,
        year=vinyl.year,
        condition=vinyl.condition,
        image_url=vinyl.image_url,
        og_image_url=vinyl.og_image_url,
        slug=vinyl.slug,
        musicbrainz_id=vinyl.musicbrainz_id,
        youtube_url=vinyl.youtube_url,
        created_at=vinyl.created_at,
        updated_at=vinyl.updated_at,
        genres=[g.name for g in vinyl.genres],
        sources=[
            VinylSourceOut(
                source_name=s.source.name,
                external_url=s.external_url,
                price=s.price,
                currency=s.currency,
                in_stock=s.in_stock,
                scraped_at=s.scraped_at,
            )
            for s in vinyl.sources
        ],
        tracklist=[
            TrackOut(
                position=t.position,
                title=t.title,
                duration=t.duration,
                youtube_url=t.youtube_url,
            )
            for t in vinyl.tracklist
        ],
    )


def _vinyl_to_list_item(vinyl: Vinyl) -> VinylListItem:
    prices = [s.price for s in vinyl.sources]
    any_in_stock = any(s.in_stock for s in vinyl.sources)
    currencies = [s.currency for s in vinyl.sources]
    return VinylListItem(
        id=vinyl.id,
        title=vinyl.title,
        artist=vinyl.artist,
        image_url=vinyl.image_url,
        year=vinyl.year,
        genres=[g.name for g in vinyl.genres] if vinyl.genres else [],
        min_price=min(prices) if prices else None,
        currency=currencies[0] if currencies else "GEL",
        in_stock=any_in_stock,
        source_count=len(vinyl.sources),
        slug=vinyl.slug,
    )


@router.get("/vinyl", response_model=PaginatedResponse)
async def search_vinyl(
    vinyl_repo: FromDishka[VinylRepository],
    q: str | None = Query(None, description="Search query"),
    genre: str | None = Query(None, description="Comma-separated genre slugs"),
    source: str | None = Query(None, description="Source name"),
    in_stock: bool | None = Query(None, description="Filter in stock"),
    price_min: float | None = Query(None, ge=0),
    price_max: float | None = Query(None, ge=0),
    condition: str | None = Query(None, description="Filter by condition grade (e.g. VG+, NM)"),
    sort: str = Query("date", pattern="^(price_asc|price_desc|date|title)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=100),
) -> PaginatedResponse:
    genre_slugs = [s.strip() for s in genre.split(",") if s.strip()] if genre else None
    source_names = [s.strip() for s in source.split(",") if s.strip()] if source else None
    items, total = await vinyl_repo.search(
        q=q,
        genre_slugs=genre_slugs,
        source_names=source_names,
        in_stock=in_stock,
        price_min=price_min,
        price_max=price_max,
        condition=condition,
        sort=sort,
        page=page,
        per_page=per_page,
    )
    return PaginatedResponse(
        items=[_vinyl_to_list_item(v) for v in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.get("/vinyl/by-slug/{slug}", response_model=VinylDetail)
async def get_vinyl_by_slug(
    slug: str,
    vinyl_repo: FromDishka[VinylRepository],
) -> VinylDetail:
    vinyl = await vinyl_repo.get_by_slug(slug)
    if not vinyl:
        raise HTTPException(status_code=404, detail="Vinyl not found")
    return _vinyl_to_detail(vinyl)


@router.get("/vinyl/sitemap", response_model=list[VinylSitemapItem])
async def get_vinyl_sitemap(
    vinyl_repo: FromDishka[VinylRepository],
) -> list[VinylSitemapItem]:
    records = await vinyl_repo.get_all_for_sitemap()
    return [VinylSitemapItem(id=r[0], slug=r[1], updated_at=r[2]) for r in records]


@router.get("/vinyl/{vinyl_id}", response_model=VinylDetail)
async def get_vinyl(
    vinyl_id: uuid.UUID,
    vinyl_repo: FromDishka[VinylRepository],
) -> VinylDetail:
    vinyl = await vinyl_repo.get_by_id(vinyl_id)
    if not vinyl:
        raise HTTPException(status_code=404, detail="Vinyl not found")
    return _vinyl_to_detail(vinyl)


@router.get("/genres", response_model=list[GenreOut])
async def list_genres(
    genre_repo: FromDishka[GenreRepository],
    q: str | None = Query(None, description="Search query"),
    source: str | None = Query(None, description="Source name"),
    in_stock: bool | None = Query(None, description="Filter in stock"),
    genre: str | None = Query(None, description="Comma-separated genre slugs already selected"),
    condition: str | None = Query(None, description="Minimum condition grade (e.g. VG+, NM)"),
) -> list[GenreOut]:
    genre_slugs = [s.strip() for s in genre.split(",") if s.strip()] if genre else None
    source_names = [s.strip() for s in source.split(",") if s.strip()] if source else None
    genres_with_counts = await genre_repo.get_all_with_counts(
        q=q,
        source_names=source_names,
        in_stock=in_stock,
        genre_slugs=genre_slugs,
        condition=condition,
    )
    return [
        GenreOut(
            id=genre.id,
            name=genre.name,
            slug=genre.slug,
            vinyl_count=count,
        )
        for genre, count in genres_with_counts
    ]


@router.get("/sources", response_model=list[SourceOut])
async def list_sources(source_repo: FromDishka[SourceRepository]) -> list[SourceOut]:
    sources = await source_repo.get_all()
    return [
        SourceOut(
            id=s.id,
            name=s.name,
            base_url=s.base_url,
            enabled=s.enabled,
            last_scraped_at=s.last_scraped_at,
        )
        for s in sources
    ]


@router.get("/stats", response_model=StatsOut)
async def get_stats(stats_repo: FromDishka[StatsRepository]) -> StatsOut:
    stats = await stats_repo.get_stats()
    return StatsOut(**stats)


@router.post(
    "/admin/scrape",
    response_model=ScrapeStatusOut,
    dependencies=[Depends(verify_admin_key)],
)
async def trigger_scrape(req: ScrapeRequest) -> ScrapeStatusOut:
    # This will be implemented with the scheduler
    return ScrapeStatusOut(
        status="queued",
        message=f"Scrape job queued for source: {req.source or 'all'}",
    )


@router.get(
    "/admin/scrape/status",
    response_model=ScrapeStatusOut,
    dependencies=[Depends(verify_admin_key)],
)
async def scrape_status() -> ScrapeStatusOut:
    return ScrapeStatusOut(status="idle", message="No active scrape jobs")

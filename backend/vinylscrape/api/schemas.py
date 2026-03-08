import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class GenreOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    vinyl_count: int = 0


class SourceOut(BaseModel):
    id: uuid.UUID
    name: str
    base_url: str
    enabled: bool
    last_scraped_at: datetime | None = None


class VinylSourceOut(BaseModel):
    source_name: str
    external_url: str
    price: Decimal
    currency: str
    in_stock: bool
    scraped_at: datetime


class TrackOut(BaseModel):
    position: str
    title: str
    duration: str | None = None
    youtube_url: str | None = None


class VinylListItem(BaseModel):
    id: uuid.UUID
    title: str
    artist: str
    image_url: str | None = None
    year: int | None = None
    genres: list[str] = []
    min_price: Decimal | None = None
    currency: str = "GEL"
    in_stock: bool = False
    source_count: int = 0
    slug: str | None = None


class VinylDetail(BaseModel):
    id: uuid.UUID
    title: str
    artist: str
    label: str | None = None
    catalog_number: str | None = None
    year: int | None = None
    condition: str | None = None
    image_url: str | None = None
    og_image_url: str | None = None
    slug: str | None = None
    musicbrainz_id: str | None = None
    youtube_url: str | None = None
    created_at: datetime
    updated_at: datetime
    genres: list[str] = []
    sources: list[VinylSourceOut] = []
    tracklist: list[TrackOut] = []


class VinylSitemapItem(BaseModel):
    id: uuid.UUID
    slug: str | None
    updated_at: datetime


class PaginatedResponse(BaseModel):
    items: list[VinylListItem]
    total: int
    page: int
    per_page: int
    pages: int


class StatsOut(BaseModel):
    total_vinyls: int
    in_stock: int
    sources: int
    top_genres: dict[str, int]
    last_updated_at: datetime | None = None


class ScrapeRequest(BaseModel):
    source: str | None = None


class ScrapeStatusOut(BaseModel):
    status: str
    message: str

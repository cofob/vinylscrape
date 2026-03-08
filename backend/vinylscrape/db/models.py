import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


vinyl_genre = Table(
    "vinyl_genre",
    Base.metadata,
    Column("vinyl_id", UUID(as_uuid=True), ForeignKey("vinyl.id", ondelete="CASCADE")),
    Column("genre_id", UUID(as_uuid=True), ForeignKey("genre.id", ondelete="CASCADE")),
)


class Vinyl(Base):
    __tablename__ = "vinyl"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    artist: Mapped[str] = mapped_column(String(500), nullable=False)
    label: Mapped[str | None] = mapped_column(String(500))
    catalog_number: Mapped[str | None] = mapped_column(String(200))
    year: Mapped[int | None] = mapped_column(Integer)
    condition: Mapped[str | None] = mapped_column(String(50))
    image_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    og_image_url: Mapped[str | None] = mapped_column(Text)
    slug: Mapped[str | None] = mapped_column(String(600), unique=True)

    # Enrichment data
    musicbrainz_id: Mapped[str | None] = mapped_column(String(36))
    release_group_id: Mapped[str | None] = mapped_column(String(36))
    youtube_url: Mapped[str | None] = mapped_column(Text)
    enrichment_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    sources: Mapped[list["VinylSource"]] = relationship(
        back_populates="vinyl", cascade="all, delete-orphan"
    )
    genres: Mapped[list["Genre"]] = relationship(secondary=vinyl_genre, back_populates="vinyls")
    tracklist: Mapped[list["Track"]] = relationship(
        back_populates="vinyl", cascade="all, delete-orphan", order_by="Track.position"
    )

    __table_args__ = (
        Index("ix_vinyl_artist_title", func.lower(artist), func.lower(title)),
        Index(
            "ix_vinyl_musicbrainz_id",
            "musicbrainz_id",
            unique=True,
            postgresql_where=musicbrainz_id.isnot(None),
        ),
    )


class Source(Base):
    __tablename__ = "source"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    scraper_key: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    vinyl_sources: Mapped[list["VinylSource"]] = relationship(back_populates="source")


class VinylSource(Base):
    __tablename__ = "vinyl_source"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vinyl_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vinyl.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source.id", ondelete="CASCADE"), nullable=False
    )
    external_url: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="GEL")
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    vinyl: Mapped["Vinyl"] = relationship(back_populates="sources")
    source: Mapped["Source"] = relationship(back_populates="vinyl_sources")

    __table_args__ = (
        Index("ix_vinyl_source_vinyl_source", "vinyl_id", "source_id"),
        Index("ix_vinyl_source_url", "external_url", "source_id", unique=True),
    )


class Genre(Base):
    __tablename__ = "genre"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)

    vinyls: Mapped[list["Vinyl"]] = relationship(secondary=vinyl_genre, back_populates="genres")


class Track(Base):
    __tablename__ = "tracklist"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vinyl_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vinyl.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    duration: Mapped[str | None] = mapped_column(String(20))
    youtube_url: Mapped[str | None] = mapped_column(Text)

    vinyl: Mapped["Vinyl"] = relationship(back_populates="tracklist")

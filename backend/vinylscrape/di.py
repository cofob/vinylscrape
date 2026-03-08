from collections.abc import AsyncIterator

from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from vinylscrape.config import Config
from vinylscrape.db.repositories import (
    GenreRepository,
    SourceRepository,
    StatsRepository,
    TrackRepository,
    VinylRepository,
    VinylSourceRepository,
)
from vinylscrape.db.session import create_engine, create_session_factory
from vinylscrape.enrichment.musicbrainz import MusicBrainzClient
from vinylscrape.enrichment.pipeline import EnrichmentPipeline
from vinylscrape.enrichment.web_search import ExaSearchEnricher
from vinylscrape.enrichment.youtube import YouTubeSearcher
from vinylscrape.scrapers.registry import ScraperRegistry
from vinylscrape.storage.s3 import ImageStorage


class ConfigProvider(Provider):
    @provide(scope=Scope.APP)
    def get_config(self) -> Config:
        return Config()


class DbProvider(Provider):
    @provide(scope=Scope.APP)
    def get_engine(self, config: Config) -> AsyncEngine:
        return create_engine(config)

    @provide(scope=Scope.APP)
    def get_session_factory(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return create_session_factory(engine)

    @provide(scope=Scope.REQUEST)
    async def get_session(
        self, factory: async_sessionmaker[AsyncSession]
    ) -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session


class RepositoryProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def vinyl_repo(self, session: AsyncSession) -> VinylRepository:
        return VinylRepository(session)

    @provide(scope=Scope.REQUEST)
    def source_repo(self, session: AsyncSession) -> SourceRepository:
        return SourceRepository(session)

    @provide(scope=Scope.REQUEST)
    def vinyl_source_repo(self, session: AsyncSession) -> VinylSourceRepository:
        return VinylSourceRepository(session)

    @provide(scope=Scope.REQUEST)
    def genre_repo(self, session: AsyncSession) -> GenreRepository:
        return GenreRepository(session)

    @provide(scope=Scope.REQUEST)
    def track_repo(self, session: AsyncSession) -> TrackRepository:
        return TrackRepository(session)

    @provide(scope=Scope.REQUEST)
    def stats_repo(self, session: AsyncSession) -> StatsRepository:
        return StatsRepository(session)


class ScraperProvider(Provider):
    @provide(scope=Scope.APP)
    def get_registry(self) -> ScraperRegistry:
        return ScraperRegistry()


class StorageProvider(Provider):
    @provide(scope=Scope.APP)
    def get_image_storage(self, config: Config) -> ImageStorage:
        return ImageStorage(config)


class EnrichmentProvider(Provider):
    @provide(scope=Scope.APP)
    def get_musicbrainz(self, config: Config) -> MusicBrainzClient:
        return MusicBrainzClient(config.musicbrainz_app_name)

    @provide(scope=Scope.APP)
    def get_exa_search(self, config: Config) -> ExaSearchEnricher:
        return ExaSearchEnricher(config.exa_api_key)

    @provide(scope=Scope.APP)
    def get_youtube_searcher(self, config: Config) -> YouTubeSearcher:
        return YouTubeSearcher(config.serpapi_api_key, config.exa_api_key)

    @provide(scope=Scope.APP)
    def get_pipeline(
        self,
        mb: MusicBrainzClient,
        yt: YouTubeSearcher,
        web: ExaSearchEnricher,
    ) -> EnrichmentPipeline:
        return EnrichmentPipeline(mb, yt, web)


def create_container() -> AsyncContainer:
    return make_async_container(
        ConfigProvider(),
        DbProvider(),
        RepositoryProvider(),
        ScraperProvider(),
        StorageProvider(),
        EnrichmentProvider(),
    )

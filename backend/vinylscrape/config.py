from pydantic_settings import BaseSettings


class Config(BaseSettings):
    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}

    database_url: str = "postgresql+asyncpg://user:password@localhost/db"
    musicbrainz_app_name: str = "VinylScrape/1.0"
    admin_api_key: str = "changeme"

    # S3 storage settings
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "vinylscrape"
    s3_region: str = "us-east-1"
    s3_public_url: str | None = (
        None  # e.g. "https://cdn.example.com" — if None, built from endpoint + bucket
    )

    # Enrichment API keys (optional — enrichment steps are skipped if keys are empty)
    exa_api_key: str = ""
    serpapi_api_key: str = ""

    # Scraper settings
    scrape_delay: float = 1.0  # seconds between HTTP requests
    scrape_concurrent: int = 3  # max concurrent scrapers

    # Scheduler settings
    full_scrape_interval_hours: int = 24
    incremental_scrape_interval_hours: int = 1
    enrichment_interval_minutes: int = 30
    incremental_pages: int = 3  # number of pages for incremental scrape

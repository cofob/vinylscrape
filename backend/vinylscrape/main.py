import logging

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure scrapers are registered
import vinylscrape.scrapers.morevi  # noqa: F401
import vinylscrape.scrapers.retromania  # noqa: F401
import vinylscrape.scrapers.vinylge  # noqa: F401
import vinylscrape.scrapers.vodkast  # noqa: F401
from vinylscrape.api.router import router
from vinylscrape.di import create_container

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="VinylScrape",
        description="Vinyl records aggregator for Georgian shops",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    container = create_container()
    setup_dishka(container, app)

    return app


app = create_app()

# VinylScrape

Vinyl record search aggregator for Georgian shops. Collects listings from multiple sources, enriches them with metadata from MusicBrainz and web search, finds YouTube previews, and provides a unified search interface.

Live instance: [vinylscrape.cfb.wtf](https://vinylscrape.cfb.wtf)

## Features

- **Multi-source scraping** — modular scraper system collecting from 4 Georgian vinyl shops
- **Metadata enrichment** — automatic tagging via MusicBrainz API with Exa web search fallback
- **YouTube previews** — finds and embeds audio/video previews for records via SerpAPI and Exa
- **Price comparison** — same record across multiple shops with stock tracking
- **Cover art** — downloads images from sources and MusicBrainz Cover Art Archive, stored in S3 with content-addressed deduplication
- **OG image generation** — dynamic Open Graph images for each vinyl record
- **PWA support** — installable progressive web app with offline fallback
- **Shopping cart** — localStorage-backed cart for collecting records across shops
- **SEO** — dynamic sitemap, robots.txt, JSON-LD structured data
- **Periodic updates** — background worker keeps data fresh via scheduled scraping and enrichment

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Dishka (DI), Alembic
- **Frontend:** Next.js 16, React 19, Tailwind CSS 4, TanStack Query, nuqs, React Compiler
- **Database:** PostgreSQL 16
- **Storage:** S3-compatible object storage (MinIO for dev)
- **Infrastructure:** Docker Compose, uv

## Data Sources

| Source | URL | Status |
|--------|-----|--------|
| Morevi | https://morevi.ge | Implemented |
| Retromania | https://retromania.ge | Implemented |
| Vodkast | https://www.vodkast.ge/ | Implemented |
| Vinyl.ge | https://vinyl.ge/shop/ | Implemented |

## Project Structure

```
vinylscrape/
├── backend/
│   ├── vinylscrape/            # Python package
│   │   ├── api/                # FastAPI routes + schemas
│   │   ├── db/                 # SQLAlchemy models, session, repositories
│   │   ├── scrapers/           # BaseScraper ABC, registry, 4 shop scrapers
│   │   ├── enrichment/         # MusicBrainz, Exa web search, YouTube, pipeline
│   │   ├── storage/            # S3 image storage (download + re-upload)
│   │   ├── scheduler/          # Background worker (scrape + enrich + images)
│   │   ├── og/                 # Open Graph image generator
│   │   ├── config.py           # Pydantic Settings
│   │   ├── di.py               # Dishka DI container
│   │   └── main.py             # FastAPI app entry point
│   ├── alembic/                # Database migrations
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                # Next.js pages (home, vinyl detail, about, cart, docs, offline)
│   │   ├── components/         # SearchBar, VinylCard, FilterPanel, CartIcon, YouTubeEmbed, etc.
│   │   ├── lib/                # API client (client + server), cart context
│   │   └── types/              # TypeScript types
│   ├── public/                 # Static assets (icons, OG images)
│   ├── package.json
│   └── Dockerfile
├── local/                      # Sample HTML for scraper development
├── docker-compose.yml          # Full production stack
├── docker-compose.dev.yaml     # Dev services (PostgreSQL + MinIO)
└── README.md
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Node.js](https://nodejs.org/) 22+
- [Docker](https://www.docker.com/) and Docker Compose

## Development Setup

### 1. Start dev services

```bash
docker compose -f docker-compose.dev.yaml up -d
```

This starts:
- **PostgreSQL** on `localhost:5432` (user `user`, password `password`, database `db`)
- **MinIO** on `localhost:9000` (access key `minioadmin`, secret `minioadmin`, console at `localhost:9001`)

### 2. Backend

```bash
cd backend

# Install dependencies
uv sync

# Run database migrations
uv run alembic upgrade head

# Start the API server
uv run uvicorn vinylscrape.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000. Interactive docs at http://localhost:8000/docs.

### 3. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

The frontend will be available at http://localhost:3000.

API requests are proxied through Next.js rewrites (`/api/*` -> backend). Set `BACKEND_URL` to change the backend address (default: `http://localhost:8000`).

### 4. Run the scraper worker

In a separate terminal:

```bash
cd backend
uv run python -m vinylscrape.scheduler.worker
```

The worker runs a continuous loop that:
1. Crawls new products from all enabled sources
2. Runs metadata enrichment (MusicBrainz + Exa web search)
3. Downloads cover art from MusicBrainz Cover Art Archive
4. Backfills URL slugs for new records
5. Generates Open Graph images
6. Refreshes prices and availability for existing listings

Optional flags:
- `--skip-crawl` — skip the crawl phase, run enrichment only
- `--skip-enrichment` — skip metadata enrichment
- `--skip-image-enrichment` — skip MusicBrainz Cover Art Archive downloads
- `--skip-image-generation` — skip OG image generation

## Production Deployment

Run the full stack with Docker Compose:

```bash
# Copy and edit environment variables
cp .env.example .env  # create this with your secrets

# Start everything
docker compose up -d --build
```

Services:
- **db** — PostgreSQL 16 on port 5432
- **minio** — S3-compatible storage on port 9000 (console on 9001)
- **backend** — FastAPI on port 8000
- **worker** — Background scraper/enrichment process
- **frontend** — Next.js on port 3000

### Environment Variables

#### Backend / Worker

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://user:password@localhost/db` | Full database URL |
| `MUSICBRAINZ_APP_NAME` | `VinylScrape/1.0` | User-agent for MusicBrainz API |
| `ADMIN_API_KEY` | `changeme` | API key for admin endpoints |
| `S3_ENDPOINT_URL` | `http://localhost:9000` | S3-compatible endpoint |
| `S3_ACCESS_KEY` | `minioadmin` | S3 access key |
| `S3_SECRET_KEY` | `minioadmin` | S3 secret key |
| `S3_BUCKET` | `vinylscrape` | S3 bucket name |
| `S3_REGION` | `us-east-1` | S3 region |
| `S3_PUBLIC_URL` | *(auto)* | Public base URL for images (if unset, built from `S3_ENDPOINT_URL`/`S3_BUCKET`) |
| `EXA_API_KEY` | *(empty)* | [Exa](https://exa.ai) API key for web search enrichment (optional) |
| `SERPAPI_API_KEY` | *(empty)* | [SerpAPI](https://serpapi.com) API key for YouTube search (optional) |
| `SCRAPE_DELAY` | `1.0` | Seconds between HTTP requests during scraping |
| `SCRAPE_CONCURRENT` | `3` | Max concurrent scrapers |
| `FULL_SCRAPE_INTERVAL_HOURS` | `24` | Hours between full scrape cycles |
| `INCREMENTAL_SCRAPE_INTERVAL_HOURS` | `1` | Hours between incremental scrapes |
| `ENRICHMENT_INTERVAL_MINUTES` | `30` | Minutes between enrichment runs |
| `INCREMENTAL_PAGES` | `3` | Number of pages for incremental scrape |

#### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_URL` | `http://localhost:8000` | Backend URL for the Next.js API proxy |

### S3 / Image Storage

During scraping, all product images are downloaded from source websites and re-uploaded to S3-compatible storage. The `image_url` stored in the database points to the S3 object, not the original source.

Images are stored with content-addressed keys (`images/<sha256>.<ext>`), so identical images from different sources are automatically deduplicated.

**Local development** uses MinIO (started by `docker-compose.dev.yaml`). No additional configuration is needed — the defaults point at MinIO on `localhost:9000`.

**Production** — set the `S3_*` variables to point at your S3-compatible provider:

```bash
# AWS S3 example
S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_ACCESS_KEY=AKIA...
S3_SECRET_KEY=...
S3_BUCKET=vinylscrape-images
S3_REGION=eu-west-1
S3_PUBLIC_URL=https://vinylscrape-images.s3.eu-west-1.amazonaws.com

# Cloudflare R2 example
S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_BUCKET=vinylscrape
S3_PUBLIC_URL=https://cdn.example.com

# Self-hosted MinIO example
S3_ENDPOINT_URL=https://minio.example.com
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_BUCKET=vinylscrape
S3_PUBLIC_URL=https://minio.example.com/vinylscrape
```

The `S3_PUBLIC_URL` is what gets stored in the database as the image URL prefix. If your bucket is behind a CDN or has a custom domain, set this to the public-facing URL. If left unset, it defaults to `<S3_ENDPOINT_URL>/<S3_BUCKET>`.

### Enrichment APIs

The enrichment pipeline runs after scraping and fills in metadata that isn't available on the source websites. All enrichment APIs are **optional** — the system works without them, but data will be less complete.

The pipeline runs in order:

1. **MusicBrainz** (always enabled, no API key needed) — looks up the release by artist + title, extracts MusicBrainz ID, label, year, genres, and YouTube URLs from URL relations.

2. **Exa web search** (requires `EXA_API_KEY`) — fallback when MusicBrainz doesn't return label, year, or genres. Searches the web for vinyl release info and extracts structured data from the results. Get an API key at [exa.ai](https://exa.ai).

3. **SerpAPI YouTube search** (requires `SERPAPI_API_KEY`) — finds YouTube preview videos for records that don't already have a YouTube URL (from scraping or MusicBrainz). Uses SerpAPI's YouTube search engine. Get an API key at [serpapi.com](https://serpapi.com).

```bash
# .env example
EXA_API_KEY=your-exa-api-key
SERPAPI_API_KEY=your-serpapi-api-key
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/vinyl` | Search and filter vinyl records (supports `q`, `genre`, `source`, `in_stock`, `price_min`, `price_max`, `condition`, `sort`, `page`, `per_page`) |
| `GET` | `/api/v1/vinyl/{id}` | Vinyl detail with sources, prices, tracklist |
| `GET` | `/api/v1/vinyl/by-slug/{slug}` | Vinyl detail by URL slug |
| `GET` | `/api/v1/vinyl/sitemap` | All vinyl IDs and slugs for sitemap generation |
| `GET` | `/api/v1/genres` | List genres with vinyl counts (supports `q`, `source`, `in_stock`, `genre`, `condition` filters) |
| `GET` | `/api/v1/sources` | List shop sources |
| `GET` | `/api/v1/stats` | Overall statistics |
| `POST` | `/api/v1/admin/scrape` | Trigger manual scrape (requires `X-API-Key` header) |
| `GET` | `/api/v1/admin/scrape/status` | Check scraping status (requires `X-API-Key` header) |

## Database Migrations

```bash
cd backend

# Generate a new migration after model changes
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback one step
uv run alembic downgrade -1
```

## License

See [LICENSE](LICENSE).

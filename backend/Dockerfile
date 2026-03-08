FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project files
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic/ alembic/
COPY vinylscrape/ vinylscrape/

RUN uv sync --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "vinylscrape.main:app", "--host", "0.0.0.0", "--port", "8000"]

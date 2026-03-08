"""Shared HTTP helpers with retry + exponential backoff for scrapers."""

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Status codes that are worth retrying
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

# Default retry configuration
DEFAULT_MAX_RETRIES = 5
DEFAULT_BASE_DELAY = 2.0  # seconds
DEFAULT_MAX_DELAY = 120.0  # seconds


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    **kwargs: Any,
) -> httpx.Response:
    """Send an HTTP request with automatic retry on transient errors.

    Handles:
    - 429 Too Many Requests (respects Retry-After header)
    - 5xx Server Errors
    - Connection / timeout errors

    Uses exponential backoff with jitter between retries.
    """
    last_exc: BaseException | None = None

    for attempt in range(max_retries + 1):
        try:
            resp = await client.request(method, url, **kwargs)

            if resp.status_code not in _RETRYABLE_STATUS_CODES:
                return resp

            # Retryable HTTP status -- compute wait time
            if attempt >= max_retries:
                return resp  # out of retries, return as-is for caller to handle

            wait = _compute_wait(resp, attempt, base_delay, max_delay)
            logger.warning(
                "HTTP %d from %s (attempt %d/%d), retrying in %.1fs",
                resp.status_code,
                url,
                attempt + 1,
                max_retries + 1,
                wait,
            )
            await asyncio.sleep(wait)

        except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as exc:
            last_exc = exc
            if attempt >= max_retries:
                raise

            wait = _compute_backoff(attempt, base_delay, max_delay)
            logger.warning(
                "%s for %s (attempt %d/%d), retrying in %.1fs",
                type(exc).__name__,
                url,
                attempt + 1,
                max_retries + 1,
                wait,
            )
            await asyncio.sleep(wait)

    # Should not be reached, but just in case:
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("request_with_retry exhausted retries without a response")


def _compute_wait(
    resp: httpx.Response,
    attempt: int,
    base_delay: float,
    max_delay: float,
) -> float:
    """Compute wait time, respecting Retry-After header if present."""
    retry_after = resp.headers.get("retry-after")
    if retry_after is not None:
        try:
            wait = float(retry_after)
            # Clamp to max_delay to avoid absurdly long waits
            return min(wait, max_delay)
        except (ValueError, OverflowError):
            pass

    return _compute_backoff(attempt, base_delay, max_delay)


def _compute_backoff(attempt: int, base_delay: float, max_delay: float) -> float:
    """Exponential backoff: base_delay * 2^attempt, clamped to max_delay."""
    import random

    delay = base_delay * (2**attempt)
    # Add jitter: 75%-125% of computed delay
    delay *= 0.75 + random.random() * 0.5  # noqa: S311
    return min(delay, max_delay)

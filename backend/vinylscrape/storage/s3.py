import hashlib
import logging
from urllib.parse import urlparse

import aioboto3
import httpx

from vinylscrape.config import Config
from vinylscrape.scrapers.http import request_with_retry

logger = logging.getLogger(__name__)

# Map content-type to extension
_CONTENT_TYPE_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
}

# Map URL extension to content-type (fallback)
_EXT_CONTENT_TYPE = {v: k for k, v in _CONTENT_TYPE_EXT.items()}
_EXT_CONTENT_TYPE[".jpeg"] = "image/jpeg"


class ImageStorage:
    """Downloads images from URLs and re-uploads them to S3."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._session = aioboto3.Session()
        self._http = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "VinylScrape/1.0"},
            follow_redirects=True,
        )

    @property
    def _public_base(self) -> str:
        if self._config.s3_public_url:
            return self._config.s3_public_url.rstrip("/")
        return f"{self._config.s3_endpoint_url.rstrip('/')}/{self._config.s3_bucket}"

    def _s3_kwargs(self) -> dict[str, str]:
        return {
            "service_name": "s3",
            "endpoint_url": self._config.s3_endpoint_url,
            "aws_access_key_id": self._config.s3_access_key,
            "aws_secret_access_key": self._config.s3_secret_key,
            "region_name": self._config.s3_region,
        }

    async def ensure_bucket(self) -> None:
        """Create the bucket if it doesn't exist."""
        async with self._session.client(**self._s3_kwargs()) as s3:
            try:
                await s3.head_bucket(Bucket=self._config.s3_bucket)
            except Exception:
                logger.info("Creating S3 bucket: %s", self._config.s3_bucket)
                await s3.create_bucket(Bucket=self._config.s3_bucket)

    async def upload_image(self, source_url: str) -> str | None:
        """Download an image from source_url and upload to S3.

        Returns the public URL of the uploaded image, or None on failure.
        """
        try:
            resp = await request_with_retry(self._http, "GET", source_url)
            resp.raise_for_status()
        except Exception:
            logger.warning("Failed to download image: %s", source_url, exc_info=True)
            return None

        data = resp.content
        if not data:
            return None

        # Determine content type and extension
        content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
        ext = _CONTENT_TYPE_EXT.get(content_type)

        if not ext:
            # Fallback: guess from URL
            path = urlparse(source_url).path
            for candidate_ext in _EXT_CONTENT_TYPE:
                if path.lower().endswith(candidate_ext):
                    ext = candidate_ext
                    content_type = _EXT_CONTENT_TYPE[candidate_ext]
                    break

        if not ext:
            ext = ".jpg"
            content_type = "image/jpeg"

        # Content-addressed key: hash the image data so duplicates are deduplicated
        digest = hashlib.sha256(data).hexdigest()
        key = f"images/{digest}{ext}"

        try:
            async with self._session.client(**self._s3_kwargs()) as s3:
                # Check if already uploaded
                try:
                    await s3.head_object(Bucket=self._config.s3_bucket, Key=key)
                    logger.debug("Image already in S3: %s", key)
                    return f"{self._public_base}/{key}"
                except Exception:
                    pass

                await s3.put_object(
                    Bucket=self._config.s3_bucket,
                    Key=key,
                    Body=data,
                    ContentType=content_type,
                )
                logger.info("Uploaded image to S3: %s (%d bytes)", key, len(data))
                return f"{self._public_base}/{key}"
        except Exception:
            logger.warning("Failed to upload image to S3: %s", source_url, exc_info=True)
            return None

    async def close(self) -> None:
        await self._http.aclose()

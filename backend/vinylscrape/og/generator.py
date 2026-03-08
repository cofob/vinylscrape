"""OG image generator using Pillow.

Generates 1200x630 Open Graph preview images for vinyl records,
containing album cover, title, artist name, and VinylScrape branding.
"""

import io
import logging
import uuid
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

from vinylscrape.config import Config
from vinylscrape.storage.s3 import ImageStorage

logger = logging.getLogger(__name__)

_FONTS_DIR = Path(__file__).parent / "fonts"

# Canvas dimensions
WIDTH = 1200
HEIGHT = 630

# Layout
COVER_SIZE = 420
COVER_X = 60
COVER_Y = (HEIGHT - COVER_SIZE) // 2  # vertically centred

TEXT_X = COVER_X + COVER_SIZE + 60
TEXT_MAX_WIDTH = WIDTH - TEXT_X - 60

# Colours
BG_COLOR = (23, 23, 23)  # #171717
ARTIST_COLOR = (217, 119, 6)  # #d97706 amber
TITLE_COLOR = (255, 255, 255)  # white
BRAND_COLOR = (115, 115, 115)  # neutral-500

# Font sizes
ARTIST_FONT_SIZE = 36
TITLE_FONT_SIZE = 52
BRAND_FONT_SIZE = 28


def _load_font(bold: bool = False, size: int = 36) -> ImageFont.FreeTypeFont:
    filename = "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"
    path = _FONTS_DIR / filename
    return ImageFont.truetype(str(path), size=size)


def _wrap_text(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int
) -> list[str]:
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


class OgImageGenerator:
    """Generates 1200x630 OG preview images for vinyl records."""

    def __init__(self, image_storage: ImageStorage, config: Config) -> None:
        self._storage = image_storage
        self._config = config
        self._http = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "VinylScrape/1.0"},
        )

    async def generate(
        self,
        vinyl_id: uuid.UUID,
        title: str,
        artist: str,
        image_url: str | None,
    ) -> str | None:
        """Generate OG image and upload to S3. Returns public URL or None on failure."""
        try:
            return await self._generate(vinyl_id, title, artist, image_url)
        except Exception:
            logger.exception("Failed to generate OG image for vinyl %s", vinyl_id)
            return None

    async def _generate(
        self,
        vinyl_id: uuid.UUID,
        title: str,
        artist: str,
        image_url: str | None,
    ) -> str | None:
        # 1. Create canvas
        img = Image.new("RGB", (WIDTH, HEIGHT), color=BG_COLOR)
        draw = ImageDraw.Draw(img)

        # 2. Draw album cover on left side
        if image_url:
            cover = await self._download_image(image_url)
            if cover:
                cover = cover.convert("RGB")
                cover = cover.resize((COVER_SIZE, COVER_SIZE), Image.LANCZOS)
                img.paste(cover, (COVER_X, COVER_Y))

        # 3. Load fonts
        artist_font = _load_font(bold=False, size=ARTIST_FONT_SIZE)
        title_font = _load_font(bold=True, size=TITLE_FONT_SIZE)
        brand_font = _load_font(bold=False, size=BRAND_FONT_SIZE)

        # 4. Draw text on right side
        y = 140

        # Artist
        artist_lines = _wrap_text(draw, artist, artist_font, TEXT_MAX_WIDTH)
        for line in artist_lines[:2]:  # at most 2 lines
            draw.text((TEXT_X, y), line, font=artist_font, fill=ARTIST_COLOR)
            bbox = draw.textbbox((TEXT_X, y), line, font=artist_font)
            y += (bbox[3] - bbox[1]) + 8
        y += 12

        # Title
        title_lines = _wrap_text(draw, title, title_font, TEXT_MAX_WIDTH)
        for line in title_lines[:4]:  # at most 4 lines
            draw.text((TEXT_X, y), line, font=title_font, fill=TITLE_COLOR)
            bbox = draw.textbbox((TEXT_X, y), line, font=title_font)
            y += (bbox[3] - bbox[1]) + 10

        # Branding at bottom right
        brand_text = "VinylScrape"
        brand_bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
        brand_w = brand_bbox[2] - brand_bbox[0]
        draw.text(
            (WIDTH - brand_w - 40, HEIGHT - 60), brand_text, font=brand_font, fill=BRAND_COLOR
        )

        # 5. Save to bytes
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        data = buf.getvalue()

        # 6. Upload to S3 under og/{vinyl_id}.png
        key = f"og/{vinyl_id}.png"
        try:
            async with self._storage._session.client(**self._storage._s3_kwargs()) as s3:
                await s3.put_object(
                    Bucket=self._storage._config.s3_bucket,
                    Key=key,
                    Body=data,
                    ContentType="image/png",
                )
            logger.info("Uploaded OG image to S3: %s (%d bytes)", key, len(data))
            return f"{self._storage._public_base}/{key}"
        except Exception:
            logger.exception("Failed to upload OG image to S3 for vinyl %s", vinyl_id)
            return None

    async def _download_image(self, url: str) -> Image.Image | None:
        try:
            resp = await self._http.get(url)
            resp.raise_for_status()
            return Image.open(io.BytesIO(resp.content))
        except Exception:
            logger.warning("Failed to download image for OG generation: %s", url)
            return None

    async def close(self) -> None:
        await self._http.aclose()

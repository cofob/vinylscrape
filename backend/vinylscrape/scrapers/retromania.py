import logging
import re
from decimal import Decimal, InvalidOperation

import httpx
from bs4 import BeautifulSoup, Tag

from vinylscrape.scrapers.base import (
    BaseScraper,
    ScrapedTrack,
    ScrapedVinylDetail,
    ScrapedVinylListing,
)
from vinylscrape.scrapers.http import request_with_retry
from vinylscrape.scrapers.registry import register_scraper

logger = logging.getLogger(__name__)

BASE_URL = "https://retromania.ge"
CATEGORY_URL = f"{BASE_URL}/product-category/vinyls"


def _tag_attr_str(tag: Tag | None, attr: str) -> str | None:
    if tag is None:
        return None
    value = tag.get(attr)
    return value if isinstance(value, str) else None


def _tag_attr_tokens(tag: Tag | None, attr: str) -> list[str]:
    if tag is None:
        return []
    value = tag.get(attr)
    if isinstance(value, str):
        return value.split()
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


# Map Georgian category slug -> English genre name
_GENRE_MAP: dict[str, str] = {
    "rock": "Rock",
    "pop": "Pop",
    "jazz": "Jazz",
    "blues": "Blues",
    "electronic": "Electronic",
    "hip-hop": "Hip-Hop",
    "folk": "Folk",
    "country": "Country",
    "rock-and-roll": "Rock and Roll",
    "soundtracks": "Soundtrack",
    "classic": "Classical",
    "punk": "Punk",
    "soul": "Soul",
    "metal": "Metal",
    "reggae": "Reggae",
    "disco": "Disco",
    "funk": "Funk",
    "r-n-b": "R&B",
}

# Categories that are NOT genres (should be skipped)
_SKIP_CATEGORIES: set[str] = {
    "vinyls",
    "akhali-presebi",  # "new pressings"
    "dzveli-presebi",  # "old/collectible pressings"
    "cd-diskebi",  # "CD discs"
}

# Map long-form condition text (in parentheses) -> Goldmine abbreviation
_CONDITION_MAP: dict[str, str] = {
    "mint": "M",
    "near mint": "NM",
    "excellent": "EX",
    "very good +": "VG+",
    "very good plus": "VG+",
    "very good": "VG",
    "good +": "G+",
    "good plus": "G+",
    "good": "G",
    "fair": "F",
    "poor": "P",
}


def _parse_artist_title(raw: str) -> tuple[str, str]:
    """Parse 'Artist – Title' or 'Artist - Title' format."""
    for sep in [" \u2013 ", " \u2014 ", " - "]:
        if sep in raw:
            parts = raw.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    return "", raw.strip()


def _parse_price(text: str) -> Decimal | None:
    """Extract numeric price from text like '125,00 ₾'.

    Retromania uses comma as decimal separator (e.g. '125,00').
    """
    # Replace comma with dot for decimal parsing
    cleaned = text.strip()
    cleaned = re.sub(r"[^\d,.]", "", cleaned)
    # Handle Georgian comma-as-decimal format: "125,00" -> "125.00"
    if "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    if cleaned:
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            pass
    return None


def _map_condition(raw: str) -> str | None:
    """Map a condition string from the website to a Goldmine abbreviation.

    The website uses formats like:
      - "ახალი (Mint)" -> "M"
      - "ძალიან კარგი + (VG+)" -> "VG+"
      - "შესანიშნავი (EX)" -> "EX"

    First tries to extract a parenthesized English term and map it,
    then falls back to checking if the raw text is already a grade code.
    """
    if not raw:
        return None

    # Try to extract English condition from parentheses, e.g. "(Mint)", "(VG+)"
    paren_match = re.search(r"\(([^)]+)\)", raw)
    if paren_match:
        inner = paren_match.group(1).strip()
        # Check if it's already a Goldmine abbreviation
        upper = inner.upper()
        if upper in ("M", "NM", "EX", "VG+", "VG", "G+", "G", "F", "P"):
            return upper
        # Map long-form English name
        mapped = _CONDITION_MAP.get(inner.lower())
        if mapped:
            return mapped

    # Fallback: check if raw text itself is a grade code
    raw_upper = raw.strip().upper()
    if raw_upper in ("M", "NM", "EX", "VG+", "VG", "G+", "G", "F", "P"):
        return raw_upper

    return None


def _extract_genre_from_slug(slug: str) -> str | None:
    """Convert a WooCommerce category slug to a genre name."""
    if slug in _SKIP_CATEGORIES:
        return None
    return _GENRE_MAP.get(slug)


def _extract_youtube_id(url: str) -> str | None:
    """Extract YouTube video ID from an embed or watch URL."""
    m = re.search(r"(?:youtube\.com/embed/|youtube\.com/watch\?v=|youtu\.be/)([\w-]+)", url)
    return m.group(1) if m else None


def _parse_description_field(desc_text: str, key: str) -> str | None:
    """Extract a field value from the short description text.

    Handles various whitespace/punctuation inconsistencies:
      - "ლეიბლი – Warner"
      - "ლეიბლი –Warner"  (no space after dash)
      - "ლეიბლი- Warner"  (dash attached to key)
    """
    # Match key followed by optional spaces, a dash/en-dash/em-dash, optional spaces, then value
    pattern = rf"{re.escape(key)}\s*[-–—]\s*(.+?)(?:\n|$)"
    match = re.search(pattern, desc_text)
    if match:
        return match.group(1).strip()
    return None


@register_scraper("retromania")
class RetromaniaScraper(BaseScraper):
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "VinylScrape/1.0"},
            follow_redirects=True,
        )
        self._total_pages: int | None = None

    async def get_total_pages(self) -> int | None:
        if self._total_pages is not None:
            return self._total_pages

        resp = await request_with_retry(self._client, "GET", f"{CATEGORY_URL}/")
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Retromania uses <a class="page-numbers"> inside <div class="page_links">
        pages = soup.select("a.page-numbers:not(.next):not(.prev)")
        if pages:
            # The last numeric page link gives us total pages
            last_text = pages[-1].get_text(strip=True)
            try:
                self._total_pages = int(last_text)
            except ValueError:
                pass

        return self._total_pages

    async def scrape_listing(self, page: int) -> list[ScrapedVinylListing]:
        url = f"{CATEGORY_URL}/page/{page}/" if page > 1 else f"{CATEGORY_URL}/"
        logger.info("Scraping retromania listing page: %s", url)

        resp = await request_with_retry(self._client, "GET", url)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        items: list[ScrapedVinylListing] = []

        for li in soup.select("ul.products li.product"):
            try:
                item = self._parse_listing_item(li)
                if item:
                    items.append(item)
            except Exception:
                logger.exception("Failed to parse retromania listing item")
                continue

        logger.info("Found %d items on page %d", len(items), page)
        return items

    def _parse_listing_item(self, li: Tag) -> ScrapedVinylListing | None:
        # Title and detail URL
        title_el = li.select_one("h3.woo_product_post_title a, h3.posts_grid_post_title a")
        if not title_el:
            return None
        raw_title = title_el.get_text(strip=True)
        artist, title = _parse_artist_title(raw_title)

        detail_url = _tag_attr_str(title_el, "href")

        # Price
        price_el = li.select_one(".woocommerce-Price-amount bdi")
        price = Decimal("0")
        if price_el:
            p = _parse_price(price_el.get_text())
            if p is not None:
                price = p

        # Image — retromania uses lazy loading (data-lazy-src)
        image_url = None
        img_el = li.select_one(".woo_product_post_media img")
        if img_el:
            image_url = (
                _tag_attr_str(img_el, "data-lazy-src")
                or _tag_attr_str(img_el, "data-src")
                or _tag_attr_str(img_el, "src")
            )
        # Fallback: try noscript img
        if not image_url:
            noscript = li.select_one("noscript")
            if noscript:
                noscript_soup = BeautifulSoup(str(noscript), "lxml")
                ns_img = noscript_soup.select_one("img")
                if ns_img:
                    image_url = _tag_attr_str(ns_img, "src")

        # Stock status from CSS classes on the <li>
        classes = _tag_attr_tokens(li, "class")
        in_stock = "outofstock" not in classes

        return ScrapedVinylListing(
            title=title,
            artist=artist,
            price=price,
            currency="GEL",
            image_url=image_url,
            detail_url=detail_url,
            in_stock=in_stock,
        )

    async def scrape_detail(self, url: str) -> ScrapedVinylDetail:
        logger.info("Scraping retromania detail page: %s", url)
        resp = await request_with_retry(self._client, "GET", url)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        # Title
        title_el = soup.select_one("h1.product_title")
        raw_title = title_el.get_text(strip=True) if title_el else ""
        artist, title = _parse_artist_title(raw_title)

        # Price
        price_el = soup.select_one("p.price .woocommerce-Price-amount bdi")
        price = Decimal("0")
        if price_el:
            p = _parse_price(price_el.get_text())
            if p is not None:
                price = p

        # Image — prefer data-large_image on gallery img
        image_url = None
        gallery_img = soup.select_one(".woocommerce-product-gallery__image img")
        if gallery_img:
            image_url = (
                _tag_attr_str(gallery_img, "data-large_image")
                or _tag_attr_str(gallery_img, "data-lazy-src")
                or _tag_attr_str(gallery_img, "data-src")
                or _tag_attr_str(gallery_img, "src")
            )

        # Stock status
        in_stock = True
        stock_el = soup.select_one("p.stock")
        if stock_el:
            in_stock = "in-stock" in _tag_attr_tokens(stock_el, "class")
        else:
            # Fallback: check product div classes
            product_div = soup.select_one("div.product")
            if product_div:
                product_classes = _tag_attr_tokens(product_div, "class")
                if "outofstock" in product_classes:
                    in_stock = False

        # Parse short description fields (Georgian key-value format)
        label = None
        catalog_number = None
        year = None
        condition = None

        desc_el = soup.select_one(".woocommerce-product-details__short-description")
        if desc_el:
            desc_text = desc_el.get_text()

            # Label: "ლეიბლი – Warner Bros Records / K 56344"
            label_raw = _parse_description_field(desc_text, "ლეიბლი")
            if label_raw:
                if "/" in label_raw:
                    parts = label_raw.rsplit("/", 1)
                    label = parts[0].strip()
                    catalog_number = parts[1].strip()
                else:
                    label = label_raw

            # Year: "წელი – 2015"
            year_raw = _parse_description_field(desc_text, "წელი")
            if year_raw:
                year_match = re.search(r"\d{4}", year_raw)
                if year_match:
                    year = int(year_match.group())

            # Condition: "მდგომარეობა – ახალი (Mint)"
            cond_raw = _parse_description_field(desc_text, "მდგომარეობა")
            if cond_raw:
                condition = _map_condition(cond_raw)

        # Genres — from category links in product meta
        genres: list[str] = []
        for cat_link in soup.select(".posted_in a"):
            href = _tag_attr_str(cat_link, "href") or ""
            slug_match = re.search(r"/product-category/([^/]+)/?$", href)
            if slug_match:
                slug = slug_match.group(1)
                genre = _extract_genre_from_slug(slug)
                if genre and genre not in genres:
                    genres.append(genre)

        # YouTube — from iframe in description tab
        youtube_url = None
        yt_iframe = soup.select_one('#tab-description iframe[src*="youtube"]')
        if not yt_iframe:
            # Fallback: any YouTube iframe on the page
            yt_iframe = soup.select_one('iframe[src*="youtube"]')
        if yt_iframe:
            yt_src = _tag_attr_str(yt_iframe, "src") or ""
            yt_id = _extract_youtube_id(yt_src)
            if yt_id:
                youtube_url = f"https://www.youtube.com/watch?v={yt_id}"

        # Tracklist — retromania doesn't have structured tracklists,
        # so we return an empty list (enrichment pipeline will handle this)
        tracklist: list[ScrapedTrack] = []

        return ScrapedVinylDetail(
            title=title,
            artist=artist,
            price=price,
            currency="GEL",
            image_url=image_url,
            detail_url=url,
            in_stock=in_stock,
            label=label,
            catalog_number=catalog_number,
            year=year,
            condition=condition,
            genres=genres,
            tracklist=tracklist,
            youtube_url=youtube_url,
        )

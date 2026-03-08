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

BASE_URL = "https://morevi.ge"


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


def _parse_artist_title(raw: str) -> tuple[str, str]:
    """Parse 'Artist – Title' or 'Artist - Title' format."""
    # Try en-dash first, then regular dash
    for sep in ["\u2013", "\u2014", " - ", " – "]:
        if sep in raw:
            parts = raw.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    return "", raw.strip()


def _parse_price(text: str) -> Decimal | None:
    """Extract numeric price from text like '₾ 49.99' or '29.99₾'."""
    cleaned = re.sub(r"[^\d.]", "", text.strip())
    if cleaned:
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            pass
    return None


@register_scraper("morevi")
class MoreviScraper(BaseScraper):
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

        # Fetch page 1 to determine total pages
        resp = await request_with_retry(self._client, "GET", f"{BASE_URL}/shop/")
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Try to find total from pagination
        pages = soup.select("ul.page-numbers a.page-numbers:not(.next):not(.prev)")
        if pages:
            last_page_text = pages[-1].get_text(strip=True)
            try:
                self._total_pages = int(last_page_text)
            except ValueError:
                pass

        # Fallback: parse result count
        if self._total_pages is None:
            count_el = soup.select_one("p.woocommerce-result-count")
            if count_el:
                match = re.search(r"of\s+(\d+)", count_el.get_text())
                if match:
                    total_items = int(match.group(1))
                    self._total_pages = (total_items + 15) // 16  # 16 per page

        return self._total_pages

    async def scrape_listing(self, page: int) -> list[ScrapedVinylListing]:
        url = f"{BASE_URL}/shop/page/{page}" if page > 1 else f"{BASE_URL}/shop/"
        logger.info("Scraping listing page: %s", url)

        resp = await request_with_retry(self._client, "GET", url)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        items: list[ScrapedVinylListing] = []

        for li in soup.select("li.home_small_box"):
            try:
                item = self._parse_listing_item(li)
                if item:
                    items.append(item)
            except Exception:
                logger.exception("Failed to parse listing item")
                continue

        logger.info("Found %d items on page %d", len(items), page)
        return items

    def _parse_listing_item(self, li: Tag) -> ScrapedVinylListing | None:
        # Title and artist
        title_el = li.select_one(".sb_title a")
        if not title_el:
            return None
        raw_title = title_el.get_text(strip=True)
        artist, title = _parse_artist_title(raw_title)

        # Detail URL
        detail_url = _tag_attr_str(title_el, "href")

        # Price
        price_el = li.select_one(".sb_price .woocommerce-Price-amount")
        price = None
        if price_el:
            price = _parse_price(price_el.get_text())
        if price is None:
            price = Decimal("0")

        # Image
        img_el = li.select_one("img.wp-post-image")
        image_url = _tag_attr_str(img_el, "src")

        # In stock: absence of soldout span means in stock
        sold_out = li.select_one("span.soldout") is not None

        return ScrapedVinylListing(
            title=title,
            artist=artist,
            price=price,
            currency="GEL",
            image_url=image_url,
            detail_url=detail_url,
            in_stock=not sold_out,
        )

    async def scrape_detail(self, url: str) -> ScrapedVinylDetail:
        logger.info("Scraping detail page: %s", url)
        resp = await request_with_retry(self._client, "GET", url)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        # Title
        title_el = soup.select_one("h1.product_title")
        raw_title = title_el.get_text(strip=True) if title_el else ""
        artist, title = _parse_artist_title(raw_title)

        # Price
        price_el = soup.select_one(".price .woocommerce-Price-amount")
        price = _parse_price(price_el.get_text()) if price_el else None
        if price is None:
            price = Decimal("0")

        # Image
        img_el = soup.select_one(".woocommerce-product-gallery__image img")
        image_url = _tag_attr_str(img_el, "data-large_image") or _tag_attr_str(img_el, "src")

        # Stock status
        in_stock = True
        stock_el = soup.select_one(".stock")
        if stock_el:
            in_stock = "in-stock" in _tag_attr_tokens(stock_el, "class")

        # Description: label, year, condition
        label = None
        catalog_number = None
        year = None
        condition = None

        desc_el = soup.select_one(".woocommerce-product-details__short-description")
        if desc_el:
            desc_text = desc_el.get_text()

            # Label and catalog number
            # "ლეიბლი – Brouqade Records / BQD044"
            label_match = re.search(r"ლეიბლი\s*[-–—]\s*(.+?)(?:\n|$)", desc_text)
            if label_match:
                label_raw = label_match.group(1).strip()
                if "/" in label_raw:
                    parts = label_raw.rsplit("/", 1)
                    label = parts[0].strip()
                    catalog_number = parts[1].strip()
                else:
                    label = label_raw

            # Year: "წელი – 2018"
            year_match = re.search(r"წელი\s*[-–—]\s*(\d{4})", desc_text)
            if year_match:
                year = int(year_match.group(1))

            # Condition: "მდგომარეობა ... (VG)"
            cond_match = re.search(r"\(([A-Z+]+)\)", desc_text)
            if cond_match:
                condition = cond_match.group(1)

        # Genres from categories
        genres: list[str] = []
        for cat_link in soup.select(".posted_in a[rel=tag]"):
            genre_text = cat_link.get_text(strip=True)
            if genre_text and genre_text.lower() not in ("uncategorized",):
                genres.append(genre_text)

        # Tracklist
        tracklist: list[ScrapedTrack] = []
        for tr in soup.select("table.playlist tr"):
            pos_el = tr.select_one(".tracklist_track_pos")
            title_el = tr.select_one(".tracklist_track_title")
            if pos_el and title_el:
                yt_link = title_el.select_one("a[href*='youtube.com']")
                tracklist.append(
                    ScrapedTrack(
                        position=pos_el.get_text(strip=True),
                        title=title_el.get_text(strip=True),
                        youtube_url=_tag_attr_str(yt_link, "href"),
                    )
                )

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
        )

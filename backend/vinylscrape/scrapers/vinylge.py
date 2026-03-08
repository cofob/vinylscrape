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

BASE_URL = "https://vinyl.ge"
CATEGORY_URL = f"{BASE_URL}/product-category/vinyl-records"


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


# Map Georgian category slug → English genre name
_GENRE_MAP: dict[str, str] = {
    "rock": "Rock",
    "jazz": "Jazz",
    "blues": "Blues",
    "metal": "Metal",
    "pop": "Pop",
    "reggae": "Reggae",
    "electronic": "Electronic",
    "georgian": "Georgian",
    "soul": "Soul",
    "hip-hop": "Hip-Hop",
    "disco": "Disco",
    "classic": "Classical",
    "for-children": "Children",
    "other": "Other",
    "sale": "Sale",
}


_CONDITION_TOKENS = {
    "sealed",
    "remaster",
    "remastered",
    "reissue",
    "deluxe",
    "jp",
    "ussr",
    "uk",
    "us",
    "eu",
    "ger",
    "2lp",
    "3lp",
    "3 lp",
    "2 lp",
    "original",
    "original press",
    "first press",
    "colored",
    "coloured",
    "limited",
    "limited edition",
    "gatefold",
    "mono",
    "stereo",
    "180g",
    "180 gram",
    "promo",
    "test pressing",
    "picture disc",
    "box set",
    "anniversary",
}


def _strip_condition_suffix(title: str) -> tuple[str, list[str]]:
    """Strip trailing parenthetical condition/format markers from a title.

    Returns (cleaned_title, list_of_extracted_tokens).

    Only the *last* parenthetical group is considered, and only if every
    comma-separated token inside it is a known condition/format keyword
    (or matches patterns like '2LP', '50th Anniversary', year-like numbers).
    Legitimate title parts like '(The Black Album)' or '(Soundtrack)' are
    left untouched.
    """
    m = re.search(r"\s*\(([^)]+)\)\s*$", title)
    if not m:
        return title, []

    inner = m.group(1)
    tokens = [t.strip() for t in inner.split(",")]
    extracted: list[str] = []

    for tok in tokens:
        tok_lower = tok.lower().strip()
        # Direct match against known tokens
        if tok_lower in _CONDITION_TOKENS:
            extracted.append(tok)
            continue
        # Pattern: "Nth Anniversary" (e.g. "50th Anniversary", "10th Anniversary Edition")
        if re.match(r"\d+\w*\s+anniversary(\s+edition)?$", tok_lower):
            extracted.append(tok)
            continue
        # Pattern: "YYYY Remaster" (e.g. "2023 Remaster")
        if re.match(r"\d{4}\s+remaster(ed)?$", tok_lower):
            extracted.append(tok)
            continue
        # Not a condition token — the whole parenthetical is part of the title
        return title, []

    cleaned = title[: m.start()].strip()
    return cleaned, extracted


def _parse_artist_title(raw: str) -> tuple[str, str, list[str]]:
    """Parse 'Artist – Title (Condition)' format.

    Returns (artist, title, condition_tokens).

    vinyl.ge uses a regular hyphen surrounded by spaces on detail pages
    and an HTML en-dash (&#8211;) on listing pages.  After BS4 decoding
    both become Unicode characters.
    """
    for sep in [" \u2013 ", " \u2014 ", " - "]:
        if sep in raw:
            parts = raw.split(sep, 1)
            artist = parts[0].strip()
            title_raw = parts[1].strip()
            title, cond_tokens = _strip_condition_suffix(title_raw)
            return artist, title, cond_tokens
    title, cond_tokens = _strip_condition_suffix(raw.strip())
    return "", title, cond_tokens


def _parse_price(text: str) -> Decimal | None:
    """Extract numeric price from text like '85 GEL' or '85₾'."""
    cleaned = re.sub(r"[^\d.]", "", text.strip())
    if cleaned:
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            pass
    return None


def _full_size_image_url(thumb_url: str) -> str:
    """Strip WooCommerce dimension suffix (-300x300) from thumbnail URL."""
    return re.sub(r"-\d+x\d+(\.\w+)$", r"\1", thumb_url)


def _extract_genre_from_slug(slug: str) -> str | None:
    """Convert a WooCommerce category slug to a genre name."""
    return _GENRE_MAP.get(slug)


def _extract_youtube_id(url: str) -> str | None:
    """Extract YouTube video ID from an embed or watch URL."""
    m = re.search(r"(?:youtube\.com/embed/|youtube\.com/watch\?v=|youtu\.be/)([\w-]+)", url)
    return m.group(1) if m else None


@register_scraper("vinylge")
class VinylGeScraper(BaseScraper):
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

        # Try pagination links: <a class="page-numbers">N</a>
        pages = soup.select("ul.page-numbers a.page-numbers:not(.next):not(.prev)")
        if pages:
            last_text = pages[-1].get_text(strip=True)
            try:
                self._total_pages = int(last_text)
            except ValueError:
                pass

        # Fallback: check <link rel="next"> to know there's at least page 2
        if self._total_pages is None:
            next_link = soup.select_one('link[rel="next"]')
            if next_link:
                # We know there are at least 2 pages; we'll discover more as we go
                self._total_pages = None  # unknown, will paginate until empty

        return self._total_pages

    async def scrape_listing(self, page: int) -> list[ScrapedVinylListing]:
        url = f"{CATEGORY_URL}/page/{page}/" if page > 1 else f"{CATEGORY_URL}/"
        logger.info("Scraping vinyl.ge listing page: %s", url)

        resp = await request_with_retry(self._client, "GET", url)
        if resp.status_code == 404:
            # Past the last page
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
                logger.exception("Failed to parse vinyl.ge listing item")
                continue

        logger.info("Found %d items on page %d", len(items), page)

        # Dynamically discover total pages from pagination on the first page
        if self._total_pages is None:
            pag_links = soup.select("ul.page-numbers a.page-numbers:not(.next):not(.prev)")
            if pag_links:
                try:
                    self._total_pages = int(pag_links[-1].get_text(strip=True))
                except ValueError:
                    pass

        return items

    def _parse_listing_item(self, li: Tag) -> ScrapedVinylListing | None:
        # Title
        title_el = li.select_one("h2.woocommerce-loop-product__title")
        if not title_el:
            return None
        raw_title = title_el.get_text(strip=True)
        artist, title, _cond_tokens = _parse_artist_title(raw_title)

        # Detail URL
        link_el = li.select_one("a.woocommerce-LoopProduct-link")
        detail_url = _tag_attr_str(link_el, "href")

        # Price
        price_el = li.select_one("span.price bdi")
        price = Decimal("0")
        if price_el:
            p = _parse_price(price_el.get_text())
            if p is not None:
                price = p

        # Image — get full-size from thumbnail src
        img_el = li.select_one("img.attachment-woocommerce_thumbnail")
        image_url = None
        if img_el:
            src = _tag_attr_str(img_el, "src")
            if src:
                image_url = _full_size_image_url(src)

        # Stock status — from <li> class list
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
        logger.info("Scraping vinyl.ge detail page: %s", url)
        resp = await request_with_retry(self._client, "GET", url)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        # Title
        title_el = soup.select_one("h1.product_title")
        raw_title = title_el.get_text(strip=True) if title_el else ""
        artist, title, cond_tokens = _parse_artist_title(raw_title)

        # Price
        price_el = soup.select_one(".price bdi")
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
                or _tag_attr_str(gallery_img, "data-src")
                or _tag_attr_str(gallery_img, "src")
            )

        # Stock status — use the main product wrapper (Elementor single-product
        # template or WooCommerce div.product) which has "instock" / "outofstock".
        # We must NOT look at span.custom-out-of-stock globally because related
        # products at the bottom also contain those spans.
        in_stock = True
        product_div = soup.select_one("[data-elementor-type='product']") or soup.select_one(
            "div.product"
        )
        if product_div:
            product_classes = _tag_attr_tokens(product_div, "class")
            if "outofstock" in product_classes:
                in_stock = False
        # Also check the WooCommerce stock paragraph inside the main product summary
        summary = soup.select_one(
            ".summary, .product-info, .elementor-widget-woocommerce-product-meta"
        )
        if summary:
            stock_el = summary.select_one("p.stock.out-of-stock")
            if stock_el:
                in_stock = False

        # Genres — from category links in product_meta
        genres: list[str] = []
        for cat_link in soup.select("div.product_meta span.posted_in a[rel='tag']"):
            href = _tag_attr_str(cat_link, "href") or ""
            # Extract slug from URL like /product-category/vinyl-records/jazz/
            slug_match = re.search(r"/product-category/(?:vinyl-records/)?([^/]+)/?$", href)
            if slug_match:
                slug = slug_match.group(1)
                # Skip the parent "vinyl-records" category itself
                if slug == "vinyl-records":
                    continue
                genre = _extract_genre_from_slug(slug)
                if genre and genre not in genres:
                    genres.append(genre)

        # Attributes table — label, year, condition
        label = None
        catalog_number = None
        year = None
        condition = None

        attr_table = soup.select_one("table.woocommerce-product-attributes")
        if attr_table:
            for row in attr_table.select("tr"):
                row_classes = " ".join(_tag_attr_tokens(row, "class"))
                td = row.select_one("td p")
                if not td:
                    td = row.select_one("td")
                if not td:
                    continue
                val = td.get_text(strip=True)

                if "attribute_pa_vinyl-label" in row_classes:
                    label = val
                elif "attribute_pa_vinyl-year" in row_classes:
                    year_match = re.search(r"\d{4}", val)
                    if year_match:
                        year = int(year_match.group())
                elif "attribute_pa_vinyl-condition" in row_classes:
                    # Try to extract grading code like "VG+", "NM", "N"
                    cond_match = re.search(r"\b([A-Z][A-Z+]*)\b", val)
                    if cond_match:
                        condition = cond_match.group(1)
                    else:
                        condition = val

        # Fallback: infer condition from title suffix tokens like "(Sealed)"
        if not condition and cond_tokens:
            lowered = {t.lower() for t in cond_tokens}
            if "sealed" in lowered:
                condition = "M"  # Sealed = Mint

        # Tracklist — from short description (tracks separated by <br>)
        tracklist: list[ScrapedTrack] = []
        short_desc = soup.select_one(".woocommerce-product-details__short-description")
        if short_desc:
            # Get all text nodes separated by <br> tags
            # We need the raw HTML to split on <br>
            desc_html = short_desc.decode_contents()
            # Split on <br>, <br/>, <br />
            lines = re.split(r"<br\s*/?>", desc_html)
            position = 1
            for line in lines:
                # Strip HTML tags and whitespace
                track_title = re.sub(r"<[^>]+>", "", line).strip()
                if track_title:
                    tracklist.append(
                        ScrapedTrack(
                            position=str(position),
                            title=track_title,
                        )
                    )
                    position += 1

        # YouTube embed — "Listen before buying"
        youtube_url = None
        yt_iframe = soup.select_one('iframe[src*="youtube"]')
        if yt_iframe:
            yt_src = _tag_attr_str(yt_iframe, "src") or ""
            yt_id = _extract_youtube_id(yt_src)
            if yt_id:
                youtube_url = f"https://www.youtube.com/watch?v={yt_id}"

        # Attach the YouTube URL to the first track if we have a tracklist,
        # otherwise store it — the enrichment pipeline will pick it up later.
        # For consistency with morevi scraper, we store it on tracks.
        # But since we have one embed for the whole album, attach to first track.
        if youtube_url and tracklist and not tracklist[0].youtube_url:
            tracklist[0] = ScrapedTrack(
                position=tracklist[0].position,
                title=tracklist[0].title,
                duration=tracklist[0].duration,
                youtube_url=youtube_url,
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
            youtube_url=youtube_url,
        )

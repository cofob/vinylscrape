import logging
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

import httpx

from vinylscrape.scrapers.base import (
    BaseScraper,
    ScrapedTrack,
    ScrapedVinylDetail,
    ScrapedVinylListing,
)
from vinylscrape.scrapers.http import request_with_retry
from vinylscrape.scrapers.registry import register_scraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.vodkast.ge"
GRAPHQL_URL = "https://api-client.common-ground.io/graphql"
PAGE_SIZE = 80

_GRAPHQL_HEADERS = {
    "User-Agent": "VinylScrape/1.0",
    "content-type": "application/json",
    "commonground-origin": "www.vodkast.ge",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/",
}

_FILTERS = {
    "styles": [],
    "artists": [],
    "genres": [],
    "labels": [],
    "years": [],
    "formats": [],
    "formatDescriptions": [],
    "countries": [],
    "manufacturers": [],
    "types": [],
    "itemTypes": [],
    "categories": [],
    "stock": "instock",
    "from": "",
    "preorders": "false",
    "type": "All",
    "wantlist": False,
}

_PAGINATION_QUERY = """
query inventoryFiltersPagination($filters: InventoryFiltersInput!, $pagination: PaginationInput!) {
  inventoryFiltersPagination(filters: $filters, pagination: $pagination) {
    pages
    __typename
  }
}
"""

_LISTING_QUERY = """
query inventoryItems($filters: InventoryFiltersInput!, $pagination: PaginationInput!) {
  inventoryItems(filters: $filters, pagination: $pagination) {
    items {
      _id
      id
      type
      path
      uri
      listings {
        available
        secondHand
        stock {
          quantity
          __typename
        }
        prices {
          beforeTaxes
          sale
          compare
          __typename
        }
        options {
          name
          value
          __typename
        }
        comments
        __typename
      }
      data {
        title
        images {
          uri
          alternative {
            uri
            __typename
          }
          __typename
        }
        genres
        styles
        releaseDate
        formats {
          descriptions
          name
          qty
          __typename
        }
        country
        artists {
          name
          anv
          id
          join
          __typename
        }
        labels {
          name
          id
          catno
          __typename
        }
        videos {
          uri
          __typename
        }
        __typename
      }
      descriptions {
        main
        shop {
          text
          html
          short
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
}
"""

_DETAIL_QUERY = """
query item($id: Float!) {
  item(id: $id) {
    _id
    id
    type
    path
    uri
    created
    listings {
      _id
      id
      available
      secondHand
      stock {
        quantity
        __typename
      }
      prices {
        beforeTaxes
        sale
        compare
        __typename
      }
      options {
        name
        value
        __typename
      }
      comments
      __typename
    }
    descriptions {
      main
      shop {
        text
        html
        short
        __typename
      }
      __typename
    }
    data {
      title
      images {
        uri
        alternative {
          uri
          __typename
        }
        __typename
      }
      genres
      styles
      cat
      releaseDate
      tracklist {
        type_
        title
        artists {
          name
          id
          anv
          __typename
        }
        uri
        duration
        position
        __typename
      }
      formats {
        descriptions
        name
        qty
        __typename
      }
      country
      artists {
        name
        anv
        id
        join
        __typename
      }
      labels {
        name
        id
        catno
        __typename
      }
      videos {
        uri
        __typename
      }
      __typename
    }
    __typename
  }
}
"""

_CONDITION_MAP = {
    "mint": "M",
    "near mint": "NM",
    "near mint minus": "NM",
    "excellent": "EX",
    "very good plus": "VG+",
    "very good": "VG",
    "good plus": "G+",
    "good": "G",
    "fair": "F",
    "poor": "P",
}

JsonDict = dict[str, Any]


def _join_artists(artists: list[JsonDict]) -> str:
    parts: list[str] = []
    for artist in artists:
        name = (artist.get("anv") or artist.get("name") or "").strip()
        if not name:
            continue
        parts.append(name)
        join = (artist.get("join") or "").strip()
        if join:
            parts.append(join)
    return " ".join(parts).strip()


def _to_decimal(value: float | int | str | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _is_vinyl(item_data: JsonDict) -> bool:
    formats = item_data.get("formats") or []
    return any((fmt.get("name") or "").lower() == "vinyl" for fmt in formats)


def _normalize_condition(value: str | None) -> str | None:
    if not value:
        return None

    value = value.strip()
    paren_match = re.search(r"\(([A-Z][A-Z+\-]*)\)", value)
    if paren_match:
        code = paren_match.group(1).upper()
        if code in {"M", "NM", "EX", "VG+", "VG", "G+", "G", "F", "P"}:
            return code

    lowered = value.lower().strip()
    for needle, mapped in _CONDITION_MAP.items():
        if needle in lowered:
            return mapped

    upper = value.upper()
    if upper in {"M", "NM", "EX", "VG+", "VG", "G+", "G", "F", "P"}:
        return upper

    return None


def _extract_condition(listings: list[JsonDict]) -> str | None:
    for listing in listings:
        for option in listing.get("options") or []:
            name = (option.get("name") or "").lower()
            if name == "media condition":
                return _normalize_condition(option.get("value"))
    for listing in listings:
        for option in listing.get("options") or []:
            normalized = _normalize_condition(option.get("value"))
            if normalized:
                return normalized
    return None


def _extract_label(labels: list[JsonDict]) -> tuple[str | None, str | None]:
    if not labels:
        return None, None
    first = labels[0]
    return first.get("name") or None, first.get("catno") or None


def _extract_year(release_date_ms: int | None) -> int | None:
    if not release_date_ms:
        return None
    try:
        return datetime.fromtimestamp(release_date_ms / 1000, UTC).year
    except (OSError, OverflowError, ValueError):
        return None


def _build_detail_url(item: JsonDict) -> str:
    return item.get("uri") or f"{BASE_URL}{item.get('path', '')}"


@register_scraper("vodkast")
class VodkastScraper(BaseScraper):
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers=_GRAPHQL_HEADERS,
            follow_redirects=True,
        )
        self._total_pages: int | None = None

    async def _graphql(self, operation_name: str, query: str, variables: JsonDict) -> JsonDict:
        resp = await request_with_retry(
            self._client,
            "POST",
            GRAPHQL_URL,
            json={
                "operationName": operation_name,
                "variables": variables,
                "query": query,
            },
        )
        resp.raise_for_status()
        payload = cast(JsonDict, resp.json())
        if payload.get("errors"):
            raise RuntimeError(f"Vodkast GraphQL error: {payload['errors']}")
        return cast(JsonDict, payload["data"])

    async def get_total_pages(self) -> int | None:
        if self._total_pages is not None:
            return self._total_pages

        data = await self._graphql(
            "inventoryFiltersPagination",
            _PAGINATION_QUERY,
            {"filters": _FILTERS, "pagination": {"limit": PAGE_SIZE}},
        )
        self._total_pages = data["inventoryFiltersPagination"]["pages"]
        return self._total_pages

    async def scrape_listing(self, page: int) -> list[ScrapedVinylListing]:
        total_pages = await self.get_total_pages()
        if total_pages is not None and page > total_pages:
            return []

        logger.info("Scraping vodkast listing page %d via GraphQL", page)
        data = await self._graphql(
            "inventoryItems",
            _LISTING_QUERY,
            {
                "filters": _FILTERS,
                "pagination": {
                    "page": page,
                    "sort": "added",
                    "order": -1,
                    "limit": PAGE_SIZE,
                },
            },
        )

        items = data["inventoryItems"]["items"]
        results: list[ScrapedVinylListing] = []
        for item in items:
            item_data = item.get("data") or {}
            if not _is_vinyl(item_data):
                continue

            listings = item.get("listings") or []
            first_listing = listings[0] if listings else {}
            price = _to_decimal(((first_listing.get("prices") or {}).get("sale")))
            quantity = ((first_listing.get("stock") or {}).get("quantity")) or 0
            images = item_data.get("images") or []
            artist = _join_artists(item_data.get("artists") or [])

            results.append(
                ScrapedVinylListing(
                    title=(item_data.get("title") or "").strip(),
                    artist=artist,
                    price=price,
                    currency="GEL",
                    image_url=(images[0].get("uri") if images else None),
                    detail_url=_build_detail_url(item),
                    in_stock=quantity > 0,
                )
            )

        return results

    async def scrape_detail(self, url: str) -> ScrapedVinylDetail:
        match = re.search(r"/release/(\d+)/", url)
        if not match:
            raise ValueError(f"Could not extract release id from URL: {url}")
        release_id = float(match.group(1))

        logger.info("Scraping vodkast detail for release %s via GraphQL", match.group(1))
        data = await self._graphql("item", _DETAIL_QUERY, {"id": release_id})
        item = data["item"]
        item_data = item.get("data") or {}
        if not _is_vinyl(item_data):
            raise ValueError(f"Item is not a vinyl release: {url}")

        listings = item.get("listings") or []
        first_listing = listings[0] if listings else {}
        quantity = ((first_listing.get("stock") or {}).get("quantity")) or 0
        images = item_data.get("images") or []
        label, catalog_number = _extract_label(item_data.get("labels") or [])
        genres = list(
            dict.fromkeys((item_data.get("genres") or []) + (item_data.get("styles") or []))
        )
        videos = item_data.get("videos") or []

        tracklist = [
            ScrapedTrack(
                position=(track.get("position") or "").strip(),
                title=(track.get("title") or "").strip(),
                duration=(track.get("duration") or None),
            )
            for track in item_data.get("tracklist") or []
            if (track.get("position") or "").strip() or (track.get("title") or "").strip()
        ]

        return ScrapedVinylDetail(
            title=(item_data.get("title") or "").strip(),
            artist=_join_artists(item_data.get("artists") or []),
            price=_to_decimal(((first_listing.get("prices") or {}).get("sale"))),
            currency="GEL",
            image_url=(images[0].get("uri") if images else None),
            detail_url=_build_detail_url(item),
            in_stock=quantity > 0,
            label=label,
            catalog_number=catalog_number,
            year=_extract_year(item_data.get("releaseDate")),
            condition=_extract_condition(listings),
            genres=genres,
            tracklist=tracklist,
            youtube_url=(videos[0].get("uri") if videos else None),
        )

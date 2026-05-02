"""Zoopla scraper.

Zoopla serves Cloudflare challenges to many bot-shaped requests. We try once
politely; if the response looks like a challenge or comes back empty of expected
markers, we log and return []. We do not escalate to headless browsers — that's
out of scope per CLAUDE.md.

Listing data is in a `__NEXT_DATA__` JSON blob in the page source.
"""

import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

import httpx
from selectolax.parser import HTMLParser

from .. import config
from .base import Listing

log = logging.getLogger(__name__)

SEARCH_URL = "https://www.zoopla.co.uk/to-rent/property/oxford/"
NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', re.DOTALL
)


def _cache_path(url: str) -> Path:
    digest = hashlib.sha1(url.encode()).hexdigest()[:16]
    return config.CACHE_DIR / "zoopla" / f"{digest}.html"


def _looks_like_cloudflare(html: str) -> bool:
    markers = ["cf-browser-verification", "Just a moment...", "challenge-platform"]
    return any(m in html for m in markers)


class ZooplaScraper:
    name = "zoopla"

    def __init__(self, *, use_cache: bool = False, sleep_s: float = 2.0,
                 max_pages: int = 3):
        self.use_cache = use_cache
        self.sleep_s = sleep_s
        self.max_pages = max_pages

    def _fetch_html(self, client: httpx.Client, url: str,
                    params: Optional[dict] = None) -> Optional[str]:
        cache = _cache_path(url + str(params or {}))
        if self.use_cache and cache.exists():
            return cache.read_text()
        try:
            r = client.get(url, params=params)
        except httpx.HTTPError as e:
            log.warning("zoopla: HTTP error %s for %s", e, url)
            return None
        if r.status_code in (403, 429):
            log.warning("zoopla: %s %s — likely blocked", r.status_code, url)
            return None
        if r.status_code >= 400:
            log.warning("zoopla: %s %s", r.status_code, url)
            return None
        if _looks_like_cloudflare(r.text):
            log.warning("zoopla: cloudflare challenge detected — skipping")
            return None
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(r.text)
        time.sleep(self.sleep_s)
        return r.text

    def fetch(self) -> list[Listing]:
        listings: list[Listing] = []
        with httpx.Client(
            timeout=20.0,
            headers={
                "User-Agent": config.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-GB,en;q=0.9",
            },
            follow_redirects=True,
        ) as client:
            for page in range(1, self.max_pages + 1):
                params = {
                    "beds_min": 1, "beds_max": 3,
                    "price_max": 2200, "price_frequency": "per_month",
                    "page_size": 25, "pn": page,
                }
                html = self._fetch_html(client, SEARCH_URL, params)
                if html is None:
                    break
                page_listings = self._parse(html)
                if not page_listings:
                    break
                listings.extend(page_listings)
        log.info("zoopla: parsed %d listings", len(listings))
        return listings

    def _parse(self, html: str) -> list[Listing]:
        m = NEXT_DATA_RE.search(html)
        if not m:
            log.warning("zoopla: no __NEXT_DATA__ in HTML")
            return []
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            log.warning("zoopla: malformed __NEXT_DATA__ JSON")
            return []

        results = self._extract_results(data)
        listings: list[Listing] = []
        for item in results:
            listing_id = item.get("listingId") or item.get("id")
            if not listing_id:
                continue
            address = item.get("address") or ""
            postcode = self._guess_postcode(item, address)
            listings.append(
                Listing(
                    id=f"zoopla:{listing_id}",
                    source="zoopla",
                    url=f"https://www.zoopla.co.uk/to-rent/details/{listing_id}/",
                    title=item.get("title") or address,
                    address=address,
                    postcode=postcode,
                    bedrooms=item.get("bedrooms") or item.get("numBedrooms"),
                    monthly_rent_gbp=self._monthly_price(item),
                    raw={"zoopla_id": listing_id},
                )
            )
        return listings

    @staticmethod
    def _extract_results(data: dict) -> list[dict]:
        # Zoopla nests results deeply and varies between releases.
        # Walk the JSON and pull anything that looks like a listing.
        out: list[dict] = []

        def walk(node):
            if isinstance(node, dict):
                if ("listingId" in node or "numBedrooms" in node) and "address" in node:
                    out.append(node)
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(data)
        return out

    @staticmethod
    def _guess_postcode(item: dict, address: str) -> Optional[str]:
        from .openrent import _POSTCODE_RE  # reuse same pattern
        for key in ("postcode", "outcode"):
            if key in item and item[key]:
                return item[key]
        m = _POSTCODE_RE.search(address)
        return m.group(1) if m else None

    @staticmethod
    def _monthly_price(item: dict) -> Optional[int]:
        for key in ("rentMonthly", "priceMonthly", "monthlyPrice"):
            if key in item and item[key]:
                try:
                    return int(item[key])
                except (TypeError, ValueError):
                    pass
        price = item.get("price") or item.get("displayPrice")
        if isinstance(price, (int, float)):
            return int(price)
        if isinstance(price, str):
            m = re.search(r"£\s*([\d,]+)", price)
            if m:
                return int(m.group(1).replace(",", ""))
        return None


# Used by HTMLParser-based fallbacks if we ever add one
_ = HTMLParser  # keep import alive for future structured fallbacks

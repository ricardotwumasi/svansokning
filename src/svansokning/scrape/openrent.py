"""OpenRent scraper.

OpenRent embeds property data as JS array literals in their search-result HTML.
We parse those arrays and zip them into Listing records. If their page structure
changes, this scraper will fail loud (logged + empty list) rather than half-parse.
"""

import hashlib
import logging
import re
import time
from pathlib import Path
from typing import Optional

import httpx

from .. import config
from .base import Listing

log = logging.getLogger(__name__)

SEARCH_URL = "https://www.openrent.co.uk/properties-to-rent/oxford"
PARAMS = {"term": "Oxford, UK"}

JS_ARRAYS = {
    "ids": re.compile(r"PROPERTYIDS\s*=\s*\[([^\]]*)\]"),
    "titles": re.compile(r"PROPERTYTITLES\s*=\s*\[([^\]]*)\]"),
    "prices": re.compile(r"PROPERTYPRICES\s*=\s*\[([^\]]*)\]"),
    "bedrooms": re.compile(r"PROPERTYBEDROOMS\s*=\s*\[([^\]]*)\]"),
    "bullet_points": re.compile(r"PROPERTYBULLETS\s*=\s*\[([^\]]*)\]"),
    "lats": re.compile(r"PROPERTYLATITUDES\s*=\s*\[([^\]]*)\]"),
    "lons": re.compile(r"PROPERTYLONGITUDES\s*=\s*\[([^\]]*)\]"),
}

_POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2})\b")


def _split_js_array(blob: str) -> list[str]:
    out, buf, in_str = [], [], False
    for ch in blob:
        if ch == "'":
            in_str = not in_str
            continue
        if ch == "," and not in_str:
            out.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if buf:
        out.append("".join(buf).strip())
    return out


def _to_int(s: str) -> Optional[int]:
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return None


def _cache_path(url: str) -> Path:
    digest = hashlib.sha1(url.encode()).hexdigest()[:16]
    return config.CACHE_DIR / "openrent" / f"{digest}.html"


class OpenRentScraper:
    name = "openrent"

    def __init__(self, *, use_cache: bool = False, sleep_s: float = 1.0):
        self.use_cache = use_cache
        self.sleep_s = sleep_s

    def _fetch_html(self, client: httpx.Client, url: str, params: Optional[dict] = None) -> str:
        cache = _cache_path(url + str(params or {}))
        if self.use_cache and cache.exists():
            return cache.read_text()
        r = client.get(url, params=params)
        r.raise_for_status()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(r.text)
        time.sleep(self.sleep_s)
        return r.text

    def fetch(self) -> list[Listing]:
        with httpx.Client(
            timeout=20.0,
            headers={"User-Agent": config.USER_AGENT, "Accept": "text/html"},
            follow_redirects=True,
        ) as client:
            html = self._fetch_html(client, SEARCH_URL, PARAMS)
            return self._parse(html)

    def _parse(self, html: str) -> list[Listing]:
        arrays = {}
        for key, pattern in JS_ARRAYS.items():
            m = pattern.search(html)
            arrays[key] = _split_js_array(m.group(1)) if m else []

        ids = arrays.get("ids", [])
        if not ids:
            log.warning("openrent: no PROPERTYIDS found in HTML — site structure may have changed")
            return []

        titles = arrays.get("titles", [])
        prices = arrays.get("prices", [])
        beds = arrays.get("bedrooms", [])
        bullets = arrays.get("bullet_points", [])
        lats = arrays.get("lats", [])
        lons = arrays.get("lons", [])

        n = len(ids)
        listings: list[Listing] = []
        for i in range(n):
            pid = ids[i].strip("'\" ")
            if not pid:
                continue
            title = titles[i].strip("'\" ") if i < len(titles) else ""
            price = _to_int(prices[i]) if i < len(prices) else None
            bedrooms = _to_int(beds[i]) if i < len(beds) else None
            bullet = bullets[i].strip("'\" ") if i < len(bullets) else ""
            lat = _to_int(lats[i]) if i < len(lats) else None  # OpenRent stores * 1e6 sometimes
            lon = _to_int(lons[i]) if i < len(lons) else None

            postcode_match = _POSTCODE_RE.search(title) or _POSTCODE_RE.search(bullet)
            postcode = postcode_match.group(1) if postcode_match else None

            listings.append(
                Listing(
                    id=f"openrent:{pid}",
                    source="openrent",
                    url=f"https://www.openrent.co.uk/{pid}",
                    title=title,
                    address=bullet,
                    postcode=postcode,
                    bedrooms=bedrooms,
                    monthly_rent_gbp=price,
                    raw={"openrent_id": pid, "lat_raw": lat, "lon_raw": lon},
                )
            )
        log.info("openrent: parsed %d listings", len(listings))
        return listings

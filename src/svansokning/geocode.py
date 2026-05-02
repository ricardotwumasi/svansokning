import re
from typing import Optional

import httpx

from . import config, storage

POSTCODES_API = "https://api.postcodes.io/postcodes"
_POSTCODE_RE = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$", re.IGNORECASE)


def normalise_postcode(pc: Optional[str]) -> Optional[str]:
    if not pc:
        return None
    pc = pc.strip().upper()
    if not _POSTCODE_RE.match(pc):
        return None
    pc = pc.replace(" ", "")
    return pc[:-3] + " " + pc[-3:]


def _load_cache() -> dict:
    return storage.read_json(config.GEOCODE_CACHE, {})


def _save_cache(cache: dict) -> None:
    storage.write_json(config.GEOCODE_CACHE, cache)


def geocode_one(postcode: str, *, client: Optional[httpx.Client] = None,
                cache: Optional[dict] = None) -> Optional[tuple[float, float]]:
    pc = normalise_postcode(postcode)
    if pc is None:
        return None
    if cache is not None and pc in cache:
        entry = cache[pc]
        if entry is None:
            return None
        return (entry["lat"], entry["lon"])
    own_client = client is None
    client = client or httpx.Client(timeout=10.0, headers={"User-Agent": config.USER_AGENT})
    try:
        r = client.get(f"{POSTCODES_API}/{pc.replace(' ', '%20')}")
        if r.status_code == 404:
            result = None
        else:
            r.raise_for_status()
            data = r.json().get("result") or {}
            lat, lon = data.get("latitude"), data.get("longitude")
            result = (lat, lon) if lat is not None and lon is not None else None
    finally:
        if own_client:
            client.close()
    if cache is not None:
        cache[pc] = {"lat": result[0], "lon": result[1]} if result else None
    return result


def geocode_many(postcodes: list[str]) -> dict[str, Optional[tuple[float, float]]]:
    cache = _load_cache()
    out: dict[str, Optional[tuple[float, float]]] = {}
    with httpx.Client(timeout=10.0, headers={"User-Agent": config.USER_AGENT}) as client:
        for raw_pc in postcodes:
            out[raw_pc] = geocode_one(raw_pc, client=client, cache=cache)
    _save_cache(cache)
    return out

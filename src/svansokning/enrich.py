import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Iterable

import pandas as pd

from . import constants, geocode, storage
from .distance import haversine_km
from .scrape.base import Listing

log = logging.getLogger(__name__)


def listings_to_df(listings: Iterable[Listing]) -> pd.DataFrame:
    rows = []
    for listing in listings:
        d = asdict(listing)
        d["raw"] = json.dumps(d.get("raw") or {})
        rows.append(d)
    if not rows:
        return storage.empty_listings()
    return pd.DataFrame(rows)


def _resolve_anchor(anchor_postcode: str, cache: dict) -> tuple[float, float] | None:
    return geocode.geocode_one(anchor_postcode, cache=cache)


def enrich(
    new_listings: Iterable[Listing],
    *,
    anchor_postcode: str = constants.DEFAULT_ANCHOR["postcode"],
    now: datetime | None = None,
) -> pd.DataFrame:
    """Geocode + add distance columns + merge with prior state."""
    now = now or datetime.now(timezone.utc)
    new_df = listings_to_df(new_listings)
    if new_df.empty:
        prior = storage.read_listings()
        return prior

    postcodes = [pc for pc in new_df["postcode"].dropna().unique() if pc]
    geo = geocode.geocode_many(list(postcodes))

    # also geocode the reference points + anchor
    ref_geo = geocode.geocode_many(
        [constants.REFERENCE_POINTS["oxford_station"]["postcode"],
         constants.REFERENCE_POINTS["andrew_wiles"]["postcode"],
         anchor_postcode]
    )
    station_pt = ref_geo.get(constants.REFERENCE_POINTS["oxford_station"]["postcode"])
    aw_pt = ref_geo.get(constants.REFERENCE_POINTS["andrew_wiles"]["postcode"])
    anchor_pt = ref_geo.get(anchor_postcode)

    def lookup(pc):
        if pc and pc in geo and geo[pc]:
            return geo[pc]
        return (None, None)

    coords = new_df["postcode"].map(lookup)
    new_df["lat"] = [c[0] for c in coords]
    new_df["lon"] = [c[1] for c in coords]

    def dist_to(pt):
        if pt is None:
            return [None] * len(new_df)
        return [
            haversine_km(lat, lon, pt[0], pt[1]) if lat is not None and lon is not None else None
            for lat, lon in zip(new_df["lat"], new_df["lon"])
        ]

    new_df["dist_station_km"] = dist_to(station_pt)
    new_df["dist_andrew_wiles_km"] = dist_to(aw_pt)
    new_df["dist_anchor_km"] = dist_to(anchor_pt)

    new_df["first_seen_at"] = now
    new_df["last_seen_at"] = now
    new_df["let_agreed"] = new_df.get("let_agreed", False)

    return _merge_with_prior(new_df, now)


def _merge_with_prior(new_df: pd.DataFrame, now: datetime) -> pd.DataFrame:
    prior = storage.read_listings()
    if prior.empty:
        return _coerce_schema(new_df)

    prior = prior.set_index("id", drop=False)
    new_df_idx = new_df.set_index("id", drop=False)

    overlap = new_df_idx.index.intersection(prior.index)
    only_new = new_df_idx.index.difference(prior.index)
    only_prior = prior.index.difference(new_df_idx.index)

    # for overlap: keep prior first_seen_at, take new everything-else, set last_seen_at = now
    merged_overlap = new_df_idx.loc[overlap].copy()
    merged_overlap["first_seen_at"] = prior.loc[overlap, "first_seen_at"].values
    merged_overlap["last_seen_at"] = now

    # only_new: already has first_seen_at = now
    merged_new = new_df_idx.loc[only_new]

    # only_prior: untouched (keep history; their last_seen_at stays as before)
    untouched = prior.loc[only_prior]

    out = pd.concat([merged_overlap, merged_new, untouched], ignore_index=True)
    return _coerce_schema(out)


def _coerce_schema(df: pd.DataFrame) -> pd.DataFrame:
    template = storage.empty_listings()
    for col, dtype in storage.LISTINGS_SCHEMA.items():
        if col not in df.columns:
            df[col] = pd.Series([None] * len(df), dtype=dtype)
    df = df[list(template.columns)]
    for col, dtype in storage.LISTINGS_SCHEMA.items():
        try:
            df[col] = df[col].astype(dtype)
        except (TypeError, ValueError):
            pass
    return df.reset_index(drop=True)

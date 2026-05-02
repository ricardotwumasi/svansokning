"""Test the merge logic preserves first_seen_at and updates last_seen_at."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pandas as pd

from svansokning import enrich, geocode, storage
from svansokning.scrape.base import Listing


def _patched_geocode_many(postcodes):
    # Pretend every postcode is at the same point — distances all zero — keeps
    # tests offline + deterministic. The merge logic doesn't depend on coords.
    return {pc: (51.76, -1.26) for pc in postcodes}


def _make_listing(pid: str, rent: int = 1500) -> Listing:
    return Listing(
        id=f"openrent:{pid}",
        source="openrent",
        url=f"https://example.com/{pid}",
        title=f"Listing {pid}",
        address="123 Walton St",
        postcode="OX2 6BS",
        bedrooms=2,
        monthly_rent_gbp=rent,
    )


def test_first_seen_at_preserved_across_runs(tmp_path, monkeypatch):
    # redirect data dir to tmp
    monkeypatch.setattr(enrich.storage.config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(enrich.storage.config, "LISTINGS_PARQUET", tmp_path / "listings.parquet")
    monkeypatch.setattr(enrich.storage.config, "GEOCODE_CACHE", tmp_path / "geocode.json")
    monkeypatch.setattr(geocode, "geocode_many", _patched_geocode_many)
    monkeypatch.setattr(geocode, "geocode_one", lambda pc, **kw: (51.76, -1.26))

    day1 = datetime(2026, 5, 1, tzinfo=timezone.utc)
    day2 = day1 + timedelta(days=1)

    # Day 1: see listing "1"
    df1 = enrich.enrich([_make_listing("1")], now=day1)
    storage.write_listings(df1)
    assert len(df1) == 1
    assert df1.iloc[0]["first_seen_at"] == pd.Timestamp(day1)
    assert df1.iloc[0]["last_seen_at"] == pd.Timestamp(day1)

    # Day 2: still see "1", and a new "2"
    df2 = enrich.enrich([_make_listing("1"), _make_listing("2")], now=day2)
    storage.write_listings(df2)
    assert len(df2) == 2
    listing1 = df2[df2["id"] == "openrent:1"].iloc[0]
    listing2 = df2[df2["id"] == "openrent:2"].iloc[0]
    assert listing1["first_seen_at"] == pd.Timestamp(day1)  # preserved
    assert listing1["last_seen_at"] == pd.Timestamp(day2)   # bumped
    assert listing2["first_seen_at"] == pd.Timestamp(day2)  # new


def test_disappeared_listings_kept_with_old_last_seen(tmp_path, monkeypatch):
    monkeypatch.setattr(enrich.storage.config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(enrich.storage.config, "LISTINGS_PARQUET", tmp_path / "listings.parquet")
    monkeypatch.setattr(enrich.storage.config, "GEOCODE_CACHE", tmp_path / "geocode.json")
    monkeypatch.setattr(geocode, "geocode_many", _patched_geocode_many)
    monkeypatch.setattr(geocode, "geocode_one", lambda pc, **kw: (51.76, -1.26))

    day1 = datetime(2026, 5, 1, tzinfo=timezone.utc)
    day2 = day1 + timedelta(days=1)

    df1 = enrich.enrich([_make_listing("gone")], now=day1)
    storage.write_listings(df1)

    df2 = enrich.enrich([_make_listing("new_one")], now=day2)
    assert len(df2) == 2
    gone = df2[df2["id"] == "openrent:gone"].iloc[0]
    assert gone["last_seen_at"] == pd.Timestamp(day1)  # not bumped

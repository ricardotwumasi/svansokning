import json
from pathlib import Path

import pandas as pd

from . import config

LISTINGS_SCHEMA: dict[str, str] = {
    "id": "string",
    "source": "string",
    "url": "string",
    "first_seen_at": "datetime64[ns, UTC]",
    "last_seen_at": "datetime64[ns, UTC]",
    "postcode": "string",
    "lat": "float64",
    "lon": "float64",
    "bedrooms": "Int64",
    "monthly_rent_gbp": "Int64",
    "dist_station_km": "float64",
    "dist_andrew_wiles_km": "float64",
    "dist_anchor_km": "float64",
    "title": "string",
    "address": "string",
    "available_from": "string",
    "furnished": "string",
    "let_agreed": "boolean",
    "raw": "string",
}


def empty_listings() -> pd.DataFrame:
    return pd.DataFrame({col: pd.Series(dtype=dt) for col, dt in LISTINGS_SCHEMA.items()})


def read_listings() -> pd.DataFrame:
    if not config.LISTINGS_PARQUET.exists():
        return empty_listings()
    return pd.read_parquet(config.LISTINGS_PARQUET)


def write_listings(df: pd.DataFrame) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(config.LISTINGS_PARQUET, index=False)


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str))

import pandas as pd

from svansokning.filters import apply_criteria
from svansokning.storage import empty_listings


def _df(rows):
    base = empty_listings()
    return pd.concat([base, pd.DataFrame(rows)], ignore_index=True)


def test_empty_in_empty_out():
    out = apply_criteria(empty_listings(), {"max_rent_gbp": 2000})
    assert out.empty


def test_filters_by_rent_and_bedrooms():
    df = _df([
        {"id": "a", "source": "openrent", "bedrooms": 2, "monthly_rent_gbp": 1500, "dist_anchor_km": 1.0},
        {"id": "b", "source": "openrent", "bedrooms": 1, "monthly_rent_gbp": 2400, "dist_anchor_km": 1.0},
        {"id": "c", "source": "openrent", "bedrooms": 4, "monthly_rent_gbp": 1800, "dist_anchor_km": 1.0},
    ])
    out = apply_criteria(df, {
        "min_bedrooms": 1, "max_bedrooms": 3,
        "max_rent_gbp": 2200, "max_radius_km": 5.0,
    })
    assert set(out["id"]) == {"a"}


def test_filters_by_radius():
    df = _df([
        {"id": "near", "source": "x", "bedrooms": 2, "monthly_rent_gbp": 1500, "dist_anchor_km": 1.0},
        {"id": "far", "source": "x", "bedrooms": 2, "monthly_rent_gbp": 1500, "dist_anchor_km": 9.0},
    ])
    out = apply_criteria(df, {"max_radius_km": 3.0})
    assert set(out["id"]) == {"near"}


def test_filters_by_source():
    df = _df([
        {"id": "a", "source": "openrent", "bedrooms": 2, "monthly_rent_gbp": 1500, "dist_anchor_km": 1.0},
        {"id": "b", "source": "zoopla", "bedrooms": 2, "monthly_rent_gbp": 1500, "dist_anchor_km": 1.0},
    ])
    out = apply_criteria(df, {"sources_enabled": ["openrent"]})
    assert set(out["id"]) == {"a"}

import pandas as pd


def apply_criteria(df: pd.DataFrame, criteria: dict) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()

    sources = criteria.get("sources_enabled")
    if sources:
        out = out[out["source"].isin(sources)]

    if "min_bedrooms" in criteria:
        out = out[out["bedrooms"] >= criteria["min_bedrooms"]]
    if "max_bedrooms" in criteria:
        out = out[out["bedrooms"] <= criteria["max_bedrooms"]]

    if "max_rent_gbp" in criteria:
        out = out[out["monthly_rent_gbp"] <= criteria["max_rent_gbp"]]

    if "max_radius_km" in criteria:
        out = out[out["dist_anchor_km"] <= criteria["max_radius_km"]]

    return out.reset_index(drop=True)
